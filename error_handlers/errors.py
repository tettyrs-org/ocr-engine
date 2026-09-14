class OcrEngineError(Exception):
    code = "INTERNAL_ERROR"
    status_code = 500
    
class InvalidPdfError(OcrEngineError):
    code = "INVALID_PDF"
    status_code = 400
    
class TextLayerUnusableError(OcrEngineError):
    code = "OCR_NOT_IMPLEMENTED"
    status_code = 501

class UnsupportedMediaTypeError(OcrEngineError):
    code = "UNSUPPORTED_MEDIA_TYPE"
    status_code = 400

class FileTooLargeError(OcrEngineError):
    code = "FILE_TOO_LARGE"
    status_code = 413

class PageLimitExceededError(OcrEngineError):
    code = "PAGE_LIMIT_EXCEEDED"
    status_code = 400

class OcrEngineUnavailableError(OcrEngineError):
    code = "OCR_ENGINE_UNAVAILABLE"
    status_code = 503