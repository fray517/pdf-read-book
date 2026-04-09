"""Загрузка настроек из окружения."""

from functools import lru_cache
from pathlib import Path
from typing import List

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


load_dotenv()


class Settings(BaseSettings):
    """Конфигурация приложения."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # По умолчанию SQLite — работает без установленного PostgreSQL.
    # В Docker задайте DATABASE_URL / DATABASE_SYNC_URL на PostgreSQL (см. env.example).
    database_url: str = Field(
        default="sqlite+aiosqlite:///./data/app.db",
    )
    database_sync_url: str = Field(
        default="sqlite:///./data/app.db",
    )
    redis_url: str = Field(default="redis://localhost:6379/0")
    celery_broker_url: str = Field(default="redis://localhost:6379/0")
    # Пусто — без хранения результатов в Redis (меньше соединений). Docker задаёт явно.
    celery_result_backend: str = Field(default="")

    openai_api_key: str = Field(default="")

    jwt_secret: str = Field(default="change-me")
    jwt_algorithm: str = Field(default="HS256")
    access_token_expire_minutes: int = Field(default=60 * 24 * 7)

    storage_path: Path = Field(default=Path("./data/storage"))

    max_upload_mb: int = Field(default=80)
    max_pdf_pages: int = Field(default=500)
    daily_pages_quota: int = Field(default=200)
    daily_chars_quota: int = Field(default=500_000)

    cors_origins: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173",
    )
    api_v1_prefix: str = Field(default="/api/v1")

    @property
    def cors_origins_list(self) -> List[str]:
        """Список разрешённых origin для CORS."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    """Singleton настроек."""
    return Settings()
