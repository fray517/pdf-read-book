"""Построение списка сегментов (как GET /segments) для переиспользования."""

from __future__ import annotations

from pathlib import Path

from app.services.pdf_ocr import extract_text_by_pages_with_ocr
from app.services.pdf_text import extract_text_by_pages
from app.services.segmentation import segment_book_pages, segments_from_flat


def compute_segment_triples(
    pdf_path: Path,
    ru_path: Path,
    ocr: bool,
    use_ru: bool,
) -> tuple[list[tuple[int, int, str]], str]:
    """
    Возвращает (список (index, page_no, text), source).

    Raises:
        ValueError: нет текста или нет файла перевода.
    """
    if use_ru:
        if not ru_path.is_file():
            raise ValueError(
                "Нет файла перевода. Выполните POST /translate/{file_id} "
                "или отключите use_ru.",
            )
        body = ru_path.read_text(encoding="utf-8")
        if not body.strip():
            raise ValueError("Файл перевода пуст")
        return segments_from_flat(body), "ru_file"
    if ocr:
        raw_pages, _ = extract_text_by_pages_with_ocr(pdf_path)
    else:
        raw_pages = extract_text_by_pages(pdf_path)
    if not any(t.strip() for _, t in raw_pages):
        raise ValueError("Нет текста для сегментов")
    flat = segment_book_pages(raw_pages)
    triples = [(i, pn, tx) for i, (pn, tx) in enumerate(flat)]
    return triples, "pdf_pages"
