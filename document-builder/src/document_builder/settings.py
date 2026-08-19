from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ServiceSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", extra="ignore")

    trans_api_base_url: str = "http://localhost:8080"
    trans_api_token: str = "local-service-token"
    build_queue_capacity: int = Field(default=4, ge=1)
    build_worker_count: int = Field(default=1, ge=1)
    build_max_request_bytes: int = Field(default=1024 * 1024 * 1024, ge=1)
    build_max_elements: int = Field(default=100_000, ge=1)
    build_max_image_bytes: int = Field(default=50 * 1024 * 1024, ge=1)
    build_max_image_pixels: int = Field(default=100_000_000, ge=1)
    build_temp_root: Path = Path("/tmp/document-builder")
    build_timeout_seconds: int = Field(default=1800, ge=1)
    build_callback_retries: int = Field(default=3, ge=1)
    build_callback_retry_delay_seconds: float = Field(default=5, ge=0)
    page_width_in: float = Field(default=7, gt=0)
    page_height_in: float = Field(default=9.1875, gt=0)
    page_margin_top_in: float = Field(default=0.68, ge=0)
    page_margin_right_in: float = Field(default=0.72, ge=0)
    page_margin_bottom_in: float = Field(default=0.72, ge=0)
    page_margin_left_in: float = Field(default=0.72, ge=0)
    body_font_family: str = "Noto Serif"
    mono_font_family: str = "IBM Plex Mono"
    body_font_size_pt: float = Field(default=10.5, gt=0)
