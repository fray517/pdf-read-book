"""Разбиение текста на сегменты для TTS."""

from __future__ import annotations

import re
from typing import List, Tuple

# Лимит символов на запрос TTS (запас до 4096).
MAX_CHARS = 3500


def split_long_paragraph(para: str) -> List[str]:
    """Делит длинный абзац по предложениям или по длине."""
    para = para.strip()
    if not para:
        return []
    if len(para) <= MAX_CHARS:
        return [para]
    parts: List[str] = []
    # Разбиение по предложениям (латиница и кириллица).
    sentences = re.split(r"(?<=[.!?…])\s+", para)
    buf = ""
    for s in sentences:
        if not s:
            continue
        if len(buf) + len(s) + 1 <= MAX_CHARS:
            buf = f"{buf} {s}".strip() if buf else s
        else:
            if buf:
                parts.append(buf)
            if len(s) <= MAX_CHARS:
                buf = s
            else:
                # Жёсткая нарезка.
                for i in range(0, len(s), MAX_CHARS):
                    parts.append(s[i : i + MAX_CHARS])
                buf = ""
    if buf:
        parts.append(buf)
    return parts


def segment_book_pages(
    pages_text: List[Tuple[int, str]],
) -> List[Tuple[int, str]]:
    """
    pages_text: список (page_no, text_ru).
    Возвращает список (page_no, segment_text).
    """
    result: List[Tuple[int, str]] = []
    for page_no, text in pages_text:
        blocks = [b.strip() for b in text.split("\n\n") if b.strip()]
        if not blocks:
            continue
        for block in blocks:
            for seg in split_long_paragraph(block):
                result.append((page_no, seg))
    return result
