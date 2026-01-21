"""filesqueeze.service

Service mode for watching directories and compressing files.
"""

import os
import sys
import time
import logging
import threading
from pathlib import Path
from typing import Optional

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent, FileMovedEvent

from .config import Config
from .logger import setup_logging


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

            self.logger.info(f"Detected new file: {filepath.name}")

            # Determine file type
            ext = filepath.suffix.lstrip('.').lower()

            # Generate output path with compressed_ prefix
            output_filename = f"compressed_{filepath.name}"
            output_path = self.output_dir / output_filename

            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)

            self.logger.info(f"Compressing {ext.upper()} file: {filepath.name}")

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


class DirectoryWatcher:
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

    def start(self):
        """Start watching the directory."""
        self.observer.schedule(self.event_handler, str(self.input_dir), recursive=True)
        self.observer.start()
        self._running = True

        self.logger.info("=" * 60)
        self.logger.info("FileSqueeze Watch Mode Started")
        self.logger.info("=" * 60)
        self.logger.info(f"Watching: {self.input_dir}")
        self.logger.info(f"Output:  {self.output_dir}")
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
            print("\nReceived stop signal, shutting down...")
            self.stop()
