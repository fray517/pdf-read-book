"""Извлечение текста с OCR для «пустых» страниц (этап 3.3)."""

from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

import fitz

from app.services.ocr_vision import ocr_page_png
from app.services.openai_client import get_openai_client

# Ниже порога — страница кандидат на Vision OCR.
_MIN_TEXT_CHARS = 40


def render_page_png(page: fitz.Page, dpi: float = 2.0) -> bytes:
    """Растеризация страницы в PNG."""
    mat = fitz.Matrix(dpi, dpi)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    return pix.tobytes("png")


def extract_text_by_pages_with_ocr(
    path: Path,
) -> Tuple[List[Tuple[int, str]], List[int]]:
    """
    Текст по страницам: слой PDF, для слабых страниц — Vision OCR.

    Возвращает (список (номер, текст), номера страниц с OCR).
    """
    doc = fitz.open(path)
    result: List[Tuple[int, str]] = []
    ocr_used: List[int] = []
    client = None
    try:
        for i in range(len(doc)):
            page = doc.load_page(i)
            raw = page.get_text("text") or ""
            stripped = raw.strip()
            page_no = i + 1
            if len(stripped) >= _MIN_TEXT_CHARS:
                result.append((page_no, stripped))
                continue
            if client is None:
                client = get_openai_client()
            png = render_page_png(page)
            ocr_text = ocr_page_png(client, png)
            result.append((page_no, ocr_text.strip()))
            ocr_used.append(page_no)
    finally:
        doc.close()
    return result, ocr_used

