"""
Main Application Window — PyQt6
Dark premium theme with drag-and-drop support.
"""
from __future__ import annotations

import os
import threading
from pathlib import Path

from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QPixmap, QFont
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QFileDialog,
    QSplitter, QFrame, QMessageBox, QProgressBar,
    QTabWidget, QSizePolicy, QApplication,
)

from app.pipeline.input_handler import classify_file, collect_files_from_folder, InputType, FileEntry
from app.ui.preview_table import PreviewTableWidget
from app.ui.batch_panel import BatchPanel
from app.ui.template_editor import TemplateEditorDialog


# ── Worker thread ─────────────────────────────────────────────────────────────

class ProcessWorker(QThread):
    progress = pyqtSignal(str)
    finished = pyqtSignal(object)   # NormalizedTable
    error    = pyqtSignal(str)

    def __init__(self, entry: FileEntry, parent=None):
        super().__init__(parent)
        self.entry = entry

    def run(self):
        try:
            from app.pipeline.preprocessor import preprocess
            from app.pipeline.ocr_engine import ocr_page
            from app.pipeline.table_detector import detect_table
            from app.pipeline.normalizer import normalize_table
            from app.utils.pdf_utils import pdf_to_images, extract_tables_from_pdf
            from PIL import Image as PILImage

            self.progress.emit("Préparation du fichier…")

            all_grids = []

            if self.entry.input_type == InputType.DIGITAL_PDF:
                self.progress.emit("Extraction du texte PDF…")
                tables = extract_tables_from_pdf(self.entry.path, password=self.entry.password)
                for t in tables:
                    all_grids.extend(t)
            else:
                if self.entry.input_type == InputType.IMAGE:
                    images = [(1, PILImage.open(self.entry.path))]
                else:
                    images = list(pdf_to_images(self.entry.path, password=self.entry.password))

                for page_num, img in images:
                    self.progress.emit(f"Traitement page {page_num}…")
                    preprocessed = preprocess(img)
                    self.progress.emit("Reconnaissance OCR…")
                    ocr_result = ocr_page(preprocessed)
                    self.progress.emit("Détection du tableau…")
                    grid = detect_table(preprocessed, ocr_result)
                    if grid:
                        all_grids.extend(grid)

            self.progress.emit("Normalisation des données…")
            combined = all_grids if all_grids else [[]]
            norm = normalize_table(combined)
            self.finished.emit(norm)

        except Exception as exc:
            self.error.emit(str(exc))


# ── Main Window ───────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Facture Converter — v1.0")
        self.setMinimumSize(1100, 720)
        self.resize(1280, 800)
        self.setAcceptDrops(True)

        self._current_entry: FileEntry | None = None
        self._worker: ProcessWorker | None = None
        self._norm_table = None

        self._build_ui()
        self._apply_stylesheet()

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ── Top bar ──
        root_layout.addWidget(self._build_topbar())

        # ── Tabs ──
        self._tabs = QTabWidget()
        self._tabs.setDocumentMode(True)
        root_layout.addWidget(self._tabs)

        # Tab 1: Single file
        self._single_tab = self._build_single_tab()
        self._tabs.addTab(self._single_tab, "📄  Fichier unique")

        # Tab 2: Batch
        self._batch_tab = BatchPanel()
        self._tabs.addTab(self._batch_tab, "📂  Traitement groupé")

        # ── Status bar ──
        self._status_label = QLabel("Prêt. Glissez un fichier ou cliquez sur Ouvrir.")
        self._status_label.setObjectName("statusLabel")
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 0)  # Indeterminate
        self._progress_bar.setVisible(False)
        self._progress_bar.setMaximumHeight(4)

        status_bar = QWidget()
        status_bar.setObjectName("statusBar")
        sb_layout = QVBoxLayout(status_bar)
        sb_layout.setContentsMargins(12, 4, 12, 4)
        sb_layout.setSpacing(2)
        sb_layout.addWidget(self._progress_bar)
        sb_layout.addWidget(self._status_label)
        root_layout.addWidget(status_bar)

    def _build_topbar(self) -> QWidget:
        bar = QWidget()
        bar.setObjectName("topBar")
        bar.setFixedHeight(56)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(16, 0, 16, 0)

        logo = QLabel("🧾  Facture Converter")
        logo.setObjectName("logoLabel")
        layout.addWidget(logo)

        layout.addStretch()

        self._open_btn = QPushButton("📂  Ouvrir fichier")
        self._open_btn.setObjectName("primaryBtn")
        self._open_btn.clicked.connect(self._open_file_dialog)
        layout.addWidget(self._open_btn)

        self._template_btn = QPushButton("🗂  Modèles")
        self._template_btn.setObjectName("secondaryBtn")
        self._template_btn.clicked.connect(self._open_template_editor)
        layout.addWidget(self._template_btn)

        return bar

    def _build_single_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(12, 12, 12, 8)
        layout.setSpacing(8)

        # ── Splitter: left = drop zone / image, right = table ──
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: drop zone / image preview
        self._left_panel = self._build_left_panel()
        splitter.addWidget(self._left_panel)

        # Right: editable table
        self._preview_table = PreviewTableWidget()
        splitter.addWidget(self._preview_table)

        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)
        layout.addWidget(splitter, 1)

        # ── Export controls ──
        layout.addWidget(self._build_export_bar())

        return widget

    def _build_left_panel(self) -> QWidget:
        frame = QFrame()
        frame.setObjectName("dropFrame")
        layout = QVBoxLayout(frame)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._drop_icon = QLabel("⬇")
        self._drop_icon.setObjectName("dropIcon")
        self._drop_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._drop_label = QLabel(
            "Glissez un fichier ici\n(JPG, PNG, PDF)"
        )
        self._drop_label.setObjectName("dropLabel")
        self._drop_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._image_preview = QLabel()
        self._image_preview.setObjectName("imagePreview")
        self._image_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._image_preview.setScaledContents(False)
        self._image_preview.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._image_preview.setVisible(False)

        layout.addStretch()
        layout.addWidget(self._drop_icon)
        layout.addWidget(self._drop_label)
        layout.addWidget(self._image_preview)
        layout.addStretch()

        return frame

    def _build_export_bar(self) -> QWidget:
        bar = QWidget()
        bar.setObjectName("exportBar")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(8, 6, 8, 6)

        layout.addWidget(QLabel("Mode :"))
        self._mode_combo = QComboBox()
        self._mode_combo.addItems(["Cloner la mise en page", "Appliquer un modèle"])
        self._mode_combo.setObjectName("modeCombo")
        layout.addWidget(self._mode_combo)

        layout.addWidget(QLabel("Format :"))
        self._format_combo = QComboBox()
        self._format_combo.addItems(["XLSX", "DOCX"])
        self._format_combo.setObjectName("formatCombo")
        layout.addWidget(self._format_combo)

        layout.addStretch()

        self._export_btn = QPushButton("⬇  Exporter")
        self._export_btn.setObjectName("exportBtn")
        self._export_btn.setEnabled(False)
        self._export_btn.clicked.connect(self._export)
        layout.addWidget(self._export_btn)

        return bar

    # ── Drag and Drop ─────────────────────────────────────────────────────────

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        if not urls:
            return
        path = urls[0].toLocalFile()
        if os.path.isdir(path):
            self._tabs.setCurrentIndex(1)
            self._batch_tab.load_folder(path)
        else:
            self._load_file(path)

    # ── File loading ──────────────────────────────────────────────────────────

    def _open_file_dialog(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Ouvrir un fichier",
            os.path.expanduser("~"),
            "Fichiers supportés (*.jpg *.jpeg *.png *.bmp *.tiff *.pdf);;Tous les fichiers (*)",
        )
        if path:
            self._load_file(path)

    def _load_file(self, path: str):
        self._tabs.setCurrentIndex(0)
        entry = classify_file(path)

        if entry.input_type == InputType.UNSUPPORTED:
            QMessageBox.warning(self, "Fichier non supporté", entry.error or "Type de fichier non supporté.")
            return

        if entry.needs_password:
            from PyQt6.QtWidgets import QInputDialog
            pwd, ok = QInputDialog.getText(
                self, "PDF Protégé", "Entrez le mot de passe du PDF :",
                echo=QApplication.inputMethod().locale().__class__.echoMode if False else 0,
            )
            if not ok:
                return
            entry.password = pwd

        self._current_entry = entry
        self._show_file_preview(path)
        self._run_pipeline(entry)

    def _show_file_preview(self, path: str):
        ext = Path(path).suffix.lower()
        if ext in {".jpg", ".jpeg", ".png", ".bmp"}:
            pixmap = QPixmap(path)
            if not pixmap.isNull():
                scaled = pixmap.scaled(
                    self._left_panel.width() - 20,
                    self._left_panel.height() - 20,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                self._image_preview.setPixmap(scaled)
                self._image_preview.setVisible(True)
                self._drop_icon.setVisible(False)
                self._drop_label.setVisible(False)
        else:
            self._drop_icon.setText("📄")
            self._drop_label.setText(f"{Path(path).name}\n({self._current_entry.page_count} page(s))")

    def _run_pipeline(self, entry: FileEntry):
        if self._worker and self._worker.isRunning():
            self._worker.terminate()

        self._set_processing_state(True)
        self._export_btn.setEnabled(False)

        self._worker = ProcessWorker(entry)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_pipeline_done)
        self._worker.error.connect(self._on_pipeline_error)
        self._worker.start()

    # ── Pipeline callbacks ────────────────────────────────────────────────────

    def _on_progress(self, msg: str):
        self._status_label.setText(msg)

    def _on_pipeline_done(self, norm_table):
        self._norm_table = norm_table
        self._set_processing_state(False)
        self._preview_table.load_table(norm_table)
        self._export_btn.setEnabled(True)
        self._status_label.setText(
            f"✅ Extraction terminée — {len(norm_table.rows)} lignes. Vérifiez et exportez."
        )

    def _on_pipeline_error(self, msg: str):
        self._set_processing_state(False)
        self._status_label.setText(f"⚠ Erreur : {msg}")
        QMessageBox.critical(self, "Erreur de traitement", msg)

    def _set_processing_state(self, processing: bool):
        self._progress_bar.setVisible(processing)
        self._open_btn.setEnabled(not processing)

    # ── Export ────────────────────────────────────────────────────────────────

    def _export(self):
        if not self._norm_table:
            return

        fmt = self._format_combo.currentText().lower()
        mode = "clone" if self._mode_combo.currentIndex() == 0 else "template"

        default_name = "export"
        if self._current_entry:
            default_name = Path(self._current_entry.path).stem

        from app.utils.config import EXPORTS_DIR
        save_path, _ = QFileDialog.getSaveFileName(
            self, "Enregistrer sous",
            os.path.join(EXPORTS_DIR, f"{default_name}.{fmt}"),
            f"Fichier {fmt.upper()} (*.{fmt})",
        )
        if not save_path:
            return

        try:
            if fmt == "xlsx":
                from app.export.xlsx_writer import write_xlsx
                write_xlsx(self._norm_table, save_path, mode=mode)
            else:
                from app.export.docx_writer import write_docx
                write_docx(self._norm_table, save_path, mode=mode)

            self._status_label.setText(f"✅ Exporté : {save_path}")
            QMessageBox.information(self, "Export réussi", f"Fichier enregistré :\n{save_path}")
        except Exception as exc:
            QMessageBox.critical(self, "Erreur d'export", str(exc))

    # ── Template editor ───────────────────────────────────────────────────────

    def _open_template_editor(self):
        dlg = TemplateEditorDialog(self)
        dlg.exec()

    # ── Stylesheet ────────────────────────────────────────────────────────────

    def _apply_stylesheet(self):
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #0F0F1A;
                color: #E0E0F0;
                font-family: 'Segoe UI', sans-serif;
                font-size: 13px;
            }
            #topBar {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 #1A1A2E, stop:1 #16213E);
                border-bottom: 1px solid #2A2A4A;
            }
            #logoLabel {
                font-size: 18px;
                font-weight: bold;
                color: #7C83FD;
            }
            #primaryBtn {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 #7C83FD, stop:1 #5B63D3);
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 18px;
                font-weight: bold;
            }
            #primaryBtn:hover { background: #8A91FF; }
            #primaryBtn:disabled { background: #3A3A5A; color: #666688; }

            #secondaryBtn {
                background: transparent;
                color: #7C83FD;
                border: 1px solid #7C83FD;
                border-radius: 8px;
                padding: 7px 16px;
            }
            #secondaryBtn:hover { background: #1E1E3A; }

            #exportBtn {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 #00C9A7, stop:1 #009B7D);
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 22px;
                font-weight: bold;
                font-size: 14px;
            }
            #exportBtn:hover { background: #00DFB8; }
            #exportBtn:disabled { background: #1A3A30; color: #44665C; }

            #dropFrame {
                background: #13132A;
                border: 2px dashed #2A2A5A;
                border-radius: 16px;
            }
            #dropFrame:hover { border-color: #7C83FD; }
            #dropIcon  { font-size: 48px; color: #4A4A7A; }
            #dropLabel { color: #5A5A8A; font-size: 14px; }
            #imagePreview { border-radius: 8px; }

            #exportBar {
                background: #13132A;
                border-top: 1px solid #2A2A4A;
                border-radius: 0 0 8px 8px;
            }
            #statusBar  { background: #0A0A18; border-top: 1px solid #1A1A3A; }
            #statusLabel { color: #6A6A9A; font-size: 12px; }

            QComboBox {
                background: #1E1E3A;
                border: 1px solid #3A3A6A;
                border-radius: 6px;
                padding: 4px 10px;
                color: #C0C0E0;
            }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView {
                background: #1E1E3A;
                selection-background-color: #7C83FD;
            }

            QTabWidget::pane { border: none; }
            QTabBar::tab {
                background: #13132A;
                color: #5A5A8A;
                padding: 10px 24px;
                border: none;
                font-size: 13px;
            }
            QTabBar::tab:selected { color: #7C83FD; border-bottom: 2px solid #7C83FD; }
            QTabBar::tab:hover    { color: #A0A7FF; }

            QProgressBar {
                background: #1A1A3A;
                border: none;
                border-radius: 2px;
            }
            QProgressBar::chunk { background: #7C83FD; border-radius: 2px; }

            QSplitter::handle { background: #2A2A4A; width: 2px; }
            QMessageBox { background: #1A1A2E; }
        """)
