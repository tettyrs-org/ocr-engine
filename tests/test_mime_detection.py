import pytest

from routes.ocr import detect_mime_type, validate_file
from error_handlers.errors import UnsupportedMediaTypeError, FileTooLargeError

PADDING = b"\x00" * 64

JPEG_BYTES = b"\xff\xd8\xff\xe0" + PADDING
PNG_BYTES = b"\x89PNG\r\n\x1a\n" + PADDING
PDF_BYTES = b"%PDF-1.4" + PADDING
GARBAGE_BYTES = b"\x31\x37\x42\x99" + PADDING

class TestValidateFile:
    def test_accepts_allowed_types(self):
        validate_file(PNG_BYTES, "image/png")
        validate_file(JPEG_BYTES, "image/jpeg")
        validate_file(PDF_BYTES, "application/pdf")
        
    def test_rejects_unknown_signature(self):
        mime_type = detect_mime_type(GARBAGE_BYTES)
        
        with pytest.raises(UnsupportedMediaTypeError):
            validate_file(GARBAGE_BYTES, mime_type)
            
    
    def test_rejects_oversized_image(self):
        oversized = b"\xff\xd8\xff\xe0" + b"\x00" * (10 * 1024 * 1024)
        
        with pytest.raises(FileTooLargeError):
            validate_file(oversized, "image/jpeg")
            
    def test_rejects_oversized_pdf(self):
        oversized = b"%PDF-1.4" + b"\x00" * (25 * 1024 * 1024)
        
        with pytest.raises(FileTooLargeError):
            validate_file(oversized, "application/pdf")