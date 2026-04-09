"""Точка входа FastAPI — этапы 1.x–3.x."""

import asyncio
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, File, HTTPException, Query, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.schemas import (
    DetectLanguageRequest,
    DetectLanguageResponse,
    PageText,
    TextResponse,
    TranslateResponse,
    UploadResponse,
)
from app.services.detect_language import detect_language_code
from app.services.pdf_text import extract_text_by_pages, pages_to_full_text
from app.services.translate_ru import build_russian_text, load_pdf_full_text
from app.storage_paths import resolved_pdf_path, resolved_ru_txt_path

app = FastAPI(
    title="PDF Reader (простой)",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root() -> RedirectResponse:
    """С корня — заглушка /web/ или Swagger, если каталога нет."""
    web = get_settings().web_static_path.resolve()
    if web.is_dir():
        return RedirectResponse(url="/web/", status_code=302)
    return RedirectResponse(url="/docs", status_code=302)


@app.get("/health")
async def health() -> dict[str, str]:
    """Проверка, что сервер запущен."""
    return {"status": "ok"}


@app.get("/config/status")
async def config_status() -> dict[str, str | bool]:
    """
    Проверка, что настройки читаются из .env.
    Ключ OpenAI в ответ не попадает — только факт наличия.
    """
    s = get_settings()
    return {
        "storage_path": str(s.storage_path.resolve()),
        "openai_configured": bool(s.openai_api_key.strip()),
    }


@app.post("/upload", response_model=UploadResponse)
async def upload_pdf(
    file: UploadFile = File(..., description="Один PDF-файл"),
) -> UploadResponse:
    """Сохраняет PDF в STORAGE_PATH под уникальным именем."""
    raw_name = file.filename or ""
    if not raw_name.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нужен файл с расширением .pdf",
        )
    settings = get_settings()
    root = settings.storage_path
    root.mkdir(parents=True, exist_ok=True)
    file_id = str(uuid4())
    dest: Path = root / f"{file_id}.pdf"
    data = await file.read()
    dest.write_bytes(data)
    return UploadResponse(file_id=file_id, filename=raw_name)


@app.get("/text/{file_id}", response_model=TextResponse)
async def get_text(file_id: str) -> TextResponse:
    """Извлекает текст из ранее загруженного PDF (слой текста, не OCR)."""
    settings = get_settings()
    path = resolved_pdf_path(settings.storage_path, file_id)
    if not path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Файл не найден. Сначала загрузите PDF через POST /upload.",
        )
    raw_pages = extract_text_by_pages(path)
    pages = [PageText(page_no=n, text=t) for n, t in raw_pages]
    full_text = pages_to_full_text(raw_pages)
    return TextResponse(
        file_id=file_id,
        page_count=len(pages),
        pages=pages,
        full_text=full_text,
    )


@app.post("/detect-language", response_model=DetectLanguageResponse)
async def detect_language(
    body: DetectLanguageRequest,
) -> DetectLanguageResponse:
    """Определяет язык по переданному тексту (начало анализируется на сервере)."""
    try:
        lang = detect_language_code(body.text)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    return DetectLanguageResponse(lang=lang)


@app.post("/translate/{file_id}", response_model=TranslateResponse)
async def translate_to_russian(
    file_id: str,
    refresh: bool = Query(
        False,
        description="Пересчитать перевод, игнорируя сохранённый _ru.txt",
    ),
) -> TranslateResponse:
    """Переводит извлечённый текст PDF на русский; сохраняет `{file_id}_ru.txt`."""
    settings = get_settings()
    pdf_path = resolved_pdf_path(settings.storage_path, file_id)
    if not pdf_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Файл не найден. Сначала загрузите PDF через POST /upload.",
        )
    ru_path = resolved_ru_txt_path(settings.storage_path, file_id)

    if ru_path.is_file() and not refresh:

        def _read_cached() -> tuple[str, str]:
            body = ru_path.read_text(encoding="utf-8")
            try:
                ft = load_pdf_full_text(pdf_path)
                src = detect_language_code(ft)
            except ValueError:
                src = "und"
            return body, src

        text_ru, src_lang = await asyncio.to_thread(_read_cached)
        return TranslateResponse(
            file_id=file_id,
            text=text_ru,
            source_lang=src_lang,
            cached=True,
        )

    try:
        ru_text, src_lang = await asyncio.to_thread(
            build_russian_text,
            pdf_path,
            ru_path,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    return TranslateResponse(
        file_id=file_id,
        text=ru_text,
        source_lang=src_lang,
        cached=False,
    )


def _mount_web_static(app: FastAPI) -> None:
    """Раздача каталога WEB_STATIC_PATH (заглушка или будущий dist)."""
    root = get_settings().web_static_path.resolve()
    if not root.is_dir():
        return
    app.mount(
        "/web",
        StaticFiles(directory=str(root), html=True),
        name="web",
    )


_mount_web_static(app)
