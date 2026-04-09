"""Подключение к БД: async для API, sync для Celery."""

from collections.abc import AsyncGenerator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings

settings = get_settings()


def _sqlite_connect_args(url: str) -> dict:
    """SQLite в многопоточности (Celery / пул) требует check_same_thread=False."""
    if url.startswith("sqlite:"):
        return {"check_same_thread": False}
    return {}


async_engine = create_async_engine(
    settings.database_url,
    echo=False,
)
AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

sync_engine = create_engine(
    settings.database_sync_url,
    echo=False,
    connect_args=_sqlite_connect_args(settings.database_sync_url),
)
SessionLocal = sessionmaker(
    bind=sync_engine,
    autocommit=False,
    autoflush=False,
)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Сессия для FastAPI."""
    async with AsyncSessionLocal() as session:
        yield session


def get_sync_session() -> Session:
    """Синхронная сессия (Celery)."""
    return SessionLocal()
