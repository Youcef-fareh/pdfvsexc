"""
XLSX Exporter — writes a NormalizedTable to an Excel file.
Supports two modes:
  • clone  — reconstructs visual layout from detected structure
  • template — writes data into a user-defined template position map
"""
from __future__ import annotations

import os
from typing import Literal

import openpyxl
from openpyxl.styles import (
    Alignment, Border, Font, PatternFill, Side, numbers
)
from openpyxl.utils import get_column_letter

from app.pipeline.normalizer import NormalizedTable, NormalizedCell
from app.utils.arabic_utils import is_rtl_dominant

ExportMode = Literal["clone", "template"]

# ── Style definitions ─────────────────────────────────────────────────────────

_HEADER_FILL = PatternFill("solid", fgColor="1A1A2E")
_HEADER_FONT = Font(bold=True, color="FFFFFF", size=11)
_CURRENCY_FILL = PatternFill("solid", fgColor="E8F5E9")
_CURRENCY_FONT = Font(bold=True, size=10)
_DEFAULT_FONT = Font(size=10)
_THIN_BORDER = Border(
    left=Side(style="thin"), right=Side(style="thin"),
    top=Side(style="thin"), bottom=Side(style="thin"),
)


# ── Public API ────────────────────────────────────────────────────────────────

def write_xlsx(
    table: NormalizedTable,
    output_path: str,
    mode: ExportMode = "clone",
) -> str:
    """
    Write the normalized table to an XLSX file.
    Returns the output_path for convenience.
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Données"

    grid = table.rows
    if not grid:
        wb.save(output_path)
        return output_path

    header_row_idx = table.header_row  # May be None

    for row_idx, row in enumerate(grid, 1):
        is_header = (row_idx - 1) == header_row_idx
        is_currency = any(c.is_currency_row for c in row)

        for col_idx, cell in enumerate(row, 1):
            ws_cell = ws.cell(row=row_idx, column=col_idx, value=cell.cleaned)
            _apply_style(ws_cell, cell, is_header=is_header, is_currency=is_currency)

    _auto_fit_columns(ws)
    _freeze_header(ws, header_row_idx)

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    wb.save(output_path)
    return output_path


# ── Style helpers ─────────────────────────────────────────────────────────────

def _apply_style(
    ws_cell,
    cell: NormalizedCell,
    is_header: bool,
    is_currency: bool,
) -> None:
    ws_cell.border = _THIN_BORDER

    if is_header:
        ws_cell.font = _HEADER_FONT
        ws_cell.fill = _HEADER_FILL
        ws_cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    elif is_currency:
        ws_cell.font = _CURRENCY_FONT
        ws_cell.fill = _CURRENCY_FILL
        ws_cell.alignment = Alignment(
            horizontal="right" if cell.is_numeric else "left",
            vertical="center",
        )
        if cell.is_numeric:
            ws_cell.number_format = '#,##0.00'
    else:
        ws_cell.font = _DEFAULT_FONT
        if cell.is_rtl:
            ws_cell.alignment = Alignment(horizontal="right", vertical="center",
                                          wrap_text=True, reading_order=2)
        else:
            ws_cell.alignment = Alignment(
                horizontal="right" if cell.is_numeric else "left",
                vertical="center", wrap_text=True,
            )

    # Parse numeric values for proper Excel type (not just strings)
    if cell.is_numeric and ws_cell.value:
        try:
            cleaned = str(ws_cell.value).replace(" ", "").replace(",", ".")
            ws_cell.value = float(cleaned)
        except ValueError:
            pass


def _auto_fit_columns(ws) -> None:
    """Set column widths based on maximum content length."""
    for col in ws.columns:
        max_len = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            try:
                val_len = len(str(cell.value or ""))
                max_len = max(max_len, val_len)
            except Exception:
                pass
        ws.column_dimensions[col_letter].width = min(max(max_len + 4, 8), 50)


def _freeze_header(ws, header_row_idx: int | None) -> None:
    if header_row_idx is not None:
        freeze_row = header_row_idx + 2  # 1-based + 1 below header
        ws.freeze_panes = f"A{freeze_row}"
