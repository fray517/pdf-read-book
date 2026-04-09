"""Регистрация и вход."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import create_access_token, hash_password, verify_password
from app.database import get_async_session
from app.deps import get_current_user
from app.models import User
from app.rate_limit import limiter
from app.schemas import Token, UserCreate, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=Token)
@limiter.limit("30/minute")
async def register(
    request: Request,
    body: UserCreate,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> Token:
    """Создание пользователя."""
    existing = await session.execute(
        select(User).where(User.email == body.email.lower()),
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email уже зарегистрирован",
        )
    user = User(
        email=body.email.lower(),
        password_hash=hash_password(body.password),
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    token = create_access_token(subject=user.id)
    return Token(access_token=token)


@router.get("/me", response_model=UserOut)
async def me(
    user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Текущий пользователь."""
    return user


@router.post("/login", response_model=Token)
@limiter.limit("60/minute")
async def login(
    request: Request,
    body: UserCreate,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> Token:
    """Вход по email и паролю."""
    result = await session.execute(
        select(User).where(User.email == body.email.lower()),
    )
    user = result.scalar_one_or_none()
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль",
        )
    token = create_access_token(subject=user.id)
    return Token(access_token=token)
