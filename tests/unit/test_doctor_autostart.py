"""Unit tests for the doctor's auto-start check.

Imports of ``filesqueeze`` modules happen INSIDE the test functions: the
circular-import system tests delete sys.modules entries, so a module-level
import can bind a stale module object while monkeypatch's string target
re-imports a fresh one (same discipline as test_autostart_stale_shortcut.py).
"""

import sys


def _make_doctor():
    """Build a Doctor with fresh result lists, skipping dependency probing."""
    from filesqueeze.doctor import Doctor

    doctor = Doctor.__new__(Doctor)
    doctor.issues = []
    doctor.warnings = []
    doctor.passed = []
    return doctor


def _patch_win32(monkeypatch):
    """Force the Windows path in check_autostart (CI runs on Linux)."""
    monkeypatch.setattr(sys, "platform", "win32")


def test_doctor_warns_when_no_autostart_installed(monkeypatch):
    """Neither shortcut present: record a warning that names the fix."""
    _patch_win32(monkeypatch)
    monkeypatch.setattr("filesqueeze.autostart.check_autostart_installed", lambda system_wide: False)
    monkeypatch.setattr("filesqueeze.autostart.get_stale_system_wide_shortcut", lambda: None)

    doctor = _make_doctor()
    ok = doctor.check_autostart()

    assert ok is False
    assert any("Auto-start not installed" in w for w in doctor.warnings)
    assert any("filesqueeze service install" in w for w in doctor.warnings)
    assert doctor.passed == []


def test_doctor_passes_for_system_wide_autostart(monkeypatch):
    _patch_win32(monkeypatch)
    monkeypatch.setattr("filesqueeze.autostart.check_autostart_installed", lambda system_wide: system_wide)
    monkeypatch.setattr("filesqueeze.autostart.get_stale_system_wide_shortcut", lambda: None)

    doctor = _make_doctor()
    ok = doctor.check_autostart()

    assert ok is True
    assert any("Auto-start installed (system-wide)" in p for p in doctor.passed)
    assert doctor.warnings == []


def test_doctor_passes_for_user_autostart(monkeypatch):
    _patch_win32(monkeypatch)
    monkeypatch.setattr("filesqueeze.autostart.check_autostart_installed", lambda system_wide: not system_wide)
    monkeypatch.setattr("filesqueeze.autostart.get_stale_system_wide_shortcut", lambda: None)

    doctor = _make_doctor()
    ok = doctor.check_autostart()

    assert ok is True
    assert any("Auto-start installed (user)" in p for p in doctor.passed)
    assert doctor.warnings == []


def test_doctor_warns_when_system_wide_shortcut_is_stale(monkeypatch):
    """A shortcut pointing at a missing script fails silently every boot."""
    from pathlib import Path

    _patch_win32(monkeypatch)
    fake_shortcut = Path("C:\\ProgramData\\fake\\FileSqueeze.lnk")
    monkeypatch.setattr("filesqueeze.autostart.get_stale_system_wide_shortcut", lambda: fake_shortcut)

    doctor = _make_doctor()
    ok = doctor.check_autostart()

    assert ok is False
    assert any(str(fake_shortcut) in w for w in doctor.warnings)
    assert any("will not start on boot" in w for w in doctor.warnings)


def test_doctor_skips_autostart_check_off_windows(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")

    doctor = _make_doctor()
    ok = doctor.check_autostart()

    assert ok is True
    assert doctor.warnings == []
    assert doctor.passed == []
