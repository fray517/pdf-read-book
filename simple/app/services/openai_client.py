"""Общий клиент OpenAI для simple-приложения."""

from openai import OpenAI

from app.config import get_settings


def get_openai_client() -> OpenAI:
    """Клиент OpenAI; без ключа не создаётся."""
    key = get_settings().openai_api_key.strip()
    if not key:
        raise RuntimeError("OPENAI_API_KEY не задан в .env")
    return OpenAI(api_key=key)
