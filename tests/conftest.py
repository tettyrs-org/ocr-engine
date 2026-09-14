from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


def _tesseract_available() -> bool:
    try:
        import config as CONFIG
        from engines import OcrEngineFactory

        OcrEngineFactory.create(CONFIG.OCR_ENGINE)
        return True
    except Exception:
        return False

def pytest_collection_modifyitems(config, items):
    if _tesseract_available():
        return

    skip_ocr = pytest.mark.skip(reason="biner tesseract tidak terpasang")
    for item in items:
        if "ocr" in item.keywords:
            item.add_marker(skip_ocr)


@pytest.fixture(scope="session")
def read_fixture():
    def _read(name: str) -> bytes:
        return (FIXTURES / name).read_bytes()

    return _read
