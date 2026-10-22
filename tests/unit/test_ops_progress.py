"""Tests for ops compression progress wiring.

Verifies that video.compress / audio.compile switch to the progress
runner (with ``-progress pipe:1``) when a callback is supplied, that the
duration probe failure degrades to the plain runner, and that progress
is never reported without a usable duration. All ffmpeg entry points are
patched; no binaries needed.
"""

from unittest.mock import MagicMock, patch

from filesqueeze.ops import audio, video

# Synthetic -progress feed for a 100s input: 10% then 50%
PROGRESS_LINES = ("out_time_us=10000000\n", "out_time_us=50000000\n", "progress=end\n")


def _fake_progress_runner(captured, lines=PROGRESS_LINES):
    """A stand-in for run_subprocess_with_progress that replays lines."""

    def runner(cmd, *, timeout, tool_name, input_file, on_stdout_line, check=True):
        captured["cmd"] = cmd
        captured["input_file"] = input_file
        for line in lines:
            on_stdout_line(line)
        from subprocess import CompletedProcess

        return CompletedProcess(cmd, 0, stdout=None, stderr="")

    return runner


class TestVideoCompressProgress:
    def test_progress_runner_used_with_progress_flags(self, tmp_path):
        received = []
        captured = {}
        infile = tmp_path / "in.mp4"
        infile.write_bytes(b"x")

        with (
            patch.object(video, "get_ffmpeg_path", return_value=tmp_path / "ffmpeg.exe"),
            patch.object(video, "duration", return_value=100.0),
            patch.object(video, "run_subprocess_with_progress", side_effect=_fake_progress_runner(captured)),
            patch.object(video, "verify_output_file"),
        ):
            video.compress(str(infile), str(tmp_path / "out.mp4"), progress_cb=received.append)

        cmd = captured["cmd"]
        assert "-progress" in cmd
        assert cmd[cmd.index("-progress") + 1] == "pipe:1"
        assert "-nostats" in cmd
        assert captured["input_file"] == str(infile)
        assert received == [10, 50]

    def test_no_callback_skips_probe_and_progress_flags(self, tmp_path):
        duration_probe = MagicMock(return_value=100.0)
        infile = tmp_path / "in.mp4"
        infile.write_bytes(b"x")

        with (
            patch.object(video, "get_ffmpeg_path", return_value=tmp_path / "ffmpeg.exe"),
            patch.object(video, "duration", duration_probe),
            patch.object(video, "run_subprocess") as mock_runner,
            patch.object(video, "run_subprocess_with_progress") as mock_progress_runner,
            patch.object(video, "verify_output_file"),
        ):
            video.compress(str(infile), str(tmp_path / "out.mp4"))

        duration_probe.assert_not_called()
        mock_runner.assert_called_once()
        mock_progress_runner.assert_not_called()
        assert "-progress" not in mock_runner.call_args.args[0]

    def test_duration_probe_none_falls_back_to_plain_runner(self, tmp_path):
        infile = tmp_path / "in.mp4"
        infile.write_bytes(b"x")

        with (
            patch.object(video, "get_ffmpeg_path", return_value=tmp_path / "ffmpeg.exe"),
            patch.object(video, "duration", return_value=None),
            patch.object(video, "run_subprocess") as mock_runner,
            patch.object(video, "run_subprocess_with_progress") as mock_progress_runner,
            patch.object(video, "verify_output_file"),
        ):
            video.compress(str(infile), str(tmp_path / "out.mp4"), progress_cb=lambda percent: None)

        mock_runner.assert_called_once()
        mock_progress_runner.assert_not_called()

    def test_duration_probe_exception_falls_back_to_plain_runner(self, tmp_path):
        infile = tmp_path / "in.mp4"
        infile.write_bytes(b"x")

        with (
            patch.object(video, "get_ffmpeg_path", return_value=tmp_path / "ffmpeg.exe"),
            patch.object(video, "duration", side_effect=RuntimeError("ffprobe not found")),
            patch.object(video, "run_subprocess") as mock_runner,
            patch.object(video, "run_subprocess_with_progress") as mock_progress_runner,
            patch.object(video, "verify_output_file"),
        ):
            video.compress(str(infile), str(tmp_path / "out.mp4"), progress_cb=lambda percent: None)

        mock_runner.assert_called_once()
        mock_progress_runner.assert_not_called()


class TestAudioCompressProgress:
    def test_progress_runner_used_with_progress_flags(self, tmp_path):
        received = []
        captured = {}
        infile = tmp_path / "song.wav"
        infile.write_bytes(b"x")

        with (
            patch.object(audio, "get_ffmpeg_path", return_value=tmp_path / "ffmpeg.exe"),
            patch.object(audio, "duration", return_value=100.0),
            patch.object(audio, "run_subprocess_with_progress", side_effect=_fake_progress_runner(captured)),
            patch.object(audio, "verify_output_file"),
        ):
            audio.compress(str(infile), str(tmp_path / "out.m4a"), progress_cb=received.append)

        cmd = captured["cmd"]
        assert "-progress" in cmd
        assert cmd[cmd.index("-progress") + 1] == "pipe:1"
        assert "-nostats" in cmd
        assert received == [10, 50]

    def test_no_callback_uses_plain_runner(self, tmp_path):
        infile = tmp_path / "song.wav"
        infile.write_bytes(b"x")

        with (
            patch.object(audio, "get_ffmpeg_path", return_value=tmp_path / "ffmpeg.exe"),
            patch.object(audio, "run_subprocess") as mock_runner,
            patch.object(audio, "run_subprocess_with_progress") as mock_progress_runner,
            patch.object(audio, "verify_output_file"),
        ):
            audio.compress(str(infile), str(tmp_path / "out.m4a"))

        mock_runner.assert_called_once()
        mock_progress_runner.assert_not_called()
