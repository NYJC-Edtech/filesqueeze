"""filesqueeze.service

Service mode for watching directories and compressing files.
"""

import logging
import sys
import threading
import time
from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from .config import Config
from .logger import setup_logging  # This is the actual Logger.setup, not a wrapper


@dataclass(frozen=True)
class ProcessedFile:
    """Information about a processed file."""

    filename: str
    timestamp: str  # ISO format timestamp
    success: bool


@dataclass(frozen=True)
class CleanupStats:
    """Statistics about cleanup operations."""

    last_cleanup_time: str = ""  # ISO format timestamp
    compressed_files_deleted: int = 0
    archived_files_deleted: int = 0
    total_space_freed: int = 0  # bytes


@dataclass(frozen=True)
class ServiceState:
    """Immutable snapshot of service state.

    This dataclass provides a read-only snapshot of the service's current state,
    perfect for GUI display and status queries. It's frozen to ensure immutability.
    """

    running: bool
    input_dir: Path
    output_dir: Path
    processing_files: list[str] = field(default_factory=list)
    processed_files: list[ProcessedFile] = field(default_factory=list)
    completed_count: int = 0
    failed_count: int = 0
    uptime: timedelta = field(default_factory=timedelta)
    cleanup_stats: CleanupStats = field(default_factory=CleanupStats)


class StateProvider:
    """Interface for querying service state.

    Any component that wants to display service status (GUI, CLI, web UI, etc.)
    should depend on this interface rather than concrete implementations.
    """

    def get_state(self) -> ServiceState:
        """Get current service state.

        Returns:
            ServiceState: Immutable snapshot of current state.
        """
        raise NotImplementedError


class NotificationManager:
    """Manages Windows toast notifications with update support."""

    def __init__(self):
        """Initialize the notification manager."""
        self._notifications = {}  # Track notification tags by filename
        self._lock = threading.Lock()
        self._counter = 0  # For generating unique tags

    def show(self, title: str, message: str, filename: str = None, tag: str = None) -> bool:
        """Show a Windows toast notification.

        Args:
            title: Notification title.
            message: Notification message.
            filename: Optional filename to track this notification for updates.
            tag: Optional custom tag for the notification.

        Returns:
            True if notification was shown, False otherwise.
        """
        if sys.platform != "win32":
            return False

        # Generate tag if not provided
        if tag is None and filename:
            with self._lock:
                tag = f"file_{filename}_{self._counter}"
                self._notifications[filename] = tag
                self._counter += 1
        elif tag is None:
            tag = f"notification_{self._counter}"
            with self._lock:
                self._counter += 1

        try:
            # Use Windows toast via PowerShell with tag support
            import subprocess

            # Escape single quotes in message
            escaped_title = title.replace("'", "''")
            escaped_message = message.replace("'", "''").replace("\n", "`n")
            escaped_tag = tag.replace("'", "''")

            ps_command = f"""
            Add-Type -AssemblyName Windows.UI.Notifications
            Add-Type -AssemblyName Windows.Data.Xml.Dom

            [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
            [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom, ContentType = WindowsRuntime] | Out-Null

            $template = @"
            <toast>
                <visual>
                    <binding template="ToastGeneric">
                        <text>{escaped_title}</text>
                        <text>{escaped_message}</text>
                    </binding>
                </visual>
            </toast>
            "@

            $xml = New-Object Windows.Data.Xml.Dom.XmlDocument
            $xml.LoadXml($template)
            $toast = New-Object Windows.UI.Notifications.ToastNotification $xml
            $toast.Tag = "{escaped_tag}"
            $notifier = [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("FileSqueeze")

            # Clear any existing notification with the same tag
            try {{
                $notifier.Hide($notifier.GetHistory() | Where-Object {{ $_.Tag -eq "{escaped_tag}" }} | Select-Object -First 1)
            }} catch {{}}

            $notifier.Show($toast)
            """

            # Run PowerShell in background, don't wait for it
            # Don't redirect stdout/stderr - they're discarded by the OS anyway
            # This avoids creating a 'nul' file in the working directory
            subprocess.Popen(["powershell", "-Command", ps_command], creationflags=subprocess.CREATE_NO_WINDOW)
            return True

        except Exception:
            # Silently fail - don't disrupt the service if notifications don't work
            return False

    def get_tag(self, filename: str) -> str:
        """Get the notification tag for a file.

        Args:
            filename: The filename to get the tag for.

        Returns:
            The notification tag, or None if not found.
        """
        with self._lock:
            return self._notifications.get(filename)

    def clear(self, filename: str):
        """Clear the notification tag for a file.

        Args:
            filename: The filename to clear the tag for.
        """
        with self._lock:
            self._notifications.pop(filename, None)


# Global notification manager instance
_notification_manager = NotificationManager()


def show_windows_notification(title: str, message: str, filename: str = None) -> bool:
    """Show a Windows toast notification.

    Args:
        title: Notification title.
        message: Notification message.
        filename: Optional filename to track this notification for updates.

    Returns:
        True if notification was shown, False otherwise.
    """
    return _notification_manager.show(title, message, filename=filename)


class CompressionHandler(FileSystemEventHandler):
    """Handler for file system events."""

    def __init__(self, config: Config, input_dir: Path, output_dir: Path, logger: logging.Logger, watcher):
        """Initialize the compression handler.

        Args:
            config: Config object.
            input_dir: Input directory to watch.
            output_dir: Output directory for compressed files.
            logger: Logger instance.
            watcher: DirectoryWatcher instance for state updates.
        """
        self.config = config
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.logger = logger
        self._watcher = watcher
        self._processing = set()
        self._lock = threading.Lock()

    def on_created(self, event):
        """Handle file creation event.

        Args:
            event: FileCreatedEvent from watchdog.
        """
        if event.is_directory:
            return

        filepath = Path(event.src_path)
        self._process_file(filepath)

    def on_moved(self, event):
        """Handle file move event.

        Args:
            event: FileMovedEvent from watchdog.
        """
        if event.is_directory:
            return

        filepath = Path(event.dest_path)
        self._process_file(filepath)

    def _process_file(self, filepath: Path):
        """Process a file if it meets criteria.

        Args:
            filepath: Path to the file.
        """
        # Check if already being processed
        with self._lock:
            file_key = str(filepath.absolute())
            if file_key in self._processing:
                return
            self._processing.add(file_key)

        try:
            # Import here to avoid circular imports
            from .file_type_registry import get_file_type_registry
            from .scanner import FileScanner

            scanner = FileScanner(self.config)

            # Check if file is valid
            if not scanner.is_valid_file(filepath):
                return

            # Wait for file to be stable (for network drives and slow writes)
            # Check if file size is stable over 2 seconds
            if not self._wait_for_file_stability(filepath):
                self.logger.warning(f"File not stable, skipping: {filepath.name}")
                return

            self.logger.info(f"Detected new file: {filepath.name}")

            # Determine file type
            ext = filepath.suffix.lstrip(".").lower()

            # Generate output path with compressed_ prefix
            output_filename = f"compressed_{filepath.name}"
            output_path = self.output_dir / output_filename

            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)

            self.logger.info(f"Compressing {ext.upper()} file: {filepath.name}")

            # Show Windows notification (only on first detection, not modal)
            # Include filename to track for updates
            show_windows_notification(
                "FileSqueeze",
                f"Compressing {filepath.name}...\n\nType: {ext.upper()}\nThis may take a few minutes.",
                filename=filepath.name,
            )

            try:
                # Process file based on type using registry
                registry = get_file_type_registry()
                processor = registry.get_processor(ext)

                if processor is None:
                    self.logger.warning(f"Unsupported file type: {ext}")
                    return

                result_path = processor(str(filepath), config=self.config, output_path=str(output_path))

                # Verify output file exists
                if Path(result_path).exists():
                    # Calculate compression ratio
                    input_size = filepath.stat().st_size
                    output_size = Path(result_path).stat().st_size
                    reduction = (1 - output_size / input_size) * 100

                    self.logger.info(f"Compression complete: {filepath.name}")
                    self.logger.info(f"  Input:  {input_size:,} bytes ({input_size / 1024 / 1024:.2f} MB)")
                    self.logger.info(f"  Output: {output_size:,} bytes ({output_size / 1024 / 1024:.2f} MB)")
                    if reduction > 0:
                        self.logger.info(f"  Saved:  {reduction:.1f}%")
                    else:
                        self.logger.info("  Note: Output is larger")

                    # Show Windows notification for successful completion
                    # Include filename to replace the previous "compressing" notification
                    show_windows_notification(
                        "FileSqueeze - Complete!",
                        f"Successfully compressed: {filepath.name}\n\n"
                        f"Input:  {input_size / 1024 / 1024:.2f} MB\n"
                        f"Output: {output_size / 1024 / 1024:.2f} MB\n"
                        f"Saved:  {reduction:.1f}%",
                        filename=filepath.name,
                    )

                    # Clear the notification tag for this file
                    _notification_manager.clear(filepath.name)

                    # Archive original file - invariant: must always preserve at least one copy
                    archive_dir = self.config.archive_dir
                    if archive_dir:
                        # Move to archive directory
                        archive_path = archive_dir / filepath.name
                        archive_path.parent.mkdir(parents=True, exist_ok=True)

                        # Handle name collisions in archive
                        if archive_path.exists():
                            # Add timestamp to avoid overwriting
                            timestamp_str = time.strftime("%Y%m%d_%H%M%S")
                            stem = filepath.stem
                            suffix = filepath.suffix
                            archive_path = archive_dir / f"{stem}_{timestamp_str}{suffix}"

                        filepath.rename(archive_path)
                        self.logger.info(f"Archived original file: {filepath.name} -> {archive_path}")
                    else:
                        # INVARINT: Never delete the original file without preserving it
                        # Keep original file in input directory when archive is not configured
                        self.logger.warning(
                            f"Archive directory not configured - original file preserved in input: {filepath.name}"
                        )
                        self.logger.warning(
                            "To enable archiving, set 'directories.archive' in config. " "See: filesqueeze init-config"
                        )

                    # Add to processed files
                    self._watcher._add_processed_file(filepath.name, success=True)

                else:
                    self.logger.error(f"Output file not created: {result_path}")
                    # Add to processed files as failed
                    self._watcher._add_processed_file(filepath.name, success=False)

            except Exception as e:
                self.logger.error(f"Failed to compress {filepath.name}: {e}", exc_info=True)
                # Keep original file in place (as per requirements)
                # Add to processed files as failed
                self._watcher._add_processed_file(filepath.name, success=False)

        finally:
            # Remove from processing set
            with self._lock:
                self._processing.discard(str(filepath.absolute()))

    def _wait_for_file_stability(self, filepath: Path, timeout: int = 30) -> bool:
        """Wait for file to be stable (not being written to).

        This is important for network drives where files may appear before they're fully written.

        Args:
            filepath: Path to the file.
            timeout: Maximum seconds to wait for stability.

        Returns:
            True if file is stable, False if timeout exceeded.
        """
        try:
            import time as time_module

            # Check stability by monitoring file size
            previous_size = -1
            stable_count = 0
            start_time = time_module.time()

            while time_module.time() - start_time < timeout:
                try:
                    current_size = filepath.stat().st_size

                    # File size hasn't changed
                    if current_size == previous_size:
                        stable_count += 1
                        # Need 2 consecutive checks with same size (1 second apart)
                        if stable_count >= 2:
                            self.logger.debug(f"File stable: {filepath.name} ({current_size:,} bytes)")
                            return True
                    else:
                        # File size changed, reset counter
                        stable_count = 0
                        previous_size = current_size
                        self.logger.debug(f"File size changed: {filepath.name} ({current_size:,} bytes)")

                    time_module.sleep(0.5)

                except FileNotFoundError:
                    # File was deleted, don't process
                    self.logger.debug(f"File disappeared during stability check: {filepath.name}")
                    return False

            # Timeout exceeded
            self.logger.warning(f"File stability timeout for: {filepath.name}")
            return False

        except Exception as e:
            self.logger.error(f"Error checking file stability: {e}")
            # On error, assume file is stable and try to process anyway
            return True


class RetentionManager:
    """Manages retention-based cleanup of compressed and archived files."""

    def __init__(self, config: Config, output_dir: Path, logger: logging.Logger):
        """Initialize the retention manager.

        Args:
            config: Config object.
            output_dir: Output directory for compressed files.
            logger: Logger instance.
        """
        self.config = config
        self.output_dir = output_dir
        self.logger = logger
        self._running = False
        self._cleanup_thread = None
        self._stats_lock = threading.Lock()
        self._cleanup_stats = CleanupStats()
        self._first_run_confirmed = False

        # Get retention settings
        self.enable_cleanup = self.config.get("retention.enable_cleanup", True)
        self.cleanup_interval_hours = self.config.get("retention.cleanup_interval_hours", 1)
        self.compressed_retention_hours = self.config.get("retention.compressed_retention_hours", 48)
        self.archive_retention_days = self.config.get("retention.archive_retention_days", 30)
        self.max_compressed_size_gb = self.config.get("retention.max_compressed_size_gb", 0)
        self.max_archive_size_gb = self.config.get("retention.max_archive_size_gb", 0)
        self.min_age_hours = self.config.get("retention.min_age_hours", 1)
        self.dry_run = self.config.get("retention.dry_run", False)
        self.require_confirmation = self.config.get("retention.require_confirmation", True)

        # Archive directory
        self.archive_dir = self.config.archive_dir

    def start(self):
        """Start the periodic cleanup thread."""
        if not self.enable_cleanup:
            self.logger.info("Retention cleanup is disabled in configuration")
            return

        self._running = True
        self._cleanup_thread = threading.Thread(target=self._cleanup_worker, daemon=True)
        self._cleanup_thread.start()

        interval_desc = "dry-run" if self.dry_run else "active"
        self.logger.info("=" * 60)
        self.logger.info("Retention Manager Started")
        self.logger.info("=" * 60)
        self.logger.info(f"Mode: {interval_desc}")
        self.logger.info(f"Cleanup interval: {self.cleanup_interval_hours} hour(s)")
        self.logger.info(f"Compressed files retention: {self.compressed_retention_hours} hours")
        if self.max_compressed_size_gb > 0:
            self.logger.info(f"Compressed files size limit: {self.max_compressed_size_gb} GB")
        if self.archive_dir:
            self.logger.info(f"Archived files retention: {self.archive_retention_days} days")
            if self.max_archive_size_gb > 0:
                self.logger.info(f"Archived files size limit: {self.max_archive_size_gb} GB")
        self.logger.info(f"Minimum age safeguard: {self.min_age_hours} hours")
        self.logger.info("=" * 60)

    def stop(self):
        """Stop the periodic cleanup thread."""
        self._running = False
        if self._cleanup_thread:
            self._cleanup_thread.join(timeout=5)
            self.logger.info("Retention manager stopped")

    def get_cleanup_stats(self) -> CleanupStats:
        """Get cleanup statistics (thread-safe).

        Returns:
            CleanupStats: Immutable snapshot of cleanup statistics.
        """
        with self._stats_lock:
            return self._cleanup_stats

    def _cleanup_worker(self):
        """Background worker for periodic cleanup."""
        import time as time_module

        while self._running:
            try:
                # Calculate sleep time in seconds
                sleep_time = self.cleanup_interval_hours * 3600

                # Sleep in small intervals to check _running flag
                for _ in range(int(sleep_time)):
                    if not self._running:
                        return
                    time_module.sleep(1)

                if self._running:
                    self._run_cleanup()

            except Exception as e:
                self.logger.error(f"Error in cleanup thread: {e}", exc_info=True)

    def _run_cleanup(self):
        """Run the cleanup process."""
        try:
            from datetime import datetime

            # Check if confirmation needed for first run
            if self.require_confirmation and not self._first_run_confirmed:
                self._handle_first_run_confirmation()
                if not self._first_run_confirmed:
                    return  # User declined confirmation

            compressed_deleted = 0
            archived_deleted = 0
            space_freed = 0

            self.logger.info("=" * 60)
            self.logger.info("Starting Retention Cleanup")
            self.logger.info("=" * 60)

            # Clean compressed files
            if self.dry_run:
                self.logger.info("DRY-RUN MODE: No files will be deleted")

            compressed_deleted, space_freed = self._cleanup_compressed_files()
            if self.archive_dir:
                archived_deleted, additional_space = self._cleanup_archived_files()
                space_freed += additional_space

            # Size-based cleanup if limits exceeded
            if self._should_cleanup_by_size():
                self.logger.info("=" * 60)
                self.logger.info("Size limits exceeded, running size-based cleanup")
                self.logger.info("=" * 60)

                compressed_size_deleted, size_space_freed = self._cleanup_compressed_files_by_size()
                if self.archive_dir:
                    archived_size_deleted, additional_size_space = self._cleanup_archived_files_by_size()
                    size_space_freed += additional_size_space
                else:
                    archived_size_deleted = 0

                compressed_deleted += compressed_size_deleted
                archived_deleted += archived_size_deleted
                space_freed += size_space_freed

            # Update statistics
            with self._stats_lock:
                self._cleanup_stats = CleanupStats(
                    last_cleanup_time=datetime.now().isoformat(),
                    compressed_files_deleted=compressed_deleted,
                    archived_files_deleted=archived_deleted,
                    total_space_freed=space_freed,
                )

            self.logger.info("=" * 60)
            self.logger.info("Cleanup Summary")
            self.logger.info("=" * 60)
            self.logger.info(f"Compressed files deleted: {compressed_deleted}")
            if self.archive_dir:
                self.logger.info(f"Archived files deleted: {archived_deleted}")
            self.logger.info(f"Total space freed: {space_freed:,} bytes ({space_freed / 1024 / 1024:.2f} MB)")
            self.logger.info("=" * 60)

            # Show Windows notification
            if compressed_deleted > 0 or archived_deleted > 0:
                show_windows_notification(
                    "FileSqueeze - Cleanup Complete",
                    f"Deleted {compressed_deleted} compressed, {archived_deleted} archived files\n"
                    f"Freed {space_freed / 1024 / 1024:.2f} MB",
                )

        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}", exc_info=True)

    def _handle_first_run_confirmation(self):
        """Handle confirmation for first cleanup run."""
        self.logger.warning("=" * 60)
        self.logger.warning("FIRST RUN CONFIRMATION REQUIRED")
        self.logger.warning("=" * 60)
        self.logger.warning("Retention cleanup is about to run for the first time.")
        self.logger.warning("This will PERMANENTLY DELETE files older than:")
        self.logger.warning(f"  - Compressed files: {self.compressed_retention_hours} hours")
        if self.archive_dir:
            self.logger.warning(f"  - Archived files: {self.archive_retention_days} days")
        self.logger.warning("")
        self.logger.warning("To enable automatic cleanup, update your config:")
        self.logger.warning("  [retention]")
        self.logger.warning("  require_confirmation = false")
        self.logger.warning("")
        self.logger.warning("Or run with: filesqueeze service --confirm-cleanup")
        self.logger.warning("=" * 60)

        # For now, we'll log this but require manual config update
        # In the future, this could be interactive
        self.logger.info("Cleanup cancelled. Update config to enable automatic cleanup.")

    def _cleanup_compressed_files(self) -> tuple[int, int]:
        """Clean up compressed files older than retention period.

        Returns:
            Tuple of (files_deleted, space_freed)
        """
        from datetime import datetime, timedelta

        compressed_deleted = 0
        space_freed = 0
        cutoff_time = datetime.now() - timedelta(hours=self.compressed_retention_hours)
        min_age_time = datetime.now() - timedelta(hours=self.min_age_hours)

        self.logger.info(f"Scanning compressed directory: {self.output_dir}")
        self.logger.info(f"Deleting files older than: {cutoff_time.isoformat()}")
        self.logger.info(f"Skipping files newer than: {min_age_time.isoformat()} (minimum age safeguard)")

        try:
            for filepath in self.output_dir.iterdir():
                if not filepath.is_file():
                    continue

                try:
                    # Get file modification time
                    file_mtime = datetime.fromtimestamp(filepath.stat().st_mtime)

                    # Check minimum age safeguard
                    if file_mtime > min_age_time:
                        self.logger.debug(f"Skipping (too young): {filepath.name}")
                        continue

                    # Check if file is old enough for cleanup
                    if file_mtime < cutoff_time:
                        file_size = filepath.stat().st_size

                        if self.dry_run:
                            self.logger.info(f"Would delete: {filepath.name} ({file_size:,} bytes)")
                        else:
                            filepath.unlink()
                            self.logger.info(f"Deleted: {filepath.name} ({file_size:,} bytes)")
                            compressed_deleted += 1
                            space_freed += file_size

                except Exception as e:
                    self.logger.warning(f"Error processing {filepath.name}: {e}")

        except Exception as e:
            self.logger.error(f"Error scanning compressed directory: {e}")

        return compressed_deleted, space_freed

    def _cleanup_archived_files(self) -> tuple[int, int]:
        """Clean up archived files older than retention period.

        Returns:
            Tuple of (files_deleted, space_freed)
        """
        from datetime import datetime, timedelta

        archived_deleted = 0
        space_freed = 0
        cutoff_time = datetime.now() - timedelta(days=self.archive_retention_days)
        min_age_time = datetime.now() - timedelta(hours=self.min_age_hours)

        self.logger.info(f"Scanning archive directory: {self.archive_dir}")
        self.logger.info(f"Deleting files older than: {cutoff_time.isoformat()}")
        self.logger.info(f"Skipping files newer than: {min_age_time.isoformat()} (minimum age safeguard)")

        try:
            for filepath in self.archive_dir.iterdir():
                if not filepath.is_file():
                    continue

                try:
                    # Get file modification time
                    file_mtime = datetime.fromtimestamp(filepath.stat().st_mtime)

                    # Check minimum age safeguard
                    if file_mtime > min_age_time:
                        self.logger.debug(f"Skipping (too young): {filepath.name}")
                        continue

                    # Check if file is old enough for cleanup
                    if file_mtime < cutoff_time:
                        file_size = filepath.stat().st_size

                        if self.dry_run:
                            self.logger.info(f"Would delete: {filepath.name} ({file_size:,} bytes)")
                        else:
                            filepath.unlink()
                            self.logger.info(f"Deleted: {filepath.name} ({file_size:,} bytes)")
                            archived_deleted += 1
                            space_freed += file_size

                except Exception as e:
                    self.logger.warning(f"Error processing {filepath.name}: {e}")

        except Exception as e:
            self.logger.error(f"Error scanning archive directory: {e}")

        return archived_deleted, space_freed

    def _get_directory_size(self, directory: Path) -> int:
        """Calculate total size of directory in bytes.

        Args:
            directory: Directory path to calculate size for.

        Returns:
            Total size in bytes. Returns 0 if directory doesn't exist or on error.
        """
        try:
            total_size = 0
            for filepath in directory.iterdir():
                if filepath.is_file():
                    total_size += filepath.stat().st_size
            return total_size
        except Exception as e:
            self.logger.warning(f"Error calculating directory size for {directory}: {e}")
            return 0

    def _should_cleanup_by_size(self) -> bool:
        """Check if size-based cleanup should be run.

        Returns:
            True if any size limits are configured and exceeded.
        """
        # Check compressed files size limit
        if self.max_compressed_size_gb > 0:
            compressed_size = self._get_directory_size(self.output_dir)
            compressed_limit_bytes = self.max_compressed_size_gb * 1024 * 1024 * 1024
            if compressed_size > compressed_limit_bytes:
                return True

        # Check archive files size limit
        if self.max_archive_size_gb > 0 and self.archive_dir:
            archive_size = self._get_directory_size(self.archive_dir)
            archive_limit_bytes = self.max_archive_size_gb * 1024 * 1024 * 1024
            if archive_size > archive_limit_bytes:
                return True

        return False

    def _cleanup_compressed_files_by_size(self) -> tuple[int, int]:
        """Clean up compressed files by deleting largest files until under size limit.

        Returns:
            Tuple of (files_deleted, space_freed)
        """
        from datetime import datetime, timedelta

        compressed_deleted = 0
        space_freed = 0

        if self.max_compressed_size_gb <= 0:
            return compressed_deleted, space_freed

        max_size_bytes = self.max_compressed_size_gb * 1024 * 1024 * 1024
        min_age_time = datetime.now() - timedelta(hours=self.min_age_hours)

        self.logger.info(f"Size-based cleanup for compressed directory: {self.output_dir}")
        self.logger.info(f"Size limit: {self.max_compressed_size_gb} GB ({max_size_bytes:,} bytes)")

        try:
            # Get all files with their sizes and modification times
            files = []
            for filepath in self.output_dir.iterdir():
                if not filepath.is_file():
                    continue

                try:
                    file_size = filepath.stat().st_size
                    file_mtime = datetime.fromtimestamp(filepath.stat().st_mtime)
                    files.append((filepath, file_size, file_mtime))
                except Exception as e:
                    self.logger.warning(f"Error getting file info for {filepath.name}: {e}")

            # Calculate current total size
            total_size = sum(file_size for _, file_size, _ in files)

            if total_size <= max_size_bytes:
                self.logger.info(
                    f"Current size: {total_size:,} bytes ({total_size / 1024 / 1024 / 1024:.2f} GB) - within limit"
                )
                return compressed_deleted, space_freed

            self.logger.info(f"Current size: {total_size:,} bytes ({total_size / 1024 / 1024 / 1024:.2f} GB) - exceeds limit")
            self.logger.info(f"Deleting largest files until under {self.max_compressed_size_gb} GB limit")

            # Sort by size (largest first)
            files.sort(key=lambda x: x[1], reverse=True)

            # Delete largest files until under limit
            for filepath, file_size, file_mtime in files:
                if total_size <= max_size_bytes:
                    break

                # Check minimum age safeguard
                if file_mtime > min_age_time:
                    self.logger.debug(f"Skipping (too young): {filepath.name}")
                    continue

                try:
                    if self.dry_run:
                        self.logger.info(f"Would delete: {filepath.name} ({file_size:,} bytes)")
                    else:
                        filepath.unlink()
                        self.logger.info(f"Deleted: {filepath.name} ({file_size:,} bytes)")
                        compressed_deleted += 1
                        space_freed += file_size
                        total_size -= file_size

                except Exception as e:
                    self.logger.warning(f"Error deleting {filepath.name}: {e}")

        except Exception as e:
            self.logger.error(f"Error during size-based cleanup of compressed directory: {e}")

        return compressed_deleted, space_freed

    def _cleanup_archived_files_by_size(self) -> tuple[int, int]:
        """Clean up archived files by deleting largest files until under size limit.

        Returns:
            Tuple of (files_deleted, space_freed)
        """
        from datetime import datetime, timedelta

        archived_deleted = 0
        space_freed = 0

        if not self.archive_dir or self.max_archive_size_gb <= 0:
            return archived_deleted, space_freed

        max_size_bytes = self.max_archive_size_gb * 1024 * 1024 * 1024
        min_age_time = datetime.now() - timedelta(hours=self.min_age_hours)

        self.logger.info(f"Size-based cleanup for archive directory: {self.archive_dir}")
        self.logger.info(f"Size limit: {self.max_archive_size_gb} GB ({max_size_bytes:,} bytes)")

        try:
            # Get all files with their sizes and modification times
            files = []
            for filepath in self.archive_dir.iterdir():
                if not filepath.is_file():
                    continue

                try:
                    file_size = filepath.stat().st_size
                    file_mtime = datetime.fromtimestamp(filepath.stat().st_mtime)
                    files.append((filepath, file_size, file_mtime))
                except Exception as e:
                    self.logger.warning(f"Error getting file info for {filepath.name}: {e}")

            # Calculate current total size
            total_size = sum(file_size for _, file_size, _ in files)

            if total_size <= max_size_bytes:
                self.logger.info(
                    f"Current size: {total_size:,} bytes ({total_size / 1024 / 1024 / 1024:.2f} GB) - within limit"
                )
                return archived_deleted, space_freed

            self.logger.info(f"Current size: {total_size:,} bytes ({total_size / 1024 / 1024 / 1024:.2f} GB) - exceeds limit")
            self.logger.info(f"Deleting largest files until under {self.max_archive_size_gb} GB limit")

            # Sort by size (largest first)
            files.sort(key=lambda x: x[1], reverse=True)

            # Delete largest files until under limit
            for filepath, file_size, file_mtime in files:
                if total_size <= max_size_bytes:
                    break

                # Check minimum age safeguard
                if file_mtime > min_age_time:
                    self.logger.debug(f"Skipping (too young): {filepath.name}")
                    continue

                try:
                    if self.dry_run:
                        self.logger.info(f"Would delete: {filepath.name} ({file_size:,} bytes)")
                    else:
                        filepath.unlink()
                        self.logger.info(f"Deleted: {filepath.name} ({file_size:,} bytes)")
                        archived_deleted += 1
                        space_freed += file_size
                        total_size -= file_size

                except Exception as e:
                    self.logger.warning(f"Error deleting {filepath.name}: {e}")

        except Exception as e:
            self.logger.error(f"Error during size-based cleanup of archive directory: {e}")

        return archived_deleted, space_freed


class DirectoryWatcher(StateProvider):
    """Watcher for monitoring directories and compressing files."""

    def __init__(self, input_dir: Path, output_dir: Path, config: Config | None = None):
        """Initialize the directory watcher.

        Args:
            input_dir: Input directory to watch.
            output_dir: Output directory for compressed files.
            config: Optional Config object.
        """
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.config = config or Config()

        # Setup logging
        self.logger = setup_logging(self.config)

        # Register logger with system for consistent logging across all modules
        from .system import register_binary_finder, register_logger
        from .system.binaries import BinaryFinder

        register_logger(self.logger)
        register_binary_finder(BinaryFinder(self.config))

        # Verify directories
        if not self.input_dir.exists():
            raise ValueError(f"Input directory does not exist: {self.input_dir}")

        # Create output directory if needed
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Setup watcher
        self.event_handler = CompressionHandler(
            self.config, self.input_dir, self.output_dir, self.logger, self  # Pass watcher reference to handler
        )
        self.observer = Observer()
        self._running = False
        self._start_time = None
        self._completed_count = 0
        self._failed_count = 0
        self._processed_files = []  # List of ProcessedFile objects
        self._max_processed_files = 100  # Keep only last 100 processed files
        self._state_lock = threading.Lock()

        # Polling fallback mechanism (scan periodically to catch missed files)
        self._poll_interval = self.config.get("service.poll_interval", 300)  # Default: 5 minutes
        self._last_poll_time = 0

        # Initialize retention manager
        self._retention_manager = RetentionManager(self.config, self.output_dir, self.logger)

    def _add_processed_file(self, filename: str, success: bool):
        """Add a processed file to the tracking list (thread-safe).

        Args:
            filename: Name of the processed file.
            success: True if processing succeeded, False if failed.
        """
        from datetime import datetime

        with self._state_lock:
            # Create ProcessedFile with timestamp
            processed_file = ProcessedFile(filename=filename, timestamp=datetime.now().isoformat(), success=success)

            # Add to list
            self._processed_files.append(processed_file)

            # Keep only the most recent files
            if len(self._processed_files) > self._max_processed_files:
                self._processed_files = self._processed_files[-self._max_processed_files :]

            # Update counters
            if success:
                self._completed_count += 1
            else:
                self._failed_count += 1

    def get_state(self) -> ServiceState:
        """Get current service state (thread-safe).

        Returns:
            ServiceState: Immutable snapshot of current state.
        """
        with self._state_lock:
            # Calculate uptime
            uptime = timedelta()
            if self._start_time is not None:
                uptime = timedelta(seconds=time.time() - self._start_time)

            # Get processing files list (thread-safe copy)
            with self.event_handler._lock:
                processing = list(self.event_handler._processing)

            # Get cleanup stats from retention manager
            cleanup_stats = self._retention_manager.get_cleanup_stats()

            return ServiceState(
                running=self._running,
                input_dir=self.input_dir,
                output_dir=self.output_dir,
                processing_files=processing,
                processed_files=list(self._processed_files),  # Thread-safe copy
                completed_count=self._completed_count,
                failed_count=self._failed_count,
                uptime=uptime,
                cleanup_stats=cleanup_stats,
            )

    def start(self):
        """Start watching the directory."""
        self.observer.schedule(self.event_handler, str(self.input_dir), recursive=True)
        self.observer.start()
        self._running = True
        self._start_time = time.time()

        self.logger.info("=" * 60)
        self.logger.info("FileSqueeze Watch Mode Started")
        self.logger.info("=" * 60)
        self.logger.info(f"Watching: {self.input_dir}")
        self.logger.info(f"Output:  {self.output_dir}")
        self.logger.info("=" * 60)

        # Perform initial scan to catch any files that existed before service started
        self.logger.info("Performing initial scan for existing files...")
        self._scan_existing_files()

        # Start polling thread for periodic fallback scans
        if self._poll_interval > 0:
            self._start_polling_thread()

        # Start retention manager for periodic cleanup
        self._retention_manager.start()

        self.logger.info("=" * 60)
        self.logger.info("Press Ctrl+C to stop...")

    def stop(self):
        """Stop watching the directory."""
        if self._running:
            self._running = False

            # Stop retention manager
            self._retention_manager.stop()

            self.observer.stop()
            self.observer.join()
            self.logger.info("Watch mode stopped")

    def run(self):
        """Run the watcher until interrupted."""
        self.start()
        try:
            while self._running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.logger.info("Received stop signal, shutting down...")
            self.stop()

    def _scan_existing_files(self):
        """Scan for existing files that may have been missed.

        This catches:
        - Files that existed before the service started
        - Files that were added while service was down
        - Files missed by watchdog events
        """
        try:
            from .scanner import FileScanner

            scanner = FileScanner(self.config)

            file_count = 0
            for filepath in scanner.scan(self.input_dir):
                # Skip if already being processed
                file_key = str(filepath.absolute())
                with self.event_handler._lock:
                    if file_key in self.event_handler._processing:
                        continue

                # Check if this is truly an existing file (not just created)
                # Use file modification time to filter very recent files that watchdog might handle
                import time as time_module

                file_mtime = filepath.stat().st_mtime
                file_age = time_module.time() - file_mtime

                # Only process files older than 5 seconds (give watchdog a chance to handle new files)
                if file_age < 5:
                    self.logger.debug(f"Skipping recent file (watchdog may handle): {filepath.name}")
                    continue

                # Process the file
                file_count += 1
                self.logger.info(f"Found existing file: {filepath.name}")
                self.event_handler._process_file(filepath)

            if file_count > 0:
                self.logger.info(f"Initial scan processed {file_count} existing files")
            else:
                self.logger.info("No existing files found to process")

        except Exception as e:
            self.logger.error(f"Error during initial scan: {e}", exc_info=True)

    def _start_polling_thread(self):
        """Start background thread for periodic polling scans."""

        def poll_worker():
            while self._running:
                try:
                    time.sleep(self._poll_interval)
                    if self._running:
                        self.logger.debug("Running periodic poll scan...")
                        self._scan_existing_files()
                except Exception as e:
                    self.logger.error(f"Error in polling thread: {e}", exc_info=True)

        poll_thread = threading.Thread(target=poll_worker, daemon=True)
        poll_thread.start()
        self.logger.info(f"Periodic polling enabled (every {self._poll_interval}s)")
