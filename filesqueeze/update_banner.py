"""filesqueeze.update_banner

Shared update-UI widgets for the FileSqueeze windows, driven by a shared
:class:`~filesqueeze.updater.UpdateController`. The controller's worker
thread never touches Tk: the widgets poll ``snapshot()`` on the Tk main
thread via ``after()``.

- :class:`UpdateBanner` — the Compress dialog's "Update available" banner:
  hidden until a newer release is found, with Update now / Release notes,
  status text and cancel.
- :class:`AboutTab` — the Status window's About tab: current version, the
  "Check for updates" button, and an always-present Update Now button that
  stays greyed out until a newer release is found and no update is running.

When the install cannot self-update (dev checkout, or a release without a
published wheel), both widgets keep only the releases-page route and explain
why in their status text.
"""

import threading
import tkinter as tk
import webbrowser
from tkinter import ttk
from typing import Callable

from .config import Config
from .update_check import (
    MANUAL_CHECK_DISABLED,
    MANUAL_CHECK_ERROR,
    MANUAL_CHECK_UP_TO_DATE,
    MANUAL_CHECK_UPDATE_AVAILABLE,
    RELEASES_PAGE_URL,
    UpdateInfo,
    get_current_version,
    run_manual_check,
)
from .updater import (
    PHASE_CANCELLED,
    PHASE_DONE,
    PHASE_DOWNLOADING,
    PHASE_FAILED,
    PHASE_INSTALLING,
    PHASE_VERIFYING,
    PHASE_WAITING,
    UpdateController,
    UpdateProgress,
    can_self_update,
)

# Gold/red/green/gray tones shared with the rest of the FileSqueeze UI
_COLOR_AVAILABLE = "#B8860B"
_COLOR_INFO = "#555555"
_COLOR_OK = "#2E7D32"
_COLOR_ERROR = "#B22222"
_COLOR_MUTED = "#666666"

_TERMINAL_PHASES = (PHASE_DONE, PHASE_FAILED, PHASE_CANCELLED)


def _format_progress_text(snap: UpdateProgress) -> str:
    """Controller message with the download percentage appended, when known."""
    if snap.percent is None:
        return snap.message
    return f"{snap.message} ({snap.percent}%)"


class UpdateBanner(ttk.LabelFrame):
    """'Update available' banner: Update now / Release notes, progress, cancel."""

    POLL_INTERVAL_MS = 200

    def __init__(
        self,
        master: tk.Misc | None,
        controller: UpdateController,
        update_info: UpdateInfo | None = None,
        *,
        restart: bool = False,
        on_update_applied: Callable[[], None] | None = None,
    ):
        """Build the banner.

        Args:
            master: Parent widget.
            controller: The (usually shared) download/apply controller.
            update_info: The newer release to offer; None renders nothing until
                :meth:`set_update_info` fills it in.
            restart: Relaunch FileSqueeze after installing. Only enable this
                when ``on_update_applied`` is provided — the app must quit for
                the detached updater to take over (the tray service passes its
                stop method).
            on_update_applied: Called on the updater thread after the handoff.
        """
        super().__init__(master, text="Update available", padding="5")
        self.columnconfigure(0, weight=1)

        self._controller = controller
        self._update_info = update_info
        self._restart = restart and on_update_applied is not None
        self._on_update_applied = on_update_applied

        self._buttons_frame: ttk.Frame | None = None
        self._status_label: ttk.Label | None = None
        self._cancel_btn: ttk.Button | None = None

        if update_info is not None:
            self._build_widgets(update_info)

    # ------------------------------------------------------------- population

    def set_update_info(self, update_info: UpdateInfo | None) -> None:
        """Fill the banner with an update (after a late background check)."""
        if update_info is None:
            return
        self._update_info = update_info
        self._build_widgets(update_info)

    def _build_widgets(self, update_info: UpdateInfo) -> None:
        """(Re)build the banner contents; widgets already showing are replaced."""
        for child in self.winfo_children():
            child.destroy()

        message = f"FileSqueeze v{update_info.latest_version} is available (installed: v{update_info.current_version})."
        ttk.Label(self, text=message, font=("Helvetica", 9, "bold"), foreground=_COLOR_AVAILABLE).grid(
            row=0, column=0, sticky="w"
        )

        self._buttons_frame = ttk.Frame(self)
        self._buttons_frame.grid(row=0, column=1, padx=(10, 0), sticky="e")

        can_auto, _reason = can_self_update(update_info)
        if can_auto:
            ttk.Button(self._buttons_frame, text="Update now", command=self._on_update_now).pack(side="left", padx=(0, 5))
        ttk.Button(self._buttons_frame, text="Release notes", command=self._open_release_notes).pack(side="left")

        # Status row: gridded then removed so the grid options are remembered
        self._status_label = ttk.Label(self, text="", foreground=_COLOR_INFO)
        self._status_label.grid(row=1, column=0, columnspan=2, sticky="w", pady=(5, 0))
        self._status_label.grid_remove()

        self._cancel_btn = ttk.Button(self, text="Cancel", command=self._on_cancel_update)
        self._cancel_btn.grid(row=1, column=1, sticky="e", pady=(5, 0))
        self._cancel_btn.grid_remove()

        # Reflect an update the shared controller may already have in flight
        self._poll()

    # ---------------------------------------------------------------- actions

    def _on_update_now(self) -> None:
        """Start download+apply on the controller and poll it onto the widgets.

        The controller holds the handoff while app tasks are running (the tray
        wires its task gate into the controller), so "Update now" is always
        safe to click — the app quits only once tasks have finished.
        """
        if self._update_info is None:
            return
        self._controller.start(self._update_info, restart=self._restart, on_applied=self._on_update_applied)
        # Renders the fresh in-progress state, or why the update was refused /
        # where an already-running one stands
        self._poll()

    def _on_cancel_update(self) -> None:
        """Cancel a running download (only the download phase is cancellable)."""
        self._controller.cancel()
        if self._cancel_btn is not None:
            self._cancel_btn.state(["disabled"])

    def _open_release_notes(self) -> None:
        url = self._update_info.download_url if self._update_info else RELEASES_PAGE_URL
        webbrowser.open(url)

    # ---------------------------------------------------------------- polling

    def _poll(self) -> None:
        """Read the controller once and repaint; reschedules while in flight."""
        if not self.winfo_exists():
            return
        snap = self._controller.snapshot()
        if snap.phase == "idle":
            return
        self._render(snap)
        if self._controller.running or snap.phase not in _TERMINAL_PHASES:
            self.after(self.POLL_INTERVAL_MS, self._poll)

    def _render(self, snap: UpdateProgress) -> None:
        """Repaint the widgets for an update phase (Tk main thread only).

        Text-only by design: the release wheel is small and downloads in a
        flash, so a progress bar only flickers through its animation modes —
        the status label (with the percentage when the server reports a size)
        is the whole progress report.
        """
        label = self._status_label
        cancel = self._cancel_btn
        buttons = self._buttons_frame
        if label is None or cancel is None or buttons is None:
            return

        if snap.phase == PHASE_DOWNLOADING:
            buttons.grid_remove()
            label.grid()
            label.config(text=_format_progress_text(snap), foreground=_COLOR_INFO)
            cancel.state(["!disabled"])
            cancel.grid()
        elif snap.phase in (PHASE_VERIFYING, PHASE_WAITING, PHASE_INSTALLING):
            buttons.grid_remove()
            label.grid()
            label.config(text=snap.message, foreground=_COLOR_INFO)
            # Waiting is still cancellable — nothing has been handed off yet
            if snap.phase == PHASE_WAITING:
                cancel.state(["!disabled"])
                cancel.grid()
            else:
                cancel.grid_remove()
        elif snap.phase == PHASE_DONE:
            self._show_outcome(f"✓ {snap.message}", _COLOR_OK)
        elif snap.phase == PHASE_FAILED:
            self._show_outcome(snap.message, _COLOR_ERROR)
        elif snap.phase == PHASE_CANCELLED:
            self._show_outcome("Update cancelled.", _COLOR_MUTED)

    def _show_outcome(self, message: str, foreground: str) -> None:
        """Show a terminal state: message only, buttons back for retry."""
        if self._cancel_btn is None or self._status_label is None or self._buttons_frame is None:
            return
        self._cancel_btn.grid_remove()
        self._status_label.grid()
        self._status_label.config(text=message, foreground=foreground)
        self._buttons_frame.grid()


class UpdateWaitingDialog:
    """Buttonless notice: "FileSqueeze will close and update after all tasks complete."

    Shown by the tray when an update is verified but tasks (a running
    compression, a watched file mid-processing) delay the quit, so the user
    knows what is about to happen instead of the app vanishing later. There
    are deliberately no buttons — the update was already confirmed by the
    click that started it; the window closes itself when the update leaves
    the waiting state (applied → the process exits anyway; failed/cancelled →
    the banner is the place to retry from).
    """

    POLL_INTERVAL_MS = 500
    MESSAGE = "FileSqueeze will close and install the update after all tasks complete."

    def __init__(self, controller: UpdateController):
        self._controller = controller

        self.root = tk.Tk()
        self.root.title("FileSqueeze update")
        self.root.geometry("430x110")
        self.root.resizable(False, False)
        self.root.attributes("-topmost", True)

        frame = ttk.Frame(self.root, padding="20")
        frame.grid(row=0, column=0, sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        ttk.Label(frame, text=self.MESSAGE, wraplength=380, justify="center", font=("Helvetica", 10)).pack(expand=True)

        # Informational only: the window manager's close button just dismisses
        # the notice; it does not cancel the update (use the banner's Cancel).
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self._poll()

    def _poll(self) -> None:
        """Close once the update is no longer waiting (and the quit is near)."""
        if not self.root.winfo_exists():
            return
        phase = self._controller.snapshot().phase
        if phase not in (PHASE_WAITING, PHASE_DOWNLOADING, PHASE_VERIFYING, PHASE_INSTALLING):
            self.root.destroy()
            return
        self.root.after(self.POLL_INTERVAL_MS, self._poll)

    def _on_close(self) -> None:
        self.root.destroy()

    def show(self) -> None:
        """Run the dialog's event loop (blocks until closed)."""
        self.root.mainloop()

    def close(self) -> None:
        """Close the dialog programmatically."""
        try:
            self.root.destroy()
        except tk.TclError:
            pass


class AboutTab(ttk.Frame):
    """The Status window's About tab.

    Shows the running version, owns the "Check for updates" button, and keeps
    an always-present **Update Now** button that is greyed out unless a newer
    release has been found and no update is currently running — plus the
    latest version and a GitHub releases-page link once one is found. The
    update's progress is reported as text only (with a percentage while the
    server reports the download size) in the same section.

    Manual checks run off the Tk thread; found updates are surfaced here and
    reported through ``on_update_found`` so the tray can arm its menu item.
    """

    POLL_INTERVAL_MS = 200

    def __init__(
        self,
        master: tk.Misc | None,
        controller: UpdateController,
        config: Config | None = None,
        update_info: UpdateInfo | None = None,
        *,
        restart: bool = False,
        on_update_applied: Callable[[], None] | None = None,
        on_update_found: Callable[[UpdateInfo], None] | None = None,
        current_version: str | None = None,
    ):
        """Build the tab.

        Args:
            master: Parent widget (the window's notebook).
            controller: The (usually shared) download/apply controller.
            config: Config for the manual check's settings.
            update_info: A newer release already found (e.g. by the startup
                check); the tab renders it immediately.
            restart: Relaunch FileSqueeze after installing — only with
                ``on_update_applied`` (the tray passes its stop method).
            on_update_applied: Called on the updater thread after the handoff.
            on_update_found: Called with an UpdateInfo when the manual check
                finds a newer release (arms the tray menu item).
            current_version: Override for the displayed version (tests);
                defaults to the running version.
        """
        super().__init__(master, padding="10")
        self._controller = controller
        self._config = config
        self._update_info = update_info
        self._restart = restart and on_update_applied is not None
        self._on_update_applied = on_update_applied
        self._on_update_found = on_update_found
        self._current_version = current_version or get_current_version() or "unknown"
        self._manual_check_thread: threading.Thread | None = None
        self._manual_check_result: tuple | None = None

        self._build_widgets()
        self._render_update_state()
        if update_info is not None:
            self._poll()

    # ------------------------------------------------------------------ build

    def _build_widgets(self) -> None:
        """Lay out identity, the manual check, and the update section."""
        self.columnconfigure(0, weight=1)

        ttk.Label(self, text="FileSqueeze", font=("Helvetica", 16, "bold")).grid(row=0, column=0, sticky=tk.W)
        self._version_label = ttk.Label(self, text=f"Current version: v{self._current_version}", font=("Helvetica", 10))
        self._version_label.grid(row=1, column=0, sticky=tk.W, pady=(2, 14))

        check_row = ttk.Frame(self)
        check_row.grid(row=2, column=0, sticky=tk.W)
        self._check_btn = ttk.Button(check_row, text="Check for updates", command=self._on_check_updates)
        self._check_btn.pack(side=tk.LEFT)
        self._check_result_label = ttk.Label(check_row, text="", foreground=_COLOR_INFO, font=("Helvetica", 9))
        self._check_result_label.pack(side=tk.LEFT, padx=(10, 0))

        section = ttk.LabelFrame(self, text="Update", padding="10")
        section.grid(row=3, column=0, sticky="ew", pady=(14, 0))
        section.columnconfigure(0, weight=1)

        self._latest_label = ttk.Label(section, text="", font=("Helvetica", 10, "bold"), foreground=_COLOR_AVAILABLE)
        self._latest_label.grid(row=0, column=0, columnspan=2, sticky=tk.W)

        self._status_label = ttk.Label(section, text="", foreground=_COLOR_INFO, wraplength=430, justify=tk.LEFT)
        self._status_label.grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=(3, 8))

        buttons = ttk.Frame(section)
        buttons.grid(row=2, column=0, sticky=tk.W)
        self._release_notes_btn = ttk.Button(buttons, text="Release notes on GitHub", command=self._open_release_notes)
        self._release_notes_btn.pack(side=tk.LEFT, padx=(0, 8))
        self._update_now_btn = ttk.Button(buttons, text="Update Now", command=self._on_update_now)
        self._update_now_btn.pack(side=tk.LEFT)
        self._cancel_btn = ttk.Button(buttons, text="Cancel", command=self._on_cancel_update)
        self._cancel_btn.pack(side=tk.LEFT, padx=(8, 0))
        self._cancel_btn.pack_forget()

    # ---------------------------------------------------------------- actions

    def _on_check_updates(self) -> None:
        """Run a fresh (uncached) update check off the Tk thread."""
        if self._manual_check_thread is not None and self._manual_check_thread.is_alive():
            return

        self._check_btn.state(["disabled"])
        self._check_result_label.config(text="Checking for updates…", foreground=_COLOR_INFO)

        def _check() -> None:
            try:
                self._manual_check_result = run_manual_check(self._config)
            except Exception:
                self._manual_check_result = (MANUAL_CHECK_ERROR, None)

        self._manual_check_thread = threading.Thread(target=_check, name="manual-update-check", daemon=True)
        self._manual_check_thread.start()
        self.after(self.POLL_INTERVAL_MS, self._poll_manual_check)

    def _poll_manual_check(self) -> None:
        """Collect the manual check result and update the UI (Tk main thread)."""
        if not self.winfo_exists():
            return
        if self._manual_check_thread is not None and self._manual_check_thread.is_alive():
            self.after(self.POLL_INTERVAL_MS, self._poll_manual_check)
            return

        result = self._manual_check_result
        self._manual_check_result = None
        self._manual_check_thread = None
        self._check_btn.state(["!disabled"])
        if result is None:
            return

        status, info = result
        if status == MANUAL_CHECK_UPDATE_AVAILABLE and info is not None:
            self._check_result_label.config(text=f"Update found: v{info.latest_version}", foreground=_COLOR_AVAILABLE)
            self.set_update_info(info)
            if self._on_update_found is not None:
                try:
                    self._on_update_found(info)
                except Exception:
                    pass
        elif status == MANUAL_CHECK_UP_TO_DATE:
            self._check_result_label.config(text="You're up to date.", foreground=_COLOR_OK)
        elif status == MANUAL_CHECK_DISABLED:
            self._check_result_label.config(text="Update checks are disabled in the configuration.", foreground=_COLOR_MUTED)
        else:
            self._check_result_label.config(text="Couldn't reach GitHub — check the connection.", foreground=_COLOR_ERROR)

    def set_update_info(self, update_info: UpdateInfo | None) -> None:
        """Show a found update (startup result or a fresh manual check)."""
        if update_info is None:
            return
        self._update_info = update_info
        self._render_update_state()
        self._poll()

    def _on_update_now(self) -> None:
        """Start download+apply on the controller and poll it onto the widgets.

        The controller holds the handoff while app tasks are running (the tray
        wires its task gate into the controller), so "Update Now" is always
        safe to click — the app quits only once tasks have finished.
        """
        if self._update_info is None:
            return
        self._controller.start(self._update_info, restart=self._restart, on_applied=self._on_update_applied)
        self._render_update_state()
        self._poll()

    def _on_cancel_update(self) -> None:
        """Cancel a running download (only the download/waiting phase is cancellable)."""
        self._controller.cancel()
        self._cancel_btn.state(["disabled"])

    def _open_release_notes(self) -> None:
        url = self._update_info.download_url if self._update_info else RELEASES_PAGE_URL
        webbrowser.open(url)

    # ---------------------------------------------------------------- polling

    def _poll(self) -> None:
        """Read the controller once and repaint; reschedules while in flight."""
        if not self.winfo_exists():
            return
        snap = self._controller.snapshot()
        if snap.phase == "idle":
            return
        self._render_update_state()
        if self._controller.running or snap.phase not in _TERMINAL_PHASES:
            self.after(self.POLL_INTERVAL_MS, self._poll)

    # --------------------------------------------------------------- rendering

    def _render_update_state(self) -> None:
        """Repaint the update section from (update_info, controller state)."""
        snap = self._controller.snapshot()
        found = self._update_info is not None

        if found:
            self._latest_label.config(text=f"Latest version: v{self._update_info.latest_version}")
            self._latest_label.grid()
        else:
            self._latest_label.config(text="")
            self._latest_label.grid_remove()

        message = ""
        color = _COLOR_INFO
        update_now_enabled = False
        cancel_visible = False

        if snap.phase in (PHASE_DOWNLOADING, PHASE_VERIFYING, PHASE_WAITING, PHASE_INSTALLING):
            message = _format_progress_text(snap)
            cancel_visible = snap.phase in (PHASE_DOWNLOADING, PHASE_WAITING)
        elif snap.phase == PHASE_DONE:
            message = snap.message
            color = _COLOR_OK
        elif snap.phase == PHASE_FAILED:
            message = snap.message
            color = _COLOR_ERROR
            update_now_enabled = found
        elif snap.phase == PHASE_CANCELLED:
            message = "Update cancelled."
            color = _COLOR_MUTED
            update_now_enabled = found
        elif self._update_info is not None:
            can_auto, reason = can_self_update(self._update_info)
            if can_auto:
                message = f"FileSqueeze v{self._update_info.latest_version} is available — click “Update Now” to install."
                color = _COLOR_AVAILABLE
                update_now_enabled = True
            else:
                # Dev checkout or a release without a wheel: keep the button
                # greyed out and say why
                message = reason
                color = _COLOR_MUTED

        self._update_now_btn.state(["!disabled"] if update_now_enabled else ["disabled"])
        self._status_label.config(text=message, foreground=color)

        if cancel_visible:
            self._cancel_btn.state(["!disabled"])
            self._cancel_btn.pack()
        else:
            self._cancel_btn.pack_forget()
