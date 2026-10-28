"""
OCR Engine — Tesseract 5 wrapper.
Uses the bundled Tesseract binary from vendor/tesseract/.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

import pytesseract
from PIL import Image

from app.utils.config import (
    TESSERACT_EXE,
    TESSDATA_DIR,
    OCR_LANGUAGES,
    OCR_CONFIDENCE_THRESHOLD,
)

# Point pytesseract at our bundled binary
pytesseract.pytesseract.tesseract_cmd = TESSERACT_EXE


@dataclass
class OcrWord:
    text: str
    left: int
    top: int
    width: int
    height: int
    confidence: float
    is_low_confidence: bool = field(init=False)

    def __post_init__(self) -> None:
        self.is_low_confidence = self.confidence < OCR_CONFIDENCE_THRESHOLD


@dataclass
class OcrResult:
    raw_text: str
    words: list[OcrWord]

    @property
    def low_confidence_count(self) -> int:
        return sum(1 for w in self.words if w.is_low_confidence)

    @property
    def average_confidence(self) -> float:
        if not self.words:
            return 0.0
        return sum(w.confidence for w in self.words) / len(self.words)


# ── Core OCR functions ────────────────────────────────────────────────────────

def _build_config(psm: int = 6) -> str:
    """Build Tesseract config string with tessdata dir and page segmentation mode."""
    tessdata = TESSDATA_DIR.replace("\\", "/")
    return f'--tessdata-dir "{tessdata}" --psm {psm} --oem 3'


def ocr_page(image: Image.Image, psm: int = 6) -> OcrResult:
    """
    Run full-page OCR on a PIL Image.

    psm=6  → Assume a single uniform block of text (best for standard factures)
    psm=4  → Assume single column (use for narrow receipts)
    psm=11 → Sparse text (use when layout is chaotic)
    """
    config = _build_config(psm)

    # Get plain text
    raw_text: str = pytesseract.image_to_string(
        image, lang=OCR_LANGUAGES, config=config
    )

    # Get detailed word-level data
    df = pytesseract.image_to_data(
        image,
        lang=OCR_LANGUAGES,
        config=config,
        output_type=pytesseract.Output.DICT,
    )

    words: list[OcrWord] = []
    n = len(df["text"])
    for i in range(n):
        text = str(df["text"][i]).strip()
        if not text:
            continue
        try:
            conf = float(df["conf"][i])
        except (ValueError, TypeError):
            conf = 0.0
        if conf < 0:
            continue  # Tesseract returns -1 for block-level entries

        words.append(
            OcrWord(
                text=text,
                left=int(df["left"][i]),
                top=int(df["top"][i]),
                width=int(df["width"][i]),
                height=int(df["height"][i]),
                confidence=conf,
            )
        )

    return OcrResult(raw_text=raw_text.strip(), words=words)


def ocr_region(image: Image.Image, region: tuple[int, int, int, int], psm: int = 6) -> OcrResult:
    """
    Run OCR on a rectangular crop of an image.
    region: (left, top, width, height)
    """
    left, top, width, height = region
    cropped = image.crop((left, top, left + width, top + height))
    return ocr_page(cropped, psm=psm)


def get_tesseract_version() -> str:
    """Return installed Tesseract version string (useful for diagnostics)."""
    try:
        return pytesseract.get_tesseract_version().vstring  # type: ignore[union-attr]
    except Exception:
        return "unknown"
