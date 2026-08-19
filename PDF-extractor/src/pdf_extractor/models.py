from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


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


@dataclass(frozen=True, slots=True)
class PageExtraction:
    usable: bool
    blocks: tuple[RawTextBlock, ...]


class ExtractionCommand(BaseModel):
    model_config = ConfigDict(frozen=True, populate_by_name=True)

    process_id: int = Field(alias="processId", gt=0)
    book_id: int = Field(alias="bookId", gt=0)
    source_sha256: str | None = Field(default=None, alias="sourceSha256")


@dataclass(frozen=True, slots=True)
class ImageTextRegion:
    stable_key: str
    source_hash: str
    physical_page: int
    sequential_number: int
    bbox: BoundingBox
    text: str
    confidence: float | None


@dataclass(frozen=True, slots=True)
class ExtractedImage:
    stable_key: str
    sequential_number: int
    physical_page: int
    bbox: BoundingBox
    media_type: str
    content: bytes
    regions: tuple[ImageTextRegion, ...]


@dataclass(frozen=True, slots=True)
class ExtractionResult:
    command: ExtractionCommand
    pdf_sha256: str
    algorithm_version: str
    segments: tuple[ExtractedSegment, ...]
    images: tuple[ExtractedImage, ...]
    regions: tuple[ImageTextRegion, ...]

    @property
    def expected_segment_count(self) -> int:
        return len(self.segments)

    @property
    def expected_image_count(self) -> int:
        return len(self.images)

    @property
    def expected_region_count(self) -> int:
        return len(self.regions)
