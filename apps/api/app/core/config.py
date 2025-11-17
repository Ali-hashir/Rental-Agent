"""Application configuration for the minimal demo."""
from __future__ import annotations

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration."""

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    app_env: str = Field(default="development")
    cors_allow_origins: list[str] = Field(default_factory=lambda: ["*"])

    gemini_api_key: str = Field(default="")
    gemini_model: str = Field(default="gemini-2.0-flash")
    gemini_model_fallbacks: list[str] = Field(default_factory=lambda: [
        "gemini-2.0-flash-lite",
        "gemini-1.5-flash-latest",
        "gemini-1.5-flash-001",
        "gemini-1.5-pro-latest",
    ])

    whisper_model: str = Field(default="small")
    whisper_device: str = Field(default="cpu")
    whisper_compute_type: str = Field(default="int8")

    tts_provider: str = Field(default="gtts")
    tts_voice: str = Field(default="en-US-AriaNeural")

    @field_validator("gemini_model_fallbacks", mode="before")
    @classmethod
    def _split_fallbacks(cls, value: object) -> object:
        """Allow comma-separated env values for Gemini fallback models."""

        if isinstance(value, str):
            parts = [item.strip() for item in value.split(",") if item.strip()]
            return parts
        return value


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""

    return Settings()


settings = get_settings()
