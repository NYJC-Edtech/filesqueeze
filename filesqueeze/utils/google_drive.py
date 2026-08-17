"""Google Drive detection and safe file handling utilities."""

import re
import shutil
import tempfile
from pathlib import Path

from filesqueeze.system import logger


def is_google_drive_path(path: Path | str) -> bool:
    """Detect if a path is on a Google Drive virtual filesystem.

    Args:
        path: Path to check

    Returns:
        True if path appears to be on Google Drive, False otherwise
    """
    path_str = str(path).lower()

    # Common Google Drive path patterns
    google_drive_patterns = [
        "shared drives",  # Google Drive shared drives
        "my drive",  # Google Drive personal drive
        "team drives",  # Alternative name for shared drives
        "\\\\google\\",  # UNC path for Google Drive
        "google drive streaming",  # Google Drive streaming path
    ]

    for pattern in google_drive_patterns:
        if pattern in path_str:
            return True

    return False


def create_temp_copy(filepath: Path | str) -> Path:
    """Create a temporary copy of a file for safe processing.

    Args:
        filepath: Original file path

    Returns:
        Path to temporary copy

    Raises:
        OSError: If copy operation fails
    """
    filepath = Path(filepath)

    # Create temp directory
    temp_dir = Path(tempfile.gettempdir()) / "filesqueeze_processing"
    temp_dir.mkdir(parents=True, exist_ok=True)

    # Create temp copy with original name
    temp_path = temp_dir / filepath.name

    logger.info(f"Creating temp copy for Google Drive file: {filepath.name}")
    logger.info(f"  Source: {filepath}")
    logger.info(f"  Temp:   {temp_path}")

    try:
        shutil.copy2(filepath, temp_path)
        logger.info(f"Temp copy created successfully: {temp_path.stat().st_size:,} bytes")
        return temp_path
    except Exception as e:
        logger.error(f"Failed to create temp copy: {e}")
        raise


def move_result_to_google_drive(temp_result: Path | str, target_path: Path | str) -> None:
    """Move processed result from temp to Google Drive location.

    Args:
        temp_result: Path to processed file in temp directory
        target_path: Final destination on Google Drive

    Raises:
        OSError: If move operation fails
    """
    temp_result = Path(temp_result)
    target_path = Path(target_path)

    logger.info(f"Moving result to Google Drive: {temp_result.name}")
    logger.info(f"  From: {temp_result}")
    logger.info(f"  To:   {target_path}")

    try:
        # Ensure target directory exists
        target_path.parent.mkdir(parents=True, exist_ok=True)

        # Move file (atomic operation)
        shutil.move(str(temp_result), str(target_path))
        logger.info(f"Result moved successfully: {target_path.stat().st_size:,} bytes")
    except Exception as e:
        logger.error(f"Failed to move result to Google Drive: {e}")
        raise


def cleanup_temp_file(temp_path: Path | str) -> None:
    """Clean up temporary file.

    Args:
        temp_path: Path to temporary file to remove
    """
    temp_path = Path(temp_path)
    try:
        if temp_path.exists():
            temp_path.unlink()
            logger.info(f"Cleaned up temp file: {temp_path.name}")
    except Exception as e:
        logger.warning(f"Failed to cleanup temp file {temp_path.name}: {e}")


def cleanup_temp_directory() -> None:
    """Clean up entire FileSqueeze temp directory."""
    temp_dir = Path(tempfile.gettempdir()) / "filesqueeze_processing"
    try:
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
            logger.info(f"Cleaned up temp directory: {temp_dir}")
    except Exception as e:
        logger.warning(f"Failed to cleanup temp directory: {e}")
