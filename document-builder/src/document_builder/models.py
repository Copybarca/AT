from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ElementType(StrEnum):
    TEXT = "TEXT"
    IMAGE = "IMAGE"


class TextStyle(StrEnum):
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


class DocumentMetadata(BaseModel):
    model_config = ConfigDict(frozen=True)

    title: str = Field(min_length=1, max_length=256)
    language: str = Field(min_length=2, max_length=32)


class BuildElement(BaseModel):
    model_config = ConfigDict(frozen=True, populate_by_name=True)

    sequential_number: int = Field(alias="sequentialNumber", gt=0)
    type: ElementType
    text: str | None = None
    style: TextStyle | None = None
    asset_key: str | None = Field(default=None, alias="assetKey")
    media_type: str | None = Field(default=None, alias="mediaType")
    alt_text: str | None = Field(default=None, alias="altText")

    @model_validator(mode="after")
    def validate_shape(self) -> Self:
        if self.type is ElementType.TEXT:
            if self.text is None or not self.text.strip():
                raise ValueError("TEXT element requires non-empty text")
            if self.style is None:
                raise ValueError("TEXT element requires style")
            if self.asset_key is not None or self.media_type is not None:
                raise ValueError("TEXT element cannot reference an asset")
        else:
            if not self.asset_key or not self.asset_key.strip():
                raise ValueError("IMAGE element requires assetKey")
            if self.media_type not in {"image/png", "image/jpeg"}:
                raise ValueError("IMAGE element requires PNG or JPEG mediaType")
            if self.text is not None or self.style is not None:
                raise ValueError("IMAGE element cannot contain text or style")
        return self


class BuildRequest(BaseModel):
    model_config = ConfigDict(frozen=True, populate_by_name=True)

    process_id: int = Field(alias="processId", gt=0)
    book_id: int = Field(alias="bookId", gt=0)
    result_callback_url: str = Field(alias="resultCallbackUrl", min_length=1)
    document: DocumentMetadata
    elements: tuple[BuildElement, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_callback(self) -> Self:
        expected = f"/internal/v1/books/{self.book_id}/build-result"
        if self.result_callback_url != expected:
            raise ValueError("resultCallbackUrl is not the trusted trans-api callback")
        return self


@dataclass(frozen=True, slots=True)
class BuildAsset:
    asset_key: str
    path: Path
    media_type: str
    sha256: str
    size: int
    width: int
    height: int


@dataclass(frozen=True, slots=True)
class BuildInput:
    request: BuildRequest
    elements: tuple[BuildElement, ...]
    assets: tuple[BuildAsset, ...]
    job_directory: Path
    manifest_sha256: str

    def asset(self, asset_key: str) -> BuildAsset:
        for asset in self.assets:
            if asset.asset_key == asset_key:
                return asset
        raise KeyError(asset_key)
