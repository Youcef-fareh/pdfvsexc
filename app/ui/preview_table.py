"""
Preview Table Widget — editable spreadsheet-like grid showing OCR results.
Low-confidence cells are highlighted in amber; currency rows in green.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt, QAbstractTableModel, QModelIndex, QVariant
from PyQt6.QtGui import QColor, QFont, QBrush
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableView,
    QPushButton, QHeaderView, QAbstractItemView, QLabel,
    QSizePolicy,
)

from app.pipeline.normalizer import NormalizedTable, NormalizedCell


# ── Table model ───────────────────────────────────────────────────────────────

class TableModel(QAbstractTableModel):
    _COL_HEADER_BG  = QColor("#1A1A2E")
    _COL_HEADER_FG  = QColor("#7C83FD")
    _LOW_CONF_BG    = QColor("#3A2E00")
    _LOW_CONF_FG    = QColor("#FFD54F")
    _CURRENCY_BG    = QColor("#0A2E20")
    _CURRENCY_FG    = QColor("#4CAF50")
    _EVEN_ROW_BG    = QColor("#13132A")
    _ODD_ROW_BG     = QColor("#0F0F20")
    _DEFAULT_FG     = QColor("#D0D0F0")

    def __init__(self, norm_table: NormalizedTable, parent=None):
        super().__init__(parent)
        self._table = norm_table
        # Mutable copy for in-place editing
        self._data: list[list[str]] = [
            [cell.cleaned for cell in row]
            for row in norm_table.rows
        ]
        self._meta: list[list[NormalizedCell]] = norm_table.rows

    # ── Qt Model interface ────────────────────────────────────────────────────

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self._data)

    def columnCount(self, parent=QModelIndex()) -> int:
        if not self._data:
            return 0
        return max(len(r) for r in self._data)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return QVariant()
        r, c = index.row(), index.column()
        row = self._data[r]
        val = row[c] if c < len(row) else ""

        if role == Qt.ItemDataRole.DisplayRole or role == Qt.ItemDataRole.EditRole:
            return val

        if role == Qt.ItemDataRole.BackgroundRole:
            return self._bg_color(r, c)

        if role == Qt.ItemDataRole.ForegroundRole:
            return self._fg_color(r, c)

        if role == Qt.ItemDataRole.TextAlignmentRole:
            try:
                meta = self._meta[r][c] if c < len(self._meta[r]) else None
                if meta and (meta.is_numeric or meta.is_rtl):
                    return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            except IndexError:
                pass
            return Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter

        return QVariant()

    def setData(self, index: QModelIndex, value, role=Qt.ItemDataRole.EditRole) -> bool:
        if role == Qt.ItemDataRole.EditRole and index.isValid():
            r, c = index.row(), index.column()
            while len(self._data[r]) <= c:
                self._data[r].append("")
            self._data[r][c] = str(value)
            self.dataChanged.emit(index, index, [role])
            return True
        return False

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        return (Qt.ItemFlag.ItemIsEnabled |
                Qt.ItemFlag.ItemIsSelectable |
                Qt.ItemFlag.ItemIsEditable)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int):
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                return chr(65 + section) if section < 26 else f"C{section}"
            return str(section + 1)
        if role == Qt.ItemDataRole.ForegroundRole:
            return QBrush(self._COL_HEADER_FG)
        return QVariant()

    # ── Row/column operations ─────────────────────────────────────────────────

    def insert_row(self, after_row: int) -> None:
        pos = min(after_row + 1, len(self._data))
        cols = self.columnCount()
        self.beginInsertRows(QModelIndex(), pos, pos)
        self._data.insert(pos, [""] * cols)
        self._meta.insert(pos, [NormalizedCell(raw="", cleaned="", is_numeric=False)] * cols)
        self.endInsertRows()

    def delete_row(self, row: int) -> None:
        if 0 <= row < len(self._data):
            self.beginRemoveRows(QModelIndex(), row, row)
            self._data.pop(row)
            self._meta.pop(row)
            self.endRemoveRows()

    def to_string_grid(self) -> list[list[str]]:
        return [list(row) for row in self._data]

    # ── Colour helpers ────────────────────────────────────────────────────────

    def _bg_color(self, r: int, c: int) -> QBrush:
        try:
            meta = self._meta[r][c] if c < len(self._meta[r]) else None
        except IndexError:
            meta = None

        if meta:
            if meta.is_currency_row:
                return QBrush(self._CURRENCY_BG)
        return QBrush(self._EVEN_ROW_BG if r % 2 == 0 else self._ODD_ROW_BG)

    def _fg_color(self, r: int, c: int) -> QBrush:
        try:
            meta = self._meta[r][c] if c < len(self._meta[r]) else None
        except IndexError:
            meta = None
        if meta and meta.is_currency_row:
            return QBrush(self._CURRENCY_FG)
        return QBrush(self._DEFAULT_FG)


# ── Widget ────────────────────────────────────────────────────────────────────

class PreviewTableWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._model: TableModel | None = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Toolbar
        toolbar = QWidget()
        tb_layout = QHBoxLayout(toolbar)
        tb_layout.setContentsMargins(8, 4, 8, 4)

        title = QLabel("📊  Données extraites")
        title.setObjectName("sectionTitle")
        tb_layout.addWidget(title)
        tb_layout.addStretch()

        add_row_btn = QPushButton("+ Ligne")
        add_row_btn.setObjectName("toolBtn")
        add_row_btn.setFixedWidth(80)
        add_row_btn.clicked.connect(self._add_row)
        tb_layout.addWidget(add_row_btn)

        del_row_btn = QPushButton("− Ligne")
        del_row_btn.setObjectName("toolBtnDanger")
        del_row_btn.setFixedWidth(80)
        del_row_btn.clicked.connect(self._delete_row)
        tb_layout.addWidget(del_row_btn)

        layout.addWidget(toolbar)

        # Table view
        self._view = QTableView()
        self._view.setAlternatingRowColors(False)
        self._view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        self._view.setSelectionMode(QAbstractItemView.SelectionMode.ContiguousSelection)
        self._view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self._view.horizontalHeader().setDefaultSectionSize(130)
        self._view.verticalHeader().setDefaultSectionSize(30)
        self._view.setShowGrid(True)
        self._view.setGridStyle(Qt.PenStyle.SolidLine)
        self._view.setObjectName("previewTable")
        layout.addWidget(self._view)

        self._apply_styles()

    def load_table(self, norm_table: NormalizedTable) -> None:
        self._model = TableModel(norm_table)
        self._view.setModel(self._model)
        self._view.resizeColumnsToContents()

    def get_data(self) -> list[list[str]]:
        if self._model:
            return self._model.to_string_grid()
        return []

    def _add_row(self):
        if not self._model:
            return
        selected = self._view.selectionModel().currentIndex()
        row = selected.row() if selected.isValid() else self._model.rowCount() - 1
        self._model.insert_row(row)

    def _delete_row(self):
        if not self._model:
            return
        selected = self._view.selectionModel().currentIndex()
        if selected.isValid():
            self._model.delete_row(selected.row())

    def _apply_styles(self):
        self.setStyleSheet("""
            #sectionTitle { color: #7C83FD; font-weight: bold; font-size: 14px; }
            #toolBtn {
                background: #1E1E3A; color: #7C83FD;
                border: 1px solid #3A3A6A; border-radius: 5px; padding: 3px 8px;
            }
            #toolBtn:hover { background: #2A2A5A; }
            #toolBtnDanger {
                background: #2A1A1A; color: #EF5350;
                border: 1px solid #5A2A2A; border-radius: 5px; padding: 3px 8px;
            }
            #toolBtnDanger:hover { background: #3A1A1A; }
            #previewTable {
                background: #0F0F20;
                gridline-color: #2A2A4A;
                border: none;
                border-radius: 8px;
            }
            QHeaderView::section {
                background: #1A1A2E; color: #7C83FD;
                border: none; border-right: 1px solid #2A2A4A;
                padding: 4px 8px; font-weight: bold;
            }
            QTableView::item:selected { background: #2A2A6A; color: white; }
        """)
