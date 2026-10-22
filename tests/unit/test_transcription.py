"""Tests for the stcc startup existence check (filesqueeze.transcription)."""

import logging

import pytest

from filesqueeze.transcription import get_stcc_path, log_stcc_status


class _StubConfig:
    def __init__(self, stcc_path: str = ""):
        self._stcc_path = stcc_path

    def get(self, key, default=None):
        assert key == "transcription.stcc_path"
        return self._stcc_path if self._stcc_path else default


@pytest.fixture
def caplog_info(caplog):
    caplog.set_level(logging.DEBUG)
    return caplog


def test_get_stcc_path_empty_when_unconfigured():
    assert get_stcc_path(_StubConfig()) == ""


def test_get_stcc_path_returns_configured_value(tmp_path):
    assert get_stcc_path(_StubConfig(str(tmp_path / "stcc.py"))) == str(tmp_path / "stcc.py")


def test_log_status_not_configured(caplog):
    with caplog.at_level(logging.INFO, logger="filesqueeze-test"):
        log_stcc_status(_StubConfig(), logging.getLogger("filesqueeze-test"))
    messages = [r.getMessage() for r in caplog.records]
    assert any("not configured" in m for m in messages)
    assert not any("missing" in m for m in messages)


def test_log_status_available(tmp_path, caplog):
    stcc = tmp_path / "stcc.py"
    stcc.write_text("# stub", encoding="utf-8")
    with caplog.at_level(logging.INFO, logger="filesqueeze-test"):
        log_stcc_status(_StubConfig(str(stcc)), logging.getLogger("filesqueeze-test"))
    messages = [r.getMessage() for r in caplog.records]
    assert any("available" in m and str(stcc) in m for m in messages)


def test_log_status_missing_warns(tmp_path, caplog):
    missing = tmp_path / "gone" / "stcc.py"
    with caplog.at_level(logging.WARNING, logger="filesqueeze-test"):
        log_stcc_status(_StubConfig(str(missing)), logging.getLogger("filesqueeze-test"))
    warnings = [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]
    assert any("configured but missing" in m and str(missing) in m for m in warnings)
