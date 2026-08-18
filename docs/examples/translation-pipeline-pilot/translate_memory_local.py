"""Conservative literal-preservation rule used by the pilot worker bundle."""

from __future__ import annotations

import re


URL_RE = re.compile(r"(?:https?://|urn:)[^\s]+$", re.I)
IDENTIFIER_RE = re.compile(r"[A-Z][A-Z0-9_.:/+-]{1,}$")
NUMBER_OR_PUNCTUATION_RE = re.compile(r"[^A-Za-zА-Яа-яЁё]+")


def preserve_text_segment(text: str) -> bool:
    """Return true only for obvious literals that should bypass inference.

    The rule is intentionally conservative: glossary matches are handled by
    ``exact_glossary_translation`` and ambiguous English text still goes to the
    model.
    """

    value = text.strip()
    if not value:
        return True
    if URL_RE.fullmatch(value) or IDENTIFIER_RE.fullmatch(value):
        return True
    return bool(NUMBER_OR_PUNCTUATION_RE.fullmatch(value))
