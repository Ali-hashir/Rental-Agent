"""Application configuration via pydantic settings."""
from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from pydantic import Field, RedisDsn, AnyHttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central runtime configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="",
        case_sensitive=False,
        extra="ignore",
    )

    app_env: str = Field(default="development")
    cors_allow_origins: list[str] = Field(default_factory=lambda: ["*"])

    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/rental_agent"
    )
    redis_url: RedisDsn = Field(default="redis://localhost:6379/0")

    deepgram_api_key: str = Field(default="", min_length=0)
    elevenlabs_api_key: str = Field(default="", min_length=0, alias="eleven_labs_api_key")
    gemini_api_key: str = Field(default="", min_length=0)

    livekit_url: str | None = None
    livekit_api_key: str | None = None
    livekit_api_secret: str | None = None

    email_from: str = Field(default="leasing@example.com")
    sendgrid_api_key: str | None = None
    sms_provider_key: str | None = None

    observability_endpoint: Annotated[str | None, AnyHttpUrl] = None

    @property
    def database_async_url(self) -> str:
        """Return async-compatible SQLAlchemy URL.

        Accept both standard `postgresql://` DSNs (e.g. Neon) and driver-qualified
        URLs. When the async driver is missing we rewrite the scheme to include
        `+asyncpg` so that SQLAlchemy can create an async engine.
        """

        if self.database_url.startswith("postgresql+asyncpg://"):
            return self.database_url
        if self.database_url.startswith("postgres://"):
            return self.database_url.replace("postgres://", "postgresql+asyncpg://", 1)
        if self.database_url.startswith("postgresql://"):
            return self.database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return self.database_url


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""

    return Settings()  # type: ignore[arg-type]


settings = get_settings()
