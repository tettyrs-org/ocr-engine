import os
import time
from typing import Optional

import cv2
import numpy as np
import pytesseract

import config as CONFIG
from engines.base import OcrEngine, OcrEngineFactory, OcrEngineResult, WordResult


class TesseractEngine(OcrEngine):
    def __init__(
        self,
        data_prefix: Optional[str] = None,
        lang: Optional[str] = None,
        cmd: Optional[str] = None,                                    # ← baru
        config: str = "--oem 3 --psm 6",
    ):
        self.data_prefix = data_prefix or getattr(CONFIG, "TESSERACT_DATA_PREFIX", None)
        self.lang = lang or getattr(CONFIG, "TESSERACT_LANG", "ind")
        self.cmd = cmd or getattr(CONFIG, "TESSERACT_CMD", None)      # ← baru
        self.config = config

        if self.cmd:                                                  # ← baru
            pytesseract.pytesseract.tesseract_cmd = self.cmd          # ← baru

        if self.data_prefix:
            os.environ["TESSDATA_PREFIX"] = self.data_prefix

        try:
            pytesseract.get_tesseract_version()
        except Exception as e:
            raise RuntimeError(f"Tesseract tidak ditemukan atau gagal dijalankan: {e}") from e

    def recognize(self, image: np.ndarray) -> OcrEngineResult:
        started = time.perf_counter()

        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB) if image.ndim == 3 else image

        data = pytesseract.image_to_data(
            rgb,
            lang=self.lang,
            config=self.config,
            output_type=pytesseract.Output.DICT,
        )

        words = []
        confidences = []

        for i in range(len(data["text"])):
            text = data["text"][i].strip()
            conf = float(data["conf"][i])

            if not text or conf <= 0:
                continue

            x, y = int(data["left"][i]), int(data["top"][i])
            w, h = int(data["width"][i]), int(data["height"][i])

            words.append(
                WordResult(text=text, bbox=[x, y, x + w, y + h], confidence=conf / 100.0)
            )
            confidences.append(conf / 100.0)

        duration_ms = int((time.perf_counter() - started) * 1000)
        confidence_mean = sum(confidences) / len(confidences) if confidences else 0.0

        return OcrEngineResult(
            words=words,
            engine_name=self.get_name(),
            engine_version=self._get_version(),
            confidence_mean=confidence_mean,
            duration_ms=duration_ms,
        )

    def _get_version(self) -> str:
        try:
            return str(pytesseract.get_tesseract_version())
        except Exception:
            return "unknown"

    def get_name(self) -> str:
        return "tesseract"

    def get_version(self) -> str:
        return self._get_version()


OcrEngineFactory.register("tesseract", TesseractEngine)
