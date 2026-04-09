"""Синтез MP3 через OpenAI TTS (этап 3.5)."""

from __future__ import annotations

from pathlib import Path

from openai import (
    APIConnectionError,
    APITimeoutError,
    OpenAI,
    RateLimitError,
)

from app.services.openai_client import get_openai_client
from app.services.segment_pipeline import compute_segment_triples

TTS_MODEL = "tts-1"
# Совпадает с лимитом в OpenAI Speech API.
_MAX_INPUT = 4096


def synthesize_speech_mp3(
    client: OpenAI,
    text: str,
    *,
    voice: str = "alloy",
    speed: float = 1.0,
) -> bytes:
    """Генерирует MP3-байты для одного сегмента."""
    body = text.strip()
    if not body:
        return b""
    payload = body[:_MAX_INPUT]
    try:
        audio = client.audio.speech.create(
            model=TTS_MODEL,
            voice=voice,
            input=payload,
            response_format="mp3",
            speed=speed,
        )
    except APIConnectionError as exc:
        raise RuntimeError(
            "Нет соединения с API OpenAI (TTS).",
        ) from exc
    except APITimeoutError as exc:
        raise RuntimeError("Таймаут OpenAI (TTS).") from exc
    except RateLimitError as exc:
        raise RuntimeError("Лимит запросов OpenAI (TTS).") from exc
    if hasattr(audio, "read"):
        return audio.read()
    return getattr(audio, "content", b"")


def audio_dir_for_file(storage_root: Path, file_id: str) -> Path:
    """Каталог `data/audio/{file_id}/` рядом с `data/files`."""
    return storage_root.resolve().parent / "audio" / file_id


def segment_mp3_filename(index: int, voice: str, speed: float) -> str:
    """Имя файла с учётом голоса и скорости (кэш TTS)."""
    spd = f"{speed:.2f}".replace(".", "_")
    return f"{index}_{voice}_{spd}.mp3"


def segment_mp3_path(
    storage_root: Path,
    file_id: str,
    index: int,
    voice: str,
    speed: float,
) -> Path:
    """Путь к MP3 сегмента."""
    name = segment_mp3_filename(index, voice, speed)
    return audio_dir_for_file(storage_root, file_id) / name


def ensure_segment_mp3_file(
    storage_root: Path,
    pdf_path: Path,
    ru_path: Path,
    file_id: str,
    segment_index: int,
    ocr: bool,
    use_ru: bool,
    voice: str,
    speed: float,
) -> Path:
    """
    Гарантирует наличие файла MP3 для сегмента (создаёт при отсутствии).

    Raises:
        LookupError: индекс вне диапазона сегментов.
        ValueError: пустой сегмент или пустой ответ TTS.
        RuntimeError: нет ключа OpenAI или ошибка API (через synthesize).
    """
    triples, _ = compute_segment_triples(pdf_path, ru_path, ocr, use_ru)
    if segment_index < 0 or segment_index >= len(triples):
        raise LookupError(
            "Нет сегмента с таким номером",
        )
    text = triples[segment_index][2]
    if not text.strip():
        raise ValueError("Пустой сегмент")
    out = segment_mp3_path(
        storage_root,
        file_id,
        segment_index,
        voice,
        speed,
    )
    if out.is_file():
        return out
    client = get_openai_client()
    mp3 = synthesize_speech_mp3(
        client,
        text,
        voice=voice,
        speed=speed,
    )
    if not mp3:
        raise ValueError("TTS вернул пустые данные")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(mp3)
    return out
