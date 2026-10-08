# Multi-stage build untuk ocr-engine (OCR service dengan Tesseract)
FROM python:3.11-slim AS builder

WORKDIR /app

# Install system dependencies untuk Tesseract dan image processing
RUN apt-get update && apt-get install -y --no-install-recommends \
  tesseract-ocr \
  tesseract-ocr-ind \
  libtesseract-dev \
  build-essential \
  && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Runtime stage
FROM python:3.11-slim

WORKDIR /app

# Install Tesseract runtime only
RUN apt-get update && apt-get install -y --no-install-recommends \
  tesseract-ocr \
  tesseract-ocr-ind \
  && rm -rf /var/lib/apt/lists/*

# Copy Python dependencies from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# Run application (assumes FastAPI with uvicorn)
ENTRYPOINT ["python", "-m", "uvicorn"]
CMD ["main:app", "--host", "0.0.0.0", "--port", "8000"]
