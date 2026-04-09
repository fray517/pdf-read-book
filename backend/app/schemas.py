"""Pydantic-схемы API."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field

from app.models import BookStatus, ExtractionMethod, JobStatus, JobType


class Token(BaseModel):
    """Ответ с JWT."""

    access_token: str
    token_type: str = "bearer"


class UserCreate(BaseModel):
    """Регистрация."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserOut(BaseModel):
    """Пользователь в ответах."""

    id: str
    email: str

    model_config = {"from_attributes": True}


class BookCreateResponse(BaseModel):
    """После загрузки PDF."""

    book_id: str
    job_id: str


class BookListItem(BaseModel):
    """Элемент списка книг."""

    id: str
    title: str
    status: BookStatus
    source_lang: Optional[str]
    created_at: datetime
    status_message: Optional[str] = None

    model_config = {"from_attributes": True}


class BookDetail(BaseModel):
    """Детали книги."""

    id: str
    title: str
    status: BookStatus
    source_lang: Optional[str]
    target_lang: str
    created_at: datetime
    pages_count: int = 0
    segments_count: int = 0
    status_message: Optional[str] = None

    model_config = {"from_attributes": True}


class SegmentOut(BaseModel):
    """Сегмент для читалки."""

    id: str
    order_index: int
    page_no: Optional[int]
    text: str
    duration_sec: Optional[float]
    has_audio: bool

    model_config = {"from_attributes": True}


class SegmentPage(BaseModel):
    """Страница списка сегментов."""

    items: List[SegmentOut]
    total: int
    page: int
    page_size: int


class JobOut(BaseModel):
    """Статус задачи."""

    id: str
    book_id: str
    job_type: JobType
    status: JobStatus
    error_message: Optional[str]
    progress_percent: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
