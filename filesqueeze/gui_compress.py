"""filesqueeze.gui_compress

Standalone "Compress a File" dialog.

Single-file compression UX: the user picks one file and a destination, and
FileSqueeze compresses it with the same pipeline, quality settings, and
naming conventions (``compressed_<stem>.<ext>``) as monitoring mode.

The dialog owns its Tk root so it can run in two contexts:
- inside the tray service (launched on its own thread, like StatusWindow)
- as a dialog-only process via ``filesqueeze compress --gui``

All compression work runs on a worker thread; the UI thread polls for
completion. Nothing tkinter-specific crosses the thread boundary — the
worker only writes plain Python values into ``self._result``.

This module deliberately avoids ``print()`` so it also works under
``pythonw.exe`` (no console attached, e.g. Start Menu / Send To launches).
"""

import logging
import os
import subprocess
import sys
import threading
import time
import tkinter as tk
import tomllib
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .config import Config
from .standalone import (
    CATEGORY_LABELS,
    STANDALONE_UNSUPPORTED_MESSAGE,
    build_filetypes,
    compress_file,
    describe_result,
    detect_category,
    format_size,
    predict_output_path,
    resolve_final_output_path,
)

STATE_SECTION = "gui"
STATE_KEY = "last_compress_dir"

logger = logging.getLogger(__name__)


def _default_state_path() -> Path:
    """Return the default GUI state file path (kept separate from config.toml).

    The dialog stores only presentation state here (e.g. the last chosen
    destination folder). User settings remain in config.toml, which the app
    never writes to programmatically.
    """
    return Path.home() / ".config" / "filesqueeze" / "state.toml"


def load_last_compress_dir(state_path: Path | None = None) -> str | None:
    """Load the last destination folder chosen in the compress dialog.

    Args:
        state_path: Override for the state file location (for testing).

    Returns:
        The stored directory path, or None when absent or unreadable.
    """
    state_file = state_path or _default_state_path()
    try:
        with open(state_file, "rb") as f:
            data = tomllib.load(f)
    except (FileNotFoundError, OSError, tomllib.TOMLDecodeError):
        return None
    value = data.get(STATE_SECTION, {}).get(STATE_KEY)
    return value if isinstance(value, str) and value else None


def save_last_compress_dir(directory: str, state_path: Path | None = None) -> None:
    """Persist the last destination folder chosen in the compress dialog.

    Best-effort: failures (e.g. tomli_w unavailable) are logged and ignored
    so they never block a compression.

    Args:
        directory: The folder path to remember.
        state_path: Override for the state file location (for testing).
    """
    state_file = state_path or _default_state_path()
    try:
        import tomli_w

        state_file.parent.mkdir(parents=True, exist_ok=True)
        with open(state_file, "wb") as f:
            tomli_w.dump({STATE_SECTION: {STATE_KEY: directory}}, f)
    except Exception:
        logger.warning("Could not save compress-dialog state to %s", state_file, exc_info=True)


def _open_folder(path: Path) -> None:
    """Open a folder in the platform file manager."""
    if sys.platform == "win32":
        os.startfile(str(path))
    elif sys.platform == "darwin":
        subprocess.run(["open", str(path)], check=False)
    else:
        subprocess.run(["xdg-open", str(path)], check=False)


class CompressDialog:
    """Standalone single-file compression dialog.

    UI states are three stacked frames (setup / progress / result); exactly
    one is visible at a time. Compression runs on a worker thread whose
    outcome is polled from the Tk event loop.
    """

    POLL_INTERVAL_MS = 200

    def __init__(self, config: Config | None = None, initial_file: Path | str | None = None):
        """Initialize the dialog.

        Args:
            config: Configuration providing quality settings and binary paths.
            initial_file: Optional file path to pre-select (e.g. from Send To).
        """
        self.config = config or Config()
        self.logger = logging.getLogger(__name__)

        self._worker: threading.Thread | None = None
        self._result: tuple | None = None
        self._started_at: float | None = None
        self._after_id: str | None = None
        self._last_result_dir: Path | None = None

        # Create the window first so widgets can be attached
        self.root = tk.Tk()
        self.root.title("FileSqueeze — Compress a File")
        self.root.geometry("580x400")
        self.root.minsize(520, 360)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self._create_widgets()

        if initial_file is not None:
            self._file_var.set(str(initial_file))
            self._update_preview()

    # ------------------------------------------------------------------ UI

    def _create_widgets(self) -> None:
        """Build all frames and widgets."""
        main = ttk.Frame(self.root, padding="10")
        main.grid(row=0, column=0, sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main.columnconfigure(0, weight=1)
        main.rowconfigure(0, weight=1)

        # Stacked state frames occupy the same grid cell; tkraise selects
        self._setup_frame = ttk.Frame(main)
        self._progress_frame = ttk.Frame(main)
        self._result_frame = ttk.Frame(main)
        for frame in (self._setup_frame, self._progress_frame, self._result_frame):
            frame.columnconfigure(0, weight=1)
            frame.grid(row=0, column=0, sticky="nsew")

        self._build_setup_frame()
        self._build_progress_frame()
        self._build_result_frame()

        self._show_frame(self._setup_frame)

    def _build_setup_frame(self) -> None:
        """Build the file/destination selection state."""
        frame = self._setup_frame

        # File selection
        file_frame = ttk.LabelFrame(frame, text="File", padding="5")
        file_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        file_frame.columnconfigure(0, weight=1)

        self._file_var = tk.StringVar()
        self._file_var.trace_add("write", lambda *_: self._update_preview())
        self._file_entry = ttk.Entry(file_frame, textvariable=self._file_var)
        self._file_entry.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        self._browse_file_btn = ttk.Button(file_frame, text="Browse…", command=self._on_browse_file)
        self._browse_file_btn.grid(row=0, column=1)

        self._info_label = ttk.Label(file_frame, text="No file selected.", foreground="gray", font=("Helvetica", 9))
        self._info_label.grid(row=1, column=0, columnspan=2, sticky="w", pady=(4, 0))

        # Destination
        dest_frame = ttk.LabelFrame(frame, text="Save to", padding="5")
        dest_frame.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        dest_frame.columnconfigure(1, weight=1)

        self._dest_var = tk.StringVar(value="source")
        self._source_radio = ttk.Radiobutton(
            dest_frame,
            text="Same folder as the original",
            variable=self._dest_var,
            value="source",
            command=self._update_preview,
        )
        self._source_radio.grid(row=0, column=0, columnspan=3, sticky="w")

        self._custom_radio = ttk.Radiobutton(
            dest_frame, text="Choose folder…", variable=self._dest_var, value="custom", command=self._update_preview
        )
        self._custom_radio.grid(row=1, column=0, sticky="w", padx=(0, 5))

        initial_dir = load_last_compress_dir() or str(self.config.output_dir)
        self._dest_dir_var = tk.StringVar(value=initial_dir)
        self._dest_dir_var.trace_add("write", lambda *_: self._update_preview())
        self._dest_dir_entry = ttk.Entry(dest_frame, textvariable=self._dest_dir_var)
        self._dest_dir_entry.grid(row=1, column=1, sticky="ew", padx=(0, 5))

        self._browse_dest_btn = ttk.Button(dest_frame, text="Browse…", command=self._on_browse_destination)
        self._browse_dest_btn.grid(row=1, column=2)

        # Output name preview + collision warning
        self._preview_label = ttk.Label(frame, text="", foreground="#444444", font=("Helvetica", 9), wraplength=540)
        self._preview_label.grid(row=2, column=0, sticky="w", pady=(0, 4))

        self._conflict_label = ttk.Label(frame, text="", foreground="#B8860B", font=("Helvetica", 9), wraplength=540)
        self._conflict_label.grid(row=3, column=0, sticky="w", pady=(0, 10))

        # Buttons
        buttons = ttk.Frame(frame)
        buttons.grid(row=4, column=0, sticky="e")
        self._compress_btn = ttk.Button(buttons, text="Compress", command=self._on_compress, state="disabled")
        self._compress_btn.grid(row=0, column=0, padx=(0, 5))
        self._setup_close_btn = ttk.Button(buttons, text="Close", command=self._on_close)
        self._setup_close_btn.grid(row=0, column=1)

    def _build_progress_frame(self) -> None:
        """Build the compression-in-progress state."""
        frame = self._progress_frame

        self._progress_status = ttk.Label(frame, text="", font=("Helvetica", 11, "bold"))
        self._progress_status.grid(row=0, column=0, sticky="w", pady=(20, 10))

        self._progress_bar = ttk.Progressbar(frame, mode="indeterminate", length=380)
        self._progress_bar.grid(row=1, column=0, sticky="ew", pady=(0, 6))

        self._elapsed_label = ttk.Label(frame, text="0:00 elapsed", font=("Helvetica", 9), foreground="#444444")
        self._elapsed_label.grid(row=2, column=0, sticky="w", pady=(0, 4))

        hint = ttk.Label(frame, text="Large videos can take several minutes.", font=("Helvetica", 9), foreground="gray")
        hint.grid(row=3, column=0, sticky="w", pady=(0, 20))

        buttons = ttk.Frame(frame)
        buttons.grid(row=4, column=0, sticky="e")
        self._progress_close_btn = ttk.Button(buttons, text="Close (keeps running)", command=self._on_close)
        self._progress_close_btn.grid(row=0, column=0)

    def _build_result_frame(self) -> None:
        """Build the finished/error state."""
        frame = self._result_frame

        self._result_title = ttk.Label(frame, text="", font=("Helvetica", 11, "bold"))
        self._result_title.grid(row=0, column=0, sticky="w", pady=(20, 10))

        self._result_detail = ttk.Label(frame, text="", font=("Helvetica", 9), wraplength=540, justify="left")
        self._result_detail.grid(row=1, column=0, sticky="w", pady=(0, 20))

        buttons = ttk.Frame(frame)
        buttons.grid(row=2, column=0, sticky="e")
        self._open_folder_btn = ttk.Button(buttons, text="Open folder", command=self._on_open_folder)
        self._open_folder_btn.grid(row=0, column=0, padx=(0, 5))
        self._retry_btn = ttk.Button(buttons, text="Retry", command=self._on_retry)
        self._retry_btn.grid(row=0, column=1, padx=(0, 5))
        self._again_btn = ttk.Button(buttons, text="Compress another", command=self._on_compress_another)
        self._again_btn.grid(row=0, column=2, padx=(0, 5))
        self._result_close_btn = ttk.Button(buttons, text="Close", command=self._on_close)
        self._result_close_btn.grid(row=0, column=3)

    def _show_frame(self, frame: ttk.Frame) -> None:
        """Raise one of the stacked state frames."""
        frame.tkraise()

    # ------------------------------------------------------------- actions

    def _on_browse_file(self) -> None:
        """Open a file picker and select the chosen file."""
        chosen = filedialog.askopenfilename(parent=self.root, title="Choose a file to compress", filetypes=build_filetypes())
        if chosen:
            self._file_var.set(chosen)

    def _on_browse_destination(self) -> None:
        """Open a folder picker for the destination."""
        initial_dir = self._dest_dir_var.get().strip() or str(self.config.output_dir)
        chosen = filedialog.askdirectory(parent=self.root, title="Choose destination folder", initialdir=initial_dir)
        if chosen:
            self._dest_dir_var.set(chosen)
            self._dest_var.set("custom")
            save_last_compress_dir(chosen)

    def _on_compress(self) -> None:
        """Start compression on a worker thread."""
        file_path = self._evaluate_selection()[0]
        if file_path is None:
            return

        destination = self._destination_dir(file_path.parent)
        if destination is None:  # pragma: no cover - guarded by _evaluate_selection
            return
        predicted = predict_output_path(file_path, destination)
        final_path, _renamed = resolve_final_output_path(predicted)

        try:
            final_path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            messagebox.showerror("FileSqueeze", f"Cannot create destination folder:\n{e}", parent=self.root)
            return

        if self._dest_var.get() == "custom":
            save_last_compress_dir(str(destination))

        self._result = None
        self._started_at = time.monotonic()
        self._progress_status.config(text=f"Compressing {file_path.name}…")
        self._progress_bar.start(20)
        self._show_frame(self._progress_frame)

        self._worker = threading.Thread(target=self._work, args=(file_path, final_path), daemon=False)
        self._worker.start()
        self._poll_worker()

    def _on_open_folder(self) -> None:
        """Open the folder containing the last result."""
        if self._last_result_dir is not None:
            _open_folder(self._last_result_dir)

    def _on_retry(self) -> None:
        """Return to setup, keeping the current file selection."""
        self._show_frame(self._setup_frame)
        self._update_preview()

    def _on_compress_another(self) -> None:
        """Return to setup with a cleared file selection."""
        self._file_var.set("")
        self._show_frame(self._setup_frame)
        self._update_preview()
        self._file_entry.focus_set()

    def _on_close(self) -> None:
        """Close the window, confirming when compression is still running.

        The worker thread is non-daemon: closing the window does not abort
        the running compression; the process simply finishes it in the
        background before exiting.
        """
        if self._worker is not None and self._worker.is_alive():
            proceed = messagebox.askyesno(
                "FileSqueeze",
                "A file is still compressing. If you close now, the compression keeps running in the "
                "background until it finishes.\n\nClose anyway?",
                parent=self.root,
            )
            if not proceed:
                return
            self._after_id = None  # let the poller die with the window
        self.root.destroy()

    # ------------------------------------------------------------- helpers

    def _destination_dir(self, source_dir: Path) -> Path | None:
        """Return the configured destination directory, or None if unset."""
        if self._dest_var.get() == "source":
            return source_dir
        raw = self._dest_dir_var.get().strip().strip('"')
        return Path(raw) if raw else None

    def _evaluate_selection(self) -> tuple[Path | None, str, str]:
        """Validate the current file selection and destination.

        Returns:
            Tuple of (path, info text, info colour). ``path`` is None unless
            the selection is fully valid and ready to compress.
        """
        raw = self._file_var.get().strip().strip('"')
        if not raw:
            return None, "No file selected.", "gray"

        path = Path(raw)
        if not path.exists():
            return None, f"File not found: {path}", "#B22222"

        category = detect_category(path.suffix)
        if category is None:
            return (
                None,
                f"Unsupported file type '{path.suffix}'. Supported: videos, PDFs, and images.",
                "#B22222",
            )
        if category == "presentation":
            return None, STANDALONE_UNSUPPORTED_MESSAGE, "#B22222"

        try:
            size_text = format_size(path.stat().st_size)
        except OSError:
            size_text = "unknown size"
        return path, f"{CATEGORY_LABELS[category]} · {size_text}", "black"

    def _update_preview(self) -> None:
        """Refresh info, output-name preview, and collision warning."""
        path, info_text, info_color = self._evaluate_selection()

        preview_text = ""
        conflict_text = ""
        compress_state = "disabled"

        if path is not None:
            destination = self._destination_dir(path.parent)
            if destination is None:
                info_text = "Choose a destination folder."
                info_color = "#B22222"
            elif not destination.exists():
                info_text = f"Destination folder does not exist: {destination}"
                info_color = "#B22222"
            else:
                predicted = predict_output_path(path, destination)
                final_path, renamed = resolve_final_output_path(predicted)
                preview_text = f"Saved as: {final_path}"
                if renamed:
                    conflict_text = (
                        f"A file named '{predicted.name}' already exists there — it will be saved as '{final_path.name}'."
                    )
                compress_state = "normal"

        self._info_label.config(text=info_text, foreground=info_color)
        self._compress_btn.config(state=compress_state)
        self._preview_label.config(text=preview_text)
        self._conflict_label.config(text=conflict_text)

    def _work(self, input_path: Path, output_path: Path) -> None:
        """Worker thread body: compress and record the outcome.

        Touches no tkinter objects — only plain values in ``self._result``.
        """
        try:
            result_path = compress_file(input_path, output_path, self.config)
            self._result = ("ok", result_path, input_path)
        except Exception as e:
            self.logger.error("Standalone compression of %s failed: %s", input_path, e, exc_info=True)
            self._result = ("error", str(e))

    def _poll_worker(self) -> None:
        """Poll worker completion from the UI thread and update state."""
        if not self.root.winfo_exists():
            return

        if self._worker is not None and self._worker.is_alive():
            if self._started_at is not None:
                self._elapsed_label.config(text=self._format_elapsed(time.monotonic() - self._started_at))
            self._after_id = self.root.after(self.POLL_INTERVAL_MS, self._poll_worker)
            return

        self._worker = None
        self._after_id = None
        self._progress_bar.stop()

        result = self._result
        if result is not None and result[0] == "ok":
            self._show_done(result[1], result[2])
        else:
            self._show_error(result[1] if result is not None else "Compression failed for an unknown reason.")

    def _show_done(self, result_path: Path, input_path: Path) -> None:
        """Switch to the success result state."""
        try:
            detail = describe_result(input_path.stat().st_size, result_path.stat().st_size)
        except OSError:
            detail = "Compression finished."
        self._result_title.config(text="✓ Done", foreground="green")
        self._result_detail.config(text=f"{detail}\nSaved to: {result_path}")
        self._last_result_dir = result_path.parent
        self._open_folder_btn.grid()
        self._retry_btn.grid_remove()
        self._again_btn.grid()
        self._show_frame(self._result_frame)

    def _show_error(self, message: str) -> None:
        """Switch to the failure result state."""
        self._result_title.config(text="✗ Compression failed", foreground="#B22222")
        self._result_detail.config(text=message)
        self._open_folder_btn.grid_remove()
        self._retry_btn.grid()
        self._again_btn.grid_remove()
        self._show_frame(self._result_frame)

    @staticmethod
    def _format_elapsed(seconds: float) -> str:
        """Format elapsed seconds as m:ss or h:mm:ss."""
        total = int(seconds)
        hours, remainder = divmod(total, 3600)
        minutes, secs = divmod(remainder, 60)
        if hours:
            return f"{hours}:{minutes:02d}:{secs:02d} elapsed"
        return f"{minutes}:{secs:02d} elapsed"

    # ------------------------------------------------------------ lifecycle

    def show(self) -> None:
        """Show the dialog and run its event loop (blocks until closed)."""
        self.root.mainloop()

    def close(self) -> None:
        """Close the dialog programmatically (used by tests/E2E drivers)."""
        self._on_close()


def run_compress_dialog(config: Config | None = None, initial_file: Path | str | None = None) -> None:
    """Create and show a CompressDialog (blocks until the dialog closes).

    Args:
        config: Configuration providing quality settings and binary paths.
        initial_file: Optional file path to pre-select (e.g. from Send To).
    """
    dialog = CompressDialog(config=config, initial_file=initial_file)
    dialog.show()
