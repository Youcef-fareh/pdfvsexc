<div align="center">

# 🧾 Facture Converter

**Convertisseur de factures hors-ligne — Offline Invoice Converter**

[![Build](https://github.com/Youcef-fareh/pdfvsexc/actions/workflows/build.yml/badge.svg)](https://github.com/Youcef-fareh/pdfvsexc/actions/workflows/build.yml)
[![Python 3.11](https://img.shields.io/badge/Python-3.11-blue?logo=python)](https://python.org)
[![PyQt6](https://img.shields.io/badge/UI-PyQt6-41CD52?logo=qt)](https://pypi.org/project/PyQt6/)
[![Tesseract 5](https://img.shields.io/badge/OCR-Tesseract_5-orange)](https://github.com/tesseract-ocr/tesseract)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

*Convert scanned invoices (JPG, PNG, PDF) → editable XLSX / DOCX — 100% offline, no cloud, no installation required.*

</div>

---

## ✨ Features

| Feature | Details |
|---|---|
| **Input formats** | JPG, PNG, BMP, TIFF, PDF (digital text-layer or scanned image) |
| **Output formats** | XLSX (Excel) and DOCX (Word) |
| **OCR languages** | French · Arabic · English (common on Algerian invoices) |
| **Clone Layout** | Reconstructs the original table structure and styling |
| **Template System** | Draw bounding boxes on a reference invoice; reuse for future files |
| **Editable Preview** | Fix OCR errors in an interactive table before export |
| **Batch Processing** | Drop a folder → process 10–50 files → get a batch report |
| **100% Offline** | Tesseract + Poppler bundled inside the `.exe` — zero internet needed |
| **Privacy first** | No file ever leaves your machine |
| **Low-end hardware** | Runs on Intel i5 5th gen / 8 GB RAM (no GPU required) |

---

## 📸 Screenshots

> *Coming soon — add your own screenshots to `docs/screenshots/`*

---

## 🚀 Quick Start (End Users)

1. Go to the [**Releases** page](https://github.com/Youcef-fareh/pdfvsexc/releases).
2. Download `FactureConverter-vX.X.X-win64.zip`.
3. Extract the ZIP to any folder (e.g. `C:\Tools\FactureConverter\`).
4. Double-click `FactureConverter.exe`.
5. Drag your invoice file onto the window and click **Exporter**.

> **No Python, no Tesseract, no Poppler to install.** Everything is bundled.

### System Requirements (end users)

| | Minimum | Recommended |
|---|---|---|
| **OS** | Windows 10 x64 | Windows 11 x64 |
| **RAM** | 4 GB | 8 GB |
| **CPU** | Intel i5 5th gen | Intel i5 8th gen+ |
| **GPU** | Not required | Not required |
| **Disk** | 300 MB free | 500 MB free |
| **Internet** | ❌ Not needed | ❌ Not needed |

---

## 🛠️ Developer Setup

> **Note:** System binaries (Tesseract, Poppler, UPX) are **not committed to this repo**.
> They are downloaded automatically by the GitHub Actions workflow during CI.
> For local development, you do not need them unless you want to run OCR tests.

### 1. Clone the repository

```bash
git clone https://github.com/Youcef-fareh/pdfvsexc.git
cd pdfvsexc
```

### 2. Create a virtual environment

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 3. Install Python dependencies

```powershell
pip install -r requirements.txt
```

### 4. Run the application (development mode)

```powershell
# Tesseract + Poppler must be available in vendor/ for the app to work.
# See "Building Locally" below to set them up, or run the GitHub Actions workflow.
python main.py
```

---

## 🏗️ Building Locally

The GitHub Actions workflow handles all vendor downloads automatically.
To build locally, you must first download the vendor binaries:

### Step 1 — Download Tesseract

1. Download from [UB-Mannheim Tesseract](https://digi.bib.uni-mannheim.de/tesseract/):
   - File: `tesseract-ocr-w64-setup-5.3.3.20231005.exe` (or latest)
2. Install silently: `tesseract-ocr-w64-setup-5.x.x.exe /S`
3. Copy files:

```powershell
New-Item -ItemType Directory -Force vendor\tesseract\tessdata
Copy-Item "C:\Program Files\Tesseract-OCR\tesseract.exe" vendor\tesseract\
Copy-Item "C:\Program Files\Tesseract-OCR\*.dll"         vendor\tesseract\

# Download language packs
$td = "vendor\tesseract\tessdata"
Invoke-WebRequest "https://github.com/tesseract-ocr/tessdata/raw/main/eng.traineddata" -OutFile "$td\eng.traineddata"
Invoke-WebRequest "https://github.com/tesseract-ocr/tessdata/raw/main/fra.traineddata" -OutFile "$td\fra.traineddata"
Invoke-WebRequest "https://github.com/tesseract-ocr/tessdata/raw/main/ara.traineddata" -OutFile "$td\ara.traineddata"
Invoke-WebRequest "https://github.com/tesseract-ocr/tessdata/raw/main/osd.traineddata" -OutFile "$td\osd.traineddata"
```

### Step 2 — Download Poppler

```powershell
# Download from oschwartz10612/poppler-windows
Invoke-WebRequest "https://github.com/oschwartz10612/poppler-windows/releases/download/v24.02.0-0/Release-24.02.0-0.zip" -OutFile poppler.zip
Expand-Archive poppler.zip -DestinationPath poppler_tmp
Copy-Item poppler_tmp\poppler-24.02.0\* vendor\poppler -Recurse
```

### Step 3 — Download UPX (optional but recommended for smaller output)

```powershell
Invoke-WebRequest "https://github.com/upx/upx/releases/download/v4.2.2/upx-4.2.2-win64.zip" -OutFile upx.zip
Expand-Archive upx.zip -DestinationPath upx_tmp
# Add upx_tmp\upx-4.2.2-win64\ to your PATH
```

### Step 4 — Build

```powershell
pyinstaller build.spec --clean --noconfirm
```

Output will be in `dist\FactureConverter\`. Run `dist\FactureConverter\FactureConverter.exe`.

---

## 📁 Project Structure

```
facture-converter/
├── main.py                        ← Application entry point
├── requirements.txt               ← Python dependencies
├── build.spec                     ← PyInstaller configuration
├── skipped_tests.md               ← Skipped test documentation
│
├── app/
│   ├── ui/
│   │   ├── main_window.py         ← Main window, drag-and-drop, worker thread
│   │   ├── preview_table.py       ← Editable OCR result table
│   │   ├── template_editor.py     ← Template creation dialog (draw boxes on image)
│   │   └── batch_panel.py         ← Batch processing panel
│   │
│   ├── pipeline/
│   │   ├── input_handler.py       ← File type detection & routing
│   │   ├── preprocessor.py        ← OpenCV image enhancement
│   │   ├── ocr_engine.py          ← Tesseract OCR wrapper
│   │   ├── table_detector.py      ← Table structure detection
│   │   ├── normalizer.py          ← Data cleaning & cell metadata
│   │   └── batch_runner.py        ← Sequential batch processor
│   │
│   ├── export/
│   │   ├── xlsx_writer.py         ← openpyxl XLSX export
│   │   └── docx_writer.py         ← python-docx DOCX export
│   │
│   ├── templates/
│   │   ├── template_manager.py    ← JSON template CRUD
│   │   └── examples/              ← Bundled starter templates
│   │
│   └── utils/
│       ├── config.py              ← Path resolution (dev vs. bundled)
│       ├── arabic_utils.py        ← Arabic reshaping + BiDi
│       └── pdf_utils.py           ← PDF detection & conversion
│
├── assets/
│   ├── icons/                     ← App icons (.ico, .png)
│   └── style.qss                  ← Qt stylesheet (dark theme)
│
├── tests/
│   ├── test_preprocessor.py       ← Preprocessor tests (22 skipped)
│   ├── test_ocr.py                ← OCR engine tests (8 skipped)
│   └── test_table_detector.py     ← Detector tests (6 skipped) + 5 active normalizer tests
│
├── vendor/                        ← NOT in git — created by CI workflow
│   ├── tesseract/                 ← tesseract.exe + tessdata/
│   └── poppler/                   ← pdftoppm.exe + libs
│
└── .github/
    └── workflows/
        └── build.yml              ← CI/CD: download vendors, build, release
```

---

## 🔄 How It Works

```
Input File (JPG / PNG / PDF)
        │
        ▼
  Input Handler ──────────────────┐
  (detect type)                   │
        │                         │
  ┌─────┴─────┐         ┌─────────┴──────────┐
  │ Image /   │         │   Digital PDF       │
  │ Scanned   │         │   (text layer)      │
  │   PDF     │         │                     │
  └─────┬─────┘         └─────────┬──────────┘
        │                         │
  Preprocessor            pdfplumber
  (deskew, denoise,        .extract_tables()
   CLAHE, binarize)                │
        │                         │
    OCR Engine                    │
    (Tesseract 5:                 │
     fra+ara+eng)                 │
        │                         │
        └──────────┬──────────────┘
                   │
         Table Structure Detector
         (bordered → contours,
          borderless → whitespace)
                   │
             Normalizer
             (OCR fixes, Arabic,
              currency tagging)
                   │
           Preview Table UI
           (editable by user)
                   │
         ┌─────────┴─────────┐
         │                   │
     XLSX Writer         DOCX Writer
     (openpyxl)          (python-docx)
         │                   │
    output.xlsx          output.docx
```

---

## 📋 Use Cases

### UC1 — Clone Layout
*"I have an invoice image and I want an Excel file that looks the same."*
→ Drop file → keep default mode "Cloner la mise en page" → Export XLSX.

### UC2 — Template-Based Extraction
*"I get 30 invoices a month from the same supplier."*
→ Templates → create template → draw boxes on reference invoice → save →
next month: drop folder → select template → batch export.

### UC3 — Mixed PDF Handling
*"I received a PDF but I don't know if it's digital or scanned."*
→ Drop it — the app detects automatically and routes to the correct pipeline.

### UC4 — Review Before Export
*"The scan quality is poor and I need to check the results."*
→ After processing, edit any cell in the preview table before clicking Export.

### UC5 — Batch Processing
*"I have 40 invoices to convert at once."*
→ Use the **Traitement groupé** tab → pick folder → start → batch report generated.

---

## ⚡ Performance (Lenovo ThinkPad T450)

| Document Type | Expected Time per Page |
|---|---|
| Clear printed invoice (JPG) | 5–10 seconds |
| Good quality scan (PDF) | 8–15 seconds |
| Low quality / skewed scan | 10–20 seconds |
| Digital PDF (text layer) | < 2 seconds |

> Processing is sequential (one page at a time) to stay within 8 GB RAM.

---

## ⚠️ Known Limitations

- **Handwriting**: Low accuracy. Manual correction recommended.
- **Nested/merged cells**: May not clone 100% identically.
- **Logos & stamps**: Not recreated as editable objects.
- **Encrypted PDFs**: User must provide password (a prompt will appear).
- **PDFs > 50 pages**: Processed page-by-page; may take several minutes on T450.
- **Arabic OCR accuracy**: 80–90% on clear prints; lower on handwritten Arabic.

---

## 🧪 Testing

```powershell
# Run dependency-free tests only (always works, no downloads needed)
python -m pytest tests/test_table_detector.py::TestNormalizer -v

# Run all tests (requires vendor/ binaries and test fixture images)
# See skipped_tests.md for setup instructions
python -m pytest tests/ -v
```

See [`skipped_tests.md`](skipped_tests.md) for the complete list of 22 skipped tests
and exact download URLs for all required files.

---

## 🔐 Privacy

- **No internet connection** is ever made by the application.
- **No telemetry** of any kind.
- **No cloud OCR** — all processing is local via bundled Tesseract.
- All files are processed in memory and written to your local disk only.
- Templates are stored in `%APPDATA%\FactureConverter\templates\`.
- Exports default to `%APPDATA%\FactureConverter\exports\`.

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

## 🙏 Credits

| Component | Source | License |
|---|---|---|
| Tesseract OCR | [tesseract-ocr/tesseract](https://github.com/tesseract-ocr/tesseract) | Apache 2.0 |
| Tesseract Windows Build | [UB-Mannheim/tesseract](https://github.com/UB-Mannheim/tesseract) | Apache 2.0 |
| Poppler Windows | [oschwartz10612/poppler-windows](https://github.com/oschwartz10612/poppler-windows) | GPL 2.0 |
| UPX | [upx/upx](https://github.com/upx/upx) | GPL 2.0+ special exception |
| PyQt6 | [Riverbank Computing](https://riverbankcomputing.com/software/pyqt/) | GPL 3.0 / Commercial |
| OpenCV | [opencv/opencv](https://github.com/opencv/opencv) | Apache 2.0 |
| arabic-reshaper | [mpcabd/python-arabic-reshaper](https://github.com/mpcabd/python-arabic-reshaper) | MIT |
| python-bidi | [MeirKriheli/python-bidi](https://github.com/MeirKriheli/python-bidi) | LGPL 3.0 |
