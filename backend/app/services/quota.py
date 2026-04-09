"""Дневные квоты пользователя."""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import UsageDaily


def _today_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def get_or_create_usage(session: Session, user_id: str) -> UsageDaily:
    """Текущая запись usage за сегодня."""
    day = _today_utc()
    row = session.execute(
        select(UsageDaily).where(
            UsageDaily.user_id == user_id,
            UsageDaily.day == day,
        )
    ).scalar_one_or_none()
    if row:
        return row
    row = UsageDaily(user_id=user_id, day=day)
    session.add(row)
    session.flush()
    return row


def check_can_process(
    session: Session,
    user_id: str,
    pages: int,
    chars_estimate: int,
) -> tuple[bool, str]:
    """
    Проверяет квоты. Возвращает (ok, сообщение при отказе).
    """
    settings = get_settings()
    u = get_or_create_usage(session, user_id)
    if u.pages_processed + pages > settings.daily_pages_quota:
        return False, "Превышена дневная квота страниц"
    if u.chars_processed + chars_estimate > settings.daily_chars_quota:
        return False, "Превышена дневная квота объёма текста"
    return True, ""


def record_usage(
    session: Session,
    user_id: str,
    pages: int,
    chars_delta: int,
) -> None:
    """Увеличивает счётчики после успешной обработки."""
    u = get_or_create_usage(session, user_id)
    u.pages_processed += pages
    u.chars_processed += chars_delta
