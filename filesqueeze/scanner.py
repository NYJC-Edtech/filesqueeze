"""filesqueeze.scanner

File scanner for finding and filtering files in directories.
"""

import os
import time
from pathlib import Path
from typing import Generator

from .config import Config


class FileScanner:
    """Scanner for finding and filtering files in directories."""

    def __init__(self, config: Config | None = None):
        """Initialize the file scanner.

        Args:
            config: Optional Config object for settings.
        """
        self.config = config
        self._processed: set[str] = set()

    def is_valid_extension(self, filepath: Path) -> bool:
        """Check if file extension is valid.

        Args:
            filepath: Path to the file.

        Returns:
            True if extension is valid, False otherwise.
        """
        # Get valid extensions from config
        if self.config:
            extensions = self.config.get("file_detection.extensions", [])
        else:
            # Default extensions
            extensions = ["mp4", "wmv", "avi", "mov", "mkv", "flv", "pptx", "pdf", "jpg", "jpeg", "png"]

        ext = filepath.suffix.lstrip(".").lower()
        return ext in extensions

    def meets_age_requirement(self, filepath: Path) -> bool:
        """Check if file meets minimum age requirement.

        Args:
            filepath: Path to the file.

        Returns:
            True if file is old enough, False otherwise.
        """
        # Get minimum age from config
        if self.config:
            min_age_seconds = self.config.get("file_detection.min_age_seconds", 5)
        else:
            min_age_seconds = 5

        if min_age_seconds == 0:
            return True

        # Check file modification time
        mtime = filepath.stat().st_mtime
        age = time.time() - mtime
        return age >= min_age_seconds

    def meets_size_requirement(self, filepath: Path) -> bool:
        """Check if file meets minimum size requirement.

        Args:
            filepath: Path to the file.

        Returns:
            True if file is large enough, False otherwise.
        """
        # Get minimum size from config
        if self.config:
            min_size_bytes = self.config.get("file_detection.min_size_bytes", 1024)
        else:
            min_size_bytes = 1024

        if min_size_bytes == 0:
            return True

        # Check file size
        size = filepath.stat().st_size
        return size >= min_size_bytes

    def is_valid_file(self, filepath: Path) -> bool:
        """Check if file is valid based on all criteria.

        Args:
            filepath: Path to the file.

        Returns:
            True if file is valid, False otherwise.
        """
        # Must be a file
        if not filepath.is_file():
            return False

        # Check extension
        if not self.is_valid_extension(filepath):
            return False

        # Check age
        if not self.meets_age_requirement(filepath):
            return False

        # Check size
        if not self.meets_size_requirement(filepath):
            return False

        return True

    def scan(self, directory: Path, recursive: bool = True) -> Generator[Path, None, None]:
        """Scan directory for valid files.

        Args:
            directory: Directory to scan.
            recursive: Whether to scan subdirectories.

        Yields:
            Paths to valid files.
        """
        if not directory.is_dir():
            raise ValueError(f"Not a directory: {directory}")

        # Walk the directory
        if recursive:
            # Use os.walk for better performance on large directories
            for root, _dirs, files in os.walk(directory):
                root_path = Path(root)
                for filename in files:
                    filepath = root_path / filename
                    if self.is_valid_file(filepath):
                        # Skip if already processed
                        file_key = str(filepath.absolute())
                        if file_key not in self._processed:
                            self._processed.add(file_key)
                            yield filepath
        else:
            # Non-recursive: only scan top-level directory
            for filepath in directory.iterdir():
                if self.is_valid_file(filepath):
                    # Skip if already processed
                    file_key = str(filepath.absolute())
                    if file_key not in self._processed:
                        self._processed.add(file_key)
                        yield filepath

    def walk(self, directory: Path) -> list[Path]:
        """Walk directory and return list of valid files.

        This is a backward-compatible wrapper for the scan method.

        Args:
            directory: Directory to scan.

        Returns:
            List of valid file paths.
        """
        return list(self.scan(directory))

    def reset(self):
        """Reset the processed files tracking."""
        self._processed.clear()
