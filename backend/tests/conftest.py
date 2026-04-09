"""Pytest: SQLite для изолированных smoke-тестов."""

import os

# До импорта приложения — подмена URL БД.
os.environ.setdefault(
    "DATABASE_URL",
    "sqlite+aiosqlite:///./test_app.db",
)
os.environ.setdefault(
    "DATABASE_SYNC_URL",
    "sqlite:///./test_app_sync.db",
)
