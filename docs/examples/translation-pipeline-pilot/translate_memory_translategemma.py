#!/usr/bin/env python3
"""Create keyed English-to-Russian drafts with TranslateGemma.

Drafts live in a separate table; the production translation is updated only by the
subsequent contextual editorial pass.
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / ".temporary-tools"))

from translate_memory import connect, exact_glossary_translation, load_glossary, utc_now
from translate_memory_local import preserve_text_segment


ENDPOINT = "http://127.0.0.1:11435/api/generate"
MODEL = "translategemma:12b"
PROVIDER = "translategemma-12b-page-glossary-v1"
MARKER_RE = re.compile(r"<<<(P\d{4}-B\d{3})>>>\s*")
LAYOUT_PAGE_RE = re.compile(r"([ivxlcdm]+|\d+)\s*$", re.I)
NUMBER_TOKEN_RE = re.compile(r"\b\d+(?:[.-]\d+)*\b")
PROTECTED_NUMBER_RE = re.compile(r"ZXQNUM[A-Z]+")


class IncompleteTranslation(ValueError):
    pass


class FragmentNeedsReview(RuntimeError):
    def __init__(self, segment_key: str, attempts: int, issues: list[str]) -> None:
        self.segment_key = segment_key
        self.attempts = attempts
        self.issues = issues
        super().__init__(f"{segment_key}: {','.join(issues)}")


def normalize(text: str) -> str:
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]
    text = "\n".join(line for line in lines if line)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def token_counter(text: str) -> Counter[str]:
    return Counter(NUMBER_TOKEN_RE.findall(text))


def _alphabetic_label(number: int) -> str:
    result = ""
    while number:
        number, remainder = divmod(number - 1, 26)
        result = chr(ord("A") + remainder) + result
    return result


def protect_numbers(text: str) -> tuple[str, dict[str, str]]:
    mapping: dict[str, str] = {}

    def replace(match: re.Match[str]) -> str:
        marker = "ZXQNUM" + _alphabetic_label(len(mapping) + 1)
        mapping[marker] = match.group(0)
        return marker

    return NUMBER_TOKEN_RE.sub(replace, text), mapping


def restore_protected_tokens(text: str, mapping: dict[str, str]) -> str:
    for marker, value in mapping.items():
        text = text.replace(marker, value)
    return text


def split_layout_suffix(line: str) -> tuple[str, str] | None:
    """Return (title, page label) for a contents-style line.

    PDF extraction represents leaders either as spaced dots (``. . .``) or a
    wide whitespace run. Inspecting only the trailing separator avoids the
    pathological backtracking caused by a single all-purpose regex.
    """
    page = LAYOUT_PAGE_RE.search(line)
    if not page:
        return None
    prefix = line[:page.start()]
    separator = re.search(r"[.\t ]+$", prefix)
    if not separator:
        return None
    leader = separator.group(0)
    if leader.count(".") < 2 and not re.search(r"[\t ]{3,}", leader):
        return None
    title = prefix[:separator.start()].strip()
    return (title, page.group(1)) if title else None


def layout_suffix_counter(text: str) -> Counter[str]:
    values: list[str] = []
    for line in text.splitlines():
        match = split_layout_suffix(line.strip())
        if match:
            values.append(match[1].casefold())
    return Counter(values)


def covers(required: Counter[str], actual: Counter[str]) -> bool:
    return all(actual[token] >= count for token, count in required.items())


def completeness_issues(source: str, translation: str) -> list[str]:
    issues: list[str] = []
    source_letters = len(re.findall(r"[A-Za-z]", source))
    target_letters = len(re.findall(r"[A-Za-zА-Яа-яЁё]", translation))
    if source_letters >= 100 and target_letters < source_letters * 0.42:
        issues.append(f"short:{target_letters}/{source_letters}")
    if not covers(token_counter(source), token_counter(translation)):
        missing = token_counter(source) - token_counter(translation)
        issues.append("missing-numbers:" + ",".join(missing.elements()))
    required_suffixes = layout_suffix_counter(source)
    if required_suffixes and not covers(required_suffixes, layout_suffix_counter(translation)):
        missing = required_suffixes - layout_suffix_counter(translation)
        issues.append("missing-layout-suffixes:" + ",".join(missing.elements()))
    if required_suffixes:
        source_lines = [line for line in source.splitlines() if line.strip()]
        target_lines = [line for line in translation.splitlines() if line.strip()]
        if len(target_lines) != len(source_lines):
            issues.append(f"layout-line-count:{len(target_lines)}/{len(source_lines)}")
    return issues


def ensure_draft_table(db: sqlite3.Connection) -> None:
    db.execute(
        """CREATE TABLE IF NOT EXISTS translation_drafts (
               segment_key TEXT PRIMARY KEY REFERENCES segments(segment_key),
               source_hash TEXT NOT NULL,
               translation_text TEXT NOT NULL,
               provider TEXT NOT NULL,
               updated_at TEXT NOT NULL
           )"""
    )
    db.execute(
        """CREATE TABLE IF NOT EXISTS translation_draft_history (
               history_id INTEGER PRIMARY KEY AUTOINCREMENT,
               segment_key TEXT NOT NULL,
               source_hash TEXT NOT NULL,
               translation_text TEXT NOT NULL,
               provider TEXT NOT NULL,
               reason TEXT NOT NULL,
               archived_at TEXT NOT NULL
           )"""
    )
    db.execute(
        """CREATE TABLE IF NOT EXISTS translation_attempts (
               attempt_id INTEGER PRIMARY KEY AUTOINCREMENT,
               segment_key TEXT NOT NULL,
               source_hash TEXT NOT NULL,
               attempt_no INTEGER NOT NULL,
               prompt_version TEXT NOT NULL,
               response_text TEXT NOT NULL,
               issues_json TEXT NOT NULL,
               elapsed_seconds REAL NOT NULL,
               created_at TEXT NOT NULL
           )"""
    )
    db.execute(
        """CREATE TABLE IF NOT EXISTS translation_review_queue (
               segment_key TEXT NOT NULL,
               source_hash TEXT NOT NULL,
               attempts INTEGER NOT NULL,
               reason TEXT NOT NULL,
               status TEXT NOT NULL,
               updated_at TEXT NOT NULL,
               PRIMARY KEY(segment_key, source_hash)
           )"""
    )
    db.commit()


def record_attempt(
    db: sqlite3.Connection,
    row: sqlite3.Row,
    attempt_no: int,
    prompt_version: str,
    response_text: str,
    issues: list[str],
    elapsed_seconds: float,
) -> None:
    db.execute(
        """INSERT INTO translation_attempts(
               segment_key, source_hash, attempt_no, prompt_version,
               response_text, issues_json, elapsed_seconds, created_at
           ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            row["segment_key"],
            row["source_hash"],
            attempt_no,
            prompt_version,
            response_text,
            json.dumps(issues, ensure_ascii=False),
            elapsed_seconds,
            utc_now(),
        ),
    )
    db.commit()


def mark_needs_review(
    db: sqlite3.Connection,
    row: sqlite3.Row,
    attempts: int,
    reason: str,
) -> None:
    db.execute(
        """INSERT INTO translation_review_queue(
               segment_key, source_hash, attempts, reason, status, updated_at
           ) VALUES (?, ?, ?, ?, 'needs_review', ?)
           ON CONFLICT(segment_key, source_hash) DO UPDATE SET
               attempts=excluded.attempts,
               reason=excluded.reason,
               status=excluded.status,
               updated_at=excluded.updated_at""",
        (row["segment_key"], row["source_hash"], attempts, reason, utc_now()),
    )
    db.commit()


def audit_existing_drafts(db: sqlite3.Connection) -> int:
    rows = list(
        db.execute(
            """SELECT d.*, s.source_text
                 FROM translation_drafts d JOIN segments s USING(segment_key)
                WHERE d.provider=?""",
            (PROVIDER,),
        )
    )
    now = utc_now()
    reset = 0
    for row in rows:
        issues = completeness_issues(row["source_text"], row["translation_text"])
        if not issues:
            continue
        db.execute(
            """INSERT INTO translation_draft_history(
                   segment_key, source_hash, translation_text, provider, reason, archived_at
               ) VALUES (?, ?, ?, ?, ?, ?)""",
            (
                row["segment_key"], row["source_hash"], row["translation_text"],
                row["provider"], ";".join(issues), now,
            ),
        )
        db.execute("DELETE FROM translation_drafts WHERE segment_key=?", (row["segment_key"],))
        print(f"reset incomplete {row['segment_key']}: {','.join(issues)}", flush=True)
        reset += 1
    db.commit()
    return reset


def archive_nllb(db: sqlite3.Connection) -> int:
    rows = list(db.execute("SELECT * FROM segments WHERE provider='nllb-600m-int8+glossary+rules'"))
    now = utc_now()
    for row in rows:
        db.execute(
            """INSERT INTO translation_history(
                   segment_kind, segment_key, translation_text, status, provider, archived_at
               ) VALUES ('text', ?, ?, ?, ?, ?)""",
            (row["segment_key"], row["translation_text"], row["status"], row["provider"], now),
        )
        db.execute(
            "UPDATE segments SET translation_text='', status='new', provider='', updated_at=? WHERE segment_key=?",
            (now, row["segment_key"]),
        )
    db.commit()
    return len(rows)


def archive_editor_sample(db: sqlite3.Connection) -> int:
    rows = list(
        db.execute(
            "SELECT * FROM segments WHERE provider='translategemma-4b+qwen3-8b-editor-v1'"
        )
    )
    now = utc_now()
    for row in rows:
        db.execute(
            """INSERT INTO translation_history(
                   segment_kind, segment_key, translation_text, status, provider, archived_at
               ) VALUES ('text', ?, ?, ?, ?, ?)""",
            (row["segment_key"], row["translation_text"], row["status"], row["provider"], now),
        )
        db.execute(
            "UPDATE segments SET translation_text='', status='new', provider='', updated_at=? WHERE segment_key=?",
            (now, row["segment_key"]),
        )
    db.commit()
    return len(rows)


def reset_machine_drafts(db: sqlite3.Connection) -> int:
    cursor = db.execute(
        "DELETE FROM translation_drafts WHERE provider LIKE 'translategemma-%'"
    )
    db.commit()
    return cursor.rowcount


def relevant_glossary(
    rows: list[sqlite3.Row], terms: list[tuple[str, str]], limit: int = 36
) -> list[tuple[str, str]]:
    source = "\n".join(row["source_text"] for row in rows).casefold()
    result: list[tuple[str, str]] = []
    for english, russian in terms:
        if english.casefold() in source:
            result.append((english, russian))
        if len(result) >= limit:
            break
    return result


def groups(db: sqlite3.Connection, start: int, end: int | None) -> list[list[sqlite3.Row]]:
    params: list[object] = [start]
    where = "s.status='new' AND s.page_number>=? AND d.segment_key IS NULL"
    if end is not None:
        where += " AND s.page_number<=?"
        params.append(end)
    rows = list(
        db.execute(
            f"""SELECT s.* FROM segments s
                LEFT JOIN translation_drafts d
                  ON d.segment_key=s.segment_key AND d.source_hash=s.source_hash
                WHERE {where}
                ORDER BY s.page_number, s.block_number""",
            params,
        )
    )
    # Persist and retry each fragment independently. This prevents one
    # malformed model response from invalidating or blocking a whole page.
    return [[row] for row in rows]


def prompt_for(rows: list[sqlite3.Row], terms: list[tuple[str, str]]) -> str:
    text = "\n\n".join(
        f"<<<{row['segment_key']}>>>\n{row['source_text'].strip()}" for row in rows
    )
    selected_terms = relevant_glossary(rows, terms)
    glossary = "; ".join(f"{english} = {russian}" for english, russian in selected_terms)
    terminology = (
        " Use this mandatory terminology in grammatically correct forms: " + glossary + "."
        if glossary
        else " Preserve protocol names and code identifiers unchanged."
    )
    return f"""You are a professional English (en) to Russian (ru) translator. Your goal is to accurately convey the meaning and nuances of the original English text while adhering to Russian grammar, vocabulary, and cultural sensitivities.
Produce only the Russian translation, without any additional explanations or commentary.{terminology} Keep every marker of the form <<<P0000-B000>>> exactly unchanged and in the same order. Please translate the following English text into Russian:


{text}"""


def terminology_for_text(text: str, terms: list[tuple[str, str]], limit: int = 24) -> str:
    lowered = text.casefold()
    selected = [(en, ru) for en, ru in terms if en.casefold() in lowered][:limit]
    if not selected:
        return "Preserve protocol names, numbers and code identifiers unchanged."
    glossary = "; ".join(f"{english} = {russian}" for english, russian in selected)
    return "Use this mandatory terminology in grammatically correct forms: " + glossary + "."


def plain_prompt(text: str, terms: list[tuple[str, str]]) -> str:
    return f"""You are a professional English (en) to Russian (ru) translator. Your goal is to accurately convey the meaning and nuances of the original English text while adhering to Russian grammar, vocabulary, and cultural sensitivities.
Produce only the Russian translation, without any additional explanations or commentary. {terminology_for_text(text, terms)} Please translate the following English text into Russian:


{text}"""


def fragment_prompt(
    segment_key: str,
    text: str,
    terms: list[tuple[str, str]],
    correction: list[str] | None = None,
    protected: bool = False,
) -> str:
    selected_terms = relevant_glossary(
        [{"source_text": text}],  # type: ignore[list-item]
        terms,
    )
    glossary = "; ".join(f"{english} = {russian}" for english, russian in selected_terms)
    terminology = (
        " Use this mandatory terminology in grammatically correct forms: " + glossary + "."
        if glossary
        else ""
    )
    correction_text = (
        " The previous response failed these checks: " + ", ".join(correction) + "."
        if correction
        else ""
    )
    protected_text = (
        " Preserve every alphabetic placeholder in the source exactly unchanged."
        if protected
        else ""
    )
    return f"""You are a professional English (en) to Russian (ru) translator. Translate exactly one fragment accurately into Russian.
Produce only the marker and Russian translation, without explanations.{terminology} Preserve every number, RFC identifier, protocol name, code identifier, and footnote marker unchanged.{protected_text}{correction_text} Keep the marker <<<{segment_key}>>> exactly unchanged. Do not add any other markers.


<<<{segment_key}>>>
{text.strip()}"""


def _parse_fragment_response(segment_key: str, raw: str) -> str:
    parts = MARKER_RE.split(raw)
    parsed = {
        parts[index]: normalize(parts[index + 1])
        for index in range(1, len(parts) - 1, 2)
    }
    if set(parsed) != {segment_key} or not parsed.get(segment_key):
        raise IncompleteTranslation(
            f"marker mismatch: expected {segment_key}, got {sorted(parsed)}"
        )
    return parsed[segment_key]


AttemptCallback = Callable[[int, str, str, list[str], float], None]


def translate_fragment(
    row: sqlite3.Row,
    terms: list[tuple[str, str]],
    attempt_callback: AttemptCallback,
) -> str:
    source = row["source_text"]
    segment_key = row["segment_key"]
    previous_issues: list[str] | None = None
    strategies = ("single-v1", "corrective-v1", "protected-numbers-v1")

    for attempt_no, prompt_version in enumerate(strategies, 1):
        protected = attempt_no == len(strategies)
        if protected:
            prompt_source, mapping = protect_numbers(source)
        else:
            prompt_source, mapping = source, {}
        payload = {
            "model": MODEL,
            "prompt": fragment_prompt(
                segment_key,
                prompt_source,
                terms,
                correction=previous_issues,
                protected=protected,
            ),
            "stream": False,
            "keep_alive": "30m",
            "options": {
                "temperature": 0,
                "num_ctx": 4096,
                "num_predict": max(180, min(1800, len(source))),
            },
        }
        started = time.monotonic()
        raw = call_payload(payload, retries=4)
        try:
            translated = _parse_fragment_response(segment_key, raw)
            if mapping:
                translated = restore_protected_tokens(translated, mapping)
            issues = completeness_issues(source, translated)
        except IncompleteTranslation as exc:
            translated = raw
            issues = [str(exc)]
        attempt_callback(
            attempt_no,
            prompt_version,
            raw,
            issues,
            time.monotonic() - started,
        )
        if not issues:
            return translated
        previous_issues = issues

    raise FragmentNeedsReview(segment_key, len(strategies), previous_issues or [])


def call_payload(payload: dict[str, object], retries: int = 4) -> str:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    for attempt in range(1, retries + 1):
        try:
            request = urllib.request.Request(
                ENDPOINT, data=body, headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(request, timeout=900) as response:
                outer = json.load(response)
            raw = (outer.get("response") or outer.get("thinking") or "").strip()
            if not raw:
                raise ValueError("empty model response")
            return raw
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError) as exc:
            if attempt == retries:
                raise RuntimeError(f"TranslateGemma request failed: {exc}") from exc
            time.sleep(3 * attempt)
    raise AssertionError("unreachable")


def translate_plain(
    text: str, terms: list[tuple[str, str]], single_line: bool = False
) -> str:
    payload = {
        "model": MODEL,
        "prompt": plain_prompt(text, terms),
        "stream": False,
        "keep_alive": "30m",
        "options": {
            "temperature": 0,
            "num_ctx": 4096,
            "num_predict": max(180, min(1800, len(text))),
        },
    }
    translated = normalize(call_payload(payload, retries=4))
    if single_line:
        # A translation model may offer several alternatives on separate
        # lines. Contents entries must remain one entry, so retain the primary
        # answer and let later editorial QA assess its wording.
        translated = next(
            (line.strip() for line in translated.splitlines() if line.strip()), ""
        )
        if not translated:
            raise IncompleteTranslation("empty single-line translation")
    return translated


def translate_layout_text(
    source: str, terms: list[tuple[str, str]], segment_key: str = "layout"
) -> str:
    lines = [line.strip() for line in source.splitlines() if line.strip()]
    translated_lines: list[str] = []
    for line_number, line in enumerate(lines, 1):
        match = split_layout_suffix(line)
        if match:
            core, suffix = match
            translated = translate_plain(core, terms, single_line=True)
            translated_lines.append(f"{translated} ..... {suffix}")
        else:
            translated_lines.append(translate_plain(line, terms, single_line=True))
        print(
            f"layout {segment_key}: line {line_number}/{len(lines)}",
            flush=True,
        )
    result = "\n".join(translated_lines)
    issues = completeness_issues(source, result)
    if issues:
        raise RuntimeError("layout translation incomplete: " + ",".join(issues))
    return result


def request_translation(
    rows: list[sqlite3.Row], terms: list[tuple[str, str]], retries: int = 4
) -> dict[str, str]:
    # Contents/index blocks need exact line and page-label preservation. Send
    # these lines directly through the deterministic layout path instead of
    # first asking the model to reproduce a large marked block.
    if any(layout_suffix_counter(row["source_text"]) for row in rows):
        result: dict[str, str] = {}
        for row in rows:
            if layout_suffix_counter(row["source_text"]):
                result[row["segment_key"]] = translate_layout_text(
                    row["source_text"], terms, row["segment_key"]
                )
            else:
                result.update(request_translation([row], terms, retries=retries))
        return result

    payload = {
        "model": MODEL,
        "prompt": prompt_for(rows, terms),
        "stream": False,
        "keep_alive": "30m",
        "options": {
            "temperature": 0,
            "num_ctx": 4096,
            "num_predict": max(700, min(5200, sum(len(r["source_text"]) for r in rows))),
        },
    }
    expected = [row["segment_key"] for row in rows]
    for attempt in range(1, retries + 1):
        try:
            raw = call_payload(payload, retries=4)
            parts = MARKER_RE.split(raw)
            parsed = {
                parts[index]: normalize(parts[index + 1])
                for index in range(1, len(parts) - 1, 2)
            }
            if set(parsed) != set(expected) or any(not parsed[key] for key in expected):
                raise IncompleteTranslation(
                    f"marker mismatch: expected {expected}, got {sorted(parsed)}"
                )
            incomplete = {
                row["segment_key"]: completeness_issues(
                    row["source_text"], parsed[row["segment_key"]]
                )
                for row in rows
            }
            incomplete = {key: value for key, value in incomplete.items() if value}
            if incomplete:
                raise IncompleteTranslation(json.dumps(incomplete, ensure_ascii=False))
            return parsed
        except IncompleteTranslation as exc:
            print(f"incomplete group {expected}: {exc}", flush=True)
            if len(rows) > 1:
                combined: dict[str, str] = {}
                for row in rows:
                    combined.update(request_translation([row], terms, retries=2))
                return combined
            row = rows[0]
            source_lines = [line for line in row["source_text"].splitlines() if line.strip()]
            if len(source_lines) >= 2 or split_layout_suffix(row["source_text"].strip()):
                return {
                    row["segment_key"]: translate_layout_text(
                        row["source_text"], terms, row["segment_key"]
                    )
                }
            if attempt == retries:
                raise RuntimeError(f"TranslateGemma failed for {expected}: {exc}") from exc
            time.sleep(3 * attempt)
    raise AssertionError("unreachable")


def save_local_drafts(
    db: sqlite3.Connection, exact: dict[str, str], start: int, end: int | None
) -> int:
    params: list[object] = [start]
    where = "status='new' AND page_number>=?"
    if end is not None:
        where += " AND page_number<=?"
        params.append(end)
    rows = list(db.execute(f"SELECT * FROM segments WHERE {where}", params))
    completed = 0
    now = utc_now()
    for row in rows:
        value = exact_glossary_translation(row["source_text"], exact)
        if value is None and preserve_text_segment(row["source_text"]):
            value = row["source_text"]
        if value is None:
            continue
        db.execute(
            """INSERT INTO translation_drafts(
                   segment_key, source_hash, translation_text, provider, updated_at
               ) VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(segment_key) DO UPDATE SET
                 source_hash=excluded.source_hash,
                 translation_text=excluded.translation_text,
                 provider=excluded.provider,
                 updated_at=excluded.updated_at""",
            (row["segment_key"], row["source_hash"], value, "glossary-or-preserve", now),
        )
        completed += 1
    db.commit()
    return completed


def translate(db: sqlite3.Connection, start: int, end: int | None) -> int:
    exact, terms = load_glossary()
    local = save_local_drafts(db, exact, start, end)
    work = groups(db, start, end)
    completed = local
    for index, rows in enumerate(work, 1):
        row = rows[0]
        started = time.monotonic()

        def save_attempt(
            attempt_no: int,
            prompt_version: str,
            response_text: str,
            issues: list[str],
            elapsed_seconds: float,
        ) -> None:
            record_attempt(
                db,
                row,
                attempt_no,
                prompt_version,
                response_text,
                issues,
                elapsed_seconds,
            )

        try:
            translation = translate_fragment(row, terms, save_attempt)
        except FragmentNeedsReview as exc:
            reason = ";".join(exc.issues)
            mark_needs_review(db, row, exc.attempts, reason)
            print(
                f"needs review {row['segment_key']} page {row['page_number']}: "
                f"attempts={exc.attempts} issues={reason}",
                flush=True,
            )
            continue
        now = utc_now()
        db.execute(
            """INSERT INTO translation_drafts(
                   segment_key, source_hash, translation_text, provider, updated_at
               ) VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(segment_key) DO UPDATE SET
                 source_hash=excluded.source_hash,
                 translation_text=excluded.translation_text,
                 provider=excluded.provider,
                 updated_at=excluded.updated_at""",
            (
                row["segment_key"],
                row["source_hash"],
                translation,
                PROVIDER,
                now,
            ),
        )
        db.execute(
            "DELETE FROM translation_review_queue "
            "WHERE segment_key=? AND source_hash=?",
            (row["segment_key"], row["source_hash"]),
        )
        completed += 1
        db.commit()
        print(
            f"draft fragment {index}/{len(work)} page {row['page_number']} "
            f"key={row['segment_key']}: {time.monotonic() - started:.1f}s, "
            f"total={completed}",
            flush=True,
        )
    return completed


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--end", type=int)
    parser.add_argument("--reset-nllb", action="store_true")
    parser.add_argument("--reset-editor-sample", action="store_true")
    parser.add_argument("--reset-machine-drafts", action="store_true")
    args = parser.parse_args()
    db = connect()
    ensure_draft_table(db)
    if args.reset_nllb:
        print(f"archived_nllb={archive_nllb(db)}", flush=True)
    if args.reset_editor_sample:
        print(f"archived_editor_sample={archive_editor_sample(db)}", flush=True)
    if args.reset_machine_drafts:
        print(f"deleted_machine_drafts={reset_machine_drafts(db)}", flush=True)
    print(f"reset_incomplete_drafts={audit_existing_drafts(db)}", flush=True)
    print(f"drafted={translate(db, args.start, args.end)}", flush=True)
    db.close()


if __name__ == "__main__":
    main()
