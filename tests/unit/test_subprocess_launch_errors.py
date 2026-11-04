"""Tests for executable-launch failure reporting (the missing path in the error).

A configured binary path that doesn't exist used to surface as an opaque
``FileNotFoundError: [WinError 2]`` with no filename (the colleague-ticket
failure mode). These tests pin the new contract: the spawn sites raise
``ExecutableNotFoundError`` whose message and ``.path`` carry the missing
executable. Imports of ``filesqueeze`` modules happen INSIDE the test
functions (see tests/unit/test_doctor_autostart.py for why).
"""

import sys

import pytest

MISSING_TOOL = "definitely-missing-filesqueeze-tool"


class TestSubprocessHelperLaunchErrors:
    def test_still_a_subprocess_error(self):
        """Callers catching SubprocessError/RuntimeError keep working."""
        from filesqueeze.utils.subprocess_helper import ExecutableNotFoundError, SubprocessError

        assert issubclass(ExecutableNotFoundError, SubprocessError)
        assert issubclass(ExecutableNotFoundError, RuntimeError)

    def test_run_subprocess_reports_missing_executable_path(self):
        from filesqueeze.utils.subprocess_helper import ExecutableNotFoundError, run_subprocess

        with pytest.raises(ExecutableNotFoundError) as excinfo:
            run_subprocess([MISSING_TOOL, "--version"], timeout=30, tool_name="TOOL", input_file="in.mp4")

        assert MISSING_TOOL in str(excinfo.value)
        assert "could not be launched" in str(excinfo.value)
        assert excinfo.value.path == MISSING_TOOL

    def test_run_subprocess_with_progress_reports_missing_executable_path(self):
        from filesqueeze.utils.subprocess_helper import ExecutableNotFoundError, run_subprocess_with_progress

        with pytest.raises(ExecutableNotFoundError) as excinfo:
            run_subprocess_with_progress(
                [MISSING_TOOL], timeout=30, tool_name="TOOL", input_file="in.mp4", on_stdout_line=lambda line: None
            )

        assert MISSING_TOOL in str(excinfo.value)
        assert excinfo.value.path == MISSING_TOOL

    def test_success_path_unaffected(self):
        from filesqueeze.utils.subprocess_helper import run_subprocess

        result = run_subprocess(
            [sys.executable, "-c", "print('ok')"],
            timeout=30,
            tool_name="TOOL",
            input_file="in.mp4",
            capture_output=True,
            text_mode=True,
        )

        assert result == "ok\n" or result.strip() == "ok"

    def test_launch_error_formats_winerror(self):
        """The formatter restates the exe path plus the OS reason."""
        from filesqueeze.utils.subprocess_helper import launch_error

        os_error = FileNotFoundError(2, "The system cannot find the file specified")
        os_error.winerror = 2  # Windows populates this; POSIX FileNotFoundErrors lack it

        error = launch_error("FFmpeg", "C:/ffmpeg/bin", os_error)

        assert "FFmpeg could not be launched: 'C:/ffmpeg/bin'" in str(error)
        assert "The system cannot find the file specified" in str(error)
        assert "WinError 2" in str(error)
        assert error.path == "C:/ffmpeg/bin"


class TestVideoProbeLaunchErrors:
    """ffprobe's direct subprocess.run sites report the missing path too."""

    def test_duration_missing_ffprobe_reports_path(self, monkeypatch):
        from filesqueeze.ops import video
        from filesqueeze.utils.subprocess_helper import ExecutableNotFoundError

        monkeypatch.setattr(video, "get_ffprobe_path", lambda ffmpeg_path="": MISSING_TOOL)

        with pytest.raises(ExecutableNotFoundError) as excinfo:
            video.duration("in.mp4")

        assert MISSING_TOOL in str(excinfo.value)
        assert excinfo.value.path == MISSING_TOOL

    def test_width_height_missing_ffprobe_reports_path(self, monkeypatch):
        from filesqueeze.ops import video
        from filesqueeze.utils.subprocess_helper import ExecutableNotFoundError

        monkeypatch.setattr(video, "get_ffprobe_path", lambda ffmpeg_path="": MISSING_TOOL)

        with pytest.raises(ExecutableNotFoundError) as excinfo:
            video.width_height("in.mp4")

        assert MISSING_TOOL in str(excinfo.value)
        assert excinfo.value.path == MISSING_TOOL
