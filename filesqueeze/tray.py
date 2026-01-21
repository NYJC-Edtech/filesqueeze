"""filesqueeze.tray

System tray icon for FileSqueeze service control.
"""

import sys
import threading
import time
from pathlib import Path
from typing import Optional

import pystray
from PIL import Image, ImageDraw

from .config import Config
from .logger import setup_logging
from .service import DirectoryWatcher


class TrayService:
    """FileSqueeze service with system tray icon."""

    def __init__(self, input_dir: Path, output_dir: Path, config: Optional[Config] = None):
        """Initialize the tray service.

        Args:
            input_dir: Input directory to watch.
            output_dir: Output directory for compressed files.
            config: Optional Config object.
        """
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.config = config or Config()
        self.logger = setup_logging(self.config)

        # Create watcher
        self.watcher = DirectoryWatcher(input_dir, output_dir, self.config)

        # Tray icon state
        self.icon = None
        self.running = False

    def _create_icon_image(self) -> Image.Image:
        """Create a simple icon image.

        Returns:
            PIL Image object.
        """
        # Create a simple icon (green circle)
        size = 64
        image = Image.new('RGB', (size, size), 'white')
        draw = ImageDraw.Draw(image)

        # Draw a green circle
        draw.ellipse([(8, 8), (size - 8, size - 8)], fill='green', outline='darkgreen')

        # Draw "FS" text
        draw.text((20, 20), "FS", fill='white')

        return image

    def _on_quit(self, icon=None, item=None):
        """Handle quit action.

        Args:
            icon: Tray icon instance.
            item: Menu item instance.
        """
        self.logger.info("Quit requested from tray icon")
        self.stop()

    def _on_toggle_pause(self, icon=None, item=None):
        """Handle pause/resume action.

        Args:
            icon: Tray icon instance.
            item: Menu item instance.
        """
        if self.watcher._running:
            self.logger.info("Pausing watcher")
            self.watcher.stop()
            # Update menu to show "Resume" option
        else:
            self.logger.info("Resuming watcher")
            self.watcher.start()
            # Update menu to show "Pause" option

    def _on_open_input(self, icon=None, item=None):
        """Handle open input folder action.

        Args:
            icon: Tray icon instance.
            item: Menu item instance.
        """
        import os
        import subprocess
        import platform

        self.logger.info(f"Opening input folder: {self.input_dir}")

        try:
            if platform.system() == 'Windows':
                os.startfile(str(self.input_dir))
            elif platform.system() == 'Darwin':  # macOS
                subprocess.run(['open', str(self.input_dir)])
            else:  # Linux
                subprocess.run(['xdg-open', str(self.input_dir)])
        except Exception as e:
            self.logger.error(f"Failed to open input folder: {e}")

    def _on_open_output(self, icon=None, item=None):
        """Handle open output folder action.

        Args:
            icon: Tray icon instance.
            item: Menu item instance.
        """
        import os
        import subprocess
        import platform

        self.logger.info(f"Opening output folder: {self.output_dir}")

        try:
            if platform.system() == 'Windows':
                os.startfile(str(self.output_dir))
            elif platform.system() == 'Darwin':  # macOS
                subprocess.run(['open', str(self.output_dir)])
            else:  # Linux
                subprocess.run(['xdg-open', str(self.output_dir)])
        except Exception as e:
            self.logger.error(f"Failed to open output folder: {e}")

    def _on_show_status(self, icon=None, item=None):
        """Handle show status action.

        Args:
            icon: Tray icon instance.
            item: Menu item instance.
        """
        status_text = f"""FileSqueeze Status

Watching: {self.input_dir}
Output:  {self.output_dir}
State:   {'Running' if self.watcher._running else 'Stopped'}

Files being processed: {len(self.watcher.event_handler._processing)}
"""
        self.logger.info(status_text)

        # Update icon tooltip with status
        if icon:
            icon.title = f"FileSqueeze - {'Running' if self.watcher._running else 'Stopped'}\nWatching: {self.input_dir.name}\nProcessing: {len(self.watcher.event_handler._processing)} files"

        # Show non-blocking notification
        try:
            if icon:
                icon.notify(f"State: {'Running' if self.watcher._running else 'Stopped'}\nProcessing: {len(self.watcher.event_handler._processing)} files", "FileSqueeze Status")
        except:
            # If notification fails, just log it
            pass

    def start(self):
        """Start the tray service."""
        self.logger.info("Starting FileSqueeze tray service")

        # Start the watcher in a separate thread
        watcher_thread = threading.Thread(target=self.watcher.start, daemon=True)
        watcher_thread.start()

        # Create tray icon
        icon_image = self._create_icon_image()

        # Create menu
        menu = pystray.Menu(
            pystray.MenuItem('Show Status', self._on_show_status),
            pystray.MenuItem('Open Input Folder', self._on_open_input),
            pystray.MenuItem('Open Output Folder', self._on_open_output),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem('Quit', self._on_quit),
        )

        # Create and run icon
        self.icon = pystray.Icon("filesqueeze", icon_image, "FileSqueeze", menu)
        self.running = True

        self.logger.info("Tray icon started")

        # Run the icon (this blocks until quit)
        self.icon.run()

    def stop(self):
        """Stop the tray service."""
        if self.running:
            self.running = False
            self.watcher.stop()
            if self.icon:
                self.icon.stop()
            self.logger.info("Tray service stopped")


def run_service(input_dir: Path, output_dir: Path, config: Optional[Config] = None):
    """Run FileSqueeze as a service with tray icon.

    Args:
        input_dir: Input directory to watch.
        output_dir: Output directory for compressed files.
        config: Optional Config object.
    """
    service = TrayService(input_dir, output_dir, config)
    service.start()
