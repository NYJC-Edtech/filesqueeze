"""filesqueeze.service

Service mode for watching directories and compressing files.
"""

import os
import sys
import time
import logging
import threading
from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path
from typing import Optional, List

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent, FileMovedEvent

from .config import Config
from .logger import setup_logging


@dataclass(frozen=True)
class ServiceState:
    """Immutable snapshot of service state.

    This dataclass provides a read-only snapshot of the service's current state,
    perfect for GUI display and status queries. It's frozen to ensure immutability.
    """
    running: bool
    input_dir: Path
    output_dir: Path
    processing_files: List[str] = field(default_factory=list)
    completed_count: int = 0
    failed_count: int = 0
    uptime: timedelta = field(default_factory=timedelta)


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
        if sys.platform != 'win32':
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

            ps_command = f'''
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
            '''

            # Run PowerShell in background, don't wait for it
            subprocess.Popen(
                ['powershell', '-Command', ps_command],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            return True

        except Exception as e:
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

    def __init__(self, config: Config, input_dir: Path, output_dir: Path, logger: logging.Logger):
        """Initialize the compression handler.

        Args:
            config: Config object.
            input_dir: Input directory to watch.
            output_dir: Output directory for compressed files.
            logger: Logger instance.
        """
        self.config = config
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.logger = logger
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
            from .scanner import FileScanner
            from . import make_video, make_pdf, make_image

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
            ext = filepath.suffix.lstrip('.').lower()

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
                filename=filepath.name
            )

            try:
                # Process file based on type
                if ext in ['mp4', 'wmv', 'avi', 'mkv', 'mov', 'flv']:
                    result_path = make_video(str(filepath), config=self.config, output_path=str(output_path))
                elif ext == 'pdf':
                    result_path = make_pdf(str(filepath), config=self.config, output_path=str(output_path))
                elif ext in ['jpg', 'jpeg', 'png']:
                    result_path = make_image(str(filepath), config=self.config, output_path=str(output_path))
                elif ext in ['ppt', 'pptx']:
                    self.logger.warning(f"PowerPoint files not yet supported: {filepath.name}")
                    return
                else:
                    self.logger.warning(f"Unsupported file type: {ext}")
                    return

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
                        self.logger.info(f"  Note: Output is larger")

                    # Show Windows notification for successful completion
                    # Include filename to replace the previous "compressing" notification
                    show_windows_notification(
                        "FileSqueeze - Complete!",
                        f"Successfully compressed: {filepath.name}\n\n"
                        f"Input:  {input_size / 1024 / 1024:.2f} MB\n"
                        f"Output: {output_size / 1024 / 1024:.2f} MB\n"
                        f"Saved:  {reduction:.1f}%",
                        filename=filepath.name
                    )

                    # Clear the notification tag for this file
                    _notification_manager.clear(filepath.name)

                    # Remove original file
                    filepath.unlink()
                    self.logger.info(f"Removed original file: {filepath.name}")

                else:
                    self.logger.error(f"Output file not created: {result_path}")

            except Exception as e:
                self.logger.error(f"Failed to compress {filepath.name}: {e}", exc_info=True)
                # Keep original file in place (as per requirements)

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


class DirectoryWatcher(StateProvider):
    """Watcher for monitoring directories and compressing files."""

    def __init__(self, input_dir: Path, output_dir: Path, config: Optional[Config] = None):
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

        # Verify directories
        if not self.input_dir.exists():
            raise ValueError(f"Input directory does not exist: {self.input_dir}")

        # Create output directory if needed
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Setup watcher
        self.event_handler = CompressionHandler(
            self.config,
            self.input_dir,
            self.output_dir,
            self.logger
        )
        self.observer = Observer()
        self._running = False
        self._start_time = None
        self._completed_count = 0
        self._failed_count = 0
        self._state_lock = threading.Lock()

        # Polling fallback mechanism (scan periodically to catch missed files)
        self._poll_interval = self.config.get('service.poll_interval', 300)  # Default: 5 minutes
        self._last_poll_time = 0

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

            return ServiceState(
                running=self._running,
                input_dir=self.input_dir,
                output_dir=self.output_dir,
                processing_files=processing,
                completed_count=self._completed_count,
                failed_count=self._failed_count,
                uptime=uptime
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

        self.logger.info("=" * 60)
        self.logger.info("Press Ctrl+C to stop...")

    def stop(self):
        """Stop watching the directory."""
        if self._running:
            self._running = False
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

    def run(self):
        """Run the watcher until interrupted."""
        self.start()
        try:
            while self._running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.logger.info("Received stop signal, shutting down...")
            self.stop()
