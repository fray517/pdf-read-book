"""Книги и сегменты."""

import logging
import tempfile
from pathlib import Path
from typing import Annotated, Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import SessionLocal, get_async_session
from app.deps import get_current_user
from app.rate_limit import limiter
from app.models import Book, BookStatus, Job, JobStatus, JobType, Page, Segment, User
from app.schemas import BookCreateResponse, BookDetail, BookListItem, SegmentPage, SegmentOut
from app.services.pdf_extract import page_count
from app.services.quota import check_can_process
from app.storage import get_storage
from app.tasks import process_book_task

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/books", tags=["books"])


@router.post("", response_model=BookCreateResponse)
@limiter.limit("120/hour")
async def upload_book(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[User, Depends(get_current_user)],
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
) -> BookCreateResponse:
    """Загрузка PDF и постановка в очередь обработки."""
    settings = get_settings()
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ожидается файл .pdf",
        )
    data = await file.read()
    max_bytes = settings.max_upload_mb * 1024 * 1024
    if len(data) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Файл больше {settings.max_upload_mb} МБ",
        )

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(data)
        tmp_path = Path(tmp.name)
    try:
        n_pages = page_count(tmp_path)
    finally:
        tmp_path.unlink(missing_ok=True)

    if n_pages > settings.max_pdf_pages:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Слишком много страниц: {n_pages} "
                f"(макс. {settings.max_pdf_pages})"
            ),
        )

    sync = SessionLocal()
    try:
        ok, msg = check_can_process(
            sync,
            user.id,
            n_pages,
            n_pages * 3000,
        )
        if not ok:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=msg,
            )
    finally:
        sync.close()

    storage = get_storage()
    book = Book(
        user_id=user.id,
        title=(title or file.filename or "book").strip()[:500],
        pdf_path="",
        status=BookStatus.UPLOADED,
    )
    session.add(book)
    await session.flush()
    rel = storage.save_pdf(book.id, file.filename or "book.pdf", data)
    book.pdf_path = rel
    await session.commit()
    await session.refresh(book)

    job = Job(
        book_id=book.id,
        job_type=JobType.FULL_PIPELINE,
        status=JobStatus.PENDING,
        progress_percent=0,
    )
    session.add(job)
    await session.commit()
    await session.refresh(job)

    try:
        process_book_task.delay(str(job.id))
    except Exception as exc:
        logger.warning("Celery: задача не поставлена в очередь: %s", exc)
        book.status = BookStatus.FAILED
        book.status_message = (
            "Очередь задач недоступна. Запустите Redis "
            "(docker compose up redis -d) и загрузите PDF снова."
        )
        job.status = JobStatus.FAILED
        job.error_message = str(exc)[:2000]
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=book.status_message,
        )

    return BookCreateResponse(book_id=book.id, job_id=job.id)


@router.get("", response_model=list[BookListItem])
async def list_books(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[User, Depends(get_current_user)],
) -> list[Book]:
    """Список книг пользователя."""
    result = await session.execute(
        select(Book).where(Book.user_id == user.id).order_by(Book.created_at.desc()),
    )
    return list(result.scalars().all())


@router.get("/{book_id}", response_model=BookDetail)
async def get_book(
    book_id: str,
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[User, Depends(get_current_user)],
) -> BookDetail:
    """Метаданные книги."""
    book = await session.get(Book, book_id)
    if book is None or book.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    pc = await session.scalar(
        select(func.count()).select_from(Page).where(Page.book_id == book.id),
    )
    sc = await session.scalar(
        select(func.count()).select_from(Segment).where(Segment.book_id == book.id),
    )
    return BookDetail(
        id=book.id,
        title=book.title,
        status=book.status,
        source_lang=book.source_lang,
        target_lang=book.target_lang,
        created_at=book.created_at,
        pages_count=int(pc or 0),
        segments_count=int(sc or 0),
        status_message=book.status_message,
    )


@router.delete("/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_book(
    book_id: str,
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[User, Depends(get_current_user)],
) -> None:
    """Удаление книги и файлов."""
    book = await session.get(Book, book_id)
    if book is None or book.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    storage = get_storage()
    storage.delete_book(book.id)
    await session.delete(book)
    await session.commit()


@router.get("/{book_id}/segments", response_model=SegmentPage)
async def list_segments(
    book_id: str,
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[User, Depends(get_current_user)],
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
) -> SegmentPage:
    """Сегменты с пагинацией."""
    book = await session.get(Book, book_id)
    if book is None or book.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    total = await session.scalar(
        select(func.count()).select_from(Segment).where(Segment.book_id == book_id),
    )
    total = int(total or 0)
    offset = (page - 1) * page_size
    result = await session.execute(
        select(Segment)
        .where(Segment.book_id == book_id)
        .order_by(Segment.order_index)
        .offset(offset)
        .limit(page_size),
    )
    rows = list(result.scalars().all())
    items = [
        SegmentOut(
            id=s.id,
            order_index=s.order_index,
            page_no=s.page_no,
            text=s.text,
            duration_sec=s.duration_sec,
            has_audio=bool(s.audio_path),
        )
        for s in rows
    ]
    return SegmentPage(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{book_id}/segments/{order_index}/audio")
async def get_segment_audio(
    book_id: str,
    order_index: int,
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[User, Depends(get_current_user)],
) -> FileResponse:
    """Отдача MP3 сегмента."""
    book = await session.get(Book, book_id)
    if book is None or book.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    result = await session.execute(
        select(Segment).where(
            Segment.book_id == book_id,
            Segment.order_index == order_index,
        ),
    )
    seg = result.scalar_one_or_none()
    if seg is None or not seg.audio_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    storage = get_storage()
    path = storage.full_path(seg.audio_path)
    if not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return FileResponse(
        path,
        media_type="audio/mpeg",
        filename=f"segment_{order_index:06d}.mp3",
    )
