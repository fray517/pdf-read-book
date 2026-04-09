"""Статус фоновых задач."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_session
from app.deps import get_current_user
from app.models import Book, Job, User
from app.schemas import JobOut

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/{job_id}", response_model=JobOut)
async def get_job(
    job_id: str,
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[User, Depends(get_current_user)],
) -> Job:
    """Статус задачи (только своя книга)."""
    result = await session.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    book = await session.get(Book, job.book_id)
    if book is None or book.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return job
