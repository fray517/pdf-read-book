"""Извлечение текста из PDF (слой текста, без OCR)."""

from pathlib import Path
from typing import List, Tuple

import fitz


def extract_text_by_pages(path: Path) -> List[Tuple[int, str]]:
    """
    Текст по страницам.

    Возвращает список (номер страницы с 1, текст).
    """
    doc = fitz.open(path)
    try:
        result: List[Tuple[int, str]] = []
        for i in range(len(doc)):
            page = doc.load_page(i)
            block = page.get_text("text") or ""
            result.append((i + 1, block.strip()))
        return result
    finally:
        doc.close()


def pages_to_full_text(pages: List[Tuple[int, str]]) -> str:
    """Склейка страниц в один блок (разделитель — двойной перевод строки)."""
    return "\n\n".join(text for _, text in pages if text)
