"""Celery-приложение."""

from celery import Celery

from app.config import get_settings

settings = get_settings()

_rb = (settings.celery_result_backend or "").strip()
celery_app = Celery(
    "bookreader",
    broker=settings.celery_broker_url,
    backend=_rb if _rb else None,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600 * 4,
    include=["app.tasks"],
    broker_connection_retry_on_startup=True,
)
