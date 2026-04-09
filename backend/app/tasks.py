"""Фоновые задачи Celery."""

import logging

from app.celery_app import celery_app
from app.database import SessionLocal
from app.services.pipeline_sync import fail_job, run_book_pipeline
from app.storage import LocalStorage

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.process_book_task", bind=True, max_retries=2)
def process_book_task(self, job_id: str) -> None:
    """Запускает конвейер обработки книги."""
    session = SessionLocal()
    storage = LocalStorage()
    try:
        run_book_pipeline(session, job_id, storage)
    except Exception as e:
        logger.exception("Pipeline failed job=%s", job_id)
        try:
            fail_job(session, job_id, str(e))
        except Exception:
            logger.exception("fail_job error")
        raise
    finally:
        session.close()
