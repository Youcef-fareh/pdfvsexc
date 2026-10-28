"""
Image Preprocessor — prepares images for OCR with OpenCV.
All operations run on CPU; optimised for low-end hardware (T450).
"""
from __future__ import annotations

import cv2
import numpy as np
from PIL import Image


# ── Public API ────────────────────────────────────────────────────────────────

def preprocess(image_input: str | Image.Image) -> Image.Image:
    """
    Full preprocessing pipeline:
      1. Load / convert to OpenCV grayscale
      2. Deskew
      3. Denoise
      4. CLAHE contrast enhancement
      5. Otsu binarization
      6. Return as PIL Image (mode "L")
    """
    gray = _load_as_gray(image_input)
    gray = _deskew(gray)
    gray = _denoise(gray)
    gray = _enhance_contrast(gray)
    gray = _binarize(gray)
    return Image.fromarray(gray)


# ── Step implementations ──────────────────────────────────────────────────────

def _load_as_gray(source: str | Image.Image) -> np.ndarray:
    if isinstance(source, str):
        bgr = cv2.imread(source)
        if bgr is None:
            raise FileNotFoundError(f"Cannot read image: {source}")
        return cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    if isinstance(source, Image.Image):
        rgb = np.array(source.convert("RGB"))
        return cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    raise TypeError(f"Unsupported image type: {type(source)}")


def _deskew(gray: np.ndarray) -> np.ndarray:
    """
    Detect document skew using the minimum-area bounding box of
    foreground pixels and rotate to correct it.
    Only corrects angles above 0.5° to avoid introducing blur on straight docs.
    """
    # Invert so text is white on black
    inv = cv2.bitwise_not(gray)
    coords = np.column_stack(np.where(inv > 128))
    if len(coords) < 100:
        return gray  # Not enough content to estimate angle

    rect = cv2.minAreaRect(coords)
    angle = rect[-1]

    # OpenCV angle convention correction
    if angle < -45:
        angle = 90 + angle
    elif angle > 45:
        angle = angle - 90

    if abs(angle) < 0.5:
        return gray  # Skip — nearly straight

    h, w = gray.shape
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(
        gray, M, (w, h),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_REPLICATE,
    )
    return rotated


def _denoise(gray: np.ndarray) -> np.ndarray:
    """
    Fast non-local means denoising — h=10 is a balanced setting
    that removes scan noise without blurring thin characters.
    """
    return cv2.fastNlMeansDenoising(gray, h=10, templateWindowSize=7, searchWindowSize=21)


def _enhance_contrast(gray: np.ndarray) -> np.ndarray:
    """
    CLAHE (Contrast Limited Adaptive Histogram Equalization).
    Improves legibility of faint / unevenly lit text.
    clipLimit=2.0 and tileGridSize=(8,8) are good defaults for A4 scans at 300 DPI.
    """
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    return clahe.apply(gray)


def _binarize(gray: np.ndarray) -> np.ndarray:
    """
    Otsu's global thresholding for clean black/white output.
    Performs better than simple fixed-threshold for varying backgrounds.
    """
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return binary
