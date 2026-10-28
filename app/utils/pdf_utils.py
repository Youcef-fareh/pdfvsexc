"""PDF detection and helper utilities."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Iterator

from app.utils.config import POPPLER_BIN, OCR_DPI


# ── PDF type detection ────────────────────────────────────────────────────────

def is_pdf(path: str) -> bool:
    return Path(path).suffix.lower() == ".pdf"


def has_text_layer(path: str) -> bool:
    """
    Return True if the PDF has a selectable text layer (not purely image-based).
    Uses pdfplumber — if any page yields words, treat as digital PDF.
    """
    try:
        import pdfplumber
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages[:3]:  # Sample first 3 pages only
                words = page.extract_words()
                if words:
                    return True
        return False
    except Exception:
        return False


def is_password_protected(path: str) -> bool:
    """Detect whether a PDF requires a password."""
    try:
        import pdfplumber
        with pdfplumber.open(path):
            pass
        return False
    except Exception as exc:
        return "password" in str(exc).lower() or "encrypted" in str(exc).lower()


# ── PDF → image conversion ────────────────────────────────────────────────────

def pdf_to_images(path: str, dpi: int = OCR_DPI, password: str | None = None):
    """
    Convert a PDF file to a list of PIL Images (one per page).
    Uses pdf2image with the bundled Poppler binaries.

    Yields (page_number: int, image: PIL.Image) tuples so the caller
    can process pages one at a time without loading the whole PDF into RAM.
    """
    from pdf2image import convert_from_path
    from pdf2image.exceptions import PDFPageCountError

    kwargs: dict = {
        "dpi": dpi,
        "fmt": "PNG",
        "thread_count": 1,         # Single thread — safe on T450
        "use_cropbox": False,
        "strict": False,
    }

    # Inject bundled Poppler path when running from bundle
    if os.path.isdir(POPPLER_BIN):
        kwargs["poppler_path"] = POPPLER_BIN

    if password:
        kwargs["userpw"] = password

    try:
        images = convert_from_path(path, **kwargs)
    except PDFPageCountError:
        images = []

    for i, img in enumerate(images):
        yield i + 1, img


# ── Digital PDF table extraction ──────────────────────────────────────────────

def extract_tables_from_pdf(path: str, password: str | None = None) -> list[list[list[str]]]:
    """
    Extract tables from a text-selectable PDF using pdfplumber.
    Returns a list of tables; each table is a list of rows; each row is a list of strings.
    """
    import pdfplumber

    open_kwargs = {}
    if password:
        open_kwargs["password"] = password

    all_tables: list[list[list[str]]] = []

    with pdfplumber.open(path, **open_kwargs) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in (tables or []):
                cleaned = [
                    [_clean_cell(cell) for cell in row]
                    for row in table
                    if any(cell for cell in row)
                ]
                if cleaned:
                    all_tables.append(cleaned)

    return all_tables


def _clean_cell(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


# ── Page count helper ─────────────────────────────────────────────────────────

def get_page_count(path: str) -> int:
    """Return the number of pages in a PDF without loading images."""
    try:
        import pdfplumber
        with pdfplumber.open(path) as pdf:
            return len(pdf.pages)
    except Exception:
        return 0
