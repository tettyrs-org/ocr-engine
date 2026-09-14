from engines.base import (
    OcrEngine,
    OcrEngineFactory,
    OcrEngineResult,
    WordResult,
)

# Diimpor demi efek sampingnya: modul engine mendaftarkan dirinya ke factory.
from engines import tesseract as _tesseract  # noqa: F401,E402

__all__ = [
    "OcrEngine",
    "OcrEngineFactory",
    "OcrEngineResult",
    "WordResult",
]
