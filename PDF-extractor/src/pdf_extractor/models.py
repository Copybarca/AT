from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ElementStyle(StrEnum):
    TITLE = "TITLE"
    SUBTITLE = "SUBTITLE"
    AUTHOR = "AUTHOR"
    CHAPTER = "CHAPTER"
    HEADING_1 = "HEADING_1"
    HEADING_2 = "HEADING_2"
    HEADING_3 = "HEADING_3"
    BODY = "BODY"
    LIST_ITEM = "LIST_ITEM"
    FIGURE_CAPTION = "FIGURE_CAPTION"
    NOTE = "NOTE"
    CODE = "CODE"


@dataclass(frozen=True, slots=True)
class BoundingBox:
    x0: float
    y0: float
    x1: float
    y1: float


@dataclass(frozen=True, slots=True)
class RawTextBlock:
    page_number: int
    block_number: int
    stable_key: str
    text: str
    bbox: BoundingBox
    style: ElementStyle
    translatable: bool


@dataclass(frozen=True, slots=True)
class ExtractedSegment:
    stable_key: str
    source_hash: str
    sequential_number: int
    physical_page: int
    bbox: BoundingBox
    style: ElementStyle
    text: str
    translatable: bool
