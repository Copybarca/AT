"""Small support layer for the retained translation-worker reference.

The production AT implementation belongs in trans-api.  This module only makes
the SQLite pilot worker self-contained enough for tests and local experiments.
"""

from __future__ import annotations

import csv
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get("TRANSLATION_MEMORY_DB", ROOT / "translation_memory.sqlite3"))
GLOSSARY_PATH = Path(os.environ.get("TRANSLATION_GLOSSARY", ROOT / "glossary.example.tsv"))


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def connect() -> sqlite3.Connection:
    if not DB_PATH.is_file():
        raise FileNotFoundError(
            f"translation-memory database does not exist: {DB_PATH}; "
            "set TRANSLATION_MEMORY_DB to a compatible pilot database"
        )
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    return db


def load_glossary() -> tuple[dict[str, str], list[tuple[str, str]]]:
    exact: dict[str, str] = {}
    terms: list[tuple[str, str]] = []
    with GLOSSARY_PATH.open(encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream, delimiter="\t"):
            english = (row.get("english") or "").strip()
            russian = (row.get("russian") or "").strip()
            if not english or not russian:
                continue
            exact[english] = russian
            terms.append((english, russian))
    return exact, terms


def exact_glossary_translation(text: str, exact: dict[str, str]) -> str | None:
    return exact.get(text.strip())
