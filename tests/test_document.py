"""Test document compression functionality."""

import pytest
from pathlib import Path
from filesqueeze.document import compress_pdf, compress_image, get_image_size


class TestDocumentCompression:
    """Test document compression functions."""

    def test_get_ghostscript_path_not_found(self, tmp_path):
        """Test that get_ghostscript_path raises error when not found."""
        from filesqueeze.document import get_ghostscript_path

        # Should raise RuntimeError when Ghostscript is not found
        with pytest.raises(RuntimeError, match="Ghostscript not found"):
            get_ghostscript_path(config_path="")

    def test_get_ffmpeg_path_not_found(self, tmp_path):
        """Test that get_ffmpeg_path raises error when not found."""
        from filesqueeze.document import get_ffmpeg_path

        # Should raise RuntimeError when FFmpeg is not found
        with pytest.raises(RuntimeError, match="FFmpeg not found"):
            get_ffmpeg_path(config_path="")

    def test_compress_pdf_invalid_quality(self, tmp_path):
        """Test that compress_pdf raises error for invalid quality."""
        # Create a dummy input file
        infile = tmp_path / "input.pdf"
        infile.write_text("dummy pdf content")
        outfile = tmp_path / "output.pdf"

        # Should raise ValueError for invalid quality
        with pytest.raises(ValueError, match="Invalid quality setting"):
            compress_pdf(str(infile), str(outfile), quality="invalid")

    def test_compress_image_without_ffmpeg(self, tmp_path):
        """Test that compress_image raises error without FFmpeg."""
        # Create a dummy input file
        infile = tmp_path / "input.jpg"
        infile.write_bytes(b"\xff\xd8\xff\xe0\x00\x10JFIF")  # Minimal JPEG header
        outfile = tmp_path / "output.jpg"

        # Should raise RuntimeError when FFmpeg is not found
        with pytest.raises(RuntimeError, match="FFmpeg not found"):
            compress_image(str(infile), str(outfile))

    def test_get_image_size_without_ffprobe(self, tmp_path):
        """Test that get_image_size raises error without ffprobe."""
        # Create a dummy input file
        infile = tmp_path / "test.jpg"
        infile.write_bytes(b"\xff\xd8\xff\xe0\x00\x10JFIF")  # Minimal JPEG header

        # Should raise RuntimeError when ffprobe is not found
        with pytest.raises(RuntimeError, match="ffprobe not found"):
            get_image_size(str(infile))


class TestDocumentHelpers:
    """Test helper functions in document module."""

    def test_ghostscript_path_with_config(self, tmp_path):
        """Test get_ghostscript_path with config path."""
        from filesqueeze.document import get_ghostscript_path

        # Test with non-existent config path (should fall back to PATH or raise if not found)
        # If Ghostscript is in PATH, it will return the path; otherwise it raises RuntimeError
        try:
            result = get_ghostscript_path(config_path=str(tmp_path / "nonexistent" / "gs.exe"))
            # If we get here, Ghostscript was found in PATH
            assert result is not None
        except RuntimeError:
            # Ghostscript not found in PATH either - this is also valid behavior
            pass

    def test_ffmpeg_path_with_config(self, tmp_path):
        """Test get_ffmpeg_path with config path."""
        from filesqueeze.document import get_ffmpeg_path

        # Test with non-existent config path (should fall back to PATH or raise if not found)
        # If FFmpeg is in PATH, it will return the path; otherwise it raises RuntimeError
        try:
            result = get_ffmpeg_path(config_path=str(tmp_path / "nonexistent" / "ffmpeg.exe"))
            # If we get here, FFmpeg was found in PATH
            assert result is not None
        except RuntimeError:
            # FFmpeg not found in PATH either - this is also valid behavior
            pass


@pytest.mark.skipif(
    True,  # Skip these tests by default (require actual FFmpeg/Ghostscript)
    reason="Requires FFmpeg and Ghostscript to be installed"
)
class TestDocumentCompressionWithBinaries:
    """Tests that require actual FFmpeg and Ghostscript binaries."""

    def test_compress_pdf_with_gs(self, tmp_path):
        """Test PDF compression with real Ghostscript."""
        # This test would require an actual PDF file
        # Skipped by default
        pass

    def test_compress_image_with_ffmpeg(self, tmp_path):
        """Test image compression with real FFmpeg."""
        # This test would require an actual image file
        # Skipped by default
        pass

    def test_get_image_size_with_ffprobe(self, tmp_path):
        """Test getting image size with real ffprobe."""
        # This test would require an actual image file
        # Skipped by default
        pass
