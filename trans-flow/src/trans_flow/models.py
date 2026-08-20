from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class GlossaryTerm(BaseModel):
    model_config = ConfigDict(populate_by_name=True, frozen=True)

    source: str
    target: str


class TranslationCommand(BaseModel):
    model_config = ConfigDict(populate_by_name=True, frozen=True)

    process_id: int = Field(alias="processId", gt=0)
    book_id: int = Field(alias="bookId", gt=0)
    segment_id: int = Field(alias="segmentId", gt=0)
    request_id: str = Field(alias="requestId", min_length=1, max_length=128)
    stable_key: str = Field(alias="stableKey", min_length=1, max_length=64)
    source_hash: str = Field(alias="sourceHash", min_length=1)
    source_language: str = Field(alias="sourceLanguage", min_length=1, max_length=32)
    target_language: str = Field(alias="targetLanguage", min_length=1, max_length=32)
    source_text: str = Field(alias="sourceText", min_length=1)
    marker: str = Field(min_length=1, max_length=256)
    glossary: tuple[GlossaryTerm, ...] = ()
    strategy: str = Field(min_length=1, max_length=64)
    previous_issues: tuple[str, ...] = Field(alias="previousIssues", default=())
    callback_path: str = Field(alias="callbackPath", min_length=1, max_length=512)

    @field_validator("callback_path")
    @classmethod
    def callback_must_be_internal_path(cls, value: str) -> str:
        if not value.startswith("/internal/v1/") or "://" in value:
            raise ValueError("callbackPath must be an internal relative path")
        return value


class TranslationResultStatus(StrEnum):
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class TranslationCallback(BaseModel):
    model_config = ConfigDict(populate_by_name=True, frozen=True)

    request_id: str = Field(alias="requestId")
    source_hash: str = Field(alias="sourceHash")
    status: TranslationResultStatus
    raw_response: str | None = Field(alias="rawResponse", default=None)
    model: str | None = None
    elapsed_milliseconds: int | None = Field(
        alias="elapsedMilliseconds",
        default=None,
        ge=0,
    )
    error: str | None = Field(default=None, max_length=2000)
