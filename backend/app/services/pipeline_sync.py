"""Синхронный конвейер обработки книги (для Celery)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import (
    Book,
    BookStatus,
    ExtractionMethod,
    Job,
    JobStatus,
    Page,
    Segment,
)
from app.services import openai_ops
from app.services.audio_meta import audio_duration_sec
from app.services.pdf_extract import extract_all_pages, open_pdf
from app.services.quota import check_can_process, record_usage
from app.services.segmentation import segment_book_pages
from app.storage import LocalStorage

logger = logging.getLogger(__name__)


def _set_job(
    session: Session,
    job: Job,
    status: JobStatus,
    progress: int,
    error: str | None = None,
) -> None:
    job.status = status
    job.progress_percent = progress
    job.updated_at = datetime.now(timezone.utc)
    if error is not None:
        job.error_message = error
    session.commit()


def run_book_pipeline(session: Session, job_id: str, storage: LocalStorage) -> None:
    """Полный цикл: извлечение, OCR, перевод, TTS."""
    job = session.get(Job, job_id)
    if job is None:
        logger.error("Job %s not found", job_id)
        return
    book = session.get(Book, job.book_id)
    if book is None:
        _set_job(session, job, JobStatus.FAILED, 0, "Книга не найдена")
        return

    settings = get_settings()
    pdf_full = storage.full_path(book.pdf_path)
    if not pdf_full.is_file():
        book.status = BookStatus.FAILED
        book.status_message = "PDF не найден на диске"
        _set_job(session, job, JobStatus.FAILED, 0, book.status_message)
        session.commit()
        return

    try:
        client = openai_ops.get_client()
    except RuntimeError as e:
        book.status = BookStatus.FAILED
        book.status_message = str(e)
        _set_job(session, job, JobStatus.FAILED, 0, str(e))
        session.commit()
        return

    n_pages = len(open_pdf(pdf_full))
    if n_pages > settings.max_pdf_pages:
        msg = f"Слишком много страниц (>{settings.max_pdf_pages})"
        book.status = BookStatus.FAILED
        book.status_message = msg
        _set_job(session, job, JobStatus.FAILED, 0, msg)
        session.commit()
        return

    char_est = n_pages * 3000
    ok, quota_msg = check_can_process(
        session,
        book.user_id,
        n_pages,
        char_est,
    )
    if not ok:
        book.status = BookStatus.FAILED
        book.status_message = quota_msg
        _set_job(session, job, JobStatus.FAILED, 0, quota_msg)
        session.commit()
        return

    book.status = BookStatus.EXTRACTING
    book.status_message = None
    job.status = JobStatus.RUNNING
    job.progress_percent = 5
    session.commit()

    session.execute(delete(Page).where(Page.book_id == book.id))
    session.execute(delete(Segment).where(Segment.book_id == book.id))
    session.commit()

    extracted = extract_all_pages(pdf_full)
    total = len(extracted)
    pages_rows: list[Page] = []

    for idx, (pno, text, png, method) in enumerate(extracted):
        if png is not None:
            try:
                text = openai_ops.ocr_page_png(client, png)
                method = ExtractionMethod.VISION_OCR
            except Exception as e:
                logger.exception("OCR failed page %s", pno)
                text = text or ""
                method = ExtractionMethod.VISION_OCR
        row = Page(
            book_id=book.id,
            page_no=pno,
            text_original=text or "",
            text_ru=None,
            extraction_method=method,
        )
        session.add(row)
        pages_rows.append(row)
        prog = 5 + int(25 * (idx + 1) / max(total, 1))
        job.progress_percent = min(prog, 30)
        session.commit()

    book.status = BookStatus.TEXT_READY
    session.commit()

    sample = "\n\n".join(p.text_original for p in pages_rows[:15])
    lang = openai_ops.detect_language_code(client, sample)
    book.source_lang = lang
    session.commit()

    job.progress_percent = 35
    session.commit()

    texts_orig = [p.text_original for p in pages_rows]
    if lang == "ru":
        for p in pages_rows:
            p.text_ru = p.text_original
    else:
        book.status = BookStatus.TRANSLATING
        session.commit()
        for i, p in enumerate(pages_rows):
            try:
                p.text_ru = openai_ops.translate_to_russian(
                    client,
                    p.text_original,
                )
            except Exception as e:
                logger.exception("Translate page %s", p.page_no)
                p.text_ru = p.text_original
            job.progress_percent = 35 + int(30 * (i + 1) / max(len(pages_rows), 1))
            session.commit()

    book.status = BookStatus.TRANSLATED
    session.commit()

    pages_for_seg = [(p.page_no, p.text_ru or "") for p in pages_rows]
    segments_data = segment_book_pages(pages_for_seg)

    book.status = BookStatus.TTS_PROCESSING
    session.commit()

    order = 0
    total_chars = 0
    for page_no, seg_text in segments_data:
        if not seg_text.strip():
            continue
        rel_audio = None
        duration = None
        try:
            mp3 = openai_ops.synthesize_speech_mp3(client, seg_text)
            if mp3:
                rel_audio = storage.save_audio(book.id, order, mp3)
                dur_path = storage.full_path(rel_audio)
                duration = audio_duration_sec(dur_path)
        except Exception as e:
            logger.exception("TTS segment %s", order)
            rel_audio = None
            duration = None
        seg = Segment(
            book_id=book.id,
            order_index=order,
            page_no=page_no,
            text=seg_text,
            audio_path=rel_audio,
            duration_sec=duration,
        )
        session.add(seg)
        total_chars += len(seg_text)
        order += 1
        job.progress_percent = 65 + int(34 * (order) / max(len(segments_data), 1))
        session.commit()

    record_usage(session, book.user_id, n_pages, total_chars)

    book.status = BookStatus.READY
    book.status_message = None
    session.commit()
    _set_job(session, job, JobStatus.SUCCESS, 100, None)


def fail_job(session: Session, job_id: str, message: str) -> None:
    """Помечает задачу и книгу как ошибочные."""
    session.rollback()
    job = session.get(Job, job_id)
    if job is None:
        return
    book = session.get(Book, job.book_id)
    if book:
        book.status = BookStatus.FAILED
        book.status_message = message[:2000]
    _set_job(session, job, JobStatus.FAILED, 0, message[:2000])
