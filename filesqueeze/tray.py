"""filesqueeze.tray

System tray icon for FileSqueeze service control.
"""

import sys
import threading
from pathlib import Path

import pystray
from PIL import Image, ImageDraw

from .config import Config
from .logger import setup_logging
from .service import DirectoryWatcher
from .update_check import (
    MANUAL_CHECK_DISABLED,
    MANUAL_CHECK_UP_TO_DATE,
    MANUAL_CHECK_UPDATE_AVAILABLE,
    UpdateInfo,
    check_for_updates,
    get_current_version,
    run_manual_check,
)
from .updater import UpdateController

# App User Model ID for Windows to recognize this app consistently
APP_USER_MODEL_ID = "com.filesqueeze.app"


class TrayService:
    """FileSqueeze service with system tray icon."""

    def __init__(self, input_dir: Path, output_dir: Path, config: Config | None = None):
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
        if sys.platform == "win32":
            self._ensure_single_instance()

        # Create watcher
        self.watcher = DirectoryWatcher(input_dir, output_dir, self.config)

        # Tray icon state
        self.icon = None
        self.running = False
        self._last_click_time = 0
        self._click_count = 0
        self._status_window = None  # Track the status window instance
        self._compress_dialog = None  # Track the standalone compress dialog instance
        self._mutex = None  # Windows named mutex for single-instance enforcement
        self._update_info: UpdateInfo | None = None  # Newer release found at startup, if any
        self._manual_check_running = False  # A user-requested check is in flight
        # Shared download/apply controller: the tray menu, status window and
        # compress dialog all show the same in-flight update through it
        self._update_controller = UpdateController(config=self.config)

    def _ensure_single_instance(self):
        """Ensure only one FileSqueeze instance is running per mode.

        Uses different mutexes for development/testing vs. production to allow
        development on a machine where FileSqueeze runs in production.

        Development modes: pytest session, FILEQUEEZE_DEV_MODE=1
        Production mode: normal user launch

        Raises:
            RuntimeError: If another instance of the same mode is already running.
        """
        import ctypes
        import os
        from ctypes import wintypes

        # Check if running in development/testing mode
        is_development = (
            os.getenv("PYTEST_CURRENT_TEST") is not None  # Running in pytest
            or os.getenv("FILEQUEEZE_DEV_MODE") == "1"  # Explicit dev mode
        )

        # Use different mutexes for dev vs. production
        if is_development:
            mutex_name = "Global\\FileSqueeze_DevInstance_Mutex"
        else:
            mutex_name = "Global\\FileSqueeze_SingleInstanceMutex"

        self._mutex = ctypes.windll.kernel32.CreateMutexW(None, True, mutex_name)

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
            self.logger.warning("Another FileSqueeze instance is already running. Only one instance is allowed at a time.")
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
        image = Image.new("RGB", (size, size), "white")
        draw = ImageDraw.Draw(image)

        # Draw a green circle
        draw.ellipse([(8, 8), (size - 8, size - 8)], fill="green", outline="darkgreen")

        # Draw "FS" text
        draw.text((20, 20), "FS", fill="white")

        return image

    def _on_quit(self, icon: object = None, item: object = None):
        """Handle quit action.

        Args:
            icon: Tray icon instance.
            item: Menu item instance.
        """
        self.logger.info("Quit requested from tray icon")
        self.stop()

    def _on_toggle_pause(self, icon: object = None, item: object = None):
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

    def _on_open_input(self, icon: object = None, item: object = None):
        """Handle open input folder action.

        Args:
            icon: Tray icon instance.
            item: Menu item instance.
        """
        import os
        import subprocess

        self.logger.info(f"Opening input folder: {self.input_dir}")
        if sys.platform == "win32":
            os.startfile(str(self.input_dir))
        elif sys.platform == "darwin":
            subprocess.run(["open", str(self.input_dir)])
        else:
            subprocess.run(["xdg-open", str(self.input_dir)])

    def _on_open_output(self, icon: object = None, item: object = None):
        """Handle open output folder action.

        Args:
            icon: Tray icon instance.
            item: Menu item instance.
        """
        import os
        import subprocess

        self.logger.info(f"Opening output folder: {self.output_dir}")
        if sys.platform == "win32":
            os.startfile(str(self.output_dir))
        elif sys.platform == "darwin":
            subprocess.run(["open", str(self.output_dir)])
        else:
            subprocess.run(["xdg-open", str(self.output_dir)])

    def _on_show_status(self, icon: object = None, item: object = None):
        """Handle show status action - opens GUI status window.

        Enforces singleton pattern: only one status window can exist.
        If window is already open but not focused, brings it to the foreground.

        Args:
            icon: Tray icon instance.
            item: Menu item instance (for menu clicks) or event (for icon clicks).
        """
        # If window already exists, bring it to the foreground
        if self._status_window is not None:
            self.logger.debug("Status window already open, bringing to foreground")
            try:
                # Use after() to schedule UI operations on the Tkinter main thread
                self._status_window.root.after(0, self._bring_to_foreground, self._status_window.root)
            except Exception as e:
                self.logger.error(f"Failed to bring window to foreground: {e}", exc_info=True)
            return

        self.logger.info("Opening status window")

        # Launch GUI status window in a separate thread
        # This prevents blocking the tray icon
        status_thread = threading.Thread(target=self._show_status_window, daemon=True)
        status_thread.start()

    def _bring_to_foreground(self, root_window: object):
        """Bring a Tkinter window to the foreground.

        This method must be called from the Tkinter main thread using after().
        It restores a minimized window, brings it to the top, and forces focus.

        Args:
            root_window: The Tkinter root window to bring to foreground.
        """
        try:
            # Restore if minimized
            root_window.deiconify()  # type: ignore[attr-defined]

            # Bring window to the top of the stacking order
            root_window.lift()  # type: ignore[attr-defined]

            # Force the window to be on top of all other windows
            root_window.attributes("-topmost", True)  # type: ignore[attr-defined]
            root_window.after_idle(root_window.attributes, "-topmost", False)  # type: ignore[attr-defined]

            # Force focus on the window
            root_window.focus_force()  # type: ignore[attr-defined]

            self.logger.debug("Window brought to foreground successfully")
        except Exception as e:
            self.logger.error(f"Error bringing window to foreground: {e}", exc_info=True)

    def _show_status_window(self):
        """Show the GUI status window.

        This runs in a separate thread to avoid blocking the tray icon.
        """
        try:
            from .gui import StatusWindow

            # Get refresh interval from config
            refresh_interval = self.config.get("gui.refresh_interval_ms", 2000) if self.config else 2000

            # CRITICAL: Create and store the window BEFORE showing it
            # This ensures _status_window is set immediately for singleton enforcement
            # even though window.show() will block on mainloop()
            self._status_window = StatusWindow(
                self.watcher,
                refresh_interval=refresh_interval,
                update_info=self._update_info,
                update_controller=self._update_controller,
                on_update_applied=self._quit_for_update,
                on_update_found=self._on_update_found,
            )
            self._status_window.show()

            # After window closes, clear the reference so a new window can be opened
            self._status_window = None

        except Exception as e:
            self.logger.error(f"Failed to show status window: {e}", exc_info=True)
            # Clear the reference on error so user can try again
            self._status_window = None

    def _on_compress_file(self, icon: object = None, item: object = None):
        """Handle 'Compress a File' action - opens the standalone compress dialog.

        Enforces the same singleton pattern as the status window: only one
        compress dialog can exist; clicking again brings it to the foreground.

        Args:
            icon: Tray icon instance.
            item: Menu item instance.
        """
        if self._compress_dialog is not None:
            self.logger.debug("Compress dialog already open, bringing to foreground")
            try:
                self._compress_dialog.root.after(0, self._bring_to_foreground, self._compress_dialog.root)
            except Exception as e:
                self.logger.error(f"Failed to bring compress dialog to foreground: {e}", exc_info=True)
            return

        self.logger.info("Opening compress dialog")

        # Launch the dialog in a separate thread so the tray icon stays responsive
        dialog_thread = threading.Thread(target=self._show_compress_dialog, daemon=True)
        dialog_thread.start()

    def _show_compress_dialog(self):
        """Show the standalone compress dialog.

        This runs in a separate thread to avoid blocking the tray icon.
        """
        try:
            from .gui_compress import CompressDialog

            # Store the dialog BEFORE show() blocks on mainloop(), so the
            # singleton check works while the dialog is open
            self._compress_dialog = CompressDialog(
                config=self.config,
                update_info=self._update_info,
                update_controller=self._update_controller,
                on_update_applied=self._quit_for_update,
            )
            self._compress_dialog.show()

            # After the dialog closes, allow a new one to be opened
            self._compress_dialog = None

        except Exception as e:
            self.logger.error(f"Failed to show compress dialog: {e}", exc_info=True)
            self._compress_dialog = None

    def _update_menu_text(self, item: object = None) -> str:
        """Dynamic tray menu label for the update item (re-evaluated on menu open)."""
        if self._update_info is None:
            return "Update"
        version = self._update_info.latest_version
        if self._update_controller.running:
            percent = self._update_controller.snapshot().percent
            if percent is not None:
                return f"Updating to v{version}… {percent}%"
            return f"Updating to v{version}…"
        return f"Update to v{version} now"

    def _on_update_now(self, icon: object = None, item: object = None):
        """Handle 'Update now' - download and apply the newer release, then restart.

        The download runs on the updater's background thread; once applied, a
        detached updater installs the wheel after this process exits and
        relaunches the service (see filesqueeze.updater).
        """
        if self._update_info is None:
            return

        if self._update_controller.running:
            self.icon.notify(self._update_controller.snapshot().message or "Update in progress…", title="FileSqueeze update")
            return

        if self._compress_dialog is not None and self._compress_dialog.is_compressing:
            # Quitting mid-compression would drop the user's file; the update
            # stays available once the compression finishes
            self.icon.notify("A compression is running — wait for it to finish before updating.", title="FileSqueeze update")
            return

        version = self._update_info.latest_version
        started = self._update_controller.start(self._update_info, restart=True, on_applied=self._quit_for_update)
        if started:
            self.logger.info(f"Update to v{version} requested from tray menu")
            self.icon.notify(
                f"Downloading FileSqueeze v{version}… FileSqueeze will restart when done.", title="Updating FileSqueeze"
            )
        else:
            # Refused (dev checkout, or release without a wheel): surface why
            reason = self._update_controller.snapshot().message
            self.logger.info(f"Automatic update not available: {reason}")
            self.icon.notify(reason, title="FileSqueeze update")

    def _quit_for_update(self):
        """Stop the service so the detached updater can install and relaunch.

        Runs on the updater thread once the handoff is in place. Quitting
        releases the single-instance mutex and closes the package files the
        detached updater needs to replace.
        """
        self.logger.info("Update applied — stopping FileSqueeze; it will restart into the new version")
        self.stop()

    def _on_update_found(self, info: UpdateInfo):
        """Store a freshly found update so the menu item and windows surface it.

        Safe to call from any thread: it only assigns an attribute and logs.
        """
        self._update_info = info
        self.logger.info(f"Update available: v{info.latest_version} (installed: v{info.current_version})")

    def _on_check_for_updates_now(self, icon: object = None, item: object = None):
        """Handle 'Check for updates' - run a fresh (uncached) check off the menu thread.

        Args:
            icon: Tray icon instance.
            item: Menu item instance.
        """
        if self._manual_check_running:
            self.icon.notify("An update check is already running…", title="FileSqueeze update check")
            return
        self._manual_check_running = True
        threading.Thread(target=self._run_manual_check, name="manual-update-check", daemon=True).start()

    def _run_manual_check(self):
        """Run the manual check and show its outcome as a tray notification.

        Unlike the silent startup check, a user-requested check reports every
        outcome: up to date, offline/error, disabled, or a found update (which
        also arms the 'Update to vX now' menu item and window banners).
        """
        try:
            status, info = run_manual_check(self.config)
            if status == MANUAL_CHECK_UPDATE_AVAILABLE and info is not None:
                self._on_update_found(info)
                message = (
                    f"FileSqueeze v{info.latest_version} is available (installed: v{info.current_version}). "
                    f"Choose 'Update to v{info.latest_version} now' to install it."
                )
            elif status == MANUAL_CHECK_UP_TO_DATE:
                current = get_current_version()
                message = f"FileSqueeze v{current} is up to date."
            elif status == MANUAL_CHECK_DISABLED:
                message = "Update checks are disabled in the configuration."
            else:
                message = "Could not check for updates — is this machine online?"
            self.icon.notify(message, title="FileSqueeze update check")
        except Exception as e:
            self.logger.warning(f"Manual update check failed: {e}", exc_info=True)
            try:
                self.icon.notify("Could not check for updates.", title="FileSqueeze update check")
            except Exception:
                self.logger.warning("Could not show manual-check failure notification", exc_info=True)
        finally:
            self._manual_check_running = False

    def _check_for_updates(self):
        """Check GitHub for a newer release; runs on a background thread.

        Never raises: on any failure the service simply runs without an
        update notification. When a newer release is found, the result is
        stored (surfacing the dynamic tray menu item and GUI banners) and a
        tray notification is shown.
        """
        try:
            info = check_for_updates(self.config)
        except Exception as e:
            self.logger.warning(f"Update check failed: {e}", exc_info=True)
            return

        if info is None:
            self.logger.debug("No newer FileSqueeze release found (or update check disabled)")
            return

        self._on_update_found(info)

        try:
            self.icon.notify(
                f"FileSqueeze v{info.latest_version} is available (installed: v{info.current_version}). "
                "Right-click the tray icon and choose 'Update now' to install it.",
                title="FileSqueeze update available",
            )
        except Exception as e:
            self.logger.warning(f"Could not show update notification: {e}", exc_info=True)

    def start(self) -> None:
        """Start the tray service."""
        self.logger.info("Starting FileSqueeze tray service")

        # Set AppUserModelID for Windows to recognize this app consistently
        # This MUST be done before creating the tray icon for Windows to remember it
        # This helps Windows remember tray icon visibility settings across reboots
        if sys.platform == "win32":
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
            pystray.MenuItem("Show Status", self._on_show_status, default=True),
            pystray.MenuItem("Compress a File…", self._on_compress_file),
            pystray.MenuItem("Open Input Folder", self._on_open_input),
            pystray.MenuItem("Open Output Folder", self._on_open_output),
            pystray.MenuItem("Check for updates", self._on_check_for_updates_now),
            # Hidden until the startup update check finds a newer release;
            # pystray re-evaluates the dynamic text/visibility each time the
            # menu is opened. Clicking downloads, installs and restarts.
            pystray.MenuItem(
                self._update_menu_text,
                self._on_update_now,
                visible=lambda item: self._update_info is not None,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit", self._on_quit),
        )

        # Create and run icon
        self.icon = pystray.Icon("filesqueeze", icon_image, "FileSqueeze", menu)
        self.running = True

        self.logger.info("Tray icon started")

        # Show a notification that the service has started
        self.icon.notify("FileSqueeze is running in the background. Look for the green 'FS' icon in your system tray.")

        # Check GitHub for a newer release in the background; on success this
        # stores _update_info (enabling the tray menu item) and notifies the user
        update_thread = threading.Thread(target=self._check_for_updates, name="update-check", daemon=True)
        update_thread.start()

        # Automatically open status window on startup
        # This provides immediate visual feedback to users that the service is running
        self.logger.info("Opening status window on startup")
        self._on_show_status()

        # Run the icon (this blocks until quit)
        # Note: On Windows, Ctrl+C may not work due to Windows message loop.
        # Use the tray icon's Quit menu option to stop the service.
        self.icon.run()

    def stop(self) -> None:
        """Stop the tray service."""
        if self.running:
            self.running = False
            self.watcher.stop()
            if self.icon:
                self.icon.stop()
            self.logger.info("Tray service stopped")


def run_service(input_dir: Path, output_dir: Path, config: Config | None = None) -> None:
    """Run FileSqueeze as a service with system tray icon.

    Args:
        input_dir: Input directory to watch.
        output_dir: Output directory for compressed files.
        config: Optional Config object.
    """
    service = TrayService(input_dir, output_dir, config)
    service.start()
