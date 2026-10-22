"""Tests for ops/transcription.py (config gating, stcc invocation, mux)."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from filesqueeze.ops.transcription import (
    build_stcc_command,
    is_enabled,
    mux_subtitles,
    resolve_stcc_path,
    transcribe_after_compress,
)

_STCC = "C:/bin/stcc/stcc.py"


class _StubConfig:
    def __init__(self, values: dict | None = None):
        self._values = values or {}

    def get(self, key, default=None):
        return self._values.get(key, default)


def _enabled_config(stcc=_STCC, **extra):
    values = {"transcription.enabled": True, "transcription.stcc_path": stcc, "transcription.threads": 0}
    values.update(extra)
    return _StubConfig(values)


class _FakeRun:
    """Configurable stand-in for subprocess.run."""

    def __init__(self, returncode=0, stderr="", side_effect=None):
        self.returncode = returncode
        self.stderr = stderr
        self.side_effect = side_effect
        self.calls = []

    def __call__(self, cmd, **kwargs):
        self.calls.append((cmd, kwargs))
        if self.side_effect:
            self.side_effect(cmd)
        result = MagicMock()
        result.returncode = self.returncode
        result.stderr = self.stderr
        result.stdout = ""
        return result


class TestIsEnabled:
    def test_default_off(self):
        assert is_enabled(_StubConfig()) is False

    def test_explicit_on(self):
        assert is_enabled(_enabled_config()) is True

    def test_none_config_is_off(self):
        assert is_enabled(None) is False


class TestResolveStccPath:
    def test_unconfigured(self, tmp_path):
        assert resolve_stcc_path(_StubConfig()) is None

    def test_missing_on_disk(self, tmp_path):
        assert resolve_stcc_path(_enabled_config(stcc=str(tmp_path / "nope.py"))) is None

    def test_existing(self, tmp_path):
        stcc = tmp_path / "stcc.py"
        stcc.write_text("# stub", encoding="utf-8")
        assert resolve_stcc_path(_enabled_config(stcc=str(stcc))) == stcc


class TestBuildCommand:
    def test_minimal(self, tmp_path):
        cmd = build_stcc_command(Path(_STCC), tmp_path / "a.mp4", tmp_path / "out", "compressed_a")
        assert cmd[0] != "" and cmd[1] == str(Path(_STCC)) and cmd[2] == "transcribe"
        assert cmd[cmd.index("--formats") + 1] == "srt,vtt"
        assert cmd[cmd.index("--name") + 1] == "compressed_a"
        assert cmd[cmd.index("--output-dir") + 1] == str(tmp_path / "out")
        assert "--threads" not in cmd
        assert cmd[-1] == str(tmp_path / "a.mp4")

    def test_threads_passthrough(self, tmp_path):
        cmd = build_stcc_command(Path(_STCC), tmp_path / "a.mp4", tmp_path, "a", threads=6)
        assert cmd[cmd.index("--threads") + 1] == "6"


class TestTranscribeAfterCompress:
    def test_none_config_skips(self, tmp_path):
        with patch.object(subprocess, "run") as run:
            assert transcribe_after_compress(tmp_path / "a.mp4", tmp_path / "compressed_a.mp4", None) is None
        run.assert_not_called()

    def test_disabled_skips(self, tmp_path):
        with patch.object(subprocess, "run") as run:
            assert transcribe_after_compress(tmp_path / "a.mp4", tmp_path / "compressed_a.mp4", _StubConfig()) is None
        run.assert_not_called()

    def test_unconfigured_stcc_skips(self, tmp_path):
        with patch.object(subprocess, "run") as run:
            assert (
                transcribe_after_compress(tmp_path / "a.mp4", tmp_path / "compressed_a.mp4", _enabled_config(stcc="")) is None
            )
        run.assert_not_called()

    def test_missing_stcc_skips(self, tmp_path):
        cfg = _enabled_config(stcc=str(tmp_path / "nope.py"))
        with patch.object(subprocess, "run") as run:
            assert transcribe_after_compress(tmp_path / "a.mp4", tmp_path / "compressed_a.mp4", cfg) is None
        run.assert_not_called()

    def test_success_writes_srt_and_muxes(self, tmp_path):
        # import inside the test: other suites delete sys.modules entries, and
        # patch target + function must resolve to the same module object
        import filesqueeze.ops.transcription as tr

        original = tmp_path / "a.mp4"
        compressed = tmp_path / "out" / "compressed_a.mp4"
        compressed.parent.mkdir()
        compressed.write_bytes(b"v")
        srt = tmp_path / "out" / "compressed_a.srt"
        stcc = tmp_path / "stcc.py"
        stcc.write_text("# stub", encoding="utf-8")

        captured = []

        def fake_run(cmd, **kwargs):
            captured.append(cmd)
            srt.write_text("captions", encoding="utf-8")
            return MagicMock(returncode=0, stderr="")

        with patch.object(subprocess, "run", fake_run), patch.object(tr, "mux_subtitles", return_value=True) as mux:
            result = tr.transcribe_after_compress(original, compressed, _enabled_config(stcc=str(stcc)))
        assert result == srt
        cmd = captured[0]
        assert cmd[cmd.index("--name") + 1] == "compressed_a"
        assert cmd[cmd.index("--output-dir") + 1] == str(compressed.parent)
        assert cmd[-1] == str(original)  # original, not compressed, is transcribed
        mux.assert_called_once()
        assert mux.call_args.args[0] == compressed
        assert mux.call_args.args[1] == srt

    def test_nonzero_exit_returns_none(self, tmp_path):
        compressed = tmp_path / "compressed_a.mp4"
        with (
            patch.object(subprocess, "run", _FakeRun(returncode=4, stderr="boom")),
            patch("filesqueeze.ops.transcription.mux_subtitles") as mux,
        ):
            assert transcribe_after_compress(tmp_path / "a.mp4", compressed, _enabled_config()) is None
        mux.assert_not_called()

    def test_missing_srt_after_success_returns_none(self, tmp_path):
        with patch.object(subprocess, "run", _FakeRun(returncode=0)):
            assert transcribe_after_compress(tmp_path / "a.mp4", tmp_path / "compressed_a.mp4", _enabled_config()) is None

    def test_non_mp4_output_skips_mux(self, tmp_path):
        original = tmp_path / "a.mkv"
        compressed = tmp_path / "compressed_a.mkv"
        srt = tmp_path / "compressed_a.srt"
        stcc = tmp_path / "stcc.py"
        stcc.write_text("# stub", encoding="utf-8")

        def fake_run(cmd, **kwargs):
            srt.write_text("c", encoding="utf-8")
            return MagicMock(returncode=0, stderr="")

        with patch.object(subprocess, "run", fake_run), patch("filesqueeze.ops.transcription.mux_subtitles") as mux:
            result = transcribe_after_compress(original, compressed, _enabled_config(stcc=str(stcc)))
        assert result == srt
        mux.assert_not_called()


class TestMuxSubtitles:
    def test_success_replaces_video_in_place(self, tmp_path, monkeypatch):
        video = tmp_path / "compressed_a.mp4"
        video.write_bytes(b"video-without-subs")
        srt = tmp_path / "compressed_a.srt"
        srt.write_text("c", encoding="utf-8")

        captured = {}

        def fake_run(cmd, **kwargs):
            captured["cmd"] = cmd
            Path(cmd[-1]).write_bytes(b"video-with-subs")
            result = MagicMock()
            result.returncode = 0
            return result

        monkeypatch.setattr("filesqueeze.ops.transcription.subprocess.run", fake_run)
        assert mux_subtitles(video, srt, Path("ffmpeg")) is True
        assert video.read_bytes() == b"video-with-subs"
        joined = " ".join(captured["cmd"])
        assert "-c:s mov_text" in joined
        assert str(video) in joined  # muxing the compressed video
        assert "muxtmp" in captured["cmd"][-1]  # staged to a temp file

    def test_failure_returns_false_and_cleans_tmp(self, tmp_path, monkeypatch):
        video = tmp_path / "compressed_a.mp4"
        video.write_bytes(b"video")
        srt = tmp_path / "compressed_a.srt"
        srt.write_text("c", encoding="utf-8")

        result = MagicMock()
        result.returncode = 1
        result.stderr = "bad"
        monkeypatch.setattr("filesqueeze.ops.transcription.subprocess.run", lambda cmd, **k: result)
        assert mux_subtitles(video, srt, Path("ffmpeg")) is False
        assert video.read_bytes() == b"video"  # untouched
        assert not list(tmp_path.glob("*muxtmp*"))


class TestBackwardCompat:
    def test_config_without_section_defaults_to_off(self, tmp_path):
        with patch.object(subprocess, "run") as run:
            assert transcribe_after_compress(tmp_path / "a.mp4", tmp_path / "compressed_a.mp4", _StubConfig()) is None
        run.assert_not_called()


if __name__ == "__main__":
    pytest.main([__file__])
