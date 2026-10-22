"""Tests for run_subprocess_with_progress.

Uses real subprocesses (sys.executable) so the streaming loop, timeout
watchdog and stderr temp-file handling are exercised end-to-end without
needing FFmpeg.
"""

import sys
import time

import pytest

from filesqueeze.utils.subprocess_helper import SubprocessError, SubprocessTimeout, run_subprocess_with_progress


class TestRunSubprocessWithProgress:
    def test_streams_stdout_lines_and_succeeds(self):
        lines = []
        cmd = [
            sys.executable,
            "-c",
            "import sys; print('out_time_us=1'); print('out_time_us=2'); sys.stderr.write('boom\\n')",
        ]

        result = run_subprocess_with_progress(
            cmd, timeout=30, tool_name="TOOL", input_file="in.mp4", on_stdout_line=lines.append
        )

        assert result.returncode == 0
        assert [line.strip() for line in lines] == ["out_time_us=1", "out_time_us=2"]
        assert "boom" in result.stderr

    def test_nonzero_exit_raises_with_stderr(self):
        cmd = [sys.executable, "-c", "import sys; print('line'); sys.stderr.write('bad input\\n'); sys.exit(3)"]

        with pytest.raises(SubprocessError) as excinfo:
            run_subprocess_with_progress(
                cmd, timeout=30, tool_name="TOOL", input_file="in.mp4", on_stdout_line=lambda line: None
            )

        assert excinfo.value.return_code == 3
        assert "bad input" in excinfo.value.stderr

    def test_check_false_returns_completed_process(self):
        cmd = [sys.executable, "-c", "raise SystemExit(5)"]

        result = run_subprocess_with_progress(
            cmd, timeout=30, tool_name="TOOL", input_file="in.mp4", on_stdout_line=lambda line: None, check=False
        )

        assert result.returncode == 5

    def test_timeout_kills_silent_process_and_raises(self):
        # No stdout output at all: the readline loop can only unblock
        # because the watchdog kills the process
        cmd = [sys.executable, "-c", "import time; time.sleep(60)"]

        start = time.monotonic()
        with pytest.raises(SubprocessTimeout):
            run_subprocess_with_progress(
                cmd, timeout=2, tool_name="TOOL", input_file="in.mp4", on_stdout_line=lambda line: None
            )

        assert time.monotonic() - start < 30

    def test_callback_exception_does_not_break_run(self):
        received = []

        def explode(line):
            if "1" in line:
                raise ValueError("callback bug")
            received.append(line.strip())

        cmd = [sys.executable, "-c", "print('one=1'); print('two=2')"]

        result = run_subprocess_with_progress(cmd, timeout=30, tool_name="TOOL", input_file="in.mp4", on_stdout_line=explode)

        assert result.returncode == 0
        assert received == ["two=2"]
