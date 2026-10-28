"""
Table Structure Detector.

Strategy (in priority order):
  1. Bordered detection  — find horizontal + vertical lines with morphology
  2. Borderless fallback — cluster words into columns by x-position proximity
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np
from PIL import Image

from app.pipeline.ocr_engine import OcrResult, OcrWord


@dataclass
class CellBox:
    row: int
    col: int
    left: int
    top: int
    width: int
    height: int
    text: str = ""
    low_confidence: bool = False


TableGrid = list[list[str]]  # 2-D list[row][col] = cell text


# ── Public API ────────────────────────────────────────────────────────────────

def detect_table(image: Image.Image, ocr_result: OcrResult) -> TableGrid:
    """
    Primary entry point.  Tries bordered detection first; falls back to
    whitespace-column clustering if no grid is found.
    """
    cv_img = _pil_to_bgr(image)
    gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)

    grid = _detect_bordered_table(gray, ocr_result)
    if grid:
        return grid

    return _detect_borderless_table(ocr_result, image.width, image.height)


# ── Bordered table detection ──────────────────────────────────────────────────

def _detect_bordered_table(gray: np.ndarray, ocr_result: OcrResult) -> TableGrid:
    """
    Use morphological operations to isolate horizontal and vertical line
    segments, find their intersections, and derive the cell grid.
    """
    # Binarize
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    h, w = thresh.shape

    # Horizontal lines kernel: 1/30 of page width
    h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (max(w // 30, 20), 1))
    horizontal = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, h_kernel, iterations=2)

    # Vertical lines kernel: 1/30 of page height
    v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(h // 30, 20)))
    vertical = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, v_kernel, iterations=2)

    # Combine to get table grid mask
    grid_mask = cv2.add(horizontal, vertical)
    contours, _ = cv2.findContours(grid_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        return []

    # Find cells by detecting contours in the combined grid
    _, joint = cv2.threshold(grid_mask, 0, 255, cv2.THRESH_BINARY)
    combined = cv2.add(horizontal, vertical)
    cell_contours, _ = cv2.findContours(
        cv2.dilate(combined, np.ones((3, 3), np.uint8)),
        cv2.RETR_TREE,
        cv2.CHAIN_APPROX_SIMPLE,
    )

    # Collect bounding rects and filter noise
    rects = []
    for c in cell_contours:
        x, y, cw, ch = cv2.boundingRect(c)
        if cw > 20 and ch > 10:  # Minimum cell size
            rects.append((x, y, cw, ch))

    if len(rects) < 2:
        return []

    # Cluster into rows and columns by y and x coords
    rows = _cluster_rects_into_rows(rects)
    if not rows:
        return []

    # Assign OCR words to cells
    words = ocr_result.words
    grid: TableGrid = []
    for row_rects in rows:
        row_cells = []
        for (x, y, rw, rh) in sorted(row_rects, key=lambda r: r[0]):
            cell_text = _collect_words_in_rect(words, x, y, rw, rh)
            row_cells.append(cell_text)
        grid.append(row_cells)

    return grid if len(grid) >= 2 else []


def _cluster_rects_into_rows(
    rects: list[tuple[int, int, int, int]],
    tolerance: int = 10,
) -> list[list[tuple[int, int, int, int]]]:
    """Group rectangles into rows based on similar top-y coordinate."""
    sorted_rects = sorted(rects, key=lambda r: r[1])
    rows: list[list[tuple]] = []
    current_row: list[tuple] = []
    current_y: int | None = None

    for rect in sorted_rects:
        y = rect[1]
        if current_y is None or abs(y - current_y) <= tolerance:
            current_row.append(rect)
            current_y = y if current_y is None else current_y
        else:
            if current_row:
                rows.append(current_row)
            current_row = [rect]
            current_y = y

    if current_row:
        rows.append(current_row)

    return rows


# ── Borderless table detection ────────────────────────────────────────────────

def _detect_borderless_table(
    ocr_result: OcrResult,
    img_width: int,
    img_height: int,
) -> TableGrid:
    """
    Group OCR words into virtual rows by y-proximity and then into columns
    by x-proximity.  This handles tables with no visible borders.
    """
    words = [w for w in ocr_result.words if w.text.strip()]
    if not words:
        return []

    # Sort words by vertical position
    words_sorted = sorted(words, key=lambda w: w.top)

    # Cluster into rows (words within ~15px vertically share a row)
    row_height_est = max(w.height for w in words_sorted) if words_sorted else 20
    row_gap = max(row_height_est * 0.6, 10)

    rows: list[list[OcrWord]] = []
    current_row: list[OcrWord] = []
    row_y: float | None = None

    for word in words_sorted:
        if row_y is None or abs(word.top - row_y) <= row_gap:
            current_row.append(word)
            row_y = word.top if row_y is None else row_y
        else:
            rows.append(current_row)
            current_row = [word]
            row_y = word.top

    if current_row:
        rows.append(current_row)

    if len(rows) < 2:
        return []

    # Determine column boundaries from the row with the most words (likely header)
    col_anchors = _infer_column_anchors([w.left for row in rows for w in row])

    # Assign each word to nearest column anchor
    grid: TableGrid = []
    for row in rows:
        cols: dict[int, list[str]] = {i: [] for i in range(len(col_anchors))}
        for word in sorted(row, key=lambda w: w.left):
            col_idx = _nearest_anchor_index(word.left, col_anchors)
            cols[col_idx].append(word.text)
        grid.append([" ".join(cols[i]) for i in range(len(col_anchors))])

    return grid


def _infer_column_anchors(x_positions: list[int], min_gap: int = 30) -> list[int]:
    """
    Cluster x-positions into column left-edges using a simple gap heuristic.
    """
    if not x_positions:
        return [0]

    sorted_x = sorted(set(x_positions))
    anchors = [sorted_x[0]]
    for x in sorted_x[1:]:
        if x - anchors[-1] > min_gap:
            anchors.append(x)

    return anchors


def _nearest_anchor_index(x: int, anchors: list[int]) -> int:
    """Return index of the nearest column anchor to x."""
    return min(range(len(anchors)), key=lambda i: abs(anchors[i] - x))


# ── Helpers ───────────────────────────────────────────────────────────────────

def _pil_to_bgr(image: Image.Image) -> np.ndarray:
    return cv2.cvtColor(np.array(image.convert("RGB")), cv2.COLOR_RGB2BGR)


def _collect_words_in_rect(
    words: list[OcrWord],
    x: int,
    y: int,
    w: int,
    h: int,
    overlap_threshold: float = 0.5,
) -> str:
    """Return text of OCR words whose center falls inside the given rect."""
    collected = []
    for word in words:
        cx = word.left + word.width // 2
        cy = word.top + word.height // 2
        if x <= cx <= x + w and y <= cy <= y + h:
            collected.append(word.text)
    return " ".join(collected)
