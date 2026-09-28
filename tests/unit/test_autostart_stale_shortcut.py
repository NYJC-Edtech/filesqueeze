"""Unit tests for stale system-wide shortcut detection in filesqueeze.autostart."""

from pathlib import Path

from filesqueeze.autostart import extract_script_path_from_arguments, warn_stale_system_wide_shortcut


def test_extract_script_path_quoted():
    """Test extraction with a quoted -File path (standard shortcut format)."""
    arguments = '-ExecutionPolicy Bypass -WindowStyle Hidden -File "C:\\Program Files\\FileSqueeze\\wrapper.ps1"'
    assert extract_script_path_from_arguments(arguments) == Path("C:\\Program Files\\FileSqueeze\\wrapper.ps1")


def test_extract_script_path_unquoted():
    """Test extraction with an unquoted -File path."""
    arguments = "-ExecutionPolicy Bypass -File C:\\temp\\wrapper.ps1"
    assert extract_script_path_from_arguments(arguments) == Path("C:\\temp\\wrapper.ps1")


def test_extract_script_path_no_file_flag():
    """Test that None is returned when there is no -File argument."""
    assert extract_script_path_from_arguments("-ExecutionPolicy Bypass -WindowStyle Hidden") is None


def test_extract_script_path_empty_arguments():
    """Test that None is returned for empty arguments."""
    assert extract_script_path_from_arguments("") is None


def test_warn_prints_warning_when_stale_shortcut_found(monkeypatch, capsys):
    """Test that a warning including the shortcut location is printed."""
    fake_shortcut = Path("C:\\ProgramData\\fake\\FileSqueeze.lnk")
    monkeypatch.setattr("filesqueeze.autostart.get_stale_system_wide_shortcut", lambda: fake_shortcut)

    warn_stale_system_wide_shortcut()

    output = capsys.readouterr().out
    assert "WARNING" in output
    assert str(fake_shortcut) in output
    assert "elevated" in output


def test_warn_is_silent_when_no_stale_shortcut(monkeypatch, capsys):
    """Test that nothing is printed when no stale shortcut exists."""
    monkeypatch.setattr("filesqueeze.autostart.get_stale_system_wide_shortcut", lambda: None)

    warn_stale_system_wide_shortcut()

    assert capsys.readouterr().out == ""
