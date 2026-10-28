"""
Batch Processing Panel — drag a folder and process multiple files sequentially.
"""
from __future__ import annotations

import os
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QProgressBar,
    QFileDialog, QComboBox, QMessageBox,
)

from app.pipeline.input_handler import collect_files_from_folder, FileEntry
from app.pipeline.batch_runner import (
    BatchResult, BatchStatus, run_batch, generate_batch_report
)
from app.utils.config import EXPORTS_DIR


# ── Batch worker ──────────────────────────────────────────────────────────────

class BatchWorker(QThread):
    progress    = pyqtSignal(int, int, object)   # current, total, BatchResult
    all_done    = pyqtSignal(list)               # list[BatchResult]

    def __init__(self, entries, fmt, mode, output_dir, parent=None):
        super().__init__(parent)
        self.entries    = entries
        self.fmt        = fmt
        self.mode       = mode
        self.output_dir = output_dir
        self._cancel    = [False]

    def cancel(self):
        self._cancel[0] = True

    def run(self):
        results = run_batch(
            entries=self.entries,
            export_format=self.fmt,
            export_mode=self.mode,
            output_dir=self.output_dir,
            progress_cb=lambda cur, tot, r: self.progress.emit(cur, tot, r),
            cancel_flag=self._cancel,
        )
        self.all_done.emit(results)


# ── Panel widget ──────────────────────────────────────────────────────────────

class BatchPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._entries: list[FileEntry] = []
        self._worker: BatchWorker | None = None
        self._build_ui()
        self._apply_style()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 8)

        # ── Top controls ──
        top = QHBoxLayout()
        self._folder_label = QLabel("Aucun dossier sélectionné")
        self._folder_label.setObjectName("folderLabel")
        top.addWidget(self._folder_label, 1)

        pick_btn = QPushButton("📂  Choisir dossier")
        pick_btn.clicked.connect(self._pick_folder)
        top.addWidget(pick_btn)
        layout.addLayout(top)

        # ── File table ──
        self._file_table = QTableWidget(0, 4)
        self._file_table.setHorizontalHeaderLabels(["Fichier", "Type", "Pages", "Statut"])
        self._file_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._file_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self._file_table.setSelectionBehavior(self._file_table.SelectionBehavior.SelectRows)
        self._file_table.setEditTriggers(self._file_table.EditTrigger.NoEditTriggers)
        self._file_table.setObjectName("batchTable")
        layout.addWidget(self._file_table, 1)

        # ── Export options ──
        opt = QHBoxLayout()
        opt.addWidget(QLabel("Format :"))
        self._fmt_combo = QComboBox()
        self._fmt_combo.addItems(["XLSX", "DOCX"])
        opt.addWidget(self._fmt_combo)

        opt.addWidget(QLabel("Mode :"))
        self._mode_combo = QComboBox()
        self._mode_combo.addItems(["Cloner mise en page", "Appliquer modèle"])
        opt.addWidget(self._mode_combo)

        opt.addWidget(QLabel("Sortie :"))
        self._out_label = QLabel(EXPORTS_DIR)
        self._out_label.setObjectName("outLabel")
        opt.addWidget(self._out_label, 1)

        out_btn = QPushButton("…")
        out_btn.setFixedWidth(30)
        out_btn.clicked.connect(self._pick_output_dir)
        opt.addWidget(out_btn)
        layout.addLayout(opt)

        # ── Progress ──
        self._overall_bar = QProgressBar()
        self._overall_bar.setMaximumHeight(6)
        self._overall_bar.setVisible(False)
        layout.addWidget(self._overall_bar)

        # ── Action buttons ──
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self._start_btn = QPushButton("▶  Lancer le traitement")
        self._start_btn.setObjectName("startBtn")
        self._start_btn.setEnabled(False)
        self._start_btn.clicked.connect(self._start_batch)
        btn_row.addWidget(self._start_btn)

        self._cancel_btn = QPushButton("⏹  Annuler")
        self._cancel_btn.setObjectName("cancelBtn")
        self._cancel_btn.setEnabled(False)
        self._cancel_btn.clicked.connect(self._cancel_batch)
        btn_row.addWidget(self._cancel_btn)

        self._report_btn = QPushButton("📊  Ouvrir rapport")
        self._report_btn.setEnabled(False)
        self._report_btn.clicked.connect(self._open_report)
        btn_row.addWidget(self._report_btn)
        layout.addLayout(btn_row)

        self._report_path: str = ""

    # ── Folder loading ────────────────────────────────────────────────────────

    def load_folder(self, folder: str) -> None:
        self._entries = collect_files_from_folder(folder)
        self._folder_label.setText(folder)
        self._populate_table()
        self._start_btn.setEnabled(bool(self._entries))

    def _pick_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Choisir un dossier")
        if folder:
            self.load_folder(folder)

    def _pick_output_dir(self):
        folder = QFileDialog.getExistingDirectory(self, "Dossier de sortie")
        if folder:
            self._out_label.setText(folder)

    def _populate_table(self):
        self._file_table.setRowCount(0)
        for entry in self._entries:
            r = self._file_table.rowCount()
            self._file_table.insertRow(r)
            self._file_table.setItem(r, 0, QTableWidgetItem(os.path.basename(entry.path)))
            self._file_table.setItem(r, 1, QTableWidgetItem(entry.input_type.name))
            self._file_table.setItem(r, 2, QTableWidgetItem(str(entry.page_count)))
            self._file_table.setItem(r, 3, QTableWidgetItem("En attente"))

    # ── Batch control ─────────────────────────────────────────────────────────

    def _start_batch(self):
        if not self._entries:
            return
        fmt  = self._fmt_combo.currentText().lower()
        mode = "clone" if self._mode_combo.currentIndex() == 0 else "template"
        out  = self._out_label.text()

        self._overall_bar.setVisible(True)
        self._overall_bar.setMaximum(len(self._entries))
        self._overall_bar.setValue(0)
        self._start_btn.setEnabled(False)
        self._cancel_btn.setEnabled(True)
        self._report_btn.setEnabled(False)

        self._worker = BatchWorker(self._entries, fmt, mode, out)
        self._worker.progress.connect(self._on_progress)
        self._worker.all_done.connect(self._on_all_done)
        self._worker.start()

    def _cancel_batch(self):
        if self._worker:
            self._worker.cancel()
        self._cancel_btn.setEnabled(False)

    def _on_progress(self, current: int, total: int, result: BatchResult):
        self._overall_bar.setValue(current)
        row = current - 1
        if 0 <= row < self._file_table.rowCount():
            status_text = {
                BatchStatus.SUCCESS: "✅ Succès",
                BatchStatus.FAILED:  "❌ Erreur",
                BatchStatus.SKIPPED: "⏭ Ignoré",
            }.get(result.status, "…")
            item = QTableWidgetItem(status_text)
            self._file_table.setItem(row, 3, item)

    def _on_all_done(self, results: list):
        self._start_btn.setEnabled(True)
        self._cancel_btn.setEnabled(False)
        self._overall_bar.setVisible(False)

        try:
            self._report_path = generate_batch_report(results, self._out_label.text())
            self._report_btn.setEnabled(True)
        except Exception:
            pass

        success = sum(1 for r in results if r.status == BatchStatus.SUCCESS)
        QMessageBox.information(
            self, "Traitement terminé",
            f"{success}/{len(results)} fichier(s) traité(s) avec succès.\n"
            f"Rapport : {self._report_path}",
        )

    def _open_report(self):
        if self._report_path and os.path.exists(self._report_path):
            os.startfile(self._report_path)

    def _apply_style(self):
        self.setStyleSheet("""
            #folderLabel { color: #7C83FD; font-weight: bold; font-size: 13px; }
            #outLabel    { color: #9090C0; font-size: 12px; }
            #batchTable  {
                background: #0F0F20; gridline-color: #2A2A4A; border: none; border-radius: 8px;
            }
            QHeaderView::section {
                background: #1A1A2E; color: #7C83FD; border: none;
                border-right: 1px solid #2A2A4A; padding: 4px 8px; font-weight: bold;
            }
            QTableWidget::item:alternate { background: #13132A; }
            #startBtn {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 #7C83FD, stop:1 #5B63D3);
                color: white; border: none; border-radius: 8px;
                padding: 8px 20px; font-weight: bold;
            }
            #startBtn:disabled { background: #2A2A4A; color: #555577; }
            #cancelBtn {
                background: #2A1A1A; color: #EF5350;
                border: 1px solid #5A2A2A; border-radius: 8px; padding: 7px 16px;
            }
            QComboBox {
                background: #1E1E3A; border: 1px solid #3A3A6A;
                border-radius: 6px; padding: 4px 10px; color: #C0C0E0;
            }
        """)
