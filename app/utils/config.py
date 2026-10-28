"""
Configuration and path resolution.
Handles both development (source) and PyInstaller (frozen) environments.
"""
import sys
import os


# ── Base path resolution ──────────────────────────────────────────────────────

def get_base_dir() -> str:
    """Return the root directory of the application bundle or source tree."""
    if getattr(sys, "frozen", False):
        # Running inside PyInstaller bundle — _MEIPASS is the extraction dir
        return sys._MEIPASS  # type: ignore[attr-defined]
    # Running from source: two levels up from this file (app/utils/config.py)
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_resource_path(relative: str) -> str:
    """Resolve a path relative to the bundle/source root."""
    return os.path.join(BASE_DIR, relative)


def get_app_data_dir() -> str:
    """Return the user-writable app-data directory (persisted across runs)."""
    base = os.environ.get("APPDATA", os.path.expanduser("~"))
    return os.path.join(base, "FactureConverter")


# ── Computed paths ────────────────────────────────────────────────────────────

BASE_DIR: str = get_base_dir()
APP_DATA_DIR: str = get_app_data_dir()

TEMPLATES_DIR: str = os.path.join(APP_DATA_DIR, "templates")
EXPORTS_DIR: str = os.path.join(APP_DATA_DIR, "exports")
LOGS_DIR: str = os.path.join(APP_DATA_DIR, "logs")

# Vendor paths (bundled via PyInstaller datas)
TESSERACT_EXE: str = get_resource_path(os.path.join("vendor", "tesseract", "tesseract.exe"))
_poppler_bin = get_resource_path(os.path.join("vendor", "poppler", "bin"))
_poppler_lib_bin = get_resource_path(os.path.join("vendor", "poppler", "Library", "bin"))
POPPLER_BIN: str = _poppler_lib_bin if (not os.path.isdir(_poppler_bin) and os.path.isdir(_poppler_lib_bin)) else _poppler_bin

# ── OCR settings ──────────────────────────────────────────────────────────────

OCR_LANGUAGES: str = "fra+ara+eng"
OCR_CONFIDENCE_THRESHOLD: int = 40   # Words below this % are flagged in the UI
OCR_DPI: int = 300                   # Optimal for Tesseract on printed docs

# ── Processing limits ─────────────────────────────────────────────────────────

MAX_PAGES_WARNING: int = 50          # Warn user when PDF exceeds this
BATCH_SEQUENTIAL: bool = True        # Always sequential — low RAM on T450

# ── Ensure writable directories exist ────────────────────────────────────────

for _d in (APP_DATA_DIR, TEMPLATES_DIR, EXPORTS_DIR, LOGS_DIR):
    os.makedirs(_d, exist_ok=True)
