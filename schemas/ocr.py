from typing import Literal, Optional

from pydantic import BaseModel


class EngineInfo(BaseModel):
    name: str
    version: str


class Word(BaseModel):
    text: str
    bbox: list[float]
    confidence: float


class PageResult(BaseModel):
    page: int
    width: float
    height: float
    deskew_angle: float
    text: str
    words: list[Word]


class OcrResponse(BaseModel):
    ocr_source: Literal["text_layer", "ocr"]
    engine: Optional[EngineInfo] = None
    page_count: int
    duration_ms: int
    pages: list[PageResult]
