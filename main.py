from fastapi import FastAPI

import config as CONFIG
from error_handlers.error_handlers import register_error_handlers
from routes import ocr

app = FastAPI(title=CONFIG.SERVICE_NAME,
              version=CONFIG.SERVICE_VERSION)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": CONFIG.SERVICE_NAME,
        "version": CONFIG.SERVICE_VERSION,
        "environment": CONFIG.ENVIRONMENT
    }


app.include_router(ocr.router)
register_error_handlers(app)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host=CONFIG.HOST, port=CONFIG.PORT, reload=True)
