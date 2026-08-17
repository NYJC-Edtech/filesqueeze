"""Unit tests for MP4 file verification."""

import tempfile
from pathlib import Path

import pytest

from filesqueeze.utils.subprocess_helper import verify_mp4_file


def test_verify_mp4_file_success():
    """Test MP4 verification with valid MP4 file."""
    # Create a temporary file with MP4 header
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        tmp_path = Path(tmp.name)
        # Write minimal MP4 header (ftyp box)
        # [4 bytes size][4 bytes type "ftyp"][4 bytes brand]
        header = b'\x00\x00\x00\x20ftypisom'  # Size 32, type ftyp, brand isom
        tmp.write(header)
        tmp.write(b'\x00' * 100)  # Add some padding
        tmp.flush()

    try:
        # Should not raise any exception
        result = verify_mp4_file(str(tmp_path), min_size=100)
        assert result == tmp_path
    finally:
        tmp_path.unlink()


def test_verify_mp4_file_not_found():
    """Test MP4 verification with missing file."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        nonexistent = Path(tmp_dir) / "nonexistent.mp4"
        with pytest.raises(FileNotFoundError, match="Output file not created"):
            verify_mp4_file(str(nonexistent))


def test_verify_mp4_file_too_small():
    """Test MP4 verification with file too small."""
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        tmp_path = Path(tmp.name)
        tmp.write(b'small')  # Very small content
        tmp.flush()

    try:
        with pytest.raises(RuntimeError, match="Output file is too small"):
            verify_mp4_file(str(tmp_path), min_size=1000)
    finally:
        tmp_path.unlink()


def test_verify_mp4_file_invalid_header():
    """Test MP4 verification with invalid header (should warn but not fail)."""
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        tmp_path = Path(tmp.name)
        # Write invalid MP4 header (not ftyp)
        invalid_header = b'INVALID_HEADER_NO_FTYP_HERE'
        tmp.write(invalid_header)
        tmp.write(b'\x00' * 2000)  # Add enough content to pass size check
        tmp.flush()

    try:
        # Should not raise exception even with invalid header (just warns)
        result = verify_mp4_file(str(tmp_path), min_size=100)
        assert result == tmp_path
    finally:
        tmp_path.unlink()


def test_verify_mp4_file_empty():
    """Test MP4 verification with empty file."""
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        tmp_path = Path(tmp.name)
        # Create empty file

    try:
        with pytest.raises(RuntimeError, match="Output file is too small"):
            verify_mp4_file(str(tmp_path), min_size=1000)
    finally:
        tmp_path.unlink()
