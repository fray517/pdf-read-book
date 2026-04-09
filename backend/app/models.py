"""ORM-модели SQLAlchemy."""

import enum
from datetime import datetime
from typing import List, Optional
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Базовый класс моделей."""


class BookStatus(str, enum.Enum):
    """Статус обработки книги."""

    UPLOADED = "uploaded"
    EXTRACTING = "extracting"
    TEXT_READY = "text_ready"
    TRANSLATING = "translating"
    TRANSLATED = "translated"
    TTS_PENDING = "tts_pending"
    TTS_PROCESSING = "tts_processing"
    READY = "ready"
    FAILED = "failed"


class JobType(str, enum.Enum):
    """Тип фоновой задачи."""

    FULL_PIPELINE = "full_pipeline"


class JobStatus(str, enum.Enum):
    """Статус задачи."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class ExtractionMethod(str, enum.Enum):
    """Способ получения текста страницы."""

    PDF_TEXT = "pdf_text"
    VISION_OCR = "vision_ocr"


def _uuid() -> str:
    return str(uuid4())


class User(Base):
    """Пользователь."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=_uuid,
    )
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
    )

    books: Mapped[List["Book"]] = relationship(
        "Book",
        back_populates="user",
        cascade="all, delete-orphan",
    )


class Book(Base):
    """Книга (PDF)."""

    __tablename__ = "books"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=_uuid,
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    title: Mapped[str] = mapped_column(String(512))
    pdf_path: Mapped[str] = mapped_column(String(1024))
    source_lang: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    target_lang: Mapped[str] = mapped_column(String(16), default="ru")
    status: Mapped[BookStatus] = mapped_column(
        Enum(BookStatus),
        default=BookStatus.UPLOADED,
    )
    status_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
    )

    user: Mapped["User"] = relationship("User", back_populates="books")
    pages: Mapped[List["Page"]] = relationship(
        "Page",
        back_populates="book",
        cascade="all, delete-orphan",
        order_by="Page.page_no",
    )
    segments: Mapped[List["Segment"]] = relationship(
        "Segment",
        back_populates="book",
        cascade="all, delete-orphan",
        order_by="Segment.order_index",
    )
    jobs: Mapped[List["Job"]] = relationship(
        "Job",
        back_populates="book",
        cascade="all, delete-orphan",
    )


class Page(Base):
    """Страница книги."""

    __tablename__ = "pages"
    __table_args__ = (UniqueConstraint("book_id", "page_no", name="uq_page_book_no"),)

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=_uuid,
    )
    book_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("books.id", ondelete="CASCADE"),
        index=True,
    )
    page_no: Mapped[int] = mapped_column(Integer)
    text_original: Mapped[str] = mapped_column(Text, default="")
    text_ru: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    extraction_method: Mapped[ExtractionMethod] = mapped_column(
        Enum(ExtractionMethod),
        default=ExtractionMethod.PDF_TEXT,
    )

    book: Mapped["Book"] = relationship("Book", back_populates="pages")


class Segment(Base):
    """Сегмент для озвучки."""

    __tablename__ = "segments"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=_uuid,
    )
    book_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("books.id", ondelete="CASCADE"),
        index=True,
    )
    order_index: Mapped[int] = mapped_column(Integer, index=True)
    page_no: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    text: Mapped[str] = mapped_column(Text)
    audio_path: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    duration_sec: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    book: Mapped["Book"] = relationship("Book", back_populates="segments")


class Job(Base):
    """Фоновая задача."""

    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=_uuid,
    )
    book_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("books.id", ondelete="CASCADE"),
        index=True,
    )
    job_type: Mapped[JobType] = mapped_column(Enum(JobType))
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus),
        default=JobStatus.PENDING,
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    progress_percent: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    book: Mapped["Book"] = relationship("Book", back_populates="jobs")


class UsageDaily(Base):
    """Учёт дневных квот по пользователю."""

    __tablename__ = "usage_daily"
    __table_args__ = (
        UniqueConstraint("user_id", "day", name="uq_usage_user_day"),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=_uuid,
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    day: Mapped[str] = mapped_column(String(10))
    pages_processed: Mapped[int] = mapped_column(Integer, default=0)
    chars_processed: Mapped[int] = mapped_column(Integer, default=0)
