"""Точка входа FastAPI."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.config import get_settings
from app.rate_limit import limiter
from app.database import async_engine
from app.models import Base
from app.routers import auth, books, jobs

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Создание таблиц при старте (для разработки)."""
    cfg = get_settings()
    Path("data").mkdir(parents=True, exist_ok=True)
    cfg.storage_path.mkdir(parents=True, exist_ok=True)
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await async_engine.dispose()


settings = get_settings()

app = FastAPI(
    title="PDF Book Reader API",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

prefix = settings.api_v1_prefix
app.include_router(auth.router, prefix=prefix)
app.include_router(books.router, prefix=prefix)
app.include_router(jobs.router, prefix=prefix)


@app.get("/health")
async def health() -> dict[str, str]:
    """Проверка живости сервиса."""
    return {"status": "ok"}


@app.get("/")
async def root() -> dict[str, str]:
    """Корень API."""
    return {"service": "pdf-book-reader", "docs": "/docs"}
