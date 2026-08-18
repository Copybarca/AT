#!/usr/bin/env python3
"""Export the keyed translation memory as agent-friendly Markdown manuscripts."""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "translation_memory.sqlite3"
MANUSCRIPT = ROOT / "manuscript"


def clean(text: str) -> str:
    return text.strip().replace("\r\n", "\n").replace("\r", "\n")


def segment_markdown(row: sqlite3.Row, bilingual: bool) -> str:
    bbox = json.loads(row["bbox_json"])
    metadata = (
        f'<!-- segment: {row["segment_key"]}; page: {row["page_number"]}; '
        f'bbox: {json.dumps(bbox, ensure_ascii=False, separators=(",", ":"))}; '
        f'status: {row["display_status"]}; provider: {row["display_provider"] or "none"} -->'
    )
    parts = [
        f'### {row["segment_key"]}',
        metadata,
        "",
        "English:",
        "",
        clean(row["source_text"]),
    ]
    if bilingual:
        parts.extend(
            [
                "",
                "Russian:",
                "",
                clean(row["display_translation_text"]) or "⟦TRANSLATION PENDING⟧",
            ]
        )
    return "\n".join(parts)


def figure_markdown(
    figure: sqlite3.Row, labels: list[sqlite3.Row], bilingual: bool
) -> str:
    # An absolute workspace path renders correctly both in the consolidated
    # manuscript and in per-page files. Final portable links are rewritten by
    # the packaging step when the project is copied.
    relative_image = str(ROOT / figure["image_path"])
    parts = [
        f'### {figure["figure_key"]}',
        (
            f'<!-- figure: {figure["figure_key"]}; page: {figure["page_number"]}; '
            f'xref: {figure["xref"]}; bbox: {figure["image_bbox_json"]} -->'
        ),
        "",
        f'![Source figure {figure["figure_key"]}]({relative_image})',
    ]
    active = [label for label in labels if label["status"] != "ignore"]
    if active:
        parts.extend(["", "Figure labels:", ""])
        for label in active:
            ru = clean(label["translation_text"]) or "⟦TRANSLATION PENDING⟧"
            line = f'- `{label["label_key"]}` — EN: {clean(label["source_text"])}'
            if bilingual:
                line += f' — RU: {ru}'
            parts.append(line)
    return "\n".join(parts)


def page_markdown(
    page: int,
    rows: list[sqlite3.Row],
    figures: list[sqlite3.Row],
    labels_by_figure: dict[str, list[sqlite3.Row]],
    bilingual: bool,
) -> str:
    chapter = next((row["chapter"] for row in rows if row["chapter"]), "")
    parts = [
        "---",
        f"page: {page}",
        f"chapter: {json.dumps(chapter, ensure_ascii=False)}",
        f"mode: {'bilingual' if bilingual else 'source'}",
        "---",
        "",
        f"# PDF page {page}",
    ]
    for row in rows:
        parts.extend(["", segment_markdown(row, bilingual)])
    for figure in figures:
        parts.extend(
            ["", figure_markdown(figure, labels_by_figure.get(figure["figure_key"], []), bilingual)]
        )
    return "\n".join(parts).rstrip() + "\n"


def export() -> None:
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    segments = list(
        db.execute(
            """SELECT s.*,
                      COALESCE(NULLIF(s.translation_text, ''), d.translation_text, '')
                          AS display_translation_text,
                      CASE
                        WHEN s.translation_text != '' THEN s.status
                        WHEN d.translation_text IS NOT NULL THEN 'draft'
                        ELSE s.status
                      END AS display_status,
                      CASE
                        WHEN s.translation_text != '' THEN s.provider
                        WHEN d.translation_text IS NOT NULL THEN d.provider
                        ELSE s.provider
                      END AS display_provider
                 FROM segments s
                 LEFT JOIN translation_drafts d
                   ON d.segment_key=s.segment_key AND d.source_hash=s.source_hash
                ORDER BY s.page_number, s.block_number"""
        )
    )
    figures = list(db.execute("SELECT * FROM figures ORDER BY page_number, image_number"))
    has_regions = db.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='figure_text_regions'"
    ).fetchone()
    if has_regions:
        labels = list(
            db.execute(
                """SELECT r.region_key AS label_key,
                          r.figure_key,
                          r.region_number AS label_number,
                          r.source_text,
                          r.translation_text,
                          r.status,
                          r.provider,
                          r.ocr_confidence,
                          r.pixel_bbox_json
                     FROM figure_text_regions r
                     JOIN figures f USING(figure_key)
                    ORDER BY f.page_number, f.image_number, r.region_number"""
            )
        )
        label_description = "canonical figure text regions"
    else:
        labels = list(
            db.execute(
                """SELECT l.* FROM figure_labels l
                   JOIN figures f USING(figure_key)
                   ORDER BY f.page_number, f.image_number, l.label_number"""
            )
        )
        label_description = "raw OCR label candidates"
    db.close()

    segments_by_page: dict[int, list[sqlite3.Row]] = {}
    figures_by_page: dict[int, list[sqlite3.Row]] = {}
    labels_by_figure: dict[str, list[sqlite3.Row]] = {}
    for row in segments:
        segments_by_page.setdefault(row["page_number"], []).append(row)
    for figure in figures:
        figures_by_page.setdefault(figure["page_number"], []).append(figure)
    for label in labels:
        labels_by_figure.setdefault(label["figure_key"], []).append(label)

    for mode, bilingual in (("source", False), ("bilingual", True)):
        page_dir = MANUSCRIPT / mode / "pages"
        page_dir.mkdir(parents=True, exist_ok=True)
        combined = [
            "---",
            "title: Cloud Native Data Security with OAuth",
            f"mode: {mode}",
            "source_format: keyed-pdf-extraction",
            "---",
            "",
            "# Cloud Native Data Security with OAuth",
            "",
            "Each heading is a stable translation-memory key. PDF page numbers are physical pages.",
        ]
        all_pages = sorted(set(segments_by_page) | set(figures_by_page))
        for page in all_pages:
            rendered = page_markdown(
                page,
                segments_by_page.get(page, []),
                figures_by_page.get(page, []),
                labels_by_figure,
                bilingual,
            )
            (page_dir / f"page-{page:04d}.md").write_text(rendered, encoding="utf-8")
            combined.extend(["", f"<!-- BEGIN PDF PAGE {page} -->", "", rendered.rstrip()])
        (MANUSCRIPT / mode / "book.md").write_text(
            "\n".join(combined).rstrip() + "\n", encoding="utf-8"
        )
    print(
        f"exported {len(segments)} text segments, {len(figures)} figures, "
        f"{len(labels)} {label_description} to {MANUSCRIPT}",
        flush=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.parse_args()
    export()


if __name__ == "__main__":
    main()
