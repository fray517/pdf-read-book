"""Безопасное разрешение пути к загруженному PDF."""

import re
from pathlib import Path

from fastapi import HTTPException, status

_UUID = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.I,
)


def resolved_pdf_path(storage_root: Path, file_id: str) -> Path:
    """Путь к `{uuid}.pdf` внутри каталога хранилища."""
    fid = file_id.strip()
    if not _UUID.match(fid):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Некорректный file_id",
        )
    root = storage_root.resolve()
    path = (root / f"{fid}.pdf").resolve()
    try:
        path.relative_to(root)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Некорректный путь",
        ) from None
    return path


def resolved_ru_txt_path(storage_root: Path, file_id: str) -> Path:
    """Путь к `{uuid}_ru.txt` рядом с PDF."""
    fid = file_id.strip()
    if not _UUID.match(fid):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Некорректный file_id",
        )
    root = storage_root.resolve()
    path = (root / f"{fid}_ru.txt").resolve()
    try:
        path.relative_to(root)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Некорректный путь",
        ) from None
    return path
