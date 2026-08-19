from __future__ import annotations

from threading import RLock
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class FragmentationSettings(BaseModel):
    model_config = ConfigDict(frozen=True)

    min_sentences: int = Field(default=5, ge=1)
    max_sentences: int = Field(default=10, ge=1)
    boundary_tolerance_sentences: int = Field(default=2, ge=0)

    @model_validator(mode="after")
    def validate_range(self) -> Self:
        if self.max_sentences < self.min_sentences:
            raise ValueError("max_sentences must be greater than or equal to min_sentences")
        return self


class RuntimeFragmentationSettings:
    def __init__(self, initial: FragmentationSettings) -> None:
        self._value = initial
        self._lock = RLock()

    def snapshot(self) -> FragmentationSettings:
        with self._lock:
            return self._value.model_copy(deep=True)

    def replace(self, replacement: FragmentationSettings) -> FragmentationSettings:
        with self._lock:
            self._value = replacement.model_copy(deep=True)
            return self._value.model_copy(deep=True)


class ServiceSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", extra="ignore")

    fragment_min_sentences: int = Field(default=5, ge=1)
    fragment_max_sentences: int = Field(default=10, ge=1)
    fragment_boundary_tolerance_sentences: int = Field(default=2, ge=0)

    @property
    def fragmentation(self) -> FragmentationSettings:
        return FragmentationSettings(
            min_sentences=self.fragment_min_sentences,
            max_sentences=self.fragment_max_sentences,
            boundary_tolerance_sentences=self.fragment_boundary_tolerance_sentences,
        )
