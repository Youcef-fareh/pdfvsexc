"""
OCR Engine unit tests.

SKIPPED: All tests require:
  • Tesseract 5 binary in vendor/tesseract/tesseract.exe
  • tessdata files: fra.traineddata, ara.traineddata, eng.traineddata
  • A preprocessed sample PIL Image for OCR input
See skipped_tests.md for full details.
"""
import unittest


class TestOcrEngine(unittest.TestCase):

    @unittest.skip("Requires: Tesseract binary in vendor/tesseract/")
    def test_tesseract_version_detected(self):
        """get_tesseract_version() should return a non-empty string."""
        pass

    @unittest.skip("Requires: Tesseract + fra+eng tessdata + sample PIL image")
    def test_ocr_page_returns_ocrresult(self):
        """ocr_page() should return an OcrResult instance."""
        pass

    @unittest.skip("Requires: Tesseract + tessdata + sample image with known text")
    def test_known_text_extracted(self):
        """OCR on a sample 'FACTURE N° 001' image should extract that string."""
        pass

    @unittest.skip("Requires: Tesseract + ara tessdata + sample Arabic text image")
    def test_arabic_text_extracted(self):
        """OCR should detect Arabic characters on an Arabic-text image."""
        pass

    @unittest.skip("Requires: Tesseract + tessdata + sample image — tests confidence scoring")
    def test_confidence_range(self):
        """All OcrWord.confidence values should be in [0, 100]."""
        pass

    @unittest.skip("Requires: Tesseract + tessdata + low-quality image — tests low_confidence flag")
    def test_low_confidence_flagged(self):
        """Words below OCR_CONFIDENCE_THRESHOLD should have is_low_confidence=True."""
        pass

    @unittest.skip("Requires: Tesseract + tessdata + sample image with a defined region")
    def test_ocr_region_crops_correctly(self):
        """ocr_region() should only extract text from the specified bounding box."""
        pass

    @unittest.skip("Requires: Tesseract — tests that wrong tessdata path raises RuntimeError")
    def test_missing_tessdata_raises(self):
        """Missing tessdata should raise an exception, not silently return empty."""
        pass


if __name__ == "__main__":
    unittest.main()
