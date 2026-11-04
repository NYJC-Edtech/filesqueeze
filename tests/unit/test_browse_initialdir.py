"""Tests for the Browse start-location gating and the tray-spawned dialog process.

The Browse hang (2026-11-04): native pickers seeded with a cloud/removable
folder block enumerating it while the provider stalls — the dialog never
paints and the owning window ghosts as "(Not Responding)". The fix gates
every picker's initialdir on local fixed drives (GetDriveTypeW on the drive
root — no path I/O), falls back to the user's Documents folder, else omits
initialdir; the tray now spawns the dialog as a separate process so a wedged
picker can never take the service down. Imports of ``filesqueeze`` modules
happen INSIDE the test functions (see tests/unit/test_doctor_autostart.py
for why).
"""

import os
import sys

import pytest

pytest.importorskip("tkinter", reason="tkinter not available")


class TestDriveIsLocalFixed:
    def test_home_drive_is_local_on_windows(self):
        if os.name != "nt":
            pytest.skip("drive types are a Windows concept")
        from filesqueeze.gui_compress import drive_is_local_fixed

        assert drive_is_local_fixed(os.path.expanduser("~")) is True

    def test_unc_path_is_not_local(self):
        if os.name != "nt":
            pytest.skip("drive types are a Windows concept")
        from filesqueeze.gui_compress import drive_is_local_fixed

        assert drive_is_local_fixed(r"\\server\share\folder") is False

    def test_relative_path_is_not_local(self):
        if os.name != "nt":
            pytest.skip("drive types are a Windows concept")
        from filesqueeze.gui_compress import drive_is_local_fixed

        assert drive_is_local_fixed("just-a-name.mp4") is False

    def test_everything_is_local_off_windows(self):
        if os.name == "nt":
            pytest.skip("only meaningful on non-Windows, where the gate is a pass-through")
        from filesqueeze.gui_compress import drive_is_local_fixed

        assert drive_is_local_fixed(r"\\server\share\folder") is True
        assert drive_is_local_fixed("relative/name") is True


class TestSafeInitialdir:
    def test_first_local_candidate_wins(self, monkeypatch):
        from filesqueeze.gui_compress import safe_initialdir

        monkeypatch.setattr("filesqueeze.gui_compress.drive_is_local_fixed", lambda p: p == "C:/local")
        monkeypatch.setattr("filesqueeze.gui_compress.documents_folder", lambda: "C:/Users/x/Documents")

        assert safe_initialdir("G:/cloud/dir", "C:/local") == "C:/local"

    def test_skips_non_local_candidates(self, monkeypatch):
        from filesqueeze.gui_compress import safe_initialdir

        monkeypatch.setattr("filesqueeze.gui_compress.drive_is_local_fixed", lambda p: False)
        monkeypatch.setattr("filesqueeze.gui_compress.documents_folder", lambda: "C:/Users/x/Documents")

        assert safe_initialdir("G:/cloud/dir", "D:/usb/dir") == "C:/Users/x/Documents"

    def test_returns_none_when_nothing_is_safe(self, monkeypatch):
        from filesqueeze.gui_compress import safe_initialdir

        monkeypatch.setattr("filesqueeze.gui_compress.drive_is_local_fixed", lambda p: False)
        monkeypatch.setattr("filesqueeze.gui_compress.documents_folder", lambda: None)

        assert safe_initialdir("G:/cloud/dir") is None

    def test_none_and_empty_candidates_are_skipped(self, monkeypatch):
        from filesqueeze.gui_compress import safe_initialdir

        seen: list[str] = []

        def gate(path):
            seen.append(path)
            return path == "C:/ok"

        monkeypatch.setattr("filesqueeze.gui_compress.drive_is_local_fixed", gate)
        monkeypatch.setattr("filesqueeze.gui_compress.documents_folder", lambda: None)

        assert safe_initialdir(None, "", "C:/ok") == "C:/ok"
        assert seen == ["C:/ok"]

    def test_documents_fallback_is_gated_too(self, monkeypatch):
        """Documents can itself be cloud-redirected; then nothing qualifies."""
        from filesqueeze.gui_compress import safe_initialdir

        monkeypatch.setattr("filesqueeze.gui_compress.drive_is_local_fixed", lambda p: p.startswith("C:/"))
        monkeypatch.setattr("filesqueeze.gui_compress.documents_folder", lambda: None)

        assert safe_initialdir("G:/cloud/dir") is None


class TestTraySpawnsDialogProcess:
    """The tray runs the dialog as a separate compress --gui process."""

    @pytest.fixture
    def service(self, tmp_path):
        import ctypes

        from filesqueeze.config import Config
        from filesqueeze.tray import TrayService

        input_dir = tmp_path / "input"
        output_dir = tmp_path / "output"
        input_dir.mkdir()
        output_dir.mkdir()
        svc = TrayService(input_dir, output_dir, Config())
        yield svc
        # TrayService.__init__ acquires the single-instance mutex; release it
        # so the next test's construction is not rejected as a second instance
        if getattr(svc, "_mutex", None):
            ctypes.windll.kernel32.ReleaseMutex(svc._mutex)
            ctypes.windll.kernel32.CloseHandle(svc._mutex)
            svc._mutex = None

    def test_spawns_dialog_as_separate_process(self, service, monkeypatch):
        import filesqueeze.tray as tray_mod

        calls: list[tuple[list[str], int]] = []

        def fake_popen(cmd, creationflags=0):
            calls.append((list(cmd), creationflags))

            class FakeProc:
                def __init__(self):
                    self._rc = None

                def poll(self):
                    return self._rc

            return FakeProc()

        monkeypatch.setattr(tray_mod.subprocess, "Popen", fake_popen)

        service._on_compress_file(None, None)

        cmd, flags = calls[0]
        assert cmd[:2] == [sys.executable, "-P"]
        assert cmd[2:6] == ["-m", "filesqueeze", "compress", "--gui"]
        assert "--no-update-check" in cmd
        if os.name == "nt":
            import subprocess

            assert flags == subprocess.CREATE_NO_WINDOW
        assert service._compress_dialog is not None

    def test_second_click_while_alive_does_not_respawn(self, service, monkeypatch):
        import filesqueeze.tray as tray_mod

        calls: list[list[str]] = []

        def fake_popen(cmd, creationflags=0):
            calls.append(list(cmd))

            class FakeProc:
                def poll(self):
                    return None  # still running

            return FakeProc()

        monkeypatch.setattr(tray_mod.subprocess, "Popen", fake_popen)

        service._on_compress_file(None, None)
        service._on_compress_file(None, None)

        assert len(calls) == 1

    def test_click_after_exit_spawns_again(self, service, monkeypatch):
        import filesqueeze.tray as tray_mod

        calls: list[list[str]] = []

        def fake_popen(cmd, creationflags=0):
            calls.append(list(cmd))

            class FakeProc:
                def poll(self):
                    return 0  # exited

            return FakeProc()

        monkeypatch.setattr(tray_mod.subprocess, "Popen", fake_popen)

        service._on_compress_file(None, None)
        service._on_compress_file(None, None)

        assert len(calls) == 2

    def test_spawn_failure_is_contained(self, service, monkeypatch):
        import filesqueeze.tray as tray_mod

        def failing_popen(cmd, creationflags=0):
            raise OSError("no interpreter")

        monkeypatch.setattr(tray_mod.subprocess, "Popen", failing_popen)

        service._on_compress_file(None, None)

        assert service._compress_dialog is None

    def test_fresh_launch_not_rejected_by_stale_last_error(self, tmp_path):
        """A leftover ERROR_ALREADY_EXISTS on the thread must not block a launch.

        Regression: GetLastError() after CreateMutexW could read a stale 183
        left by an earlier failed CreateDirectory (mkdir exist_ok) and reject
        a fresh instance as a second one. Windows-only: other platforms never
        create the mutex.
        """
        if os.name != "nt":
            pytest.skip("single-instance mutex is Windows-only")
        import ctypes

        from filesqueeze.config import Config
        from filesqueeze.tray import TrayService

        existing = tmp_path / "exists"
        existing.mkdir()
        try:
            os.mkdir(existing)  # primes the thread's Win32 last error with 183
        except FileExistsError:
            pass

        input_dir = tmp_path / "input2"
        output_dir = tmp_path / "output2"
        input_dir.mkdir()
        output_dir.mkdir()
        svc = TrayService(input_dir, output_dir, Config())

        assert svc._mutex
        ctypes.windll.kernel32.ReleaseMutex(svc._mutex)
        ctypes.windll.kernel32.CloseHandle(svc._mutex)
        svc._mutex = None

    def test_task_gate_ignores_dialog_process(self, service, monkeypatch):
        """A busy dialog process survives the update handoff by design."""
        import filesqueeze.tray as tray_mod

        monkeypatch.setattr(
            tray_mod.subprocess,
            "Popen",
            lambda cmd, creationflags=0: type("P", (), {"poll": lambda self: None})(),
        )
        service._on_compress_file(None, None)

        class FakeWatcher:
            def get_state(self):
                class S:
                    def __init__(self):
                        self.processing_files = []

                return S()

        service.watcher = FakeWatcher()

        assert service._has_running_tasks() is False
