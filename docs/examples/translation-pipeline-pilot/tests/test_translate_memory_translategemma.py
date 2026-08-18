from __future__ import annotations

import sqlite3
import unittest
from unittest.mock import patch

import translate_memory_translategemma as module


def make_segments_db() -> sqlite3.Connection:
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    db.execute(
        """CREATE TABLE segments (
               segment_key TEXT PRIMARY KEY,
               source_hash TEXT NOT NULL,
               source_text TEXT NOT NULL,
               status TEXT NOT NULL,
               page_number INTEGER NOT NULL,
               block_number INTEGER NOT NULL
           )"""
    )
    db.execute(
        """CREATE TABLE translation_drafts (
               segment_key TEXT PRIMARY KEY,
               source_hash TEXT NOT NULL,
               translation_text TEXT NOT NULL,
               provider TEXT NOT NULL,
               updated_at TEXT NOT NULL
           )"""
    )
    return db


class GroupsTests(unittest.TestCase):
    def test_each_pending_fragment_is_its_own_group(self) -> None:
        db = make_segments_db()
        rows = [
            ("P0001-B000", "h1", "First", "new", 1, 0),
            ("P0001-B001", "h2", "Second", "new", 1, 1),
            ("P0002-B000", "h3", "Third", "new", 2, 0),
        ]
        db.executemany("INSERT INTO segments VALUES (?, ?, ?, ?, ?, ?)", rows)

        work = module.groups(db, 1, None)

        self.assertEqual([len(group) for group in work], [1, 1, 1])
        self.assertEqual(
            [group[0]["segment_key"] for group in work],
            ["P0001-B000", "P0001-B001", "P0002-B000"],
        )


class PersistenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.db = make_segments_db()
        self.db.execute(
            "INSERT INTO segments VALUES (?, ?, ?, ?, ?, ?)",
            ("P0108-B002", "source-hash", "Text.1 Example", "new", 108, 2),
        )
        self.row = self.db.execute(
            "SELECT * FROM segments WHERE segment_key='P0108-B002'"
        ).fetchone()

    def test_attempt_history_retains_validation_evidence(self) -> None:
        module.ensure_draft_table(self.db)

        module.record_attempt(
            self.db,
            self.row,
            attempt_no=2,
            prompt_version="corrective-v1",
            response_text="Текст. Пример",
            issues=["missing-numbers:1"],
            elapsed_seconds=12.5,
        )

        saved = self.db.execute(
            "SELECT * FROM translation_attempts"
        ).fetchone()
        self.assertEqual(saved["segment_key"], "P0108-B002")
        self.assertEqual(saved["source_hash"], "source-hash")
        self.assertEqual(saved["attempt_no"], 2)
        self.assertEqual(saved["prompt_version"], "corrective-v1")
        self.assertEqual(saved["response_text"], "Текст. Пример")
        self.assertEqual(saved["issues_json"], '["missing-numbers:1"]')
        self.assertEqual(saved["elapsed_seconds"], 12.5)

    def test_review_queue_upserts_one_entry_per_source_version(self) -> None:
        module.ensure_draft_table(self.db)

        module.mark_needs_review(self.db, self.row, 3, "missing-numbers:1")
        module.mark_needs_review(self.db, self.row, 4, "missing-numbers:1")

        saved = list(self.db.execute("SELECT * FROM translation_review_queue"))
        self.assertEqual(len(saved), 1)
        self.assertEqual(saved[0]["attempts"], 4)
        self.assertEqual(saved[0]["status"], "needs_review")


class FragmentTranslationTests(unittest.TestCase):
    def setUp(self) -> None:
        db = make_segments_db()
        db.execute(
            "INSERT INTO segments VALUES (?, ?, ?, ?, ?, ?)",
            (
                "P0108-B002",
                "source-hash",
                "Browser history.1 Example 5-1 uses RFC 7519 and RFC 9068.",
                "new",
                108,
                2,
            ),
        )
        self.row = db.execute("SELECT * FROM segments").fetchone()

    def test_number_tokens_round_trip_without_changing_values(self) -> None:
        source = "history.1 Example 5-1 RFC 7519 RFC 9068"

        protected, mapping = module.protect_numbers(source)
        restored = module.restore_protected_tokens(protected, mapping)

        self.assertEqual(restored, source)
        self.assertNotIn("7519", protected)
        self.assertEqual(len(mapping), 4)

    def test_third_attempt_restores_protected_numbers(self) -> None:
        attempts: list[tuple[int, str, str, list[str], float]] = []

        def fake_model(payload: dict[str, object], retries: int = 4) -> str:
            prompt = str(payload["prompt"])
            if "ZXQNUM" not in prompt:
                return (
                    "<<<P0108-B002>>>\n"
                    "История браузера. Пример 5-1 использует RFC 7519 и RFC 9068."
                )
            markers = module.PROTECTED_NUMBER_RE.findall(prompt)
            return (
                "<<<P0108-B002>>>\n"
                f"История браузера.{markers[0]} Пример {markers[1]} "
                f"использует RFC {markers[2]} и RFC {markers[3]}."
            )

        with patch.object(module, "call_payload", side_effect=fake_model):
            translated = module.translate_fragment(
                self.row,
                [],
                lambda number, version, response, issues, elapsed: attempts.append(
                    (number, version, response, issues, elapsed)
                ),
            )

        self.assertEqual(
            translated,
            "История браузера.1 Пример 5-1 использует RFC 7519 и RFC 9068.",
        )
        self.assertEqual([attempt[0] for attempt in attempts], [1, 2, 3])
        self.assertEqual(attempts[0][3], ["missing-numbers:1"])
        self.assertEqual(attempts[1][3], ["missing-numbers:1"])
        self.assertEqual(attempts[2][3], [])


class TranslateLoopTests(unittest.TestCase):
    def setUp(self) -> None:
        self.db = make_segments_db()
        self.db.executemany(
            "INSERT INTO segments VALUES (?, ?, ?, ?, ?, ?)",
            [
                ("P0001-B000", "h1", "First source", "new", 1, 0),
                ("P0001-B001", "h2", "Second source", "new", 1, 1),
            ],
        )
        module.ensure_draft_table(self.db)

    def test_content_failure_is_queued_and_next_fragment_is_saved(self) -> None:
        def fragment_result(row, terms, attempt_callback):
            if row["segment_key"] == "P0001-B000":
                raise module.FragmentNeedsReview(
                    "P0001-B000", 3, ["missing-numbers:1"]
                )
            return "Второй перевод"

        with (
            patch.object(module, "load_glossary", return_value=({}, [])),
            patch.object(module, "save_local_drafts", return_value=0),
            patch.object(module, "translate_fragment", side_effect=fragment_result),
            patch.object(
                module,
                "request_translation",
                side_effect=AssertionError("group request path used"),
            ),
        ):
            completed = module.translate(self.db, 1, None)

        self.assertEqual(completed, 1)
        queued = self.db.execute(
            "SELECT * FROM translation_review_queue WHERE segment_key='P0001-B000'"
        ).fetchone()
        self.assertEqual(queued["attempts"], 3)
        saved = self.db.execute(
            "SELECT translation_text FROM translation_drafts "
            "WHERE segment_key='P0001-B001'"
        ).fetchone()
        self.assertEqual(saved[0], "Второй перевод")

    def test_transport_failure_still_stops_worker(self) -> None:
        with (
            patch.object(module, "load_glossary", return_value=({}, [])),
            patch.object(module, "save_local_drafts", return_value=0),
            patch.object(
                module,
                "translate_fragment",
                side_effect=RuntimeError("model unavailable"),
            ),
            patch.object(
                module,
                "request_translation",
                return_value={"P0001-B000": "Старый путь"},
            ),
        ):
            with self.assertRaisesRegex(RuntimeError, "model unavailable"):
                module.translate(self.db, 1, None)


if __name__ == "__main__":
    unittest.main()
