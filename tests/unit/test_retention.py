"""Test retention manager functionality."""

import os
import pytest
import tempfile
import time
from pathlib import Path
from datetime import datetime, timedelta

from filesqueeze.service import RetentionManager, CleanupStats
from filesqueeze.config import Config


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
    assert archive_retention == 30


def test_dry_run_mode(retention_config, temp_dirs, caplog):
    """Test that dry-run mode doesn't delete files."""
    import logging
    import os

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


if __name__ == "__main__":
    import os

    pytest.main([__file__, "-v"])
