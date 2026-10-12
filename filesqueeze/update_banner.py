"""filesqueeze.update_banner

Shared "Update available" banner widget for the FileSqueeze windows.

One-click update flow with progress and cancel, driven by a shared
:class:`~filesqueeze.updater.UpdateController`. The controller's worker
thread never touches Tk: the banner polls ``snapshot()`` on the Tk main
thread via ``after()``.

When the install cannot self-update (dev checkout, or a release without a
published wheel), the banner falls back to a "Release notes" button only.
"""

import webbrowser
from tkinter import ttk
from typing import Callable

from .update_check import RELEASES_PAGE_URL, UpdateInfo
from .updater import (
    PHASE_CANCELLED,
    PHASE_DONE,
    PHASE_DOWNLOADING,
    PHASE_FAILED,
    PHASE_INSTALLING,
    PHASE_VERIFYING,
    UpdateController,
    can_self_update,
)

# Gold/red/green/gray tones shared with the rest of the FileSqueeze UI
_COLOR_AVAILABLE = "#B8860B"
_COLOR_INFO = "#555555"
_COLOR_OK = "#2E7D32"
_COLOR_ERROR = "#B22222"
_COLOR_MUTED = "#666666"

_TERMINAL_PHASES = (PHASE_DONE, PHASE_FAILED, PHASE_CANCELLED)


class UpdateBanner(ttk.LabelFrame):
    """'Update available' banner: Update now / Release notes, progress, cancel."""

    POLL_INTERVAL_MS = 200

    def __init__(
        self,
        master: object,
        controller: UpdateController,
        update_info: UpdateInfo | None = None,
        *,
        restart: bool = False,
        on_update_applied: object | None = None,
        restart_decider: Callable[[], str | None] | None = None,
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
            restart_decider: Optional click-time override of ``restart``:
                returning None means restart is allowed (requires
                ``on_update_applied``); returning a string refuses the
                restart-mode update and shows the string as the reason. The
                compress dialog uses this to hold updates while a compression
                is running — the answer can change between building the
                banner and clicking the button.
        """
        super().__init__(master, text="Update available", padding="5")
        self.columnconfigure(0, weight=1)

        self._controller = controller
        self._update_info = update_info
        self._restart = restart and on_update_applied is not None and restart_decider is None
        self._on_update_applied = on_update_applied
        self._restart_decider = restart_decider

        self._buttons_frame: ttk.Frame | None = None
        self._status_label: ttk.Label | None = None
        self._cancel_btn: ttk.Button | None = None
        self._progressbar: ttk.Progressbar | None = None

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

        # Progress row: gridded then removed so the options are remembered
        self._status_label = ttk.Label(self, text="", foreground=_COLOR_INFO)
        self._status_label.grid(row=1, column=0, columnspan=2, sticky="w", pady=(5, 0))
        self._status_label.grid_remove()

        self._cancel_btn = ttk.Button(self, text="Cancel", command=self._on_cancel_update)
        self._cancel_btn.grid(row=1, column=1, sticky="e", pady=(5, 0))
        self._cancel_btn.grid_remove()

        self._progressbar = ttk.Progressbar(self, mode="determinate", maximum=100)
        self._progressbar.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(4, 0))
        self._progressbar.grid_remove()

        # Reflect an update the shared controller may already have in flight
        self._poll()

    # ---------------------------------------------------------------- actions

    def _on_update_now(self) -> None:
        """Start download+apply on the controller and poll it onto the widgets."""
        if self._update_info is None:
            return

        restart = self._restart
        if self._restart_decider is not None:
            refusal = self._restart_decider()
            if refusal is not None:
                # Cannot quit right now (e.g. a compression is running): say
                # so instead of silently installing into a wait that may
                # never end
                if self._status_label is not None:
                    self._status_label.grid()
                    self._status_label.config(text=refusal, foreground=_COLOR_ERROR)
                return
            restart = self._on_update_applied is not None

        self._controller.start(self._update_info, restart=restart, on_applied=self._on_update_applied)
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

    def _render(self, snap: object) -> None:
        """Repaint the widgets for an update phase (Tk main thread only)."""
        label = self._status_label
        bar = self._progressbar
        cancel = self._cancel_btn
        buttons = self._buttons_frame
        if label is None or bar is None or cancel is None or buttons is None:
            return

        if snap.phase == PHASE_DOWNLOADING:
            buttons.grid_remove()
            label.grid()
            label.config(text=self._format_progress_text(snap), foreground=_COLOR_INFO)
            cancel.state(["!disabled"])
            cancel.grid()
            bar.grid()
            bar.stop()
            if snap.percent is None:
                bar.config(mode="indeterminate")
                bar.start(12)
            else:
                bar.config(mode="determinate", value=snap.percent)
        elif snap.phase in (PHASE_VERIFYING, PHASE_INSTALLING):
            buttons.grid_remove()
            label.grid()
            label.config(text=snap.message, foreground=_COLOR_INFO)
            cancel.grid_remove()
            bar.grid()
            bar.stop()
            bar.config(mode="indeterminate")
            bar.start(12)
        elif snap.phase == PHASE_DONE:
            self._show_outcome(f"✓ {snap.message}", _COLOR_OK)
        elif snap.phase == PHASE_FAILED:
            self._show_outcome(snap.message, _COLOR_ERROR)
        elif snap.phase == PHASE_CANCELLED:
            self._show_outcome("Update cancelled.", _COLOR_MUTED)

    def _show_outcome(self, message: str, foreground: str) -> None:
        """Show a terminal state: message only, buttons back for retry."""
        if self._progressbar is None or self._cancel_btn is None or self._status_label is None or self._buttons_frame is None:
            return
        self._progressbar.stop()
        self._progressbar.grid_remove()
        self._cancel_btn.grid_remove()
        self._status_label.grid()
        self._status_label.config(text=message, foreground=foreground)
        self._buttons_frame.grid()

    @staticmethod
    def _format_progress_text(snap: object) -> str:
        if snap.percent is None:
            return snap.message
        return f"{snap.message} ({snap.percent}%)"
