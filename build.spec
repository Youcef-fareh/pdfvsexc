# ─────────────────────────────────────────────────────────────────────────────
# PyInstaller Build Spec — Facture Converter
#
# Produces a --onedir bundle in dist/FactureConverter/
# All vendor binaries (Tesseract, Poppler) must be present in vendor/ before
# running this spec.  The GitHub Actions workflow populates vendor/ automatically.
#
# Run:  pyinstaller build.spec
# ─────────────────────────────────────────────────────────────────────────────

import sys
import os
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

block_cipher = None

# ── Source root ───────────────────────────────────────────────────────────────
ROOT = os.path.dirname(os.path.abspath(SPEC))

# ── Hidden imports ────────────────────────────────────────────────────────────
# Modules that PyInstaller misses because they're imported dynamically.
hidden = [
    "arabic_reshaper",
    "bidi",
    "bidi.algorithm",
    "pdfplumber",
    "pdf2image",
    "pytesseract",
    "openpyxl",
    "openpyxl.styles",
    "openpyxl.utils",
    "docx",
    "docx.oxml",
    "docx.oxml.ns",
    "cv2",
    "PIL",
    "PIL.Image",
    "numpy",
    "PyQt6",
    "PyQt6.QtCore",
    "PyQt6.QtGui",
    "PyQt6.QtWidgets",
]

# ── Data files ────────────────────────────────────────────────────────────────
# Format: (source_glob_or_dir, destination_inside_bundle)
datas = [
    # Bundled system binaries (downloaded by CI)
    (os.path.join(ROOT, "vendor", "tesseract"),          "vendor/tesseract"),
    (os.path.join(ROOT, "vendor", "poppler"),            "vendor/poppler"),
    # Example templates
    (os.path.join(ROOT, "app", "templates", "examples"), "vendor/templates"),
    # Assets (icons, fonts, qss)
    (os.path.join(ROOT, "assets"),                       "assets"),
]

# Collect PyQt6 Qt platform plugins (needed for windowed mode on Windows)
datas += collect_data_files("PyQt6", subdir="Qt6/plugins")

# ── Binaries ──────────────────────────────────────────────────────────────────
binaries = []

# ── Exclusions — strip unused stdlib & third-party fat ───────────────────────
excludes = [
    # Unused stdlib modules
    "tkinter", "turtle", "email.mime", "unittest",
    "xmlrpc", "http.server", "ftplib", "imaplib", "smtplib",
    "antigravity", "cgi", "cgitb", "colorsys", "cProfile",
    "curses", "dbm", "difflib", "doctest", "ensurepip",
    "idlelib", "lib2to3", "msilib", "multiprocessing.managers",
    "optparse", "pdb", "pickletools", "profile", "pstats",
    "pty", "pydoc", "readline", "shelve", "sunau", "tarfile",
    "telnetlib", "termios", "test", "tty", "zipapp",
    # Heavy third-party packages not used by this app
    "scipy", "matplotlib", "pandas", "sklearn", "tensorflow",
    "torch", "IPython", "notebook", "jupyter",
    # PyQt6 modules not used
    "PyQt6.QtBluetooth", "PyQt6.QtDBus", "PyQt6.QtLocation",
    "PyQt6.QtMultimedia", "PyQt6.QtMultimediaWidgets",
    "PyQt6.QtNfc", "PyQt6.QtPositioning", "PyQt6.QtQuick",
    "PyQt6.QtQuickWidgets", "PyQt6.QtRemoteObjects",
    "PyQt6.QtSensors", "PyQt6.QtSerialPort", "PyQt6.QtSql",
    "PyQt6.QtSvg", "PyQt6.QtTest", "PyQt6.QtWebChannel",
    "PyQt6.QtWebEngine", "PyQt6.QtWebEngineCore",
    "PyQt6.QtWebEngineWidgets", "PyQt6.QtWebSockets",
    "PyQt6.QtXml",
]

# ── Analysis ──────────────────────────────────────────────────────────────────
a = Analysis(
    [os.path.join(ROOT, "main.py")],
    pathex=[ROOT],
    binaries=binaries,
    datas=datas,
    hiddenimports=hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# ── PYZ archive ───────────────────────────────────────────────────────────────
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# ── EXE ───────────────────────────────────────────────────────────────────────
exe = EXE(
    pyz,
    a.scripts,
    [],                          # No bootloader additions
    exclude_binaries=True,       # binaries go into COLLECT (onedir)
    name="FactureConverter",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,                 # strip=True can break Qt on Windows
    upx=True,                    # UPX compression on EXE itself
    upx_exclude=[
        # These DLLs are known to break when UPX-compressed on Windows
        "vcruntime140.dll",
        "vcruntime140_1.dll",
        "python311.dll",
        "python312.dll",
        "Qt6Core.dll",
        "Qt6Gui.dll",
        "Qt6Widgets.dll",
    ],
    console=False,               # No console window — GUI app
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(ROOT, "assets", "icons", "app_icon.ico"),
    version="file_version_info.txt" if os.path.exists("file_version_info.txt") else None,
)

# ── COLLECT — onedir output ───────────────────────────────────────────────────
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,                    # UPX also applied to collected binaries
    upx_exclude=[
        "vcruntime140.dll",
        "vcruntime140_1.dll",
        "python311.dll",
        "python312.dll",
        "Qt6Core.dll",
        "Qt6Gui.dll",
        "Qt6Widgets.dll",
    ],
    name="FactureConverter",
)
