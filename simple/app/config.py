"""Настройки: переменные окружения и файл .env."""

from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


class Settings(BaseSettings):
    """Конфигурация (без логирования секретов)."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openai_api_key: str = Field(default="")
    storage_path: Path = Field(default=Path("./data/files"))
    # Статика: заглушка ./web или позже путь к `npm run build` (папка dist).
    web_static_path: Path = Field(default=Path("./web"))


@lru_cache
def get_settings() -> Settings:
    """Один экземпляр настроек на процесс."""
    return Settings()
