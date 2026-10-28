"""
Preprocessor unit tests.

SKIPPED: All tests in this file require OpenCV, Pillow, and a sample
         scanned image (test_facture.jpg) to be present.
         See skipped_tests.md for the full list of requirements.
"""
import unittest


class TestPreprocessor(unittest.TestCase):

    @unittest.skip("Requires: Pillow, opencv-python-headless — not installed in CI")
    def test_load_pil_image(self):
        """preprocess() should accept a PIL Image without crashing."""
        pass

    @unittest.skip("Requires: sample scanned image at tests/fixtures/sample_scan.jpg")
    def test_load_file_path(self):
        """preprocess() should accept a string file path."""
        pass

    @unittest.skip("Requires: sample image — verifies output is PIL Image mode L")
    def test_output_is_grayscale_pil(self):
        """Return value must be a PIL Image with mode 'L'."""
        pass

    @unittest.skip("Requires: skewed sample image to verify deskew is applied")
    def test_deskew_corrects_rotation(self):
        """Deskewed image should have a measured angle near 0."""
        pass

    @unittest.skip("Requires: noisy sample image — checks pixel variance is reduced")
    def test_denoise_reduces_variance(self):
        """Variance of pixel values should decrease after denoising."""
        pass

    @unittest.skip("Requires: low-contrast sample image — checks histogram spread increases")
    def test_clahe_improves_contrast(self):
        """CLAHE should broaden the histogram of the processed image."""
        pass

    @unittest.skip("Requires: sample image — verifies binary output (only 0 and 255 pixels)")
    def test_binarization_output(self):
        """Output should contain only pixel values 0 and 255."""
        pass

    @unittest.skip("Requires: sample image — checks that unsupported input type raises TypeError")
    def test_invalid_input_raises_type_error(self):
        """Passing an integer should raise TypeError."""
        pass


if __name__ == "__main__":
    unittest.main()
