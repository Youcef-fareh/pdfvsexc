"""
Facture Converter — Application Entry Point
"""
import sys
import os

# ── Fix working directory when frozen by PyInstaller ─────────────────────────
if getattr(sys, "frozen", False):
    os.chdir(os.path.dirname(sys.executable))

# ── Qt High-DPI support ───────────────────────────────────────────────────────
os.environ.setdefault("QT_AUTO_SCREEN_SCALE_FACTOR", "1")

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon

from app.ui.main_window import MainWindow
from app.utils.config import APP_DATA_DIR, get_resource_path


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("Facture Converter")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("FactureConverter")

    # Load application stylesheet
    qss_path = get_resource_path("assets/style.qss")
    if os.path.exists(qss_path):
        with open(qss_path, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())

    # Set application icon
    icon_path = get_resource_path("assets/icons/app_icon.png")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
