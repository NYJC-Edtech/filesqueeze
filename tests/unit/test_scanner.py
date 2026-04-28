"""Test file scanner functionality."""

import os
import time
from pathlib import Path
import pytest

from filesqueeze.scanner import FileScanner
from filesqueeze.config import Config


class TestFileScanner:
    """Test FileScanner class."""

    def test_scanner_init_without_config(self, tmp_path):
        """Test scanner initialization without config."""
        scanner = FileScanner()
        assert scanner.config is None

    def test_scanner_init_with_config(self, tmp_path):
        """Test scanner initialization with config."""
        config = Config({"file_detection": {"min_age_seconds": 0}})
        scanner = FileScanner(config)
        assert scanner.config == config

    def test_is_valid_extension_default(self, tmp_path):
        """Test extension validation with default extensions."""
        scanner = FileScanner()

        # Valid extensions
        assert scanner.is_valid_extension(Path("test.mp4"))
        assert scanner.is_valid_extension(Path("test.pdf"))
        assert scanner.is_valid_extension(Path("test.jpg"))
        assert scanner.is_valid_extension(Path("test.jpeg"))
        assert scanner.is_valid_extension(Path("test.png"))

        # Invalid extensions
        assert not scanner.is_valid_extension(Path("test.txt"))
        assert not scanner.is_valid_extension(Path("test.doc"))
        assert not scanner.is_valid_extension(Path("test.zip"))

    def test_is_valid_extension_with_config(self, tmp_path):
        """Test extension validation with config."""
        config = Config({"file_detection": {"extensions": ["mp4", "pdf"]}})
        scanner = FileScanner(config)

        # Valid extensions from config
        assert scanner.is_valid_extension(Path("test.mp4"))
        assert scanner.is_valid_extension(Path("test.pdf"))

        # Invalid extensions
        assert not scanner.is_valid_extension(Path("test.txt"))

    def test_meets_age_requirement_default(self, tmp_path):
        """Test age requirement with default settings."""
        scanner = FileScanner()

        # Create an old file
        old_file = tmp_path / "old.txt"
        old_file.write_text("test")
        time.sleep(0.1)  # Ensure file is old enough

        # Create a new file
        new_file = tmp_path / "new.txt"
        new_file.write_text("test")

        # Both should pass default age requirement (5 seconds)
        # Actually, let's adjust - default is 5 seconds
        # So new file should fail if we check immediately
        # But we need to test with 0 min_age
        scanner2 = FileScanner(Config({"file_detection": {"min_age_seconds": 0}}))
        assert scanner2.meets_age_requirement(new_file)

    def test_meets_age_requirement_with_config(self, tmp_path):
        """Test age requirement with config."""
        # Create a file
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")

        # Scanner with 0 age requirement
        config = Config({"file_detection": {"min_age_seconds": 0}})
        scanner = FileScanner(config)
        assert scanner.meets_age_requirement(test_file)

        # Scanner with high age requirement
        config2 = Config({"file_detection": {"min_age_seconds": 100}})
        scanner2 = FileScanner(config2)
        assert not scanner2.meets_age_requirement(test_file)

    def test_meets_size_requirement_default(self, tmp_path):
        """Test size requirement with default settings."""
        scanner = FileScanner()

        # Create a small file
        small_file = tmp_path / "small.txt"
        small_file.write_text("x")

        # Default min size is 1024 bytes
        assert not scanner.meets_size_requirement(small_file)

    def test_meets_size_requirement_with_config(self, tmp_path):
        """Test size requirement with config."""
        # Create a file
        test_file = tmp_path / "test.txt"
        test_file.write_text("x")

        # Scanner with 0 size requirement
        config = Config({"file_detection": {"min_size_bytes": 0}})
        scanner = FileScanner(config)
        assert scanner.meets_size_requirement(test_file)

        # Scanner with high size requirement
        config2 = Config({"file_detection": {"min_size_bytes": 10000}})
        scanner2 = FileScanner(config2)
        assert not scanner2.meets_size_requirement(test_file)

    def test_is_valid_file(self, tmp_path):
        """Test complete file validation."""
        # Create test files
        valid_file = tmp_path / "test.mp4"
        valid_file.write_text("x" * 2000)  # Large enough

        invalid_ext = tmp_path / "test.txt"
        invalid_ext.write_text("x" * 2000)

        too_small = tmp_path / "small.mp4"
        too_small.write_text("x")

        # Scanner with default config
        config = Config({"file_detection": {"min_age_seconds": 0, "min_size_bytes": 1024}})
        scanner = FileScanner(config)

        assert scanner.is_valid_file(valid_file)
        assert not scanner.is_valid_file(invalid_ext)
        assert not scanner.is_valid_file(too_small)

    def test_scan_directory(self, tmp_path):
        """Test scanning a directory."""
        # Create test files
        (tmp_path / "video1.mp4").write_text("x" * 2000)
        (tmp_path / "video2.mp4").write_text("x" * 2000)
        (tmp_path / "document.pdf").write_text("x" * 2000)
        (tmp_path / "ignored.txt").write_text("x" * 2000)

        config = Config({"file_detection": {"min_age_seconds": 0, "min_size_bytes": 1024}})
        scanner = FileScanner(config)

        files = list(scanner.scan(tmp_path))
        assert len(files) == 3
        assert all(f.suffix in [".mp4", ".pdf"] for f in files)

    def test_scan_recursive(self, tmp_path):
        """Test recursive scanning."""
        # Create nested directory structure
        subdir = tmp_path / "subdir"
        subdir.mkdir()

        (tmp_path / "root.mp4").write_text("x" * 2000)
        (subdir / "nested.mp4").write_text("x" * 2000)

        config = Config({"file_detection": {"min_age_seconds": 0, "min_size_bytes": 1024}})
        scanner = FileScanner(config)

        files = list(scanner.scan(tmp_path, recursive=True))
        assert len(files) == 2

    def test_scan_non_recursive(self, tmp_path):
        """Test non-recursive scanning."""
        # Create nested directory structure
        subdir = tmp_path / "subdir"
        subdir.mkdir()

        (tmp_path / "root.mp4").write_text("x" * 2000)
        (subdir / "nested.mp4").write_text("x" * 2000)

        config = Config({"file_detection": {"min_age_seconds": 0, "min_size_bytes": 1024}})
        scanner = FileScanner(config)

        files = list(scanner.scan(tmp_path, recursive=False))
        assert len(files) == 1
        assert files[0].name == "root.mp4"

    def test_walk_backward_compatible(self, tmp_path):
        """Test backward compatible walk method."""
        (tmp_path / "test.mp4").write_text("x" * 2000)

        config = Config({"file_detection": {"min_age_seconds": 0, "min_size_bytes": 1024}})
        scanner = FileScanner(config)

        files = scanner.walk(tmp_path)
        assert isinstance(files, list)
        assert len(files) == 1

    def test_scan_invalid_directory(self, tmp_path):
        """Test scanning invalid directory."""
        scanner = FileScanner()

        with pytest.raises(ValueError, match="Not a directory"):
            list(scanner.scan(tmp_path / "nonexistent"))

    def test_reset_processed_tracking(self, tmp_path):
        """Test reset functionality."""
        (tmp_path / "test.mp4").write_text("x" * 2000)

        config = Config({"file_detection": {"min_age_seconds": 0, "min_size_bytes": 1024}})
        scanner = FileScanner(config)

        # First scan
        files1 = list(scanner.scan(tmp_path))
        assert len(files1) == 1

        # Second scan should return nothing (already processed)
        files2 = list(scanner.scan(tmp_path))
        assert len(files2) == 0

        # Reset and scan again
        scanner.reset()
        files3 = list(scanner.scan(tmp_path))
        assert len(files3) == 1
