"""Перевод извлечённого текста на русский (этап 3.2)."""

from __future__ import annotations

from pathlib import Path

from openai import (
    APIConnectionError,
    APITimeoutError,
    OpenAI,
    RateLimitError,
)

from app.services.detect_language import detect_language_code
from app.services.openai_client import get_openai_client
from app.services.pdf_text import extract_text_by_pages, pages_to_full_text

CHAT_MODEL = "gpt-4o-mini"
# Один запрос для коротких фрагментов; длинные книги — по частям.
_CHUNK_CHARS = 14_000


def _translate_chunk(client: OpenAI, text: str) -> str:
    """Один вызов Chat Completions: фрагмент → русский."""
    chunk = text.strip()
    if not chunk:
        return ""
    try:
        resp = client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Переведи на русский язык, сохраняя техническую "
                        "терминологию, нумерацию, заголовки и структуру. "
                        "Только перевод, без пояснений."
                    ),
                },
                {"role": "user", "content": chunk},
            ],
            max_tokens=8192,
        )
    except APIConnectionError as exc:
        raise RuntimeError(
            "Нет соединения с API OpenAI (не удаётся подключиться к "
            "api.openai.com). Проверьте интернет, DNS, VPN, прокси и "
            "файрвол.",
        ) from exc
    except APITimeoutError as exc:
        raise RuntimeError(
            "Превышено время ожидания ответа от OpenAI.",
        ) from exc
    except RateLimitError as exc:
        raise RuntimeError(
            "Лимит запросов OpenAI: повторите позже.",
        ) from exc
    return (resp.choices[0].message.content or "").strip()


def translate_to_russian_long(client: OpenAI, text: str) -> str:
    """Перевод всего текста; при необходимости режет на части."""
    full = text.strip()
    if not full:
        return ""
    if len(full) <= _CHUNK_CHARS:
        return _translate_chunk(client, full)
    parts: list[str] = []
    start = 0
    n = len(full)
    while start < n:
        end = min(start + _CHUNK_CHARS, n)
        if end < n:
            nl = full.rfind("\n", start, end)
            if nl > start:
                end = nl + 1
        piece = full[start:end]
        parts.append(_translate_chunk(client, piece))
        start = end
    return "".join(parts)


def load_pdf_full_text(pdf_path: Path) -> str:
    """Полный текст из PDF (как GET /text)."""
    raw = extract_text_by_pages(pdf_path)
    return pages_to_full_text(raw)


def build_russian_text(pdf_path: Path, ru_txt_path: Path) -> tuple[str, str]:
    """
    Возвращает текст на русском и код языка исходника.

    Если язык уже ru — копируем текст без вызова OpenAI.
    """
    full_text = load_pdf_full_text(pdf_path)
    if not full_text.strip():
        raise ValueError("В PDF нет извлекаемого текста — нечего переводить")

    try:
        src_lang = detect_language_code(full_text)
    except ValueError:
        src_lang = "und"

    if src_lang == "ru":
        ru_body = full_text
        ru_txt_path.write_text(ru_body, encoding="utf-8")
        return ru_body, src_lang

    client = get_openai_client()
    ru_body = translate_to_russian_long(client, full_text)
    ru_txt_path.write_text(ru_body, encoding="utf-8")
    return ru_body, src_lang
