import time

import cv2
import numpy as np
import pymupdf

import config as CONFIG
from error_handlers.errors import InvalidPdfError, PageLimitExceededError
from schemas.ocr import EngineInfo, OcrResponse
from services.image_ocr import recognize_page


def _pixmap_to_bgr(pix: pymupdf.Pixmap) -> np.ndarray:
    buffer = np.frombuffer(pix.samples, dtype=np.uint8)
    rgb = buffer.reshape(pix.height, pix.width, pix.n)

    return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)


def extract_pdf_raster(data: bytes) -> OcrResponse:
    started = time.perf_counter()
    dpi = CONFIG.PDF_RASTER_DPI

    pages = []
    engine_result = None

    try:
        doc = pymupdf.open(stream=data, filetype="pdf")
    except pymupdf.FileDataError as e:
        raise InvalidPdfError("Berkas bukan PDF yang sah") from e

    with doc:
        if doc.page_count > CONFIG.PDF_MAX_PAGES:
            raise PageLimitExceededError(
                f"PDF melebihi batas {CONFIG.PDF_MAX_PAGES} halaman"
            )

        for page in doc:
            pix = page.get_pixmap(dpi=dpi, colorspace=pymupdf.csRGB, alpha=False)
            image = _pixmap_to_bgr(pix)

            page_result, engine_result = recognize_page(
                image,
                page_number=page.number + 1,
                source_dpi=dpi,
            )
            pages.append(page_result)

    return OcrResponse(
        ocr_source="ocr",
        engine=(
            EngineInfo(
                name=engine_result.engine_name,
                version=engine_result.engine_version,
            )
            if engine_result
            else None
        ),
        page_count=len(pages),
        duration_ms=int((time.perf_counter() - started) * 1000),
        pages=pages,
    )
