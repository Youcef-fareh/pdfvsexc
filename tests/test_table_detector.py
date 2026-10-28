"""
Table Detector unit tests.

SKIPPED: Tests require opencv-python-headless, a preprocessed PIL Image,
         and an OcrResult fixture.
See skipped_tests.md for full details.
"""
import unittest


class TestTableDetector(unittest.TestCase):

    @unittest.skip("Requires: opencv-python-headless + sample bordered-table image")
    def test_bordered_table_returns_grid(self):
        """detect_table() on a clear bordered table should return a non-empty 2D list."""
        pass

    @unittest.skip("Requires: opencv-python-headless + borderless table image + OcrResult fixture")
    def test_borderless_table_fallback(self):
        """When no borders are found, the borderless heuristic should still return rows."""
        pass

    @unittest.skip("Requires: sample image with 3 columns — verifies column count")
    def test_correct_column_count(self):
        """detect_table() should return rows with the correct number of columns."""
        pass

    @unittest.skip("Requires: sample image with known header text — verifies header detection")
    def test_header_row_detected(self):
        """normalizer.detect_header_row() should return 0 for standard invoices."""
        pass

    @unittest.skip("Requires: blank/empty image — verifies empty-input handling")
    def test_empty_image_returns_empty_grid(self):
        """detect_table() on an image with no content should return []."""
        pass

    @unittest.skip("Requires: OcrResult with known word positions — tests word-to-cell assignment")
    def test_words_assigned_to_correct_cells(self):
        """OCR words should be grouped into the cell whose bounding box contains them."""
        pass


class TestNormalizer(unittest.TestCase):

    def test_empty_grid_returns_empty_table(self):
        """normalize_table([]) should not raise and should return NormalizedTable with 0 rows."""
        from app.pipeline.normalizer import normalize_table
        result = normalize_table([])
        self.assertEqual(len(result.rows), 0)

    def test_ocr_digit_fix(self):
        """'1O0' containing digit-O-digit should be corrected to '100'."""
        from app.pipeline.normalizer import normalize_table
        result = normalize_table([["1O0,00"]])
        self.assertIn("100", result.rows[0][0].cleaned)

    def test_numeric_detection(self):
        """'1234.56' should be detected as numeric."""
        from app.pipeline.normalizer import normalize_table
        result = normalize_table([["1234.56"]])
        self.assertTrue(result.rows[0][0].is_numeric)

    def test_currency_row_tagged(self):
        """A row containing 'Total TTC' should be tagged as is_currency_row."""
        from app.pipeline.normalizer import normalize_table
        result = normalize_table([["Total TTC", "15000,00"]])
        self.assertTrue(result.rows[0][0].is_currency_row)

    def test_whitespace_normalization(self):
        """Multiple spaces in a cell should be collapsed to one."""
        from app.pipeline.normalizer import normalize_table
        result = normalize_table([["hello   world"]])
        self.assertEqual(result.rows[0][0].cleaned, "hello world")


if __name__ == "__main__":
    unittest.main()
