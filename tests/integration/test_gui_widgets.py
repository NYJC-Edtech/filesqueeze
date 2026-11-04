"""In-process tkinter widget tests for CompressDialog (issue #33).

These drive real widgets — StringVar updates fire the dialog's own trace
callbacks, buttons are inspected via their ttk state, and state methods are
invoked directly — instead of asserting on source strings. Requires a
display: skipped when tkinter is missing or no display is available
(headless machines), and run under xvfb in the CI gui-widget-tests job.
"""

import time
from pathlib import Path

import pytest

tk = pytest.importorskip("tkinter")


def _make_png(path: Path, size: tuple[int, int] = (400, 300)) -> Path:
    """Create a real gradient PNG (compresses well to JPG via Pillow)."""
    from PIL import Image

    gradient = Image.linear_gradient("L").resize(size)
    gradient.convert("RGB").save(path, format="PNG")
    return path


@pytest.fixture
def dialog(tmp_path):
    """A CompressDialog with its own Tk root, destroyed after each test."""
    from filesqueeze.config import Config
    from filesqueeze.gui_compress import CompressDialog

    # Windows venvs occasionally fail Tk() init with "Can't find a usable
    # init.tcl/tk.tcl" — a transient flake (later tests in the same process
    # succeed), so retry it briefly. Genuinely headless machines raise a
    # different message and skip immediately.
    dlg = None
    for _ in range(3):
        try:
            dlg = CompressDialog(config=Config())
            break
        except tk.TclError as e:
            message = str(e)
            if "init.tcl" not in message and "tk.tcl" not in message:
                pytest.skip(f"no display available for tkinter: {e}")
            time.sleep(0.2)
    if dlg is None:
        pytest.skip("tkinter failed to initialize after retries (init.tcl/tk.tcl flake)")
    yield dlg
    try:
        dlg.root.destroy()
    except tk.TclError:
        pass


def _compress_disabled(dlg) -> bool:
    return dlg._compress_btn.instate(["disabled"])


class TestSelectionValidation:
    """Setup-frame behavior: what enables/disables the Compress button."""

    def test_no_selection_disables_compress(self, dialog):
        assert dialog._info_label.cget("text") == "No file selected."
        assert _compress_disabled(dialog)

    def test_unsupported_type_disables_compress_and_shows_reason(self, dialog, tmp_path):
        src = tmp_path / "notes.txt"
        src.write_text("not compressible", encoding="utf-8")

        dialog._file_var.set(str(src))

        assert _compress_disabled(dialog)
        assert "Unsupported file type '.txt'" in dialog._info_label.cget("text")

    def test_pptx_shows_standalone_unsupported_message(self, dialog, tmp_path):
        from filesqueeze.standalone import STANDALONE_UNSUPPORTED_MESSAGE

        src = tmp_path / "slides.pptx"
        src.write_bytes(b"PK fake pptx")

        dialog._file_var.set(str(src))

        assert _compress_disabled(dialog)
        assert dialog._info_label.cget("text") == STANDALONE_UNSUPPORTED_MESSAGE

    def test_missing_file_shows_error_info(self, dialog, tmp_path):
        dialog._file_var.set(str(tmp_path / "does-not-exist.mp4"))

        assert _compress_disabled(dialog)
        assert "File not found" in dialog._info_label.cget("text")

    def test_valid_image_enables_compress_and_previews_name(self, dialog, tmp_path):
        src = _make_png(tmp_path / "photo.png")

        dialog._file_var.set(str(src))

        # Standalone naming converts non-JPG images to JPG output
        assert not _compress_disabled(dialog)
        assert dialog._preview_label.cget("text") == f"Saved as: {tmp_path / 'compressed_photo.jpg'}"
        assert dialog._conflict_label.cget("text") == ""


class TestCollisionWarning:
    """Existing-output detection shows the auto-rename warning."""

    def test_existing_output_shows_rename_warning(self, dialog, tmp_path):
        src = _make_png(tmp_path / "photo.png")
        (tmp_path / "compressed_photo.jpg").write_bytes(b"existing output")

        dialog._file_var.set(str(src))

        assert not _compress_disabled(dialog)
        assert "already exists" in dialog._conflict_label.cget("text")
        assert "compressed_photo_1.jpg" in dialog._conflict_label.cget("text")
        assert "compressed_photo_1.jpg" in dialog._preview_label.cget("text")


class TestResultStates:
    """Result-frame behavior driven through the dialog's own state methods."""

    def test_done_state_shows_size_summary(self, dialog, tmp_path):
        src = _make_png(tmp_path / "photo.png")
        result = tmp_path / "compressed_photo.png"
        result.write_bytes(b"0" * 100)

        dialog._show_done(result, src)

        assert dialog._result_title.cget("text") == "✓ Done"
        assert "Saved to:" in dialog._result_detail.cget("text")
        assert "smaller" in dialog._result_detail.cget("text")
        assert dialog._open_folder_btn.winfo_manager() != ""  # gridded
        assert dialog._retry_btn.winfo_manager() == ""  # grid_remove'd

    def test_error_state_offers_retry(self, dialog):
        dialog._show_error("boom: compression exploded")

        assert dialog._result_title.cget("text") == "✗ Compression failed"
        assert "boom: compression exploded" in dialog._result_detail.cget("text")
        assert dialog._retry_btn.winfo_manager() != ""  # gridded
        assert dialog._open_folder_btn.winfo_manager() == ""  # grid_remove'd
        assert dialog._again_btn.winfo_manager() == ""

    def test_retry_returns_to_setup_with_selection_revalidated(self, dialog, tmp_path):
        dialog._show_error("boom")
        src = _make_png(tmp_path / "photo.png")
        dialog._file_var.set(str(src))  # would normally be set before the run

        dialog._on_retry()

        # Setup frame is active again and the preview reflects the selection
        assert not _compress_disabled(dialog)
        assert "compressed_photo.jpg" in dialog._preview_label.cget("text")

    def test_compress_another_clears_selection(self, dialog, tmp_path):
        src = _make_png(tmp_path / "photo.png")
        dialog._file_var.set(str(src))
        dialog._show_done(tmp_path / "compressed_photo.png", src)

        dialog._on_compress_another()

        assert dialog._file_var.get() == ""
        assert _compress_disabled(dialog)
        assert dialog._info_label.cget("text") == "No file selected."


class TestFullFlow:
    """The whole pipeline through the real worker thread and Tk poller."""

    def test_compress_image_end_to_end(self, dialog, tmp_path):
        src = _make_png(tmp_path / "photo.png")
        dialog._file_var.set(str(src))

        dialog._on_compress()

        # Pump the Tk event loop so the 200ms completion poller fires
        # (no is_compressing assert here: a tiny input can finish before we look)
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            dialog.root.update()
            if dialog._result_title.cget("text"):
                break
            time.sleep(0.02)

        assert not dialog.is_compressing
        assert dialog._result_title.cget("text") == "✓ Done"
        assert "Saved to:" in dialog._result_detail.cget("text")
        outputs = list(tmp_path.glob("compressed_photo.*"))
        assert outputs, "expected a compressed_* output next to the source"


class _StubStateProvider:
    """Minimal StateProvider returning a fixed ServiceState snapshot."""

    def __init__(self, input_dir: Path, output_dir: Path, processed_files=None):
        from filesqueeze.service import ServiceState

        self._state = ServiceState(
            running=True, input_dir=input_dir, output_dir=output_dir, processed_files=processed_files or []
        )

    def get_state(self):
        return self._state


class TestStatusWindowConfigRow:
    """The Configuration frame in the top cluster shows the detected config."""

    def _build(self, config):
        from filesqueeze.gui import StatusWindow

        provider = _StubStateProvider(Path("C:/FileSqueeze/upload"), Path("C:/FileSqueeze/compressed"))
        window = None
        for _ in range(3):
            try:
                window = StatusWindow(provider, refresh_interval=None, config=config)
                break
            except tk.TclError as e:
                message = str(e)
                if "init.tcl" not in message and "tk.tcl" not in message:
                    pytest.skip(f"no display available for tkinter: {e}")
                time.sleep(0.2)
        if window is None:
            pytest.skip("tkinter failed to initialize after retries (init.tcl/tk.tcl flake)")
        return window

    def test_shows_detected_config_file(self, tmp_path):
        from filesqueeze.config import Config

        cfg = tmp_path / "filesqueeze.toml"
        cfg.write_text("[gui]\nrefresh_interval_ms = 1000\n", encoding="utf-8")

        window = self._build(Config(config_path=str(cfg)))
        try:
            assert str(cfg) in window.config_value.cget("text")
        finally:
            window.root.destroy()

    def test_shows_none_detected_without_config_sources(self):
        from filesqueeze.config import Config

        window = self._build(Config({}))
        try:
            assert "None detected" in window.config_value.cget("text")
        finally:
            window.root.destroy()


class TestProcessedFilesErrorDetails:
    """Failed processed-file rows carry an inline error-details button."""

    _DETAILS_REPORT = (
        "FileSqueeze error report\n"
        "Version:  0.9.10\n"
        "Platform: Windows-11 | Python 3.13\n"
        "Time:     2026-11-04T09:25:15\n"
        "File:     C:\\FileSqueeze\\upload\\NY041 Camera 1.MP4\n"
        "\n"
        "Error: RuntimeError: File processing failed: NY041 Camera 1.MP4\n"
        "\n"
        "Traceback:\n"
        '  File "service.py", in _process_file\n'
        "RuntimeError: File processing failed: NY041 Camera 1.MP4"
    )

    def _build(self, processed_files):
        from filesqueeze.config import Config
        from filesqueeze.gui import StatusWindow

        provider = _StubStateProvider(
            Path("C:/FileSqueeze/upload"), Path("C:/FileSqueeze/compressed"), processed_files=processed_files
        )
        window = None
        for _ in range(3):
            try:
                window = StatusWindow(provider, refresh_interval=None, config=Config({}))
                break
            except tk.TclError as e:
                message = str(e)
                if "init.tcl" not in message and "tk.tcl" not in message:
                    pytest.skip(f"no display available for tkinter: {e}")
                time.sleep(0.2)
        if window is None:
            pytest.skip("tkinter failed to initialize after retries (init.tcl/tk.tcl flake)")
        return window

    def _failed_record(self):
        from filesqueeze.service import ErrorDetails, ProcessedFile

        details = ErrorDetails(summary="RuntimeError: File processing failed", report=self._DETAILS_REPORT)
        return [
            ProcessedFile(filename="good.mp4", timestamp="2026-11-04T09:00:00", success=True),
            ProcessedFile(
                filename="bad.mp4",
                timestamp="2026-11-04T09:25:15",
                success=False,
                error_details=details,
            ),
        ]

    def _find_dialog(self, root):
        from tkinter import Toplevel

        dialogs = [child for child in root.winfo_children() if isinstance(child, Toplevel)]
        assert dialogs, "expected the error-details dialog to open"
        return dialogs[-1]

    def _dialog_report_text(self, dialog):
        from tkinter import Text

        # ScrolledText wraps an inner Frame, so the Text is not a direct child
        def walk(widget):
            for child in widget.winfo_children():
                if isinstance(child, Text):
                    return child
                found = walk(child)
                if found is not None:
                    return found
            return None

        report = walk(dialog)
        assert report is not None, "expected a report Text widget in the dialog"
        return report.get("1.0", "end").rstrip("\n")

    def test_failed_row_gets_inline_error_details_button(self):
        window = self._build(self._failed_record())
        try:
            assert len(window._processed_error_buttons) == 1
            assert window._processed_error_buttons[0].cget("text") == "Error details"
        finally:
            window.root.destroy()

    def test_successful_row_gets_no_button(self):
        from filesqueeze.service import ProcessedFile

        window = self._build([ProcessedFile(filename="ok.mp4", timestamp="2026-11-04T09:00:00", success=True)])
        try:
            assert window._processed_error_buttons == []
        finally:
            window.root.destroy()

    def test_failed_row_without_details_gets_no_button(self):
        from filesqueeze.service import ProcessedFile

        record = ProcessedFile(filename="old.mp4", timestamp="2026-11-03T08:00:00", success=False)
        window = self._build([record])
        try:
            assert window._processed_error_buttons == []
        finally:
            window.root.destroy()

    def test_button_opens_dialog_with_report(self):
        window = self._build(self._failed_record())
        try:
            window._processed_error_buttons[0].invoke()
            dialog = self._find_dialog(window.root)
            assert "bad.mp4" in dialog.title()
            assert self._dialog_report_text(dialog) == self._DETAILS_REPORT
        finally:
            window.root.destroy()

    def test_copy_details_puts_report_on_clipboard(self):
        window = self._build(self._failed_record())
        try:
            window._processed_error_buttons[0].invoke()
            dialog = self._find_dialog(window.root)
            dialog._copy_button.invoke()
            assert dialog._copy_button.cget("text") == "Copied ✓"
            try:
                assert dialog.clipboard_get() == self._DETAILS_REPORT
            except tk.TclError:
                pass  # headless clipboard unavailable; button feedback already verified
        finally:
            window.root.destroy()

    def test_unchanged_state_skips_rebuild(self):
        window = self._build(self._failed_record())
        try:
            button_before = window._processed_error_buttons[0]
            window.update_display()  # Same snapshot: the button must not be rebuilt
            assert window._processed_error_buttons[0] is button_before
        finally:
            window.root.destroy()
