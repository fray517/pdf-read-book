"""Извлечение текста из PDF и рендер страниц."""

import base64
import logging
from pathlib import Path
from typing import List, Tuple

import fitz

from app.models import ExtractionMethod

logger = logging.getLogger(__name__)

# Минимум символов, ниже — считаем страницу кандидатом на OCR.
MIN_TEXT_CHARS = 40


def page_text_and_image(
    doc: fitz.Document,
    page_no: int,
    dpi_scale: float = 2.0,
) -> Tuple[str, bytes | None]:
    """
    Текст страницы и PNG для OCR (если текст слабый).
    page_no: 0-based.
    """
    page = doc.load_page(page_no)
    raw = page.get_text("text") or ""
    stripped = raw.strip()
    png: bytes | None = None
    if len(stripped) < MIN_TEXT_CHARS:
        mat = fitz.Matrix(dpi_scale, dpi_scale)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        png = pix.tobytes("png")
    return raw, png


def open_pdf(path: Path) -> fitz.Document:
    """Открывает PDF."""
    return fitz.open(path)


def page_count(path: Path) -> int:
    """Число страниц."""
    doc = fitz.open(path)
    try:
        return len(doc)
    finally:
        doc.close()


def extract_all_pages(path: Path) -> List[Tuple[int, str, bytes | None, ExtractionMethod]]:
    """
    Список (1-based page_no, text, png_or_none, method).
    """
    doc = fitz.open(path)
    out: List[Tuple[int, str, bytes | None, ExtractionMethod]] = []
    try:
        for i in range(len(doc)):
            text, png = page_text_and_image(doc, i)
            if png is not None:
                method = ExtractionMethod.VISION_OCR
            else:
                method = ExtractionMethod.PDF_TEXT
            out.append((i + 1, text, png, method))
    finally:
        doc.close()
    return out


def image_to_data_url(png: bytes) -> str:
    """Data URL для Vision API."""
    b64 = base64.standard_b64encode(png).decode("ascii")
    return f"data:image/png;base64,{b64}"
