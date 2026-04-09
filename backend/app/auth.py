"""JWT и хеширование паролей."""

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import bcrypt
from jose import JWTError, jwt

from app.config import get_settings


def verify_password(plain: str, hashed: str) -> bool:
    """Проверка пароля (bcrypt, совместимо с любой версией пакета bcrypt)."""
    try:
        return bcrypt.checkpw(
            plain.encode("utf-8"),
            hashed.encode("utf-8"),
        )
    except (ValueError, TypeError):
        return False


def hash_password(plain: str) -> str:
    """Хеш пароля."""
    digest = bcrypt.hashpw(
        plain.encode("utf-8"),
        bcrypt.gensalt(rounds=12),
    )
    return digest.decode("ascii")


def create_access_token(
    subject: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Создание JWT."""
    settings = get_settings()
    expire = datetime.now(timezone.utc) + (
        expires_delta
        if expires_delta
        else timedelta(minutes=settings.access_token_expire_minutes)
    )
    to_encode: dict[str, Any] = {"sub": subject, "exp": expire}
    return jwt.encode(
        to_encode,
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


def decode_token(token: str) -> Optional[str]:
    """Декодирование JWT; возвращает user_id или None."""
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
        sub = payload.get("sub")
        if isinstance(sub, str):
            return sub
        return None
    except JWTError:
        return None
