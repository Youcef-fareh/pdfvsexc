"""
DOCX Exporter — writes a NormalizedTable to a Word document.
Supports clone (auto-styled) and template modes.
"""
from __future__ import annotations

import os
from typing import Literal

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.shared import Inches, Pt, RGBColor
from docx.enum.table import WD_TABLE_ALIGNMENT

from app.pipeline.normalizer import NormalizedTable, NormalizedCell

ExportMode = Literal["clone", "template"]

# ── Colour palette ────────────────────────────────────────────────────────────
_HEADER_BG   = "1A1A2E"   # Dark navy for table header
_HEADER_FG   = "FFFFFF"
_CURRENCY_BG = "E8F5E9"   # Light green for totals rows
_ALT_ROW_BG  = "F5F5F5"   # Subtle alternating rows


# ── Public API ────────────────────────────────────────────────────────────────

def write_docx(
    table: NormalizedTable,
    output_path: str,
    mode: ExportMode = "clone",
) -> str:
    """
    Write the normalized table to a DOCX file.
    Returns output_path for convenience.
    """
    doc = Document()

    # Page margins — slightly narrower to fit wider tables on A4
    for section in doc.sections:
        section.left_margin   = Inches(0.75)
        section.right_margin  = Inches(0.75)
        section.top_margin    = Inches(0.75)
        section.bottom_margin = Inches(0.75)

    grid = table.rows
    if not grid:
        doc.save(output_path)
        return output_path

    num_cols = max(len(row) for row in grid)
    num_rows = len(grid)
    header_row_idx = table.header_row

    # Create Word table
    word_table = doc.add_table(rows=num_rows, cols=num_cols)
    word_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    word_table.style = "Table Grid"

    for row_idx, row in enumerate(grid):
        is_header   = (row_idx == header_row_idx)
        is_currency = any(c.is_currency_row for c in row)

        for col_idx in range(num_cols):
            cell_obj = row[col_idx] if col_idx < len(row) else None
            word_cell = word_table.cell(row_idx, col_idx)
            text = cell_obj.cleaned if cell_obj else ""

            _style_word_cell(
                word_cell, text,
                is_header=is_header,
                is_currency=is_currency,
                is_rtl=cell_obj.is_rtl if cell_obj else False,
                is_numeric=cell_obj.is_numeric if cell_obj else False,
                row_idx=row_idx,
            )

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    doc.save(output_path)
    return output_path


# ── Cell styling helpers ──────────────────────────────────────────────────────

def _style_word_cell(
    word_cell,
    text: str,
    is_header: bool,
    is_currency: bool,
    is_rtl: bool,
    is_numeric: bool,
    row_idx: int,
) -> None:
    para = word_cell.paragraphs[0]
    run  = para.add_run(text)

    if is_header:
        run.bold = True
        run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        run.font.size = Pt(10)
        _set_cell_bg(word_cell, _HEADER_BG)
        para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    elif is_currency:
        run.bold = True
        run.font.size = Pt(9)
        _set_cell_bg(word_cell, _CURRENCY_BG)
        para.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    else:
        run.font.size = Pt(9)
        if row_idx % 2 == 0:
            _set_cell_bg(word_cell, _ALT_ROW_BG)
        if is_rtl:
            _set_rtl(para)
            para.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        elif is_numeric:
            para.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        else:
            para.alignment = WD_ALIGN_PARAGRAPH.LEFT


def _set_cell_bg(cell, hex_color: str) -> None:
    """Set table cell background colour via OOXML shading element."""
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    tcPr.append(shd)


def _set_rtl(para) -> None:
    """Enable right-to-left paragraph direction for Arabic text."""
    pPr = para._p.get_or_add_pPr()
    bidi = OxmlElement("w:bidi")
    pPr.append(bidi)
