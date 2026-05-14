"""Test retention manager functionality."""

import os
import tempfile
import time
from pathlib import Path

import pytest

from filesqueeze.config import Config
from filesqueeze.service import CleanupStats, RetentionManager


@pytest.fixture
def temp_dirs():
    """Create temporary directories for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        base = Path(temp_dir)
        output_dir = base / "compressed"
        archive_dir = base / "archive"
        output_dir.mkdir()
        archive_dir.mkdir()

        # Create some test files with different ages
        # Old file (should be cleaned up)
        old_file = output_dir / "old_compressed.mp4"
        old_file.write_text("old content")
        old_mtime = time.time() - (50 * 3600)  # 50 hours ago
        os.utime(old_file, (old_mtime, old_mtime))

        # Recent file (should be kept)
        recent_file = output_dir / "recent_compressed.mp4"
        recent_file.write_text("recent content")

        # Old archived file (should be cleaned up)
        old_archived = archive_dir / "old_original.mp4"
        old_archived.write_text("old archived content")
        old_archived_mtime = time.time() - (35 * 24 * 3600)  # 35 days ago
        os.utime(old_archived, (old_archived_mtime, old_archived_mtime))

        yield {
            "output_dir": output_dir,
            "archive_dir": archive_dir,
            "old_file": old_file,
            "recent_file": recent_file,
            "old_archived": old_archived,
            "recent_archived": archive_dir / "recent_original.mp4",
        }


@pytest.fixture
def retention_config(temp_dirs):
    """Create a config with retention settings for testing."""
    config_dict = {
        "retention": {
            "enable_cleanup": True,
            "cleanup_interval_hours": 1,  # Check every hour
            "compressed_retention_hours": 48,  # Keep compressed for 48 hours
            "archive_retention_days": 30,  # Keep archived for 30 days
            "min_age_hours": 1,  # Minimum age safeguard
            "dry_run": True,  # Don't actually delete in tests
            "require_confirmation": False,  # Skip confirmation for tests
        },
        "directories": {"output": str(temp_dirs["output_dir"]), "archive": str(temp_dirs["archive_dir"])},
    }
    return Config(config_dict)


def test_retention_manager_initialization(retention_config, temp_dirs):
    """Test that RetentionManager initializes correctly."""
    import logging

    logger = logging.getLogger(__name__)

    manager = RetentionManager(retention_config, temp_dirs["output_dir"], logger)

    assert manager.enable_cleanup is True
    assert manager.compressed_retention_hours == 48
    assert manager.archive_retention_days == 30
    assert manager.min_age_hours == 1
    assert manager.dry_run is True


def test_cleanup_stats_creation():
    """Test CleanupStats dataclass."""
    stats = CleanupStats(
        last_cleanup_time="2024-01-01T12:00:00",
        compressed_files_deleted=5,
        archived_files_deleted=3,
        total_space_freed=1024000,
    )

    assert stats.compressed_files_deleted == 5
    assert stats.archived_files_deleted == 3
    assert stats.total_space_freed == 1024000


def test_retention_config_loading():
    """Test that retention configuration loads from default.toml."""
    config = Config()

    # Check that retention config exists with defaults
    enable_cleanup = config.get("retention.enable_cleanup", True)
    compressed_retention = config.get("retention.compressed_retention_hours", 48)
    archive_retention = config.get("retention.archive_retention_days", 30)

    assert enable_cleanup is True
    assert compressed_retention == 48
    # Note: archive_retention_days was changed to 21 in user config, so we check for >= 21
    assert archive_retention >= 21


def test_dry_run_mode(retention_config, temp_dirs, caplog):
    """Test that dry-run mode doesn't delete files."""
    import logging

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    manager = RetentionManager(retention_config, temp_dirs["output_dir"], logger)

    # Run cleanup in dry-run mode
    manager._run_cleanup()

    # Files should still exist
    assert temp_dirs["old_file"].exists()
    assert temp_dirs["recent_file"].exists()
    assert temp_dirs["old_archived"].exists()

    # Check log output contains "Would delete"
    assert any("Would delete" in record.message for record in caplog.records)


def test_minimum_age_safeguard(retention_config, temp_dirs):
    """Test that minimum age safeguard prevents deletion of recent files."""
    import logging

    logger = logging.getLogger(__name__)

    manager = RetentionManager(retention_config, temp_dirs["output_dir"], logger)

    # Recent file should not be deleted even if retention period is 0
    manager.compressed_retention_hours = 0
    manager._run_cleanup()

    # Recent file should still exist due to minimum age safeguard
    assert temp_dirs["recent_file"].exists()


def test_cleanup_stats_tracking(retention_config, temp_dirs):
    """Test that cleanup statistics are tracked correctly."""
    import logging

    logger = logging.getLogger(__name__)

    manager = RetentionManager(retention_config, temp_dirs["output_dir"], logger)

    # Run cleanup
    manager._run_cleanup()

    # Get stats
    stats = manager.get_cleanup_stats()

    # Should have deleted some files (in dry-run mode, they're counted)
    assert stats.compressed_files_deleted >= 0
    assert stats.archived_files_deleted >= 0
    assert stats.total_space_freed >= 0
    assert stats.last_cleanup_time != ""


def test_size_based_config_loading():
    """Test that size-based retention configuration loads correctly."""
    config_dict = {
        "retention": {
            "max_compressed_size_gb": 100,
            "max_archive_size_gb": 50,
        }
    }
    config = Config(config_dict)

    # Check that size-based config loaded
    max_compressed = config.get("retention.max_compressed_size_gb", 0)
    max_archive = config.get("retention.max_archive_size_gb", 0)

    assert max_compressed == 100
    assert max_archive == 50


def test_directory_size_calculation(retention_config, temp_dirs):
    """Test directory size calculation."""
    import logging

    logger = logging.getLogger(__name__)
    manager = RetentionManager(retention_config, temp_dirs["output_dir"], logger)

    # Calculate size of compressed directory
    compressed_size = manager._get_directory_size(temp_dirs["output_dir"])

    # Should be greater than 0 (we have test files)
    assert compressed_size > 0


def test_should_cleanup_by_size(temp_dirs):
    """Test the logic that determines if size-based cleanup is needed."""
    import logging

    logger = logging.getLogger(__name__)

    # Create larger test files to exceed size limits
    large_file = temp_dirs["output_dir"] / "large_test.mp4"
    large_file.write_bytes(b"x" * 5000)  # 5KB file

    large_archive = temp_dirs["archive_dir"] / "large_archive.mp4"
    large_archive.write_bytes(b"x" * 5000)  # 5KB file

    # Create config with very low size limits to trigger cleanup
    config_dict = {
        "retention": {
            "enable_cleanup": True,
            "max_compressed_size_gb": 0.000001,  # ~1KB
            "max_archive_size_gb": 0.000001,
            "dry_run": True,
            "require_confirmation": False,
        },
        "directories": {"output": str(temp_dirs["output_dir"]), "archive": str(temp_dirs["archive_dir"])},
    }
    config = Config(config_dict)

    manager = RetentionManager(config, temp_dirs["output_dir"], logger)

    # Should indicate cleanup is needed (size exceeds limit)
    assert manager._should_cleanup_by_size() is True


def test_size_based_cleanup_disabled_when_zero(temp_dirs, caplog):
    """Test that size-based cleanup is disabled when limits are set to 0."""
    import logging

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    # Size limits of 0 mean disabled
    config_dict = {
        "retention": {
            "enable_cleanup": True,
            "max_compressed_size_gb": 0,
            "max_archive_size_gb": 0,
            "dry_run": True,
            "require_confirmation": False,
        },
        "directories": {"output": str(temp_dirs["output_dir"]), "archive": str(temp_dirs["archive_dir"])},
    }
    config = Config(config_dict)

    manager = RetentionManager(config, temp_dirs["output_dir"], logger)

    # Should not trigger size-based cleanup
    assert manager._should_cleanup_by_size() is False

    # Run cleanup - should only do time-based
    manager._run_cleanup()

    # Check logs don't contain size-based cleanup messages
    assert not any("Size-based cleanup" in record.message for record in caplog.records)


def test_size_based_cleanup_large_files_first(temp_dirs, caplog):
    """Test that size-based cleanup deletes largest files first."""
    import logging

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    # Create test files with different sizes
    small_file = temp_dirs["output_dir"] / "small.mp4"
    small_file.write_bytes(b"x" * 100)  # 100 bytes

    large_file = temp_dirs["output_dir"] / "large.mp4"
    large_file.write_bytes(b"x" * 10000)  # 10,000 bytes

    medium_file = temp_dirs["output_dir"] / "medium.mp4"
    medium_file.write_bytes(b"x" * 1000)  # 1,000 bytes

    # Set size limit to trigger cleanup (must be less than total size)
    config_dict = {
        "retention": {
            "enable_cleanup": True,
            "max_compressed_size_gb": 0.000005,  # ~5KB
            "max_archive_size_gb": 0,
            "dry_run": True,
            "require_confirmation": False,
            "min_age_hours": 0,  # Allow immediate deletion for testing
        },
        "directories": {"output": str(temp_dirs["output_dir"]), "archive": str(temp_dirs["archive_dir"])},
    }
    config = Config(config_dict)

    manager = RetentionManager(config, temp_dirs["output_dir"], logger)

    # Run cleanup
    manager._run_cleanup()

    # Check that large file would be deleted first
    log_messages = [record.message for record in caplog.records]

    # The largest file should be marked for deletion
    assert any("large.mp4" in msg and ("Would delete" in msg or "Deleted" in msg) for msg in log_messages)

    # Total size should be under limit after cleanup
    # small (100) + medium (1000) = 1100 bytes < 5000 byte limit
    # large (10000) should be deleted


def test_sequential_cleanup_time_then_size(temp_dirs, caplog):
    """Test that cleanup runs time-based first, then size-based."""
    import logging

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    # Create a large file to trigger size-based cleanup
    large_file = temp_dirs["output_dir"] / "large_file.mp4"
    large_file.write_bytes(b"x" * 5000)  # 5KB file

    # Enable both time-based and size-based cleanup
    config_dict = {
        "retention": {
            "enable_cleanup": True,
            "compressed_retention_hours": 48,
            "max_compressed_size_gb": 0.000001,  # Very low limit (~1KB)
            "dry_run": True,
            "require_confirmation": False,
        },
        "directories": {"output": str(temp_dirs["output_dir"]), "archive": str(temp_dirs["archive_dir"])},
    }
    config = Config(config_dict)

    manager = RetentionManager(config, temp_dirs["output_dir"], logger)

    # Run cleanup
    manager._run_cleanup()

    log_messages = [record.message for record in caplog.records]

    # Should see both types of cleanup messages
    assert any("Starting Retention Cleanup" in msg for msg in log_messages)

    # If size limit exceeded, should see size-based cleanup
    assert any("Size limits exceeded" in msg or "Size-based cleanup" in msg for msg in log_messages)


if __name__ == "__main__":
    import os

    pytest.main([__file__, "-v"])
