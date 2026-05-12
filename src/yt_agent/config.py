"""Application configuration."""

from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables and optional .env files."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: Literal["development", "test", "production"] = "development"
    app_base_url: str = "http://localhost:8000"
    app_secret_token: str = Field(default="change-me", min_length=8)

    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-20250514"
    anthropic_max_tokens: int = Field(default=4000, ge=1)

    telegram_bot_token: str = ""
    telegram_allowed_chat_ids: Annotated[list[int], NoDecode] = Field(default_factory=list)
    telegram_webhook_secret: str = Field(default="change-me", min_length=8)

    data_dir: Path = Path("data")
    reports_dir: Path | None = None
    transcripts_dir: Path | None = None
    sqlite_path: Path | None = None
    log_path: Path | None = None

    job_mode: Literal["background", "inline"] = "background"
    max_transcript_chars_per_chunk: int = Field(default=18_000, ge=1)
    max_chunks_per_video: int = Field(default=20, ge=1)

    @field_validator(
        "data_dir",
        "reports_dir",
        "transcripts_dir",
        "sqlite_path",
        "log_path",
        mode="before",
    )
    @classmethod
    def expand_path(cls, value: str | Path | None) -> Path | None:
        if value is None or isinstance(value, Path):
            return value
        return Path(value).expanduser()

    @field_validator("telegram_allowed_chat_ids", mode="before")
    @classmethod
    def parse_chat_ids(cls, value: str | list[int] | tuple[int, ...] | None) -> list[int]:
        if value in (None, ""):
            return []
        if isinstance(value, str):
            return [int(item.strip()) for item in value.split(",") if item.strip()]
        return list(value)

    @model_validator(mode="after")
    def fill_default_paths(self) -> "Settings":
        if self.reports_dir is None:
            self.reports_dir = self.data_dir / "reports"
        if self.transcripts_dir is None:
            self.transcripts_dir = self.data_dir / "transcripts"
        if self.sqlite_path is None:
            self.sqlite_path = self.data_dir / "jobs" / "app.sqlite3"
        if self.log_path is None:
            self.log_path = self.data_dir / "logs" / "app.log"
        return self


@lru_cache
def get_settings() -> Settings:
    """Return cached process settings."""

    return Settings()
