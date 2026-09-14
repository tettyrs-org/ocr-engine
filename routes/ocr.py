from fastapi import APIRouter, UploadFile, HTTPException, Header
from starlette.concurrency import run_in_threadpool
import filetype

from schemas.ocr import OcrResponse
from services.pdf_text import extract_text
from services.image_ocr import extract_image_text
from services.pdf_raster import extract_pdf_raster
from error_handlers.errors import InvalidPdfError, TextLayerUnusableError, UnsupportedMediaTypeError, FileTooLargeError
import config as CONFIG

router = APIRouter()

MAX_IMAGE_SIZE = 10 * 1024 * 1024
MAX_PDF_SIZE = 25 * 1024 * 1024
MAX_PDF_PAGES = 15

ALLOWED_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "application/pdf"
}

def detect_mime_type(data: bytes) -> str:
    return filetype.guess_mime(data) or "application/octet-stream"

def validate_file(data: bytes, mime_type: str) -> None:
    if mime_type not in ALLOWED_MIME_TYPES:
        raise UnsupportedMediaTypeError(f"Tipe berkas tidak didukung: {mime_type}. Hanya JPG, PNG, PDF.")
    
    if mime_type == "application/pdf":
        if len(data) > MAX_PDF_SIZE:
            raise FileTooLargeError(f"PDF melebihi batas 25 MB")
    else:
        if len(data) > MAX_IMAGE_SIZE:
            raise FileTooLargeError(f"Gambar melebihi batas 10 MB")

@router.post("/ocr", response_model=OcrResponse)
async def extract(
    file: UploadFile,
    traceparent: str = Header(None, alias="traceparent")
):
    data = await file.read()
    
    mime_type = detect_mime_type(data)
    validate_file(data, mime_type)
    
    if mime_type == "application/pdf":
        try:
            return await run_in_threadpool(extract_text, data)
        except TextLayerUnusableError:
            return await run_in_threadpool(extract_pdf_raster, data)
    else:
        return await run_in_threadpool(extract_image_text, data)

