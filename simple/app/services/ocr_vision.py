"""OCR страницы через OpenAI Vision (этап 3.3)."""

from __future__ import annotations

import base64

from openai import (
    APIConnectionError,
    APITimeoutError,
    OpenAI,
    RateLimitError,
)

VISION_MODEL = "gpt-4o-mini"


def image_to_data_url(png: bytes) -> str:
    """Data URL для Vision API."""
    b64 = base64.standard_b64encode(png).decode("ascii")
    return f"data:image/png;base64,{b64}"


def ocr_page_png(client: OpenAI, png: bytes) -> str:
    """Распознавание текста со скана через Vision."""
    url = image_to_data_url(png)
    try:
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
                            "text": (
                                "Извлеки весь текст с изображения страницы."
                            ),
                        },
                        {"type": "image_url", "image_url": {"url": url}},
                    ],
                },
            ],
            max_tokens=4096,
        )
    except APIConnectionError as exc:
        raise RuntimeError(
            "Нет соединения с API OpenAI (OCR). Проверьте интернет и "
            "доступность api.openai.com.",
        ) from exc
    except APITimeoutError as exc:
        raise RuntimeError(
            "Превышено время ожидания ответа OpenAI (OCR).",
        ) from exc
    except RateLimitError as exc:
        raise RuntimeError(
            "Лимит запросов OpenAI (OCR).",
        ) from exc
    choice = resp.choices[0].message.content
    return (choice or "").strip()
