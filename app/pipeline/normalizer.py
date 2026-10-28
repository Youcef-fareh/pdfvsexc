"""
Data Normalizer — cleans raw OCR output for display and export.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.utils.arabic_utils import process_cell_text, is_rtl_dominant

TableGrid = list[list[str]]


# ── Cell-level fixes ──────────────────────────────────────────────────────────

_OCR_FIXES: list[tuple[str, str]] = [
    # Common Tesseract confusion pairs in numbers
    (r"(?<=\d)O(?=\d)", "0"),   # digit-O-digit → digit-0-digit
    (r"(?<=\d)l(?=\d)", "1"),   # digit-l-digit → digit-1-digit
    (r"(?<=\d)I(?=\d)", "1"),
    # French decimal separators
    (r"(\d)\s+(\d{3})\b", r"\1\2"),  # Remove spurious space inside numbers
    # Remove stray pipe characters (table border artifact)
    (r"\|", " "),
]

_CURRENCY_KEYWORDS = {
    "total", "ttc", "ht", "tva", "montant", "sous-total",
    "sous total", "net à payer", "remise", "discount",
}


@dataclass
class NormalizedCell:
    raw: str
    cleaned: str
    is_numeric: bool
    is_currency_row: bool = False
    is_rtl: bool = False


@dataclass
class NormalizedTable:
    rows: list[list[NormalizedCell]]
    header_row: int | None = None   # Index of the detected header row

    def to_string_grid(self) -> TableGrid:
        return [[cell.cleaned for cell in row] for row in self.rows]


# ── Public API ────────────────────────────────────────────────────────────────

def normalize_table(grid: TableGrid) -> NormalizedTable:
    """
    Apply all cleaning passes to a raw 2D string grid.
    Returns a NormalizedTable with per-cell metadata.
    """
    if not grid:
        return NormalizedTable(rows=[])

    normalized_rows: list[list[NormalizedCell]] = []

    for row in grid:
        norm_row = [_normalize_cell(cell) for cell in row]
        normalized_rows.append(norm_row)

    result = NormalizedTable(rows=normalized_rows)
    _tag_currency_rows(result)
    result.header_row = _detect_header_row(result)
    return result


# ── Cell normalization ────────────────────────────────────────────────────────

def _normalize_cell(raw: str) -> NormalizedCell:
    text = raw.strip()

    # Apply OCR fixes
    for pattern, replacement in _OCR_FIXES:
        text = re.sub(pattern, replacement, text)

    # Normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()

    # Handle Arabic / RTL content
    text = process_cell_text(text)
    rtl = is_rtl_dominant(text)

    numeric = _is_numeric(text)

    return NormalizedCell(
        raw=raw,
        cleaned=text,
        is_numeric=numeric,
        is_rtl=rtl,
    )


def _is_numeric(text: str) -> bool:
    """Return True if the cell contains a number (possibly with currency symbols)."""
    cleaned = re.sub(r"[,.\s\u202F\u00A0DA$€£%]", "", text)
    return bool(cleaned) and cleaned.lstrip("-+").isdigit()


# ── Row-level tagging ─────────────────────────────────────────────────────────

def _tag_currency_rows(table: NormalizedTable) -> None:
    """Mark rows that likely contain totals / subtotals."""
    for row in table.rows:
        row_text = " ".join(c.cleaned.lower() for c in row)
        if any(kw in row_text for kw in _CURRENCY_KEYWORDS):
            for cell in row:
                cell.is_currency_row = True


def _detect_header_row(table: NormalizedTable) -> int | None:
    """
    Heuristically find the table header row:
    - Row where most cells are non-numeric and non-empty.
    - Usually the first row with content.
    """
    for i, row in enumerate(table.rows):
        non_empty = [c for c in row if c.cleaned]
        if not non_empty:
            continue
        non_numeric_ratio = sum(1 for c in non_empty if not c.is_numeric) / len(non_empty)
        if non_numeric_ratio > 0.6:
            return i
    return None
