import time
from dataclasses import dataclass, field
from typing import List, Tuple

import cv2
import numpy as np

import config as CONFIG


@dataclass
class PreprocessResult:
    image: np.ndarray                                        # Processed image
    steps_applied: List[str] = field(default_factory=list)   # ["deskew", "denoise", etc]
    deskew_angle: float = 0.0                                # Degrees rotated (for logging)
    input_resolution: Tuple[int, int] = (0, 0)               # (width, height) before
    output_resolution: Tuple[int, int] = (0, 0)              # (width, height) after
    duration_ms: int = 0                                     # Total time


def _get_image_resolution(image: np.ndarray) -> tuple:
    heigh, weight = image.shape[:2]
    return (weight, heigh)

def _denoise(image: np.ndarray) -> np.ndarray:  # non local Means
    return cv2.fastNlMeansDenoising(image, None, 10, 7, 11)

def _deskew(image: np.ndarray) -> tuple[np.ndarray, float]:  # core algorithm
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    
    rows, cols = np.where(thresh > 0)
    if len(rows) == 0:
        return image, 0.0
    
    coords = np.column_stack((cols,rows))
    angle = cv2.minAreaRect(coords)[-1]
    
    if angle > 45:
        angle -= 90
            
    if abs(angle) < 0.5:
        return image, 0.0
    
    height, weight = image.shape[:2]
    center = (weight // 2, height // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(image, M, (weight, height), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    
    return rotated, angle

def _correct_perspective(image: np.ndarray) -> np.ndarray: # Document Quad Detection
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
    blurred = cv2.GaussianBlur(gray, (5,5), 0)
    edged = cv2.Canny(blurred, 50,200)
    
    contours, _ = cv2.findContours(edged, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:5]
    
    image_area = image.shape[0] * image.shape[1]
    
    for contour in contours:
        if cv2.contourArea(contour) < 0.1 * image_area:
            break
        
        peri = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.02 * peri, True)
        
        if len(approx) != 4:
            continue
        
        pts = approx.reshape(4,2).astype(np.float32)
        
        rect = np.zeros((4,2), dtype=np.float32)
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]     # top-left
        rect[2] = pts[np.argmax(s)]     # bottom-right
        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(diff)]  # top-right
        rect[3] = pts[np.argmax(diff)]  # bottom-left
        
        (tl, tr, br, bl) = rect
        width_a = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
        width_b = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
        max_width = max(int(width_a), int(width_b))
        
        height_a = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
        height_b = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
        max_height = max(int(height_a), int(height_b))
        
        if max_width < 2 or max_height < 2:
            continue
        
        dst = np.array([
            [0,0],
            [max_width - 1, 0],
            [max_width - 1, max_height - 1],
            [0, max_height - 1]
        ], dtype=np.float32)
        
        M = cv2.getPerspectiveTransform(rect, dst)
        warped = cv2.warpPerspective(image, M, (max_width, max_height))
        return warped
    return image
    
def _adaptive_threshold(image: np.ndarray) -> np.ndarray: # Binarization
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
    return cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
    )

def _upscale_to_dpi(image: np.ndarray, target_dpi: int = 300, current_dpi: int = 72) -> np.ndarray: # Resolution Normalization
    height, width = image.shape[:2]
    
    scale = target_dpi / current_dpi
    if scale <= 1.0:
        return image
    
    new_width = int(width * scale)
    new_height = int(height * scale)
    
    return cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_CUBIC)

def _morphological_cleanup(image: np.ndarray) -> np.ndarray: # Final Polish
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2,2))
    return cv2.morphologyEx(image, cv2.MORPH_CLOSE, kernel)

def preprocess_image(image: np.ndarray, source_dpi: int = 72) -> PreprocessResult: # Orchestrator
    started = time.perf_counter()
    input_res = _get_image_resolution(image)
    
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image.copy()
    
    result = PreprocessResult(
        image = gray,
        input_resolution=input_res
    )
    
    if getattr(CONFIG, 'PREPROCESS_DESKEW', True):
        result.image, angle = _deskew(result.image)
        result.deskew_angle = angle
        result.steps_applied.append("deskew")
        
    if getattr(CONFIG, 'PREPROCESS_DENOISE', True):
        result.image = _denoise(result.image)
        result.steps_applied.append("denoise")
        
    if getattr(CONFIG, 'PREPROCESS_PERSPECTIVE', True):
        result.image = _correct_perspective(result.image)
        result.steps_applied.append("perspective_correction")
    
    target_dpi = getattr(CONFIG, 'PREPROCESS_UPSCALE_DPI', 300)
    if target_dpi and target_dpi > source_dpi:
        result.image = _upscale_to_dpi(result.image, target_dpi, source_dpi)
        result.steps_applied.append(f"upscale_{target_dpi}dpi")
        
    if getattr(CONFIG, 'PREPROCESS_THRESHOLD', True):
        result.image = _adaptive_threshold(result.image)
        result.steps_applied.append("adaptive_threshold")
        
    if getattr(CONFIG, 'PREPROCESS_MORPHOLOGY', True):
        result.image = _morphological_cleanup(result.image)
        result.steps_applied.append("morphology")
        
    result.output_resolution = _get_image_resolution(result.image)
    result.duration_ms = int((time.perf_counter() - started) * 1000)
    
    return result
            