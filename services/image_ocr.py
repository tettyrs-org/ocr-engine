import threading
import time
from typing import Optional, Tuple

import cv2
import numpy as np

import config as CONFIG
from engines import OcrEngine, OcrEngineFactory
from engines.base import OcrEngineResult
from error_handlers.errors import OcrEngineUnavailableError, UnsupportedMediaTypeError
from schemas.ocr import EngineInfo, OcrResponse, PageResult, Word
from services.preprocess import preprocess_image

_engine: Optional[OcrEngine] = None
_engine_lock = threading.Lock()


def _get_engine() -> OcrEngine:
    global _engine

    if _engine is None:
        with _engine_lock:
            if _engine is None:
                try:
                    _engine = OcrEngineFactory.create(CONFIG.OCR_ENGINE)
                except (RuntimeError, ValueError) as e:
                    raise OcrEngineUnavailableError(
                        f"Mesin OCR '{CONFIG.OCR_ENGINE}' tidak siap: {e}"
                    ) from e

    return _engine


def decode_image(data: bytes) -> np.ndarray:
    buffer = np.frombuffer(data, dtype=np.uint8)
    image = cv2.imdecode(buffer, cv2.IMREAD_COLOR)

    if image is None:
        raise UnsupportedMediaTypeError("Berkas gambar tidak dapat dibaca")

    return image


def recognize_page(
    image: np.ndarray,
    page_number: int = 1,
    source_dpi: int = 72,
) -> Tuple[PageResult, OcrEngineResult]:
    prep = preprocess_image(image, source_dpi=source_dpi)
    engine_result = _get_engine().recognize(prep.image)

    width, height = prep.output_resolution

    words = [
        Word(
            text=w.text,
            bbox=[
                w.bbox[0] / width,
                w.bbox[1] / height,
                w.bbox[2] / width,
                w.bbox[3] / height,
            ],
            confidence=w.confidence,
        )
        for w in engine_result.words
    ]

    page = PageResult(
        page=page_number,
        width=width,
        height=height,
        deskew_angle=prep.deskew_angle,
        text=" ".join(w.text for w in engine_result.words),
        words=words,
    )

    return page, engine_result


def extract_image_text(data: bytes) -> OcrResponse:
    started = time.perf_counter()

    image = decode_image(data)
    page, engine_result = recognize_page(image)

    return OcrResponse(
        ocr_source="ocr",
        engine=EngineInfo(
            name=engine_result.engine_name,
            version=engine_result.engine_version,
        ),
        page_count=1,
        duration_ms=int((time.perf_counter() - started) * 1000),
        pages=[page],
    )
