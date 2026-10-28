"""
Template Editor Dialog — lets the user draw bounding boxes on a reference image
and label each box as a named field.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt, QRect, QPoint, pyqtSignal
from PyQt6.QtGui import QPainter, QPen, QColor, QPixmap, QFont
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QSplitter,
    QLabel, QPushButton, QListWidget, QListWidgetItem,
    QLineEdit, QComboBox, QMessageBox, QFileDialog,
    QScrollArea, QWidget, QInputDialog, QCheckBox,
)

from app.templates.template_manager import (
    Template, TemplateField, list_templates, load_template, save_template, delete_template
)


# ── Image canvas with box-drawing ─────────────────────────────────────────────

class RegionCanvas(QLabel):
    """
    Display a reference image and let the user draw rectangular regions.
    Emits region_added(QRect) when a box is completed.
    """
    region_added = pyqtSignal(QRect)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(400, 500)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self._origin: QPoint | None = None
        self._current_rect: QRect | None = None
        self._confirmed_rects: list[tuple[QRect, str]] = []
        self._pixmap: QPixmap | None = None
        self._scale: float = 1.0

    def load_image(self, path: str) -> None:
        self._pixmap = QPixmap(path)
        self._confirmed_rects = []
        self._update_scale()
        self.update()

    def set_fields(self, fields: list[TemplateField]) -> None:
        self._confirmed_rects = [
            (QRect(f.region[0], f.region[1], f.region[2], f.region[3]), f.name)
            for f in fields
            if len(f.region) == 4
        ]
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._origin = event.pos()
            self._current_rect = None

    def mouseMoveEvent(self, event):
        if self._origin:
            self._current_rect = QRect(self._origin, event.pos()).normalized()
            self.update()

    def mouseReleaseEvent(self, event):
        if self._origin and self._current_rect and self._current_rect.width() > 5:
            # Convert display coords to image coords
            scaled_rect = QRect(
                int(self._current_rect.x() / self._scale),
                int(self._current_rect.y() / self._scale),
                int(self._current_rect.width() / self._scale),
                int(self._current_rect.height() / self._scale),
            )
            self.region_added.emit(scaled_rect)
        self._origin = None
        self._current_rect = None

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self._pixmap:
            return

        painter = QPainter(self)
        scaled_px = self._pixmap.scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._scale = scaled_px.width() / self._pixmap.width()
        painter.drawPixmap(0, 0, scaled_px)

        # Draw confirmed regions
        for rect, name in self._confirmed_rects:
            display_rect = QRect(
                int(rect.x() * self._scale),
                int(rect.y() * self._scale),
                int(rect.width() * self._scale),
                int(rect.height() * self._scale),
            )
            painter.setPen(QPen(QColor("#7C83FD"), 2))
            painter.drawRect(display_rect)
            painter.setPen(QPen(QColor("#FFFFFF")))
            painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            painter.drawText(display_rect.topLeft() + QPoint(4, 14), name)

        # Draw in-progress rect
        if self._current_rect:
            painter.setPen(QPen(QColor("#00C9A7"), 2, Qt.PenStyle.DashLine))
            painter.drawRect(self._current_rect)

    def _update_scale(self):
        if self._pixmap:
            self._scale = min(
                self.width() / self._pixmap.width(),
                self.height() / self._pixmap.height(),
                1.0,
            )


# ── Template Editor Dialog ────────────────────────────────────────────────────

class TemplateEditorDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Gestionnaire de modèles")
        self.setMinimumSize(1000, 680)
        self.setModal(True)
        self._current_template: Template | None = None
        self._pending_rect: QRect | None = None
        self._build_ui()
        self._refresh_template_list()
        self._apply_style()

    def _build_ui(self):
        layout = QHBoxLayout(self)

        # ── Left: template list ──
        left = QWidget()
        left.setFixedWidth(220)
        ll = QVBoxLayout(left)
        ll.setContentsMargins(8, 8, 8, 8)

        ll.addWidget(QLabel("📋  Modèles sauvegardés"))

        self._template_list = QListWidget()
        self._template_list.currentItemChanged.connect(self._on_template_selected)
        ll.addWidget(self._template_list)

        btn_row = QHBoxLayout()
        new_btn = QPushButton("+ Nouveau")
        new_btn.clicked.connect(self._new_template)
        btn_row.addWidget(new_btn)

        del_btn = QPushButton("🗑")
        del_btn.setFixedWidth(36)
        del_btn.setToolTip("Supprimer le modèle")
        del_btn.clicked.connect(self._delete_template)
        btn_row.addWidget(del_btn)
        ll.addLayout(btn_row)
        layout.addWidget(left)

        # ── Center: image canvas ──
        center = QVBoxLayout()

        img_toolbar = QHBoxLayout()
        load_img_btn = QPushButton("📷  Charger image de référence")
        load_img_btn.clicked.connect(self._load_reference_image)
        img_toolbar.addWidget(load_img_btn)
        img_toolbar.addStretch()
        center.addLayout(img_toolbar)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self._canvas = RegionCanvas()
        self._canvas.region_added.connect(self._on_region_drawn)
        scroll.setWidget(self._canvas)
        center.addWidget(scroll, 1)
        layout.addLayout(center, 1)

        # ── Right: field list + editor ──
        right = QWidget()
        right.setFixedWidth(260)
        rl = QVBoxLayout(right)
        rl.setContentsMargins(8, 8, 8, 8)

        rl.addWidget(QLabel("📌  Champs du modèle"))

        self._field_list = QListWidget()
        self._field_list.setFixedHeight(200)
        rl.addWidget(self._field_list)

        del_field_btn = QPushButton("− Supprimer le champ")
        del_field_btn.clicked.connect(self._delete_field)
        rl.addWidget(del_field_btn)

        rl.addWidget(QLabel("─" * 28))
        rl.addWidget(QLabel("Nouveau champ en attente :"))

        self._field_name_input = QLineEdit()
        self._field_name_input.setPlaceholderText("Nom du champ (ex: N° Facture)")
        rl.addWidget(self._field_name_input)

        self._field_type_combo = QComboBox()
        self._field_type_combo.addItems(["text", "table", "number", "date"])
        rl.addWidget(self._field_type_combo)

        self._required_check = QCheckBox("Champ obligatoire")
        rl.addWidget(self._required_check)

        self._add_field_btn = QPushButton("✔  Valider et ajouter le champ")
        self._add_field_btn.setEnabled(False)
        self._add_field_btn.clicked.connect(self._confirm_field)
        rl.addWidget(self._add_field_btn)

        rl.addStretch()

        save_btn = QPushButton("💾  Enregistrer le modèle")
        save_btn.setObjectName("saveTplBtn")
        save_btn.clicked.connect(self._save_template)
        rl.addWidget(save_btn)

        layout.addWidget(right)

    # ── Template list ─────────────────────────────────────────────────────────

    def _refresh_template_list(self):
        self._template_list.clear()
        for name in list_templates():
            self._template_list.addItem(name)

    def _on_template_selected(self, item: QListWidgetItem | None):
        if not item:
            return
        try:
            self._current_template = load_template(item.text())
            self._refresh_field_list()
            self._canvas.set_fields(self._current_template.fields)
        except Exception as exc:
            QMessageBox.critical(self, "Erreur", str(exc))

    def _new_template(self):
        name, ok = QInputDialog.getText(self, "Nouveau modèle", "Nom du modèle :")
        if ok and name.strip():
            self._current_template = Template(name=name.strip())
            self._refresh_field_list()
            self._canvas.set_fields([])

    def _delete_template(self):
        item = self._template_list.currentItem()
        if not item:
            return
        if QMessageBox.question(self, "Confirmation",
                                f"Supprimer « {item.text()} » ?") == QMessageBox.StandardButton.Yes:
            delete_template(item.text())
            self._refresh_template_list()

    # ── Field management ──────────────────────────────────────────────────────

    def _load_reference_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Charger image de référence", "",
            "Images (*.jpg *.jpeg *.png *.bmp)"
        )
        if path:
            self._canvas.load_image(path)

    def _on_region_drawn(self, rect: QRect):
        self._pending_rect = rect
        self._add_field_btn.setEnabled(True)
        self._field_name_input.setFocus()

    def _confirm_field(self):
        if not self._current_template or not self._pending_rect:
            return
        name = self._field_name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Nom manquant", "Entrez un nom pour ce champ.")
            return

        r = self._pending_rect
        field = TemplateField(
            name=name,
            region=[r.x(), r.y(), r.width(), r.height()],
            field_type=self._field_type_combo.currentText(),
            required=self._required_check.isChecked(),
        )
        self._current_template.fields.append(field)
        self._refresh_field_list()
        self._canvas.set_fields(self._current_template.fields)
        self._field_name_input.clear()
        self._pending_rect = None
        self._add_field_btn.setEnabled(False)

    def _delete_field(self):
        if not self._current_template:
            return
        row = self._field_list.currentRow()
        if 0 <= row < len(self._current_template.fields):
            self._current_template.fields.pop(row)
            self._refresh_field_list()
            self._canvas.set_fields(self._current_template.fields)

    def _refresh_field_list(self):
        self._field_list.clear()
        if not self._current_template:
            return
        for f in self._current_template.fields:
            self._field_list.addItem(f"[{f.field_type}] {f.name}")

    def _save_template(self):
        if not self._current_template:
            QMessageBox.warning(self, "Aucun modèle", "Créez d'abord un modèle.")
            return
        save_template(self._current_template)
        self._refresh_template_list()
        QMessageBox.information(self, "Enregistré",
                                f"Modèle « {self._current_template.name} » enregistré.")

    def _apply_style(self):
        self.setStyleSheet("""
            QDialog, QWidget { background: #0F0F1A; color: #D0D0F0; font-size: 13px; }
            QListWidget {
                background: #13132A; border: 1px solid #2A2A4A;
                border-radius: 6px;
            }
            QListWidget::item:selected { background: #2A2A6A; }
            QLineEdit, QComboBox {
                background: #1E1E3A; border: 1px solid #3A3A6A;
                border-radius: 5px; padding: 5px 8px; color: #C0C0E0;
            }
            QPushButton {
                background: #1E1E3A; color: #7C83FD;
                border: 1px solid #3A3A6A; border-radius: 6px; padding: 6px 12px;
            }
            QPushButton:hover { background: #2A2A5A; }
            #saveTplBtn {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 #00C9A7, stop:1 #009B7D);
                color: white; border: none; font-weight: bold;
            }
            QScrollArea { border: none; }
            QLabel { color: #9090C0; }
        """)
