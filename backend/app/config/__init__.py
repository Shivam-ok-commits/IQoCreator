"""Application configuration and environment management."""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar, Literal

from pydantic import Field, PostgresDsn, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Supports both development and production environments.
    Environment variables are loaded from a .env file if present.
    """

    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────────────────
    app_name: str = "IQoCreator"
    app_version: str = "0.1.0"
    app_description: str = "IQoCreator - AI-powered research platform"
    debug: bool = Field(default=False, alias="DEBUG")
    environment: Literal["development", "production", "testing"] = Field(
        default="development", alias="ENVIRONMENT"
    )
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # ── Server ───────────────────────────────────────────────────────────
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8000, alias="PORT")

    # ── Database ─────────────────────────────────────────────────────────
    database_url: PostgresDsn = Field(
        default=PostgresDsn(
            "postgresql://iqocreator:iqocreator@localhost:5432/iqocreator"
        ),
        alias="DATABASE_URL",
    )
    database_echo: bool = Field(default=False, alias="DATABASE_ECHO")
    database_pool_size: int = Field(default=10, alias="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(default=20, alias="DATABASE_MAX_OVERFLOW")
    database_pool_pre_ping: bool = Field(default=True, alias="DATABASE_POOL_PRE_PING")

    # ── Redis ────────────────────────────────────────────────────────────
    redis_url: RedisDsn = Field(
        default=RedisDsn("redis://localhost:6379/0"),
        alias="REDIS_URL",
    )

    # ── CORS ─────────────────────────────────────────────────────────────
    cors_origins: list[str] = Field(
        default=["http://localhost:3000"],
        alias="CORS_ORIGINS",
    )
    cors_allow_credentials: bool = Field(default=True, alias="CORS_ALLOW_CREDENTIALS")

    # ── Paths ────────────────────────────────────────────────────────────
    project_root: Path = Field(
        default_factory=lambda: Path(__file__).resolve().parent.parent.parent
    )

    # ── OAuth ────────────────────────────────────────────────────────────
    google_client_id: str = Field(alias="GOOGLE_CLIENT_ID")
    google_client_secret: str = Field(alias="GOOGLE_CLIENT_SECRET")
    oauth_redirect_uri: str = Field(
        default="http://localhost:8000/api/auth/callback",
        alias="OAUTH_REDIRECT_URI",
    )

    # ── API Keys ─────────────────────────────────────────────────────────
    # YouTube Data API key (loaded from environment)
    youtube_api_key: str | None = Field(default=None, alias="YOUTUBE_API_KEY")

    @property
    def is_development(self) -> bool:
        return self.environment == "development"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def is_testing(self) -> bool:
        return self.environment == "testing"

    @property
    def sync_database_url(self) -> str:
        """Return a sync-compatible database URL for Alembic."""
        return str(self.database_url).replace("postgresql+asyncpg://", "postgresql://")


# Global settings instance
# pydantic-settings automatically loads from .env via model_config
settings = Settings()
