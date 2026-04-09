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
