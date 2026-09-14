from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from error_handlers.errors import OcrEngineError


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(OcrEngineError)
    async def handler_ocr_engine_error(request: Request, exc: OcrEngineError):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.code,
                    "message": str(exc)
                }
            }
        )
