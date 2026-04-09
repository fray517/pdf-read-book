"""Вызовы OpenAI: OCR, перевод, TTS."""

from __future__ import annotations

import logging
from openai import OpenAI

from app.config import get_settings
from app.services.pdf_extract import image_to_data_url

logger = logging.getLogger(__name__)

VISION_MODEL = "gpt-4o-mini"
CHAT_MODEL = "gpt-4o-mini"
TTS_MODEL = "tts-1"
TTS_VOICE = "alloy"


def get_client() -> OpenAI:
    """Клиент OpenAI."""
    settings = get_settings()
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY не задан")
    return OpenAI(api_key=settings.openai_api_key)


def ocr_page_png(client: OpenAI, png: bytes) -> str:
    """Распознавание текста со скана через Vision."""
    url = image_to_data_url(png)
    resp = client.chat.completions.create(
        model=VISION_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "Ты OCR для технических документов. Верни только "
                    "распознанный текст, сохрани абзацы и нумерацию. "
                    "Без комментариев."
                ),
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Извлеки весь текст с изображения страницы.",
                    },
                    {"type": "image_url", "image_url": {"url": url}},
                ],
            },
        ],
        max_tokens=4096,
    )
    choice = resp.choices[0].message.content
    return (choice or "").strip()


def detect_language_code(client: OpenAI, sample: str) -> str:
    """Определяет код языка (en, ru, ...)."""
    sample = sample.strip()[:8000]
    if not sample:
        return "en"
    try:
        from langdetect import detect

        code = detect(sample)
        if code in ("en", "ru"):
            return code
    except Exception:
        logger.debug("langdetect failed, using OpenAI", exc_info=True)
    resp = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "Reply with exactly one ISO 639-1 language code "
                    "for the main language of the text (e.g. en, ru)."
                ),
            },
            {"role": "user", "content": sample[:4000]},
        ],
        max_tokens=10,
    )
    raw = (resp.choices[0].message.content or "en").strip().lower()
    return raw[:2] if len(raw) >= 2 else "en"


def translate_to_russian(client: OpenAI, text: str) -> str:
    """Переводит фрагмент на русский (технический стиль)."""
    text = text.strip()
    if not text:
        return ""
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
            {"role": "user", "content": text},
        ],
        max_tokens=8192,
    )
    return (resp.choices[0].message.content or "").strip()


def synthesize_speech_mp3(client: OpenAI, text: str) -> bytes:
    """Генерирует MP3 для сегмента."""
    text = text.strip()
    if not text:
        return b""
    audio = client.audio.speech.create(
        model=TTS_MODEL,
        voice=TTS_VOICE,
        input=text[:4096],
        response_format="mp3",
    )
    if hasattr(audio, "read"):
        return audio.read()
    return getattr(audio, "content", b"")
