# ocr-engine

An OCR service for official travel documents: it accepts an image or a PDF and returns the text
along with coordinates and a confidence score for every word.

The service is deliberately **unaware of business context**. It does not know what an assignment
letter, an employee ID, or a departure date is. It has one job: turn pixels into text that other
services can map into fields. Keeping the boundary this narrow means the OCR engine inside can be
replaced without touching its callers.

```
file (JPG/PNG/PDF)
        |
        v
  PDF has a text layer? --- yes ---> read it directly (PyMuPDF), exact, ~50 ms
        |
        no
        v
  preprocessing (OpenCV: deskew, denoise, perspective correction, upscale)
        |
        v
  Tesseract  --->  text + bbox + confidence per word
```

## Requirements

| Requirement | Tested version |
|---|---|
| Python | 3.9.13 |
| Tesseract OCR | 5.4.0 |
| Tesseract language data | `ind` (Indonesian) |

## 1. Install Tesseract

Tesseract is a separate program, not a Python library, and must be installed first.

**Windows** — download the installer from
[UB Mannheim](https://github.com/UB-Mannheim/tesseract/wiki). During installation, open
**Additional language data** and tick **Indonesian**. Without it, the service fails with an error
saying the `ind` language data cannot be found.

**Linux (Debian/Ubuntu)**

```bash
sudo apt update
sudo apt install tesseract-ocr tesseract-ocr-ind
```

**macOS**

```bash
brew install tesseract tesseract-lang
```

Confirm the installation:

```bash
tesseract --version
tesseract --list-langs    # must include "ind"
```

## 2. Install the service

```bash
git clone https://github.com/tettyrs-org/ocr-engine.git
cd ocr-engine

python -m venv .venv

# Windows
.venv\Scripts\activate
# Linux / macOS
source .venv/bin/activate

pip install -r requirements.txt
```

## 3. Configure

```bash
cp .env.example .env      # Windows: copy .env.example .env
```

`config.py` **has no default values**. Every key in `.env.example` is required unless it is marked
as optional. A missing key makes the service fail at import time with an error that does not name
the variable — use the line in the traceback to find it.

Two keys usually need adjusting:

```ini
TESSERACT_DATA_PREFIX=<path-to-tessdata-folder>
TESSERACT_CMD=<path-to-tesseract-binary>
```

Both may be left empty when Tesseract is on `PATH` and uses its default locations.

> **Windows path pitfall.** Do not wrap paths in double quotes.
> `python-dotenv` processes escape sequences inside double quotes, so
> `"C:\Tesseract-OCR\tessdata"` turns `\t` into a TAB and silently breaks the path.
> Write paths unquoted, or use single quotes.

Full configuration:

| Key | Meaning |
|---|---|
| `OCR_HOST`, `OCR_PORT` | Service address. Defaults in the example to `127.0.0.1:8082` |
| `OCR_TEXT_LAYER_MIN_CHARS` | Minimum average characters per page for a PDF text layer to be accepted. Below it, the document is routed to OCR |
| `PREPROCESS_DESKEW` | Straightens a rotated page |
| `PREPROCESS_DENOISE` | Reduces speckle noise in photos |
| `PREPROCESS_PERSPECTIVE` | Flattens a page photographed at an angle |
| `PREPROCESS_THRESHOLD` | Adaptive binarization. **Off by default**: Tesseract binarizes on its own, and on the test fixtures this step hollowed out bold glyphs |
| `PREPROCESS_MORPHOLOGY` | Morphological cleanup. Off by default; only meaningful when binarization is on |
| `PREPROCESS_UPSCALE_DPI` | Target resolution before OCR |
| `PDF_RASTER_DPI` | Render resolution for PDF pages without a text layer |
| `PDF_MAX_PAGES` | Maximum number of PDF pages |
| `OCR_ENGINE` | Name of an engine registered in `OcrEngineFactory`. Currently `tesseract` |
| `TESSERACT_LANG` | Tesseract language, `ind` |

Boolean values only recognize `true` (case-insensitive). A typo such as `ture` is silently treated
as `false`.

## 4. Run

```bash
python main.py
```

or

```bash
uvicorn main:app --host 127.0.0.1 --port 8082 --reload
```

Interactive API documentation is available at <http://127.0.0.1:8082/docs>.

## Endpoints

### `GET /health`

```json
{ "status": "ok", "service": "ocr-engine", "version": "0.1.0", "environment": "local" }
```

### `POST /ocr`

`multipart/form-data` with a single `file` part containing a JPG, PNG, or PDF.

```bash
curl -X POST http://127.0.0.1:8082/ocr \
  -H 'accept: application/json' \
  -F 'file=@assignment_letter.jpg;type=image/jpeg'
```

```json
{
  "ocr_source": "ocr",
  "engine": { "name": "tesseract", "version": "5.4.0.20240606" },
  "page_count": 1,
  "duration_ms": 3340,
  "pages": [
    {
      "page": 1,
      "width": 5166,
      "height": 7308,
      "deskew_angle": 0.0,
      "text": "KEMENTERIAN KEUANGAN REPUBLIK INDONESIA ...",
      "words": [
        { "text": "KEMENTERIAN", "bbox": [0.193, 0.043, 0.379, 0.055], "confidence": 0.92 }
      ]
    }
  ]
}
```

| Field | Meaning |
|---|---|
| `ocr_source` | `text_layer` when text was read directly from the PDF, `ocr` when it went through image recognition |
| `engine` | `null` on the `text_layer` path — no OCR engine was run |
| `deskew_angle` | Rotation applied by preprocessing, in degrees. Useful when investigating poor results |
| `bbox` | `[x0, y0, x1, y1]` normalized to 0–1 relative to the page size, not pixels |
| `confidence` | 0–1 per word. Always `1.0` on the `text_layer` path |

**Do not use `confidence` to detect misread words.** In testing, a misread word scored 0.90 while
a correct one scored 0.48. The value measures how confidently glyph shapes were recognized, not
whether the content is correct. See [TESTING.md](TESTING.md), section 6.

### Errors

Response shape: `{ "error": { "code": "...", "message": "..." } }`

| HTTP | `code` | When |
|---|---|---|
| 400 | `UNSUPPORTED_MEDIA_TYPE` | Not a JPG/PNG/PDF according to its magic bytes, regardless of file extension |
| 400 | `INVALID_PDF` | The file claims to be a PDF but cannot be opened |
| 400 | `PAGE_LIMIT_EXCEEDED` | The PDF exceeds `PDF_MAX_PAGES` |
| 413 | `FILE_TOO_LARGE` | Image > 10 MB or PDF > 25 MB |
| 503 | `OCR_ENGINE_UNAVAILABLE` | Tesseract is not installed or failed to start |
| 500 | `INTERNAL_ERROR` | Unexpected failure |

Error messages returned by the service are currently in Indonesian. Clients must branch on `code`,
never on `message`.

## Docker Deployment

### Running in Docker

The service is containerized and can be run as part of the full OCR stack:

```bash
# From project root, start complete stack
cd /path/to/Projects/OCR
docker-compose --env-file .env up -d ocr-engine

# Or build and run standalone
docker build -t ocr-engine:latest ./ocr-engine
docker run -p 8000:8000 \
  -e OCR_HOST=0.0.0.0 \
  -e OCR_PORT=8000 \
  -e TESSERACT_LANG=ind+eng \
  ocr-engine:latest
```

### Accessing the Service

Once running:

```bash
# Health check
curl http://localhost:8000/health

# Interactive API documentation
open http://localhost:8000/docs

# Test OCR endpoint
curl -X POST http://localhost:8000/ocr \
  -H 'accept: application/json' \
  -F 'file=@test-document.jpg;type=image/jpeg'
```

### Docker Compose Integration

When using docker-compose, the service is automatically configured:

```bash
# The service is accessible at http://ocr-engine:8000 from other containers
# For example, from ocr-api container:
curl http://ocr-engine:8000/health
```

## Testing

```bash
pip install -r requirements-dev.txt
pytest
```

Tests that need Tesseract are **skipped automatically** when the binary is absent, so the suite
still runs on machines without it.

```bash
pytest -m "not slow"      # skip full-page OCR
pytest -m ocr             # only tests that need Tesseract
```

The test strategy, the full list of test cases, and the latest run results are in
[TESTING.md](TESTING.md), with a PDF version at
[docs/test-report-ocr-engine.pdf](docs/test-report-ocr-engine.pdf).

## Project structure

```
main.py                 FastAPI entry point, /health
config.py               reads .env, no default values
routes/ocr.py           POST /ocr: file type detection, validation, path selection
services/pdf_text.py    PDF text layer path (PyMuPDF)
services/pdf_raster.py  renders PDF pages to images, then runs OCR
services/image_ocr.py   image path: preprocessing + OCR engine call
services/preprocess.py  OpenCV: deskew, denoise, perspective, upscale, binarization
engines/base.py         OCR engine interface + factory
engines/tesseract.py    Tesseract implementation
schemas/ocr.py          response models (Pydantic)
error_handlers/         domain errors and their handlers
tests/                  pytest, including synthetic document fixtures
```

A new OCR engine only needs to subclass `OcrEngine` and register with `OcrEngineFactory`; nothing
else has to change.

## Known limitations

Listed openly so they are not mistaken for solved problems:

- **Observability is not wired up yet.** The libraries are already in `requirements.txt`, but
  structured logging, OTLP tracing, and a metrics endpoint are not implemented.
- **The `text` field is not consistent across paths.** The text layer path preserves line breaks;
  the OCR path joins words with spaces. Callers should rebuild lines from `bbox`.
- **`width` and `height` on the image path are the post-preprocessing dimensions**, not those of
  the original file. If perspective correction crops the image, `bbox` no longer aligns with the
  original photo.
- **Image source resolution is assumed to be 72 DPI**, so high-resolution photos are upscaled
  further than necessary.
- **The page limit is only enforced on the raster path**, not on the text layer path.
- **Accuracy has not been measured on real documents.** All fixtures are synthetic, with a single
  layout and a single font.

## License

Not yet determined.
