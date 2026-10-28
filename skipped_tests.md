# 🚫 Skipped Tests & Download Requirements

This document tracks all tests that are **skipped in CI** because they require
system binaries or large file downloads that are not available in the test runner
environment (and are intentionally excluded from the source repo).

---

## Summary Table

| Test File | Test Class | Test Name | Reason Skipped | What to Download |
|---|---|---|---|---|
| `test_preprocessor.py` | `TestPreprocessor` | `test_load_pil_image` | Requires Pillow + OpenCV | `pip install Pillow opencv-python-headless` |
| `test_preprocessor.py` | `TestPreprocessor` | `test_load_file_path` | Requires sample scan image | See fixture section below |
| `test_preprocessor.py` | `TestPreprocessor` | `test_output_is_grayscale_pil` | Requires sample image | See fixture section below |
| `test_preprocessor.py` | `TestPreprocessor` | `test_deskew_corrects_rotation` | Requires skewed sample image | See fixture section below |
| `test_preprocessor.py` | `TestPreprocessor` | `test_denoise_reduces_variance` | Requires noisy sample image | See fixture section below |
| `test_preprocessor.py` | `TestPreprocessor` | `test_clahe_improves_contrast` | Requires low-contrast sample | See fixture section below |
| `test_preprocessor.py` | `TestPreprocessor` | `test_binarization_output` | Requires sample image | See fixture section below |
| `test_preprocessor.py` | `TestPreprocessor` | `test_invalid_input_raises_type_error` | Requires OpenCV import | `pip install opencv-python-headless` |
| `test_ocr.py` | `TestOcrEngine` | `test_tesseract_version_detected` | Requires Tesseract binary | See Tesseract section below |
| `test_ocr.py` | `TestOcrEngine` | `test_ocr_page_returns_ocrresult` | Requires Tesseract + tessdata | See Tesseract section below |
| `test_ocr.py` | `TestOcrEngine` | `test_known_text_extracted` | Requires Tesseract + sample image | See Tesseract section below |
| `test_ocr.py` | `TestOcrEngine` | `test_arabic_text_extracted` | Requires `ara.traineddata` | See Tesseract section below |
| `test_ocr.py` | `TestOcrEngine` | `test_confidence_range` | Requires Tesseract + sample image | See Tesseract section below |
| `test_ocr.py` | `TestOcrEngine` | `test_low_confidence_flagged` | Requires low-quality sample | See Tesseract section below |
| `test_ocr.py` | `TestOcrEngine` | `test_ocr_region_crops_correctly` | Requires Tesseract + sample image | See Tesseract section below |
| `test_ocr.py` | `TestOcrEngine` | `test_missing_tessdata_raises` | Requires Tesseract binary | See Tesseract section below |
| `test_table_detector.py` | `TestTableDetector` | `test_bordered_table_returns_grid` | Requires OpenCV + bordered-table image | `pip install opencv-python-headless` + fixture |
| `test_table_detector.py` | `TestTableDetector` | `test_borderless_table_fallback` | Requires OpenCV + borderless image | `pip install opencv-python-headless` + fixture |
| `test_table_detector.py` | `TestTableDetector` | `test_correct_column_count` | Requires sample 3-column invoice image | See fixture section below |
| `test_table_detector.py` | `TestTableDetector` | `test_header_row_detected` | Requires sample image with known header | See fixture section below |
| `test_table_detector.py` | `TestTableDetector` | `test_empty_image_returns_empty_grid` | Requires OpenCV + PIL | `pip install opencv-python-headless Pillow` |
| `test_table_detector.py` | `TestTableDetector` | `test_words_assigned_to_correct_cells` | Requires OcrResult fixture + OpenCV | `pip install opencv-python-headless` |

---

## ✅ Tests that DO run in CI (no downloads needed)

These tests in `test_table_detector.py::TestNormalizer` are **always active**
because they only test pure-Python logic with no binary dependencies:

| Test Name | What it verifies |
|---|---|
| `test_empty_grid_returns_empty_table` | normalize_table([]) returns 0 rows |
| `test_ocr_digit_fix` | OCR artifact `1O0` → `100` |
| `test_numeric_detection` | `1234.56` detected as numeric |
| `test_currency_row_tagged` | Row with `Total TTC` is tagged as currency |
| `test_whitespace_normalization` | Multiple spaces collapsed to one |

---

## 📥 Download Requirements to Activate Skipped Tests

### 1. Tesseract OCR Binary

Required for: all tests in `test_ocr.py`

**Download:** [UB-Mannheim Tesseract Releases](https://github.com/UB-Mannheim/tesseract/releases)
- File: `tesseract-ocr-w64-setup-5.x.x.exe` (Windows 64-bit)
- After installing, copy to: `vendor/tesseract/tesseract.exe`

**DLLs needed** (copy from `C:\Program Files\Tesseract-OCR\`):
- `tesseract.exe`
- All `.dll` files in the installation root

### 2. Tessdata Language Files

Required for: OCR tests with French, Arabic, English content

| File | URL | Copy to |
|---|---|---|
| `eng.traineddata` | https://github.com/tesseract-ocr/tessdata/raw/main/eng.traineddata | `vendor/tesseract/tessdata/` |
| `fra.traineddata` | https://github.com/tesseract-ocr/tessdata/raw/main/fra.traineddata | `vendor/tesseract/tessdata/` |
| `ara.traineddata` | https://github.com/tesseract-ocr/tessdata/raw/main/ara.traineddata | `vendor/tesseract/tessdata/` |
| `osd.traineddata` | https://github.com/tesseract-ocr/tessdata/raw/main/osd.traineddata | `vendor/tesseract/tessdata/` |

> [!NOTE]
> `osd` is the orientation and script detection pack — needed for PSM auto-detection.

### 3. Poppler for Windows

Required for: PDF processing tests (not yet written, but needed at runtime)

**Download:** [oschwartz10612/poppler-windows](https://github.com/oschwartz10612/poppler-windows/releases)
- File: `Release-24.x.x-0.zip`
- Extract and copy to: `vendor/poppler/`
- Required subdirectory: `vendor/poppler/bin/` (must contain `pdftoppm.exe`)

### 4. UPX (for local builds only — not needed for tests)

**Download:** [upx/upx Releases](https://github.com/upx/upx/releases)
- File: `upx-4.x.x-win64.zip`
- Extract `upx.exe` and add to your system PATH (or place in project root)

### 5. Test Fixture Images

Required for: all image-based tests in `test_preprocessor.py` and `test_table_detector.py`

Create the following directory and place sample files:

```
tests/
└── fixtures/
    ├── sample_scan.jpg           ← any scanned A4 invoice (300 DPI, JPG)
    ├── sample_skewed.jpg         ← same invoice rotated ~5 degrees
    ├── sample_noisy.jpg          ← scan with visible noise
    ├── sample_low_contrast.jpg   ← scan with poor contrast
    ├── sample_bordered_table.jpg ← invoice with visible grid lines
    ├── sample_borderless.jpg     ← invoice with no table borders
    ├── sample_arabic.jpg         ← image with Arabic text for OCR test
    └── sample_low_quality.jpg    ← blurry/low-res scan for confidence test
```

> [!CAUTION]
> Never commit real customer invoice images to this repository. Use synthetic or
> anonymized samples only.

---

## How to Enable Tests Locally

Once the above downloads are complete:

```powershell
# 1. Install Python dependencies
pip install -r requirements.txt

# 2. Remove the @unittest.skip decorator from the test methods you want to run
#    (or create a conftest.py that checks for vendor/ presence before skipping)

# 3. Run all tests
python -m pytest tests/ -v

# 4. Run only the always-available tests (no downloads needed)
python -m pytest tests/test_table_detector.py::TestNormalizer -v
```

---

## CI Behavior

The GitHub Actions workflow (`build.yml`) automatically:
- Downloads Tesseract, tessdata (fra/ara/eng), Poppler, and UPX
- Places them in `vendor/` before the build step
- Runs only `TestNormalizer` tests during CI (the dependency-free subset)
- Skips all other tests without causing the build to fail

If you want full test coverage in CI, add a separate job that runs after
the vendors are downloaded, and remove the `@unittest.skip` decorators
(or use `pytest.mark.skipif(not Path('vendor/tesseract').exists(), ...)`).
