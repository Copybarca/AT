from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ServiceSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", extra="ignore")

    service_token: str = "local-service-token"
    trans_api_base_url: str = "http://localhost:8080"
    translation_queue_capacity: int = Field(default=16, ge=1)
    translation_worker_count: int = Field(default=1, ge=1)
    translation_callback_retries: int = Field(default=3, ge=1, le=20)
    translation_callback_retry_delay_seconds: float = Field(default=1.0, ge=0)
    translation_timeout_seconds: float = Field(default=300.0, gt=0)
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "qwen3:8b"
