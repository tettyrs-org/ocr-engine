import time
import pymupdf

import config as CONFIG

from error_handlers.errors import InvalidPdfError, TextLayerUnusableError
from schemas.ocr import OcrResponse, PageResult, Word

    
def _extract_page(page: pymupdf.Page) -> PageResult:
    width = page.rect.width
    height = page.rect.height
    
    words = [
        Word(
            text=w[4],
            bbox=[w[0] / width, w[1] / height, w[2] / width, w[3] / height],
            confidence=1.0,
        )
        for w in page.get_text("words")
    ]
    
    return PageResult(
        page=page.number + 1,
        width=width,
        height=height,
        deskew_angle=0.0,
        text=page.get_text("text"),
        words=words
    )

def extract_text(data: bytes) -> OcrResponse:
    started = time.perf_counter()
    
    try:
        with pymupdf.open(stream=data, filetype="pdf") as doc:
            pages = [_extract_page(page) for page in doc]
    except pymupdf.FileDataError as e:
        raise InvalidPdfError("Berkas bukan PDF yang sah") from e
    
    total_chars = sum(len(p.text.strip()) for p in pages)
    if not pages or total_chars / len(pages) < CONFIG.TEXT_LAYER_MIN_CHARS_PER_PAGE:
        raise TextLayerUnusableError(
            "Text layer tidak memadai, dokumen ini perlu OCR yang belum tersedia"
        )
    
    return OcrResponse(
        ocr_source="text_layer",
        engine=None,
        page_count=len(pages),
        duration_ms=int((time.perf_counter() - started) * 1000),
        pages=pages
    )