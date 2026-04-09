"""Абстракция локального файлового хранилища."""

import shutil
from pathlib import Path
from uuid import uuid4

from app.config import get_settings


class LocalStorage:
    """Хранение PDF и сгенерированных аудиофайлов на диске."""

    def __init__(self, base: Path | None = None) -> None:
        settings = get_settings()
        self._base = base or settings.storage_path
        self._base.mkdir(parents=True, exist_ok=True)

    def book_dir(self, book_id: str) -> Path:
        """Каталог артефактов книги."""
        d = self._base / book_id
        d.mkdir(parents=True, exist_ok=True)
        return d

    def save_pdf(self, book_id: str, filename: str, data: bytes) -> str:
        """Сохраняет PDF, возвращает относительный путь."""
        ext = Path(filename).suffix.lower() or ".pdf"
        rel = f"{book_id}/source{ext}"
        path = self._base / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return rel

    def save_audio(self, book_id: str, segment_index: int, data: bytes) -> str:
        """Сохраняет аудио сегмента (mp3)."""
        rel = f"{book_id}/audio/{segment_index:06d}.mp3"
        path = self._base / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return rel

    def full_path(self, relative: str) -> Path:
        """Абсолютный путь по относительному."""
        return (self._base / relative).resolve()

    def delete_book(self, book_id: str) -> None:
        """Удаляет каталог книги."""
        d = self._base / book_id
        if d.is_dir():
            shutil.rmtree(d, ignore_errors=True)

    def temp_name(self, suffix: str = ".bin") -> Path:
        """Временный файл внутри storage."""
        return self._base / f"_tmp_{uuid4().hex}{suffix}"


def get_storage() -> LocalStorage:
    """Экземпляр хранилища."""
    return LocalStorage()
