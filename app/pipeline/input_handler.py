"""
Input Handler — detects file types and routes each file to the correct pipeline.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Callable, Iterator

from app.utils.pdf_utils import (
    is_pdf,
    has_text_layer,
    is_password_protected,
    get_page_count,
)

SUPPORTED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif"}
SUPPORTED_PDF_EXTENSION = ".pdf"


class InputType(Enum):
    IMAGE = auto()          # JPG, PNG, etc.
    DIGITAL_PDF = auto()    # PDF with selectable text layer
    SCANNED_PDF = auto()    # PDF that is purely image-based
    UNSUPPORTED = auto()


@dataclass
class FileEntry:
    """Metadata for a single input file queued for processing."""
    path: str
    input_type: InputType
    page_count: int = 1
    needs_password: bool = False
    password: str | None = None
    error: str | None = None


def classify_file(path: str) -> FileEntry:
    """
    Inspect a file and return a FileEntry with its detected type.
    Does NOT read image content — only inspects extension + PDF metadata.
    """
    ext = Path(path).suffix.lower()

    if ext in SUPPORTED_IMAGE_EXTENSIONS:
        return FileEntry(path=path, input_type=InputType.IMAGE, page_count=1)

    if ext == SUPPORTED_PDF_EXTENSION:
        if is_password_protected(path):
            return FileEntry(
                path=path,
                input_type=InputType.DIGITAL_PDF,  # Unknown until unlocked
                needs_password=True,
            )
        pages = get_page_count(path)
        if has_text_layer(path):
            return FileEntry(path=path, input_type=InputType.DIGITAL_PDF, page_count=pages)
        return FileEntry(path=path, input_type=InputType.SCANNED_PDF, page_count=pages)

    return FileEntry(
        path=path,
        input_type=InputType.UNSUPPORTED,
        error=f"Unsupported file type: {ext}",
    )


def collect_files_from_folder(folder: str) -> list[FileEntry]:
    """
    Walk a directory and return FileEntry objects for every supported file.
    Non-recursive — only the immediate children of the folder.
    """
    entries: list[FileEntry] = []
    for name in sorted(os.listdir(folder)):
        full_path = os.path.join(folder, name)
        if not os.path.isfile(full_path):
            continue
        ext = Path(name).suffix.lower()
        if ext in SUPPORTED_IMAGE_EXTENSIONS or ext == SUPPORTED_PDF_EXTENSION:
            entries.append(classify_file(full_path))
    return entries
