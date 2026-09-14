import cv2
import numpy as np
import pytest

from error_handlers.errors import UnsupportedMediaTypeError
from services.image_ocr import decode_image, extract_image_text



def _png_bytes(text: str = "HALO DUNIA") -> bytes:
    image = np.full((200, 600, 3), 255, dtype=np.uint8)
    cv2.putText(
        image, text, (20, 120), cv2.FONT_HERSHEY_SIMPLEX, 2.0, (0, 0, 0), 4, cv2.LINE_AA
    )

    ok, buffer = cv2.imencode(".png", image)
    assert ok

    return buffer.tobytes()


class TestDecodeImage:
    def test_decodes_png(self):
        image = decode_image(_png_bytes())

        assert image.shape == (200, 600, 3)

    def test_rejects_undecodable_bytes(self):
        with pytest.raises(UnsupportedMediaTypeError):
            decode_image(b"\x89PNG\r\n\x1a\n" + b"\x00" * 64)


@pytest.mark.ocr
class TestExtractImageText:
    def test_returns_ocr_response(self):
        response = extract_image_text(_png_bytes())

        assert response.ocr_source == "ocr"
        assert response.page_count == 1
        assert len(response.pages) == 1
        assert response.engine is not None
        assert response.engine.name == "tesseract"

    def test_recognizes_rendered_text(self):
        response = extract_image_text(_png_bytes("HALO"))

        assert "HALO" in response.pages[0].text.upper()

    def test_bbox_is_normalized(self):
        response = extract_image_text(_png_bytes())

        for word in response.pages[0].words:
            for coord in word.bbox:
                assert 0.0 <= coord <= 1.0
