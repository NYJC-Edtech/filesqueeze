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
        self._last_click_time = 0
        self._click_count = 0

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
        """Handle show status action - opens GUI status window.

        Args:
            icon: Tray icon instance.
            item: Menu item instance (for menu clicks) or event (for icon clicks).
        """
        self.logger.info("Opening status window")

        # Launch GUI status window in a separate thread
        # This prevents blocking the tray icon
        status_thread = threading.Thread(
            target=self._show_status_window,
            daemon=True
        )
        status_thread.start()

    def _on_icon_click(self, icon, button, pressed):
        """Handle icon click events - left-click opens status window.

        Args:
            icon: Tray icon instance.
            button: Mouse button that was clicked (left=1, right=3, etc.).
            pressed: Whether the button was pressed (True) or released (False).
        """
        # Only open status on left-click release (button=1, pressed=False)
        if button == 1 and not pressed:
            self.logger.info("Left-click detected, opening status window")
            status_thread = threading.Thread(
                target=self._show_status_window,
                daemon=True
            )
            status_thread.start()

    def _show_status_window(self):
        """Show the GUI status window.

        This runs in a separate thread to avoid blocking the tray icon.
        """
        try:
            from .gui import show_status_window

            # Show status window with 2-second refresh
            show_status_window(self.watcher, refresh_interval=2000)

        except Exception as e:
            self.logger.error(f"Failed to show status window: {e}", exc_info=True)

    def start(self):
        """Start the tray service."""
        self.logger.info("Starting FileSqueeze tray service")

        # Start the watcher in a separate thread
        watcher_thread = threading.Thread(target=self.watcher.start, daemon=True)
        watcher_thread.start()

        # Create tray icon
        icon_image = self._create_icon_image()

        # Create menu with default action (double-click activates first item)
        menu = pystray.Menu(
            pystray.MenuItem('Show Status', self._on_show_status, default=True),
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
