"""Схемы ответов API."""

from pydantic import BaseModel, Field


class UploadResponse(BaseModel):
    """Ответ после загрузки PDF."""

    file_id: str = Field(description="Уникальный id файла на сервере")
    filename: str = Field(description="Исходное имя файла от клиента")


class PageText(BaseModel):
    """Текст одной страницы."""

    page_no: int = Field(ge=1, description="Номер страницы с 1")
    text: str = Field(description="Извлечённый текст")


class TextResponse(BaseModel):
    """Текст PDF по страницам и целиком."""

    file_id: str
    page_count: int
    pages: list[PageText]
    full_text: str = Field(
        description="Все страницы подряд, разделены пустой строкой",
    )


class DetectLanguageRequest(BaseModel):
    """Запрос определения языка по фрагменту текста."""

    text: str = Field(
        default="",
        max_length=2_000_000,
        description="Текст; для определения языка достаточно начала (см. сервис)",
    )


class DetectLanguageResponse(BaseModel):
    """Результат определения языка."""

    lang: str = Field(
        description="Код языка ISO 639-1, например en или ru",
    )


class TranslateResponse(BaseModel):
    """Текст на русском и метаданные (этап 3.2)."""

    file_id: str
    text: str = Field(description="Текст на русском")
    source_lang: str = Field(
        description="Код языка исходного текста (ISO 639-1)",
    )
    cached: bool = Field(
        default=False,
        description="Ответ прочитан из сохранённого файла *_ru.txt",
    )
