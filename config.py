import os

from dotenv import load_dotenv

load_dotenv()

LOG_LEVEL = os.getenv("OCR_LOG_LEVEL")
SERVICE_NAME = os.getenv("OCR_SERVICE_NAME")
SERVICE_VERSION = os.getenv("OCR_SERVICE_VERSION")
ENVIRONMENT = os.getenv("OCR_ENVIRONMENT")
HOST = os.getenv("OCR_HOST")
PORT = int(os.getenv("OCR_PORT"))
TEXT_LAYER_MIN_CHARS_PER_PAGE = int(os.getenv("OCR_TEXT_LAYER_MIN_CHARS"))

PREPROCESS_DESKEW = os.getenv("PREPROCESS_DESKEW").lower() == "true"
PREPROCESS_DENOISE = os.getenv("PREPROCESS_DENOISE").lower() == "true"
PREPROCESS_PERSPECTIVE = os.getenv("PREPROCESS_PERSPECTIVE").lower() == "true"
PREPROCESS_THRESHOLD = os.getenv("PREPROCESS_THRESHOLD").lower() == "true"
PREPROCESS_UPSCALE_DPI = int(os.getenv("PREPROCESS_UPSCALE_DPI"))
PREPROCESS_MORPHOLOGY = os.getenv("PREPROCESS_MORPHOLOGY").lower() == "true"

OCR_ENGINE = os.getenv("OCR_ENGINE")

TESSERACT_DATA_PREFIX = os.getenv("TESSERACT_DATA_PREFIX") or None
TESSERACT_LANG = os.getenv("TESSERACT_LANG")
TESSERACT_CMD = os.getenv("TESSERACT_CMD") or None

PDF_RASTER_DPI = int(os.getenv("PDF_RASTER_DPI"))
PDF_MAX_PAGES = int(os.getenv("PDF_MAX_PAGES"))
