"""Manual trigger for retention cleanup testing."""

import sys
from pathlib import Path

# Add filesqueeze to path (tests directory is sibling to filesqueeze)
sys.path.insert(0, str(Path(__file__).parent.parent))

from filesqueeze.config import Config
from filesqueeze.service import RetentionManager
import logging

# Setup logging to see what's happening
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")


def main():
    print("=" * 60)
    print("Manual Retention Cleanup Trigger")
    print("=" * 60)

    # Load configuration
    config = Config()

    # Get directories from config
    output_dir = config.output_dir
    archive_dir = config.archive_dir

    print(f"\nConfiguration loaded:")
    print(f"  Output directory: {output_dir}")
    print(f"  Archive directory: {archive_dir or 'Not configured'}")
    print(f"  Dry-run mode: {config.get('retention.dry_run', False)}")
    print(f"  Compressed retention: {config.get('retention.compressed_retention_hours', 48)} hours")
    print(f"  Archive retention: {config.get('retention.archive_retention_days', 30)} days")
    print(f"  Minimum age safeguard: {config.get('retention.min_age_hours', 1)} hours")

    # Create retention manager
    logger = logging.getLogger("filesqueeze")
    manager = RetentionManager(config, output_dir, logger)

    # Set first run confirmed to bypass confirmation
    manager._first_run_confirmed = True

    print("\n" + "=" * 60)
    print("Running cleanup now...")
    print("=" * 60)

    # Run cleanup immediately
    manager._run_cleanup()

    # Show statistics
    stats = manager.get_cleanup_stats()
    print("\n" + "=" * 60)
    print("Cleanup Statistics:")
    print("=" * 60)
    print(f"  Last cleanup: {stats.last_cleanup_time}")
    print(f"  Compressed files deleted: {stats.compressed_files_deleted}")
    print(f"  Archived files deleted: {stats.archived_files_deleted}")
    print(f"  Total space freed: {stats.total_space_freed:,} bytes ({stats.total_space_freed / 1024 / 1024:.2f} MB)")

    if stats.compressed_files_deleted > 0 or stats.archived_files_deleted > 0:
        print("\n✅ Cleanup completed successfully!")
        print(f"   In dry-run mode, {stats.compressed_files_deleted + stats.archived_files_deleted} files would be deleted.")
    else:
        print("\n✅ No files needed cleanup.")

    print("=" * 60)


if __name__ == "__main__":
    main()
