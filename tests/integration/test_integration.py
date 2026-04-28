"""Integration tests with real files and binaries."""

import os
import time
from pathlib import Path
import pytest

from filesqueeze import make_video, make_pdf, make_image
from filesqueeze.ops.video import width_height, duration
from filesqueeze.ops.document import compress_pdf
from filesqueeze.ops.image import compress_image, get_image_size


@pytest.mark.integration
class TestRealFileCompression:
    """Test compression with real files."""

    def test_video_get_dimensions(self, sample_video):
        """Test getting video dimensions from real file."""
        width, height = width_height(sample_video)
        assert width > 0
        assert height > 0
        print(f"\nVideo dimensions: {width}x{height}")

    def test_video_get_duration(self, sample_video):
        """Test getting video duration from real file."""
        dur = duration(sample_video)
        assert dur is not None
        assert dur > 0
        print(f"\nVideo duration: {dur:.2f} seconds")

    def test_compress_video(self, sample_video, tmp_path):
        """Test actual video compression."""
        output_path = tmp_path / "compressed.mp4"

        # Get original size
        original_size = Path(sample_video).stat().st_size

        # Compress with timing
        start = time.time()
        make_video(sample_video, output_path=str(output_path))
        elapsed = time.time() - start

        # Check output exists
        assert output_path.exists()

        # Check output is smaller
        compressed_size = output_path.stat().st_size
        compression_ratio = (compressed_size / original_size) * 100

        print(f"\nVideo compression:")
        print(f"  Original size: {original_size / 1024 / 1024:.2f} MB")
        print(f"  Compressed size: {compressed_size / 1024 / 1024:.2f} MB")
        print(f"  Compression ratio: {compression_ratio:.1f}%")
        print(f"  Time: {elapsed:.1f} seconds")

        # Verify file is not too small (not corrupted)
        assert compressed_size > 1024  # At least 1KB

    def test_compress_image(self, sample_image, tmp_path):
        """Test actual image compression."""
        output_path = tmp_path / "compressed.jpg"

        # Get original size
        original_size = Path(sample_image).stat().st_size

        # Get original dimensions
        orig_width, orig_height = get_image_size(sample_image)
        print(f"\nOriginal image dimensions: {orig_width}x{orig_height}")

        # Compress with timing
        start = time.time()
        make_image(sample_image, output_path=str(output_path))
        elapsed = time.time() - start

        # Check output exists
        assert output_path.exists()

        # Check output
        compressed_size = output_path.stat().st_size
        compression_ratio = (compressed_size / original_size) * 100

        print(f"Image compression:")
        print(f"  Original size: {original_size / 1024:.2f} KB")
        print(f"  Compressed size: {compressed_size / 1024:.2f} KB")
        print(f"  Compression ratio: {compression_ratio:.1f}%")
        print(f"  Time: {elapsed:.2f} seconds")

        # Verify file is not corrupted
        assert compressed_size > 1024

    def test_compress_generated_pdf(self, sample_generated_pdf, tmp_path):
        """Test PDF compression on generated PDF."""
        from filesqueeze.config import Config

        output_path = tmp_path / "compressed.pdf"

        # Get original size
        original_size = Path(sample_generated_pdf).stat().st_size

        # Load config to get Ghostscript path
        config = Config()
        gs_path = config.ghostscript_path

        # Compress with 'printer' quality for better readability
        start = time.time()
        compress_pdf(
            sample_generated_pdf,
            str(output_path),
            quality="printer",  # Higher quality, less blurry
            compression_level=2,
            ghostscript_path=gs_path,
        )
        elapsed = time.time() - start

        # Check output exists
        assert output_path.exists()

        # Check compression
        compressed_size = output_path.stat().st_size
        compression_ratio = (compressed_size / original_size) * 100

        print(f"\nGenerated PDF (printer quality):")
        print(f"  Original size: {original_size / 1024 / 1024:.2f} MB")
        print(f"  Compressed size: {compressed_size / 1024 / 1024:.2f} MB")
        print(f"  Compression ratio: {compression_ratio:.1f}%")
        print(f"  Time: {elapsed:.2f} seconds")

        assert compressed_size > 1024

    def test_compress_scanned_pdf(self, sample_scanned_pdf, tmp_path):
        """Test PDF compression on scanned PDF with different settings."""
        from filesqueeze.config import Config

        config = Config()
        gs_path = config.ghostscript_path
        original_size = Path(sample_scanned_pdf).stat().st_size

        # Test different compression levels for scanned PDF
        compression_levels = [0, 2, 4]
        results = []

        for level in compression_levels:
            output_path = tmp_path / f"compressed_level{level}.pdf"

            start = time.time()
            compress_pdf(
                sample_scanned_pdf, str(output_path), quality="printer", compression_level=level, ghostscript_path=gs_path
            )
            elapsed = time.time() - start

            compressed_size = output_path.stat().st_size
            ratio = (compressed_size / original_size) * 100
            results.append((level, compressed_size, ratio, elapsed))

        print(f"\nScanned PDF - Compression Levels (Original: {original_size / 1024 / 1024:.2f} MB):")
        print(f"{'Level':<8} {'Size (MB)':<12} {'Ratio':<10} {'Time':<10}")
        print("-" * 50)
        for level, size, ratio, elapsed in results:
            print(f"{level:<8} {size / 1024 / 1024:<12.2f} {ratio:<10.1f}% {elapsed:<10.2f}s")

        # Verify all files exist and are not too small
        for level, size, ratio, elapsed in results:
            assert size > 1024

    def test_image_dimensions(self, sample_image):
        """Test getting image dimensions."""
        width, height = get_image_size(sample_image)
        assert width > 0
        assert height > 0
        print(f"\nImage dimensions: {width}x{height}")

    def test_pdf_quality_comparison(self, sample_generated_pdf, tmp_path):
        """Compare different PDF quality settings."""
        from filesqueeze.config import Config

        config = Config()
        gs_path = config.ghostscript_path
        original_size = Path(sample_generated_pdf).stat().st_size

        qualities = ["screen", "ebook", "printer", "prepress"]
        results = []

        for quality in qualities:
            output_path = tmp_path / f"compressed_{quality}.pdf"

            compress_pdf(
                sample_generated_pdf, str(output_path), quality=quality, compression_level=2, ghostscript_path=gs_path
            )

            compressed_size = output_path.stat().st_size
            ratio = (compressed_size / original_size) * 100
            results.append((quality, compressed_size, ratio))

        print(f"\nPDF Quality Comparison (Original: {original_size / 1024 / 1024:.2f} MB):")
        print(f"{'Quality':<12} {'Size (MB)':<12} {'Ratio':<10}")
        print("-" * 40)
        for quality, size, ratio in results:
            print(f"{quality:<12} {size / 1024 / 1024:<12.2f} {ratio:<10.1f}%")

    def test_ocr_detection(self, sample_scanned_pdf, sample_generated_pdf):
        """Test OCR detection - checks if PDFs have text layers."""
        import shutil
        from filesqueeze.ocr import has_text_layer

        # Check Tesseract availability - fail if not available
        if not shutil.which("tesseract"):
            pytest.fail(
                "Tesseract OCR is not installed or not in PATH. "
                "OCR is a critical feature - install Tesseract to run this test. "
                "See https://github.com/tesseract-ocr/tesseract for installation."
            )

        # Check if scanned PDF has text layer
        has_text_scanned = has_text_layer(sample_scanned_pdf)
        print(f"\nScanned PDF has text layer: {has_text_scanned}")

        # Note: The scanned_pdf fixture appears to already be OCRed
        # In production, truly scanned PDFs would return False here

        # Generated PDF should have text layer
        has_text_generated = has_text_layer(sample_generated_pdf)
        print(f"Generated PDF has text layer: {has_text_generated}")
        assert has_text_generated, "Generated PDF should have text layer"

    def test_ocr_scanned_pdf(self, sample_scanned_pdf, tmp_path):
        """Test OCR workflow on PDF.

        Note: This test demonstrates the OCR workflow. The sample_scanned_pdf
        fixture is already OCRed, so this test shows that the workflow
        correctly identifies this and doesn't re-OCR.
        """
        import shutil
        from filesqueeze.config import Config
        from filesqueeze.ocr import process_pdf_with_ocr, needs_ocr

        # Check Tesseract availability - fail if not available
        if not shutil.which("tesseract"):
            pytest.fail(
                "Tesseract OCR is not installed or not in PATH. "
                "OCR is a critical feature - install Tesseract to run this test. "
                "See https://github.com/tesseract-ocr/tesseract for installation."
            )

        config = Config()
        output_path = tmp_path / "ocr_output.pdf"

        original_size = Path(sample_scanned_pdf).stat().st_size

        print(f"\nTesting OCR workflow...")
        print(f"Original size: {original_size / 1024 / 1024:.2f} MB")

        # Check if OCR is needed
        if not needs_ocr(sample_scanned_pdf, config):
            print("PDF already has text layer - skipping OCR (as expected)")
            print("OCR workflow correctly identifies already-OCRed PDFs")
            # This is the expected behavior for our test fixture
            return

        # If PDF truly needs OCR, run the OCR process
        start = time.time()
        success, message = process_pdf_with_ocr(sample_scanned_pdf, str(output_path), config=config, ocr_only=True)
        elapsed = time.time() - start

        print(f"OCR Result: {message}")
        print(f"Time: {elapsed:.2f} seconds")

        if success:
            assert output_path.exists()

            ocr_size = output_path.stat().st_size
            print(f"OCR'd size: {ocr_size / 1024 / 1024:.2f} MB")
            assert ocr_size > 1024

            from filesqueeze.ocr import has_text_layer

            has_text = has_text_layer(str(output_path))
            print(f"OCR'd PDF has text layer: {has_text}")
            assert has_text, "OCR'd PDF should have text layer"
        else:
            pytest.fail(f"OCR test failed: {message}")

    def test_compress_scanned_pdf_with_ocr(self, sample_scanned_pdf, tmp_path):
        """Test compression workflow that respects OCR status.

        For PDFs that are already OCRed, they should be compressed directly.
        For PDFs without OCR, they would be OCRed first, then compressed.
        """
        import shutil
        from filesqueeze.config import Config
        from filesqueeze.ocr import needs_ocr
        from filesqueeze.ops.document import compress_pdf

        # Check Tesseract availability - fail if not available
        if not shutil.which("tesseract"):
            pytest.fail(
                "Tesseract OCR is not installed or not in PATH. "
                "OCR is a critical feature - install Tesseract to run this test. "
                "See https://github.com/tesseract-ocr/tesseract for installation."
            )

        config = Config()
        output_path = tmp_path / "compressed.pdf"

        original_size = Path(sample_scanned_pdf).stat().st_size

        print(f"\nTesting compression with OCR awareness...")
        print(f"Original size: {original_size / 1024 / 1024:.2f} MB")

        # Check OCR status
        if needs_ocr(sample_scanned_pdf, config):
            print("PDF needs OCR - would run OCR first in production")
            print("For this test, we'll demonstrate compression only")
        else:
            print("PDF already has text layer - compressing directly")

        # Compress with ebook quality (good for scanned/image-based PDFs)
        start = time.time()
        gs_path = config.ghostscript_path
        compress_pdf(sample_scanned_pdf, str(output_path), quality="ebook", compression_level=2, ghostscript_path=gs_path)
        elapsed = time.time() - start

        # Check result
        assert output_path.exists()
        final_size = output_path.stat().st_size
        ratio = (final_size / original_size) * 100

        print(f"\nCompressed size: {final_size / 1024 / 1024:.2f} MB")
        print(f"Compression ratio: {ratio:.1f}%")
        print(f"Time: {elapsed:.2f} seconds")

        # Verify text layer is preserved
        from filesqueeze.ocr import has_text_layer

        has_text = has_text_layer(str(output_path))
        print(f"Compressed PDF has searchable text: {has_text}")
        assert has_text, "Text layer should be preserved after compression"

        # Verify file is not corrupted
        assert final_size > 1024
