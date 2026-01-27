"""filesqueeze.tray

System tray icon for FileSqueeze service control.
"""

import signal
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
from .system import logger as system_logger

# App User Model ID for Windows to recognize this app consistently
APP_USER_MODEL_ID = "com.filesqueeze.app"


class TrayService:
    """FileSqueeze service with system tray icon."""

    def __init__(self, input_dir: Path, output_dir: Path, config: Optional[Config] = None):
        """Initialize the tray service.

        Args:
            input_dir: Input directory to watch.
            output_dir: Output directory for compressed files.
            config: Optional Config object.

        Raises:
            RuntimeError: If another FileSqueeze instance is already running.
        """
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.config = config or Config()
        self.logger = setup_logging(self.config)

        # Register logger with system for consistent logging
        from .system import register_logger
        register_logger(self.logger)

        # Enforce single instance on Windows
        if sys.platform == 'win32':
            self._ensure_single_instance()

        # Create watcher
        self.watcher = DirectoryWatcher(input_dir, output_dir, self.config)

        # Tray icon state
        self.icon = None
        self.running = False
        self._last_click_time = 0
        self._click_count = 0
        self._status_window = None  # Track the status window instance
        self._mutex = None  # Windows named mutex for single-instance enforcement

    def _ensure_single_instance(self):
        """Ensure only one FileSqueeze instance is running.

        Uses Windows named mutex to prevent multiple instances.

        Raises:
            RuntimeError: If another instance is already running.
        """
        import ctypes
        from ctypes import wintypes

        # Create a named mutex
        mutex_name = "Global\\FileSqueeze_SingleInstanceMutex"
        self._mutex = ctypes.windll.kernel32.CreateMutexW(
            None, True, mutex_name
        )

        if self._mutex == 0:
            # Failed to create mutex at all
            # Need to call GetLastError directly, not via ctypes.get_last_error()
            kernel32 = ctypes.windll.kernel32
            kernel32.GetLastError.restype = wintypes.DWORD
            error = kernel32.GetLastError()
            self.logger.error(f"Failed to create mutex: Error {error}")
            return

        # Check if mutex already existed
        # CreateMutexW sets GetLastError() to ERROR_ALREADY_EXISTS (183) if mutex existed
        # Note: Must call GetLastError directly, ctypes.get_last_error() doesn't work here
        ERROR_ALREADY_EXISTS = 183
        kernel32 = ctypes.windll.kernel32
        kernel32.GetLastError.restype = wintypes.DWORD
        last_error = kernel32.GetLastError()

        if last_error == ERROR_ALREADY_EXISTS:
            # Mutex already exists - another instance is running
            self.logger.error(
                "Another FileSqueeze instance is already running. "
                "Only one instance is allowed at a time."
            )
            raise RuntimeError(
                "FileSqueeze is already running. "
                "Check the system tray for the FileSqueeze icon. "
                "To stop it, right-click the tray icon and select 'Quit'."
            )

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
        import subprocess
        import os
        self.logger.info(f"Opening input folder: {self.input_dir}")
        if sys.platform == 'win32':
            os.startfile(str(self.input_dir))
        elif sys.platform == 'darwin':
            subprocess.run(['open', str(self.input_dir)])
        else:
            subprocess.run(['xdg-open', str(self.input_dir)])

    def _on_open_output(self, icon=None, item=None):
        """Handle open output folder action.

        Args:
            icon: Tray icon instance.
            item: Menu item instance.
        """
        import subprocess
        import os
        self.logger.info(f"Opening output folder: {self.output_dir}")
        if sys.platform == 'win32':
            os.startfile(str(self.output_dir))
        elif sys.platform == 'darwin':
            subprocess.run(['open', str(self.output_dir)])
        else:
            subprocess.run(['xdg-open', str(self.output_dir)])

    def _on_show_status(self, icon=None, item=None):
        """Handle show status action - opens GUI status window.

        Enforces singleton pattern: only one status window can exist.
        If window is already open, this method returns without doing anything.

        Args:
            icon: Tray icon instance.
            item: Menu item instance (for menu clicks) or event (for icon clicks).
        """
        # Singleton enforcement: Check if status window already exists
        if self._status_window is not None:
            self.logger.debug("Status window already open, ignoring duplicate request")
            return

        self.logger.info("Opening status window")

        # Launch GUI status window in a separate thread
        # This prevents blocking the tray icon
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
            from .gui import StatusWindow

            # Get refresh interval from config
            refresh_interval = self.config.get('gui.refresh_interval_ms', 2000) if self.config else 2000

            # CRITICAL: Create and store the window BEFORE showing it
            # This ensures _status_window is set immediately for singleton enforcement
            # even though window.show() will block on mainloop()
            self._status_window = StatusWindow(self.watcher, refresh_interval=refresh_interval)
            self._status_window.show()

            # After window closes, clear the reference so a new window can be opened
            self._status_window = None

        except Exception as e:
            self.logger.error(f"Failed to show status window: {e}", exc_info=True)
            # Clear the reference on error so user can try again
            self._status_window = None

    def start(self):
        """Start the tray service."""
        self.logger.info("Starting FileSqueeze tray service")

        # Set AppUserModelID for Windows to recognize this app consistently
        # This MUST be done before creating the tray icon for Windows to remember it
        # This helps Windows remember tray icon visibility settings across reboots
        if sys.platform == 'win32':
            try:
                import ctypes
                from ctypes import wintypes

                # Set the AppUserModelID for the current process
                # Windows uses this to identify applications and remember their settings
                SetCurrentProcessExplicitAppUserModelID = ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID
                SetCurrentProcessExplicitAppUserModelID.argtypes = [wintypes.LPCWSTR]
                # HRESULT is a 32-bit signed long (not available in wintypes)
                SetCurrentProcessExplicitAppUserModelID.restype = ctypes.c_long

                hr = SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)
                if hr == 0:  # S_OK
                    self.logger.info(f"Successfully set AppUserModelID: {APP_USER_MODEL_ID}")
                else:
                    self.logger.error(f"Failed to set AppUserModelID: HRESULT={hr} (0x{hr:X})")
            except Exception as e:
                self.logger.error(f"Exception setting AppUserModelID: {e}", exc_info=True)

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

        # Show a notification that the service has started
        self.icon.notify("FileSqueeze is running in the background. Look for the green 'FS' icon in your system tray.")

        # Automatically open status window on startup
        # This provides immediate visual feedback to users that the service is running
        self.logger.info("Opening status window on startup")
        self._on_show_status()

        # Run the icon (this blocks until quit)
        # Note: On Windows, Ctrl+C may not work due to Windows message loop.
        # Use the tray icon's Quit menu option to stop the service.
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
    """Run FileSqueeze as a service with system tray icon.

    Args:
        input_dir: Input directory to watch.
        output_dir: Output directory for compressed files.
        config: Optional Config object.
    """
    service = TrayService(input_dir, output_dir, config)
    service.start()
