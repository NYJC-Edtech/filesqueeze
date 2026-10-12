"""Unit tests for filesqueeze.updater (download/apply releases, issue #35).

Imports of ``filesqueeze`` happen INSIDE the test functions: the circular-import
system tests delete sys.modules entries, and a module-level import would bind a
stale module object while unittest.mock's patch() re-imports a fresh one.
"""

import json
import os
import threading
import time
import zipfile
from unittest.mock import patch

import pytest


def _make_wheel(directory, version="0.9.3", name=None, metadata=None, filename_version=None):
    """Build a minimal-but-valid wheel file; returns its path."""
    directory = str(directory)
    if name is None:
        name = f"filesqueeze-{filename_version or version}-py3-none-any.whl"
    if metadata is None:
        metadata = f"Metadata-Version: 2.1\nName: filesqueeze\nVersion: {version}\n"
    path = f"{directory}/{name}"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(f"filesqueeze-{version}.dist-info/METADATA", metadata)
        archive.writestr("filesqueeze/__init__.py", "")
    return path


def _update_info(version="v0.9.3", wheel_url="https://example.com/filesqueeze-0.9.3-py3-none-any.whl"):
    from filesqueeze.update_check import UpdateInfo

    return UpdateInfo(
        current_version="0.9.2", latest_version=version, download_url="https://example.com/releases", wheel_url=wheel_url
    )


class _FakeResponse:
    """Fake urlopen() return value streaming fixed chunks with a Content-Length."""

    def __init__(self, chunks, content_length=None):
        self._chunks = list(chunks)
        self.headers = {"Content-Length": str(content_length) if content_length is not None else ""}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, size=-1):
        if not self._chunks:
            return b""
        return self._chunks.pop(0)


class TestHelpers:
    def test_normalize_version_strips_v_prefix(self):
        from filesqueeze.updater import normalize_version

        assert normalize_version("v0.9.3") == "0.9.3"
        assert normalize_version("0.9.3") == "0.9.3"

    def test_wheel_filename_matches_release_asset_naming(self):
        from filesqueeze.updater import wheel_filename

        assert wheel_filename("v0.9.3") == "filesqueeze-0.9.3-py3-none-any.whl"

    def test_build_pip_command_reinstalls_only_filesqueeze(self):
        import sys

        from filesqueeze.updater import build_pip_command

        command = build_pip_command("/tmp/wheel.whl")
        assert command[0] == sys.executable
        assert command[1:4] == ["-m", "pip", "install"]
        assert "--force-reinstall" in command
        assert "--no-deps" in command  # never a PyPI roundtrip on apply
        assert command[-1] == "/tmp/wheel.whl"

    def test_build_relaunch_command_preserves_cli_arguments(self):
        import sys

        from filesqueeze.updater import build_relaunch_command

        relaunch = build_relaunch_command(["ignored-path", "service", "run", "--input", "D:/watch"])
        assert relaunch == [sys.executable, "-m", "filesqueeze", "service", "run", "--input", "D:/watch"]


class TestVerifyWheel:
    def test_accepts_a_matching_wheel(self, tmp_path):
        from filesqueeze.updater import verify_wheel

        wheel = _make_wheel(tmp_path, version="0.9.3")
        verify_wheel(wheel, "v0.9.3")  # should not raise

    def test_rejects_unexpected_filename(self, tmp_path):
        from filesqueeze.updater import UpdateError, verify_wheel

        wheel = _make_wheel(tmp_path, version="0.9.3", name="totally-not-a-wheel.whl")
        with pytest.raises(UpdateError, match="Unexpected update artifact"):
            verify_wheel(wheel, "v0.9.3")

    def test_rejects_corrupt_zip(self, tmp_path):
        from filesqueeze.updater import UpdateError, verify_wheel

        wheel = _make_wheel(tmp_path, version="0.9.3")
        with open(wheel, "wb") as f:
            f.write(b"this is not a zip file")
        with pytest.raises(UpdateError, match="corrupt"):
            verify_wheel(wheel, "v0.9.3")

    def test_rejects_wrong_version_inside_metadata(self, tmp_path):
        from filesqueeze.updater import UpdateError, verify_wheel

        # Filename promises 0.9.3; the embedded METADATA says 0.9.2
        wheel = _make_wheel(tmp_path, version="0.9.2", name="filesqueeze-0.9.3-py3-none-any.whl")
        with pytest.raises(UpdateError, match=r"expected filesqueeze v0\.9\.3"):
            verify_wheel(wheel, "v0.9.3")

    def test_rejects_foreign_package(self, tmp_path):
        from filesqueeze.updater import UpdateError, verify_wheel

        metadata = "Metadata-Version: 2.1\nName: something-else\nVersion: 0.9.3\n"
        wheel = _make_wheel(tmp_path, version="0.9.3", name="filesqueeze-0.9.3-py3-none-any.whl", metadata=metadata)
        with pytest.raises(UpdateError, match="something-else"):
            verify_wheel(wheel, "v0.9.3")


class TestCanSelfUpdate:
    def test_true_for_wheel_release_on_installed_layout(self):
        from filesqueeze.updater import can_self_update

        with patch("filesqueeze.updater.is_dev_checkout", return_value=False):
            ok, reason = can_self_update(_update_info())

        assert ok is True
        assert reason == ""

    def test_false_in_dev_checkout(self):
        from filesqueeze.updater import can_self_update

        with patch("filesqueeze.updater.is_dev_checkout", return_value=True):
            ok, reason = can_self_update(_update_info())

        assert ok is False
        assert "git pull" in reason

    def test_false_without_a_published_wheel(self):
        from filesqueeze.updater import can_self_update

        with patch("filesqueeze.updater.is_dev_checkout", return_value=False):
            ok, reason = can_self_update(_update_info(wheel_url=None))

        assert ok is False
        assert "releases page" in reason


class TestDownloadWheel:
    def test_streams_to_a_temp_file_with_progress(self, tmp_path):
        from filesqueeze.updater import download_wheel

        chunks = [b"x" * 70000, b"y" * 100]
        progress_calls = []
        with patch("filesqueeze.updater.urllib.request.urlopen", return_value=_FakeResponse(chunks, content_length=70100)):
            wheel = download_wheel(_update_info(), tmp_path, progress=lambda done, total: progress_calls.append((done, total)))

        assert wheel.name == "filesqueeze-0.9.3-py3-none-any.whl"
        assert wheel.read_bytes() == b"".join(chunks)
        assert progress_calls[0] == (70000, 70100)
        assert progress_calls[-1] == (70100, 70100)

    def test_cancel_removes_partial_file(self, tmp_path):
        from filesqueeze.updater import UpdateCancelled, download_wheel

        cancel = threading.Event()
        chunks = [b"x" * 70000, b"y" * 100]
        with patch("filesqueeze.updater.urllib.request.urlopen", return_value=_FakeResponse(chunks, content_length=70100)):
            with pytest.raises(UpdateCancelled):
                download_wheel(_update_info(), tmp_path, cancel=cancel, progress=lambda done, total: cancel.set())

        assert not (tmp_path / "filesqueeze-0.9.3-py3-none-any.whl").exists()

    def test_network_failure_raises_update_error(self, tmp_path):
        import urllib.error

        from filesqueeze.updater import UpdateError, download_wheel

        with patch("filesqueeze.updater.urllib.request.urlopen", side_effect=urllib.error.URLError("no route")):
            with pytest.raises(UpdateError, match="Download failed"):
                download_wheel(_update_info(), tmp_path)

        assert not (tmp_path / "filesqueeze-0.9.3-py3-none-any.whl").exists()

    def test_truncated_download_is_rejected(self, tmp_path):
        from filesqueeze.updater import UpdateError, download_wheel

        # Server promised 1000 bytes but the stream ended early
        with patch(
            "filesqueeze.updater.urllib.request.urlopen", return_value=_FakeResponse([b"x" * 100], content_length=1000)
        ):
            with pytest.raises(UpdateError, match="incomplete"):
                download_wheel(_update_info(), tmp_path)

    def test_requires_a_wheel_url(self, tmp_path):
        from filesqueeze.updater import UpdateError, download_wheel

        with pytest.raises(UpdateError, match="wheel"):
            download_wheel(_update_info(wheel_url=None), tmp_path)


class TestUpdateProgress:
    def test_percent_known_and_unknown(self):
        from filesqueeze.updater import UpdateProgress

        assert UpdateProgress(phase="downloading", downloaded=50, total=200).percent == 25
        assert UpdateProgress(phase="downloading", downloaded=50).percent is None
        assert UpdateProgress(phase="downloading", downloaded=400, total=200).percent == 100


class TestUpdateController:
    def _wait(self, controller, timeout=5.0):
        thread = controller._thread
        if thread is not None:
            thread.join(timeout=timeout)

    def _wait_for_phase(self, controller, phase, timeout=5.0):
        deadline = time.time() + timeout
        while time.time() < deadline:
            if controller.snapshot().phase == phase:
                return True
            time.sleep(0.05)
        return False

    @pytest.fixture(autouse=True)
    def _installed_layout(self):
        # Tests run inside the repo checkout, where the real check returns True;
        # controller semantics here assume an installed (self-updatable) layout.
        with patch("filesqueeze.updater.is_dev_checkout", return_value=False):
            yield

    def test_start_happy_path_hands_off_and_calls_on_applied(self, tmp_path):
        from filesqueeze.updater import PHASE_DONE, UpdateController

        wheel = _make_wheel(tmp_path)
        applied = threading.Event()
        controller = UpdateController()

        with (
            patch("filesqueeze.updater.download_wheel", return_value=wheel) as mock_download,
            patch("filesqueeze.updater.verify_wheel") as mock_verify,
            patch("filesqueeze.updater.spawn_updater") as mock_spawn,
        ):
            assert controller.start(_update_info(), restart=True, on_applied=applied.set) is True
            self._wait(controller)

        mock_download.assert_called_once()
        mock_verify.assert_called_once_with(wheel, "0.9.3")
        mock_spawn.assert_called_once()
        assert mock_spawn.call_args.args[1] is not None  # relaunch command present
        assert applied.is_set()
        assert controller.snapshot().phase == PHASE_DONE
        assert "restart" in controller.snapshot().message.lower()
        # Must not claim the install happened: pip runs only after this process exits
        assert "installed" not in controller.snapshot().message.lower()

    def test_start_without_restart_installs_quietly(self, tmp_path):
        from filesqueeze.updater import PHASE_DONE, UpdateController

        wheel = _make_wheel(tmp_path)
        applied = threading.Event()
        controller = UpdateController()

        with (
            patch("filesqueeze.updater.download_wheel", return_value=wheel),
            patch("filesqueeze.updater.verify_wheel"),
            patch("filesqueeze.updater.spawn_updater") as mock_spawn,
        ):
            controller.start(_update_info(), restart=False, on_applied=applied.set)
            self._wait(controller)

        assert mock_spawn.call_args.args[1] is None  # no relaunch
        assert not applied.is_set()  # nothing to quit in dialog-only mode
        assert controller.snapshot().phase == PHASE_DONE
        # Honest wording: without a quit callback the wheel installs when the
        # process exits, so claiming "installed" here would be a lie
        assert "when FileSqueeze exits" in controller.snapshot().message

    def test_refuses_dev_checkout_with_reason(self):
        from filesqueeze.updater import PHASE_FAILED, UpdateController

        controller = UpdateController()
        with patch("filesqueeze.updater.is_dev_checkout", return_value=True):
            assert controller.start(_update_info(), restart=True) is False

        snap = controller.snapshot()
        assert snap.phase == PHASE_FAILED
        assert "git pull" in snap.message

    def test_refuses_when_release_has_no_wheel(self):
        from filesqueeze.updater import PHASE_FAILED, UpdateController

        controller = UpdateController()
        with patch("filesqueeze.updater.is_dev_checkout", return_value=False):
            assert controller.start(_update_info(wheel_url=None)) is False

        assert controller.snapshot().phase == PHASE_FAILED

    def test_second_start_while_running_is_ignored(self, tmp_path):
        from filesqueeze.updater import UpdateController

        release = threading.Event()
        controller = UpdateController()

        def slow_download(*args, **kwargs):
            release.wait(timeout=5)
            return _make_wheel(tmp_path)

        with (
            patch("filesqueeze.updater.download_wheel", side_effect=slow_download),
            patch("filesqueeze.updater.verify_wheel"),
            patch("filesqueeze.updater.spawn_updater"),
        ):
            assert controller.start(_update_info(), restart=False) is True
            assert controller.start(_update_info(), restart=False) is False  # busy
            release.set()
            self._wait(controller)

    def test_cancelled_download_reports_cancelled_phase(self, tmp_path):
        from filesqueeze.updater import PHASE_CANCELLED, UpdateCancelled, UpdateController

        controller = UpdateController()

        def cancellable_download(info, dest, *, progress=None, cancel=None, timeout=None):
            if cancel is not None:
                cancel.set()
            raise UpdateCancelled()

        with (
            patch("filesqueeze.updater.download_wheel", side_effect=cancellable_download),
            patch("filesqueeze.updater.verify_wheel") as mock_verify,
            patch("filesqueeze.updater.spawn_updater") as mock_spawn,
        ):
            controller.start(_update_info(), restart=False)
            self._wait(controller)

        mock_verify.assert_not_called()
        mock_spawn.assert_not_called()
        assert controller.snapshot().phase == PHASE_CANCELLED

    def test_download_failure_reports_failed_phase(self):
        from filesqueeze.updater import PHASE_FAILED, UpdateController, UpdateError

        controller = UpdateController()
        with patch("filesqueeze.updater.download_wheel", side_effect=UpdateError("boom")):
            controller.start(_update_info(), restart=False)
            self._wait(controller)

        snap = controller.snapshot()
        assert snap.phase == PHASE_FAILED
        assert "boom" in snap.message

    def test_unexpected_error_still_reports_failed_phase(self):
        from filesqueeze.updater import PHASE_FAILED, UpdateController

        controller = UpdateController()
        with patch("filesqueeze.updater.download_wheel", side_effect=RuntimeError("surprise")):
            controller.start(_update_info(), restart=False)
            self._wait(controller)

        assert controller.snapshot().phase == PHASE_FAILED

    def test_task_gate_holds_the_handoff_until_tasks_finish(self, tmp_path):
        """No handoff while tasks run: spawn deferred, notice fired, then proceed."""
        from filesqueeze.updater import PHASE_DONE, PHASE_WAITING, UpdateController

        wheel = _make_wheel(tmp_path)
        tasks_running = [True]
        waiting_fired = []
        applied = threading.Event()
        controller = UpdateController(
            wait_for_tasks=lambda: tasks_running[0],
            on_waiting=lambda: waiting_fired.append(True),
        )

        with (
            patch("filesqueeze.updater.download_wheel", return_value=wheel),
            patch("filesqueeze.updater.verify_wheel"),
            patch("filesqueeze.updater.spawn_updater") as mock_spawn,
        ):
            assert controller.start(_update_info(), restart=True, on_applied=applied.set) is True
            assert self._wait_for_phase(controller, PHASE_WAITING), "update must enter the waiting phase"
            time.sleep(0.3)  # give a slow misbehaving handoff a chance to happen

            assert waiting_fired == [True], "entering the wait must fire on_waiting once"
            mock_spawn.assert_not_called()  # the checklist: never quit mid-task
            assert not applied.is_set()

            tasks_running[0] = False
            self._wait(controller)

        mock_spawn.assert_called_once()
        assert applied.is_set()
        assert controller.snapshot().phase == PHASE_DONE

    def test_no_waiting_callback_when_tasks_are_already_idle(self, tmp_path):
        from filesqueeze.updater import PHASE_DONE, UpdateController

        wheel = _make_wheel(tmp_path)
        waiting_fired = []
        controller = UpdateController(wait_for_tasks=lambda: False, on_waiting=lambda: waiting_fired.append(True))

        with (
            patch("filesqueeze.updater.download_wheel", return_value=wheel),
            patch("filesqueeze.updater.verify_wheel"),
            patch("filesqueeze.updater.spawn_updater"),
        ):
            controller.start(_update_info(), restart=False)
            self._wait(controller)

        assert waiting_fired == [], "idle app must skip the waiting phase entirely"
        assert controller.snapshot().phase == PHASE_DONE

    def test_cancel_while_waiting_for_tasks(self, tmp_path):
        """Cancelling during the wait aborts cleanly: no handoff, no quit."""
        from filesqueeze.updater import PHASE_CANCELLED, PHASE_WAITING, UpdateController

        gate = threading.Event()
        gate.set()  # tasks "running"
        applied = threading.Event()
        controller = UpdateController(wait_for_tasks=gate.is_set)

        with (
            patch("filesqueeze.updater.download_wheel", return_value=_make_wheel(tmp_path)),
            patch("filesqueeze.updater.verify_wheel"),
            patch("filesqueeze.updater.spawn_updater") as mock_spawn,
        ):
            controller.start(_update_info(), restart=True, on_applied=applied.set)
            assert self._wait_for_phase(controller, PHASE_WAITING)
            controller.cancel()
            self._wait(controller)

        mock_spawn.assert_not_called()
        assert not applied.is_set()
        assert controller.snapshot().phase == PHASE_CANCELLED


class TestUpdaterScript:
    def test_script_installs_and_relaunches_without_importing_filesqueeze(self):
        from filesqueeze.updater import UPDATER_SCRIPT

        assert "--force-reinstall" in UPDATER_SCRIPT
        assert "--no-deps" in UPDATER_SCRIPT
        assert "relaunch" in UPDATER_SCRIPT
        assert "import filesqueeze" not in UPDATER_SCRIPT  # must stay install-agnostic

    def test_script_backs_up_verifies_and_records_the_outcome(self):
        from filesqueeze.updater import UPDATER_SCRIPT

        assert "backup_installation" in UPDATER_SCRIPT, "A bad install needs a rollback source"
        assert "restore_installation" in UPDATER_SCRIPT, "A failed install must be rolled back"
        assert "installed_version()" in UPDATER_SCRIPT, "pip's outcome must be verified, not assumed"
        assert "installed == target" in UPDATER_SCRIPT, "Success requires the exact target version installed"
        assert '"aborted"' in UPDATER_SCRIPT, "A timed-out handoff must be reported, not silent"
        assert '"failed"' in UPDATER_SCRIPT and '"success"' in UPDATER_SCRIPT, "Outcome marker needs both states"
        assert "restored" in UPDATER_SCRIPT, "Failures must record whether the old version came back"

    def test_spawn_updater_detaches_with_payload(self, tmp_path):
        from filesqueeze.updater import spawn_updater

        with patch("filesqueeze.updater.subprocess.Popen") as mock_popen:
            spawn_updater(
                tmp_path / "wheel.whl",
                ["python", "-m", "filesqueeze", "service", "run"],
                previous_version="0.9.2",
                target_version="0.9.3",
                status_file=tmp_path / "status.json",
            )

        # argv is [python, -c, UPDATER_SCRIPT, json-payload]
        payload = json.loads(mock_popen.call_args.args[0][3])
        assert payload["wheel"].endswith("wheel.whl")
        assert payload["relaunch"] == ["python", "-m", "filesqueeze", "service", "run"]
        assert payload["previous_version"] == "0.9.2"
        assert payload["target_version"] == "0.9.3"
        assert payload["status_file"].endswith("status.json")
        assert isinstance(payload["parent_pid"], int)

    def test_timeout_aborts_without_installing_and_cleans_up_the_wheel(self, tmp_path):
        """A parent that never exits must abort pip, leave the app untouched, and not strand the wheel.

        Regression test for the review finding: a restart=False handoff from a
        tray-owned window used to wait on the never-exiting tray process,
        abort after the timeout, and leave the wheel behind while the UI
        claimed the update was installed.
        """
        import os
        import subprocess
        import sys

        from filesqueeze.updater import _UPDATER_SCRIPT_TEMPLATE

        script = _UPDATER_SCRIPT_TEMPLATE.replace("@PARENT_TIMEOUT@", "2")
        wheel = tmp_path / "filesqueeze-0.9.3-py3-none-any.whl"
        wheel.write_bytes(b"fake wheel bytes")
        payload = json.dumps(
            {"parent_pid": os.getpid(), "wheel": str(wheel), "relaunch": None}
        )  # this test process stays alive

        result = subprocess.run(
            [sys.executable, "-c", script, payload],
            capture_output=True,
            text=True,
            timeout=60,
            env={**os.environ, "FILEQUEEZE_DEV_MODE": "1"},
        )

        assert result.returncode == 2, result.stdout + result.stderr
        assert "aborting update" in result.stdout
        assert "removed temporary wheel" in result.stdout
        assert not wheel.exists()  # no stray wheel left in temp
        assert "installing" not in result.stdout  # pip never ran


class TestUpdateStatusMarker:
    def test_status_path_is_none_under_pytest_and_honors_override(self, tmp_path):
        from filesqueeze.updater import update_status_path

        assert update_status_path() is None, "tests must never touch the real user marker"
        override = tmp_path / "status.json"
        with patch.dict(os.environ, {"FILEQUEEZE_UPDATE_STATUS": str(override)}):
            assert update_status_path() == override

    def test_consume_reads_and_clears_the_marker(self, tmp_path):
        from filesqueeze.updater import consume_update_status

        marker = tmp_path / "update_status.json"
        marker.write_text(
            json.dumps({"status": "failed", "version": "0.9.3", "previous": "0.9.2", "restored": True}),
            encoding="utf-8",
        )

        outcome = consume_update_status(marker)
        assert outcome is not None
        assert outcome["status"] == "failed"
        assert outcome["restored"] is True

        assert not marker.exists(), "the marker must be consumed exactly once"
        assert consume_update_status(marker) is None

    def test_consume_tolerates_missing_or_garbage_markers(self, tmp_path):
        from filesqueeze.updater import consume_update_status

        assert consume_update_status(tmp_path / "absent.json") is None

        garbage = tmp_path / "garbage.json"
        garbage.write_text("{not json", encoding="utf-8")
        assert consume_update_status(garbage) is None

    def test_consume_defaults_to_none_without_a_path(self):
        # Under pytest the default location resolves to None (never touch user state)
        from filesqueeze.updater import consume_update_status

        assert consume_update_status() is None
