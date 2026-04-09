"""Точка входа FastAPI — этапы 1.x–3.x."""

import asyncio
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, File, HTTPException, Query, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.schemas import (
    DetectLanguageRequest,
    DetectLanguageResponse,
    PageText,
    SegmentItem,
    SegmentsResponse,
    TextResponse,
    TranslateResponse,
    UploadResponse,
)
from app.services.detect_language import detect_language_code
from app.services.pdf_ocr import extract_text_by_pages_with_ocr
from app.services.pdf_text import extract_text_by_pages, pages_to_full_text
from app.services.segment_pipeline import compute_segment_triples
from app.services.segmentation import MAX_SEGMENT_CHARS
from app.services.tts_mp3 import ensure_segment_mp3_file
from app.services.translate_ru import build_russian_text, load_pdf_full_text
from app.storage_paths import resolved_pdf_path, resolved_ru_txt_path

_TTS_VOICES = frozenset(
    {"alloy", "echo", "fable", "onyx", "nova", "shimmer"},
)

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
async def get_text(
    file_id: str,
    ocr: bool = Query(
        False,
        description=(
            "Для страниц с малым текстом вызвать Vision OCR (нужен "
            "OPENAI_API_KEY)"
        ),
    ),
) -> TextResponse:
    """Извлекает текст из PDF: слой текста; при ocr=true — OCR слабых страниц."""
    settings = get_settings()
    path = resolved_pdf_path(settings.storage_path, file_id)
    if not path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Файл не найден. Сначала загрузите PDF через POST /upload.",
        )

    def _load() -> tuple[list[tuple[int, str]], list[int]]:
        if ocr:
            return extract_text_by_pages_with_ocr(path)
        raw = extract_text_by_pages(path)
        return raw, []

    try:
        raw_pages, ocr_applied = await asyncio.to_thread(_load)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    pages = [PageText(page_no=n, text=t) for n, t in raw_pages]
    full_text = pages_to_full_text(raw_pages)
    return TextResponse(
        file_id=file_id,
        page_count=len(pages),
        pages=pages,
        full_text=full_text,
        ocr_pages=ocr_applied,
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


@app.get("/segments/{file_id}", response_model=SegmentsResponse)
async def get_segments(
    file_id: str,
    ocr: bool = Query(
        False,
        description="Как в GET /text: OCR для страниц с малым текстом",
    ),
    use_ru: bool = Query(
        False,
        description="Сегментировать текст из {file_id}_ru.txt (перевод 3.2)",
    ),
) -> SegmentsResponse:
    """Разбиение текста на сегменты для будущего TTS (этап 3.4)."""
    settings = get_settings()
    pdf_path = resolved_pdf_path(settings.storage_path, file_id)
    if not pdf_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Файл не найден. Сначала загрузите PDF через POST /upload.",
        )
    ru_path = resolved_ru_txt_path(settings.storage_path, file_id)

    def _build() -> tuple[list[tuple[int, int, str]], str]:
        return compute_segment_triples(pdf_path, ru_path, ocr, use_ru)

    try:
        triples, source = await asyncio.to_thread(_build)
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

    items = [
        SegmentItem(
            index=i,
            page_no=pn,
            text=tx,
            char_count=len(tx),
        )
        for i, pn, tx in triples
    ]
    return SegmentsResponse(
        file_id=file_id,
        source=source,
        max_chars=MAX_SEGMENT_CHARS,
        segment_count=len(items),
        segments=items,
    )


@app.get("/audio/{file_id}/{segment_index}")
async def get_segment_audio(
    file_id: str,
    segment_index: int,
    ocr: bool = Query(
        False,
        description="Как в GET /segments",
    ),
    use_ru: bool = Query(
        False,
        description="Как в GET /segments",
    ),
    voice: str = Query(
        "alloy",
        description="Голос OpenAI TTS",
    ),
    speed: float = Query(
        1.0,
        ge=0.25,
        le=4.0,
        description="Скорость воспроизведения (TTS)",
    ),
) -> FileResponse:
    """Отдаёт MP3 сегмента; при отсутствии файла — синтез (этап 3.5)."""
    if segment_index < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="segment_index должен быть неотрицательным",
        )
    if voice not in _TTS_VOICES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Недопустимый voice",
        )
    settings = get_settings()
    pdf_path = resolved_pdf_path(settings.storage_path, file_id)
    if not pdf_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Файл не найден. Сначала загрузите PDF через POST /upload.",
        )
    ru_path = resolved_ru_txt_path(settings.storage_path, file_id)

    def _ensure() -> Path:
        return ensure_segment_mp3_file(
            settings.storage_path,
            pdf_path,
            ru_path,
            file_id,
            segment_index,
            ocr,
            use_ru,
            voice,
            speed,
        )

    try:
        mp3_path = await asyncio.to_thread(_ensure)
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
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

    return FileResponse(
        mp3_path,
        media_type="audio/mpeg",
        filename=mp3_path.name,
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
