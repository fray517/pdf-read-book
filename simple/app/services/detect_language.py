"""Определение языка по началу текста (этап 3.1)."""

from langdetect import LangDetectException, detect

# Анализируем начало документа; дальше выигрыша почти нет.
_SAMPLE_MAX = 2000
# Короче — langdetect часто ошибается или падает.
_MIN_CHARS = 20


def detect_language_code(text: str) -> str:
    """
    Возвращает код языка ISO 639-1 (например en, ru).

    Raises:
        ValueError: пустой/слишком короткий текст или сбой детектора.
    """
    stripped = text.strip()
    if not stripped:
        raise ValueError("Текст не должен быть пустым")
    if len(stripped) < _MIN_CHARS:
        raise ValueError(
            f"Нужно не меньше {_MIN_CHARS} символов текста",
        )
    sample = stripped[:_SAMPLE_MAX]
    try:
        return detect(sample)
    except LangDetectException as exc:
        raise ValueError(
            "Не удалось определить язык: слишком мало осмысленного текста",
        ) from exc
