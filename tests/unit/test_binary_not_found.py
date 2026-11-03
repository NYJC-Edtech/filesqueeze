"""Unit tests for BinaryNotFoundError and the parseable-logging contract.

Missing binaries are expected, actionable failures: they raise a typed
error whose message starts with the stable ``binary_not_found:`` prefix,
and the trace_function decorator logs that single line instead of a full
traceback. Imports of ``filesqueeze`` modules happen INSIDE the test
functions (see tests/unit/test_doctor_autostart.py for why).
"""

from pathlib import Path

import pytest


def test_binary_not_found_subclasses_runtime_error():
    """Callers catching RuntimeError (the old contract) keep working."""
    from filesqueeze.system.binaries import BinaryNotFoundError

    assert issubclass(BinaryNotFoundError, RuntimeError)


def test_auto_detect_failure_message_is_parseable(monkeypatch):
    """Auto-detect failure: stable prefix, binary name, and search scope."""
    from filesqueeze.config import Config
    from filesqueeze.system.binaries import BinaryFinder, BinaryNotFoundError

    finder = BinaryFinder(Config({}))
    monkeypatch.setattr(finder, "find_ffmpeg", lambda: (None, "Not found in common locations"))

    with pytest.raises(BinaryNotFoundError) as excinfo:
        finder.get_ffmpeg_path()
    message = str(excinfo.value)
    assert message.startswith("binary_not_found: ffmpeg")
    assert "Not found in common locations" in message


def test_configured_directory_is_rejected(tmp_path):
    """A configured path that is a folder (not the .exe) fails fast, clearly."""
    from filesqueeze.config import Config
    from filesqueeze.system.binaries import BinaryFinder, BinaryNotFoundError

    finder = BinaryFinder(Config(config_path={"ffmpeg": {"path": str(tmp_path)}}))

    with pytest.raises(BinaryNotFoundError, match="binary_not_found: ffmpeg"):
        finder.get_ffmpeg_path()


def test_configured_missing_path_reports_config_key(tmp_path):
    from filesqueeze.config import Config
    from filesqueeze.system.binaries import BinaryFinder, BinaryNotFoundError

    missing = str(tmp_path / "nowhere" / "ffmpeg.exe")
    finder = BinaryFinder(Config(config_path={"ffmpeg": {"path": missing}}))

    with pytest.raises(BinaryNotFoundError) as excinfo:
        finder.get_ffmpeg_path()
    assert "ffmpeg.path" in str(excinfo.value)
    assert missing in str(excinfo.value)


def test_bare_command_name_is_not_validated(monkeypatch):
    """A bare name (no separators) is PATH-resolved later, not rejected here."""
    from filesqueeze.config import Config
    from filesqueeze.system.binaries import BinaryFinder

    finder = BinaryFinder(Config(config_path={"ffmpeg": {"path": "ffmpeg"}}))
    assert finder.get_ffmpeg_path() == Path("ffmpeg")


def test_trace_function_logs_single_line_for_binary_not_found(monkeypatch):
    """Missing-binary failures log the message once, without a traceback."""
    import importlib

    from filesqueeze.config import Config
    from filesqueeze.system import decorators
    from filesqueeze.system.binaries import BinaryFinder, BinaryNotFoundError

    error_logs: list[tuple[tuple, dict]] = []

    class FakeLogger:
        def debug(self, *args, **kwargs):
            pass

        def error(self, *args, **kwargs):
            error_logs.append((args, kwargs))

    # filesqueeze.system.logger is shadowed by a lazy wrapper attribute on the
    # package, so resolve the actual module through sys.modules.
    logger_module = importlib.import_module("filesqueeze.system.logger")
    monkeypatch.setattr(logger_module, "get_logger", lambda: FakeLogger())

    @decorators.trace_function
    def boom() -> None:
        finder = BinaryFinder(Config({}))
        monkeypatch.setattr(finder, "find_ffmpeg", lambda: (None, "Not found in common locations"))
        finder.get_ffmpeg_path()

    with pytest.raises(BinaryNotFoundError):
        boom()

    assert len(error_logs) == 1
    args, kwargs = error_logs[0]
    assert args[0].startswith("binary_not_found: ffmpeg")
    assert not kwargs.get("exc_info"), "expected no traceback for typed binary errors"


def test_trace_function_keeps_traceback_for_unexpected_errors(monkeypatch):
    """Unexpected exceptions keep the old full-traceback logging."""
    import importlib

    from filesqueeze.system import decorators

    error_logs: list[tuple[tuple, dict]] = []

    class FakeLogger:
        def debug(self, *args, **kwargs):
            pass

        def error(self, *args, **kwargs):
            error_logs.append((args, kwargs))

    logger_module = importlib.import_module("filesqueeze.system.logger")
    monkeypatch.setattr(logger_module, "get_logger", lambda: FakeLogger())

    @decorators.trace_function
    def boom() -> None:
        raise ValueError("unexpected")

    with pytest.raises(ValueError):
        boom()

    assert len(error_logs) == 1
    args, kwargs = error_logs[0]
    assert args[0] == "Function failed: boom"
    assert kwargs.get("exc_info") is True
