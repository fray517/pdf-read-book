"""Разбиение текста на сегменты для TTS (этап 3.4)."""

from __future__ import annotations

import re
from typing import List, Tuple

# Запас до лимита TTS OpenAI (~4096 символов на запрос).
MAX_SEGMENT_CHARS = 3500


def split_long_paragraph(para: str) -> List[str]:
    """Делит длинный абзац по предложениям или по длине."""
    para = para.strip()
    if not para:
        return []
    if len(para) <= MAX_SEGMENT_CHARS:
        return [para]
    parts: List[str] = []
    sentences = re.split(r"(?<=[.!?…])\s+", para)
    buf = ""
    for s in sentences:
        if not s:
            continue
        if len(buf) + len(s) + 1 <= MAX_SEGMENT_CHARS:
            buf = f"{buf} {s}".strip() if buf else s
        else:
            if buf:
                parts.append(buf)
            if len(s) <= MAX_SEGMENT_CHARS:
                buf = s
            else:
                for i in range(0, len(s), MAX_SEGMENT_CHARS):
                    parts.append(s[i : i + MAX_SEGMENT_CHARS])
                buf = ""
    if buf:
        parts.append(buf)
    return parts


def segment_book_pages(
    pages_text: List[Tuple[int, str]],
) -> List[Tuple[int, str]]:
    """
    pages_text: (номер страницы с 1, текст).

    Разбиение по абзацам (двойной перевод строки), затем по лимиту.
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


def segment_flat_text(text: str) -> List[str]:
    """Цельный текст (например из _ru.txt): абзацы → сегменты."""
    stripped = text.strip()
    if not stripped:
        return []
    blocks = [b.strip() for b in stripped.split("\n\n") if b.strip()]
    out: List[str] = []
    for block in blocks:
        out.extend(split_long_paragraph(block))
    return out


def segments_from_flat(text: str) -> List[Tuple[int, int, str]]:
    """Сегменты из одного блока; page_no = 0 (не привязано к странице PDF)."""
    parts = segment_flat_text(text)
    return [(i, 0, tx) for i, tx in enumerate(parts)]
