"""Test video compression functionality."""

import pytest
from pathlib import Path
from filesqueeze.video import (
    get_ffmpeg_path,
    get_ffprobe_path,
    width_height,
    duration,
    compress
)


class TestVideoHelpers:
    """Test helper functions in video module."""

    def test_get_ffmpeg_path_not_found(self):
        """Test that get_ffmpeg_path raises error when not found."""
        # Should raise RuntimeError when FFmpeg is not found
        with pytest.raises(RuntimeError, match="FFmpeg not found"):
            get_ffmpeg_path(config_path="")

    def test_get_ffprobe_path_not_found(self):
        """Test that get_ffprobe_path raises error when not found."""
        # Should raise RuntimeError when ffprobe is not found
        with pytest.raises(RuntimeError, match="ffprobe not found"):
            get_ffprobe_path(ffmpeg_path="")

    def test_get_ffmpeg_path_with_invalid_config(self, tmp_path):
        """Test get_ffmpeg_path with non-existent config path."""
        # Test with non-existent config path (should fall back to PATH)
        with pytest.raises(RuntimeError):
            get_ffmpeg_path(config_path=str(tmp_path / "nonexistent" / "ffmpeg.exe"))

    def test_get_ffprobe_path_with_invalid_config(self, tmp_path):
        """Test get_ffprobe_path with non-existent config path."""
        # Test with non-existent ffmpeg path (should fall back to bundled or PATH)
        with pytest.raises(RuntimeError):
            get_ffprobe_path(ffmpeg_path=str(tmp_path / "nonexistent" / "ffmpeg.exe"))


class TestVideoAnalysis:
    """Test video analysis functions."""

    def test_width_height_without_ffprobe(self, tmp_path):
        """Test that width_height raises error without ffprobe."""
        # Create a dummy input file
        infile = tmp_path / "test.mp4"
        infile.write_bytes(b"dummy video content")

        # Should raise RuntimeError when ffprobe is not found
        with pytest.raises(RuntimeError, match="ffprobe not found"):
            width_height(str(infile))

    def test_duration_without_ffprobe(self, tmp_path):
        """Test that duration raises error without ffprobe."""
        # Create a dummy input file
        infile = tmp_path / "test.mp4"
        infile.write_bytes(b"dummy video content")

        # Should raise RuntimeError when ffprobe is not found
        with pytest.raises(RuntimeError, match="ffprobe not found"):
            duration(str(infile))


class TestVideoCompression:
    """Test video compression functions."""

    def test_compress_without_ffmpeg(self, tmp_path):
        """Test that compress raises error without FFmpeg."""
        # Create dummy input and output files
        infile = tmp_path / "input.mp4"
        infile.write_bytes(b"dummy video content")
        outfile = tmp_path / "output.mp4"

        # Should raise RuntimeError when FFmpeg is not found
        with pytest.raises(RuntimeError, match="FFmpeg not found"):
            compress(str(infile), str(outfile))

    def test_compress_with_config_without_ffmpeg(self, tmp_path):
        """Test compress with config object but no FFmpeg."""
        from filesqueeze.config import Config

        # Create dummy files
        infile = tmp_path / "input.mp4"
        infile.write_bytes(b"dummy video content")
        outfile = tmp_path / "output.mp4"

        # Create config
        config = Config()

        # Should raise RuntimeError when FFmpeg is not found
        with pytest.raises(RuntimeError, match="FFmpeg not found"):
            compress(str(infile), str(outfile), config=config)

    def test_compress_with_custom_params_without_ffmpeg(self, tmp_path):
        """Test compress with custom parameters but no FFmpeg."""
        # Create dummy files
        infile = tmp_path / "input.mp4"
        infile.write_bytes(b"dummy video content")
        outfile = tmp_path / "output.mp4"

        # Should raise RuntimeError when FFmpeg is not found
        with pytest.raises(RuntimeError, match="FFmpeg not found"):
            compress(
                str(infile),
                str(outfile),
                crf=23,
                threads=4,
                preset="medium",
                max_height=1080,
                audio_bitrate="128k"
            )


@pytest.mark.skipif(
    True,  # Skip these tests by default (require actual FFmpeg)
    reason="Requires FFmpeg to be installed"
)
class TestVideoCompressionWithBinaries:
    """Tests that require actual FFmpeg binaries."""

    def test_width_height_with_ffprobe(self, tmp_path):
        """Test getting video dimensions with real ffprobe."""
        # This test would require an actual video file
        # Skipped by default
        pass

    def test_duration_with_ffprobe(self, tmp_path):
        """Test getting video duration with real ffprobe."""
        # This test would require an actual video file
        # Skipped by default
        pass

    def test_compress_with_ffmpeg(self, tmp_path):
        """Test video compression with real FFmpeg."""
        # This test would require an actual video file
        # Skipped by default
        pass

    def test_compress_with_config(self, tmp_path):
        """Test video compression with config object."""
        # This test would require an actual video file
        # Skipped by default
        pass
