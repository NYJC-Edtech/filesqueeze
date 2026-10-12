"""filesqueeze.updater

Download and apply FileSqueeze releases from within the app (issue #35).

The flow, started from the tray menu or a GUI banner:

1. Stream the release wheel from GitHub to a temp file (cancellable, with
   progress callbacks for the UI).
2. Sanity-check it: wheel filename and embedded METADATA must both name
   filesqueeze at exactly the version GitHub advertised.
3. Hand off to a small detached updater process that waits for this app to
   exit (releasing the single-instance mutex and any file handles), then runs
   ``pip install --force-reinstall --no-deps`` on the wheel and relaunches
   FileSqueeze.

The handoff exists because a running Python process cannot reliably replace
its own package files. The updater is a ``python -c`` script that imports
nothing from filesqueeze, so it stays compatible with both the old and the
new install.

No admin rights are required: pip falls back to a ``--user`` install
automatically when site-packages is not writable. A dev checkout refuses to
self-update (``is_dev_checkout``) since pip cannot update a git checkout.

Installs without a published wheel degrade gracefully: callers check
``can_self_update`` first and fall back to opening the releases page.
"""

import json
import logging
import os
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
import zipfile
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Callable

from .config import Config
from .update_check import UpdateInfo, is_dev_checkout, normalize_version

logger = logging.getLogger(__name__)

_USER_AGENT = "filesqueeze-updater"

_DOWNLOAD_CHUNK_BYTES = 64 * 1024
_DOWNLOAD_TIMEOUT_SECONDS = 30.0
# How long the detached updater waits for the app to exit before giving up.
# The restart path quits within seconds; the restart=False path (dialog-only
# launches) installs whenever the user closes the dialog, so leave a
# generous window before giving up and leaving the install untouched.
_UPDATER_PARENT_TIMEOUT_SECONDS = 600
# How often the controller re-checks "are tasks still running" while waiting
# for a safe moment to hand off the update
_TASK_POLL_SECONDS = 1.0

# Update flow phases, surfaced through UpdateController.snapshot()
PHASE_IDLE = "idle"
PHASE_DOWNLOADING = "downloading"
PHASE_VERIFYING = "verifying"
PHASE_WAITING = "waiting"
PHASE_INSTALLING = "installing"
PHASE_DONE = "done"
PHASE_FAILED = "failed"
PHASE_CANCELLED = "cancelled"


class UpdateError(RuntimeError):
    """A download or installation step failed; the message is user-presentable."""


class UpdateCancelled(RuntimeError):
    """The user cancelled the update while it was downloading."""


@dataclass(frozen=True)
class UpdateProgress:
    """Point-in-time state of an update, polled by the GUI."""

    phase: str
    message: str = ""
    downloaded: int | None = None
    total: int | None = None

    @property
    def percent(self) -> int | None:
        """Download progress as 0-100, or None when the size is unknown."""
        if self.downloaded is None or not self.total:
            return None
        return min(100, self.downloaded * 100 // self.total)


def wheel_filename(version: str) -> str:
    """The release asset name for a version, as published by the release flow."""
    return f"filesqueeze-{normalize_version(version)}-py3-none-any.whl"


def can_self_update(update_info: UpdateInfo) -> tuple[bool, str]:
    """Whether this install can apply ``update_info`` itself, plus a reason if not."""
    if is_dev_checkout():
        return False, "Running from a dev checkout — update it with git pull."
    if not update_info.wheel_url:
        return False, "This release does not publish an installable wheel — download it from the releases page."
    return True, ""


def verify_wheel(path: Path, expected_version: str) -> None:
    """Sanity-check a downloaded wheel, raising UpdateError on any mismatch.

    Checks the artifact name and the wheel's embedded METADATA (Name/Version),
    so a truncated, foreign, or mis-versioned file is never handed to pip.
    """
    path = Path(path)
    if path.name != wheel_filename(expected_version):
        raise UpdateError(f"Unexpected update artifact: {path.name}")

    try:
        with zipfile.ZipFile(path) as archive:
            metadata_names = [n for n in archive.namelist() if n.endswith(".dist-info/METADATA")]
            if len(metadata_names) != 1:
                raise UpdateError("Downloaded file is not a valid FileSqueeze wheel")
            metadata_text = archive.read(metadata_names[0]).decode("utf-8", errors="replace")
    except zipfile.BadZipFile as e:
        raise UpdateError(f"Downloaded file is corrupt: {e}") from e

    name = None
    version = None
    for line in metadata_text.splitlines():
        if name and version:
            break
        if line.startswith("Name:"):
            name = line.split(":", 1)[1].strip()
        elif line.startswith("Version:"):
            version = line.split(":", 1)[1].strip()
    if (name or "").lower() != "filesqueeze" or version != normalize_version(expected_version):
        raise UpdateError(
            f"Wheel contains {name or 'unknown package'} v{version or '?'}, expected filesqueeze v{normalize_version(expected_version)}"
        )


def build_pip_command(wheel: Path) -> list[str]:
    """The pip invocation the detached updater runs to apply a wheel.

    ``--no-deps`` keeps the install offline and scoped: releases change only
    FileSqueeze itself, and a dependency resolution pass would hit PyPI —
    something school networks and locked-down machines must not depend on.
    pip falls back to a user install on its own when site-packages is
    read-only, which covers non-admin machines.
    """
    return [
        sys.executable,
        "-m",
        "pip",
        "install",
        "--force-reinstall",
        "--no-deps",
        "--disable-pip-version-check",
        str(wheel),
    ]


def build_relaunch_command(argv: list[str] | None = None) -> list[str]:
    """The command that restarts FileSqueeze with the same CLI arguments.

    ``argv`` defaults to ``sys.argv``; entry [0] (script or module path) is
    replaced by ``python -m filesqueeze``, so both the console-script and
    ``python -m`` launch styles relaunch identically.
    """
    args = list(sys.argv if argv is None else argv)
    return [sys.executable, "-m", "filesqueeze", *args[1:]]


def download_wheel(
    update_info: UpdateInfo,
    dest_dir: Path,
    *,
    progress: Callable[[int, int | None], None] | None = None,
    cancel: threading.Event | None = None,
    timeout: float = _DOWNLOAD_TIMEOUT_SECONDS,
) -> Path:
    """Stream the release wheel to ``dest_dir``, returning its path.

    Raises UpdateCancelled when ``cancel`` fires mid-download and UpdateError
    for network or truncation problems; partial files are removed in both
    cases. ``progress`` is called after every chunk with (done_bytes, total).
    """
    if not update_info.wheel_url:
        raise UpdateError("This release does not publish a downloadable wheel")

    dest = Path(dest_dir) / wheel_filename(update_info.latest_version)
    request = urllib.request.Request(update_info.wheel_url, headers={"User-Agent": _USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            length = response.headers.get("Content-Length")
            total = int(length) if length and length.isdigit() else None
            done = 0
            with open(dest, "wb") as f:
                while True:
                    if cancel is not None and cancel.is_set():
                        raise UpdateCancelled("Download cancelled")
                    chunk = response.read(_DOWNLOAD_CHUNK_BYTES)
                    if not chunk:
                        break
                    f.write(chunk)
                    done += len(chunk)
                    if progress is not None:
                        progress(done, total)
    except UpdateCancelled:
        _unlink_quietly(dest)
        raise
    except (urllib.error.URLError, OSError) as e:
        _unlink_quietly(dest)
        raise UpdateError(f"Download failed: {e}") from e

    if total is not None and done != total:
        _unlink_quietly(dest)
        raise UpdateError(f"Download incomplete: received {done} of {total} bytes")
    return dest


# Runs detached: wait for the app to exit, install the wheel, relaunch.
# Deliberately stdlib-only and filesqueeze-import-free — see module docstring.
# @PARENT_TIMEOUT@ is replaced with the timeout constant at import time
# (.format() is not usable here — the script is full of literal braces).
_UPDATER_SCRIPT_TEMPLATE = """\
import json, os, shutil, subprocess, sys, sysconfig, tempfile, time

DETACHED_FLAGS = 0x00000008 | 0x00000200 if os.name == "nt" else 0  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP


def log(message):
    print(f"[filesqueeze-updater] {message}", flush=True)


def write_status(status_file, payload):
    # Record the apply outcome so the next FileSqueeze start can inform the user.
    if not status_file:
        return
    try:
        with open(status_file, "w", encoding="utf-8") as handle:
            json.dump(payload, handle)
        log(f"recorded update outcome: {payload.get('status')}")
    except OSError as error:
        log(f"could not write update status: {error}")


def parent_has_exited(pid, timeout_seconds):
    if os.name == "nt":
        import ctypes

        synchronize = 0x00100000
        wait_object_0 = 0
        kernel32 = ctypes.windll.kernel32
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            handle = kernel32.OpenProcess(synchronize, False, int(pid))
            if not handle:
                return True
            try:
                if kernel32.WaitForSingleObject(handle, 500) == wait_object_0:
                    return True
            finally:
                kernel32.CloseHandle(handle)
        return False
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            os.kill(int(pid), 0)
        except OSError:
            return True
        time.sleep(0.25)
    return False


def installed_version():
    probe = subprocess.run(
        [sys.executable, "-c", "from importlib.metadata import version; print(version('filesqueeze'))"],
        capture_output=True,
        text=True,
    )
    if probe.returncode != 0:
        return None
    return probe.stdout.strip().lower().removeprefix("v") or None


def backup_installation():
    # Copy the installed package aside so a failed pip can be rolled back.
    # FileSqueeze is pure Python (no compiled extensions), so the package dir,
    # its dist-info and the Scripts/ launchers are all plain files.
    backup = os.path.join(tempfile.gettempdir(), "filesqueeze-update-backup")
    shutil.rmtree(backup, ignore_errors=True)
    os.makedirs(backup, exist_ok=True)
    purelib = sysconfig.get_path("purelib")
    scripts = sysconfig.get_path("scripts")
    package = os.path.join(purelib, "filesqueeze")
    if os.path.isdir(package):
        shutil.copytree(package, os.path.join(backup, "filesqueeze"))
    for name in os.listdir(purelib):
        if name.startswith("filesqueeze-") and name.endswith(".dist-info"):
            shutil.copytree(os.path.join(purelib, name), os.path.join(backup, name))
    if os.path.isdir(scripts):
        for name in os.listdir(scripts):
            source = os.path.join(scripts, name)
            if name.lower().startswith("filesqueeze") and os.path.isfile(source):
                shutil.copy2(source, os.path.join(backup, name))
    log(f"backed up current installation to {backup}")
    return backup


def restore_installation(backup):
    # Best-effort rollback: clear the broken install, put the backup back.
    if not os.path.isdir(backup):
        log("no backup available; cannot restore the previous version")
        return False
    purelib = sysconfig.get_path("purelib")
    scripts = sysconfig.get_path("scripts")
    subprocess.run([sys.executable, "-m", "pip", "uninstall", "-y", "filesqueeze"], capture_output=True, text=True)
    shutil.rmtree(os.path.join(purelib, "filesqueeze"), ignore_errors=True)
    for name in os.listdir(purelib):
        if name.startswith("filesqueeze-") and name.endswith(".dist-info"):
            shutil.rmtree(os.path.join(purelib, name), ignore_errors=True)
    if os.path.isdir(scripts):
        for name in os.listdir(scripts):
            if name.lower().startswith("filesqueeze"):
                try:
                    os.remove(os.path.join(scripts, name))
                except OSError:
                    pass
    for name in os.listdir(backup):
        source = os.path.join(backup, name)
        is_package = name == "filesqueeze" or (name.startswith("filesqueeze-") and name.endswith(".dist-info"))
        destination = os.path.join(purelib if is_package else scripts, name)
        try:
            if os.path.isdir(source):
                shutil.copytree(source, destination)
            else:
                shutil.copy2(source, destination)
        except OSError as error:
            log(f"could not restore {name}: {error}")
            return False
    shutil.rmtree(backup, ignore_errors=True)
    log("restored the previous installation from backup")
    return True


def main():
    payload = json.loads(sys.argv[1])
    pid, wheel, relaunch = int(payload["parent_pid"]), payload["wheel"], payload.get("relaunch")
    previous, target = payload.get("previous_version"), payload.get("target_version")
    status_file = payload.get("status_file")
    log(f"waiting for pid {pid} to exit")
    try:
        if not parent_has_exited(pid, @PARENT_TIMEOUT@):
            log("parent still running after timeout; aborting update (app left untouched)")
            write_status(status_file, {"status": "aborted", "version": target, "previous": previous})
            return 2

        log(f"previous version: {previous or 'unknown'}; backing up before installing")
        backup = backup_installation()

        log(f"installing {wheel}")
        command = [sys.executable, "-m", "pip", "install", "--force-reinstall", "--no-deps", "--disable-pip-version-check", wheel]
        result = subprocess.run(command, capture_output=True, text=True)
        log(f"pip exit code {result.returncode}")
        if result.stdout.strip():
            log(result.stdout.strip())
        if result.stderr.strip():
            log(result.stderr.strip())

        installed = installed_version()
        if result.returncode == 0 and installed == target:
            log(f"verified filesqueeze {installed} is installed")
            write_status(status_file, {"status": "success", "version": target, "previous": previous})
            outcome = result.returncode
        else:
            log(f"update failed (pip rc={result.returncode}, installed={installed or 'broken'}); checking rollback")
            if previous and installed == previous:
                # pip failed before touching the old version - leave it alone
                log("previous version still installed and intact; no rollback needed")
            else:
                restored_ok = restore_installation(backup)
                log(f"rollback performed: {restored_ok}")
            working = installed_version()
            write_status(
                status_file,
                {
                    "status": "failed",
                    "version": target,
                    "previous": previous,
                    "restored": bool(working),
                },
            )
            outcome = result.returncode if result.returncode != 0 else 1

        if relaunch:
            kwargs = {"creationflags": DETACHED_FLAGS} if os.name == "nt" else {"start_new_session": True}
            subprocess.Popen(relaunch, **kwargs)
            log(f"relaunched: {' '.join(relaunch)}")
        return outcome
    finally:
        try:
            os.remove(wheel)
            log("removed temporary wheel")
        except OSError as error:
            log(f"could not remove temporary wheel: {error}")


if __name__ == "__main__":
    sys.exit(main())
"""

UPDATER_SCRIPT = _UPDATER_SCRIPT_TEMPLATE.replace("@PARENT_TIMEOUT@", str(_UPDATER_PARENT_TIMEOUT_SECONDS))


def updater_log_path() -> Path:
    """Where the detached updater appends its log (temp dir, survives the app)."""
    return Path(tempfile.gettempdir()) / "filesqueeze-update.log"


def spawn_updater(
    wheel: Path,
    relaunch: list[str] | None,
    *,
    previous_version: str | None = None,
    target_version: str | None = None,
    status_file: Path | None = None,
) -> None:
    """Start the detached updater; it acts once this process has exited.

    ``status_file`` is where the updater records the apply outcome so the
    next FileSqueeze start can tell the user what happened (a bad install
    must not strand the user silently). None (dev/test runs) skips the marker.
    """
    payload = json.dumps(
        {
            "parent_pid": os.getpid(),
            "wheel": str(wheel),
            "relaunch": relaunch,
            "previous_version": previous_version,
            "target_version": target_version,
            "status_file": str(status_file) if status_file is not None else None,
        }
    )
    popen_kwargs: dict = {"stdin": subprocess.DEVNULL, "close_fds": True}
    if os.name == "nt":
        popen_kwargs["creationflags"] = 0x00000008 | 0x00000200  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
    else:
        popen_kwargs["start_new_session"] = True

    log_handle = open(updater_log_path(), "a", encoding="utf-8")
    try:
        subprocess.Popen([sys.executable, "-c", UPDATER_SCRIPT, payload], stdout=log_handle, stderr=log_handle, **popen_kwargs)
    finally:
        log_handle.close()
    logger.info("Update handoff started (wheel: %s, relaunch: %s)", wheel, relaunch)


def update_status_path() -> Path | None:
    """Where the detached updater records the apply outcome for the next start.

    Returns None in dev/test runs (never touch user state from tests);
    ``FILEQUEEZE_UPDATE_STATUS`` overrides the location and wins over the
    dev guard, so dev runs can point the marker at a sandbox.
    """
    override = os.getenv("FILEQUEEZE_UPDATE_STATUS")
    if override:
        return Path(override)
    if os.getenv("PYTEST_CURRENT_TEST") is not None or os.getenv("FILEQUEEZE_DEV_MODE") == "1":
        return None
    return Path.home() / ".config" / "filesqueeze" / "update_status.json"


def consume_update_status(path: Path | None = None) -> dict | None:
    """Read and clear the last update's outcome marker; None when absent.

    Called once per start: the caller surfaces "updated to vX" or "the update
    failed, FileSqueeze is still on vY" and the marker is removed so the
    message shows exactly once. Expected marker fields: ``status``
    (success/failed/aborted), ``version`` (attempted), ``previous``, and for
    failures ``restored`` (whether the previous version was verified working).
    """
    if path is None:
        path = update_status_path()
    if path is None:
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    try:
        path.unlink()
    except OSError:
        logger.debug("Could not remove update status marker %s", path, exc_info=True)
    return payload if isinstance(payload, dict) else None


class UpdateController:
    """Runs one download/apply flow in a background thread, with pollable state.

    The tray service owns a single controller and shares it with the windows
    it opens, so the tray menu, status window and compress dialog all show the
    same in-flight update. GUI threads poll ``snapshot()``; the controller
    thread never touches widgets.
    """

    def __init__(
        self,
        config: Config | None = None,
        wait_for_tasks: Callable[[], bool] | None = None,
        on_waiting: Callable[[], None] | None = None,
    ):
        """Wire the controller to this process's task lifecycle.

        Args:
            config: Config (reserved for per-update settings).
            wait_for_tasks: Returns True while app tasks (a running
                compression, a watched file mid-processing) are active. The
                controller never hands the wheel to the detached updater
                while it returns True — quitting mid-task would drop work.
                None disables the gate.
            on_waiting: Called on the controller thread when the update enters
                the waiting state; the tray shows its buttonless
                "will close and update after tasks complete" notice here.
        """
        self.config = config
        self._wait_for_tasks = wait_for_tasks
        self._on_waiting = on_waiting
        self._lock = threading.Lock()
        self._cancel_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._progress = UpdateProgress(phase=PHASE_IDLE)
        self._update_info: UpdateInfo | None = None
        self._restart = True
        self._on_applied: Callable[[], None] | None = None

    @property
    def running(self) -> bool:
        with self._lock:
            return self._thread is not None and self._thread.is_alive()

    def start(self, update_info: UpdateInfo, *, restart: bool = True, on_applied: Callable[[], None] | None = None) -> bool:
        """Begin download+apply for ``update_info``; False if busy or not applicable.

        ``restart`` relaunches FileSqueeze after installing (the service);
        without it the update applies silently and is picked up on the next
        start (the standalone compress dialog). ``on_applied`` runs on the
        updater thread once the handoff is in place — the tray uses it to quit
        the app so the detached updater can take over.
        """
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                logger.debug("Update already in progress; ignoring new request")
                return False

            ok, reason = can_self_update(update_info)
            if not ok:
                self._progress = UpdateProgress(phase=PHASE_FAILED, message=reason)
                return False

            self._update_info = update_info
            self._restart = restart
            self._on_applied = on_applied
            self._cancel_event = threading.Event()
            version = update_info.latest_version  # display-ready: UpdateInfo normalized it
            self._progress = UpdateProgress(phase=PHASE_DOWNLOADING, message=f"Downloading FileSqueeze v{version}…")
            self._thread = threading.Thread(target=self._run, name="update-apply", daemon=True)
            self._thread.start()
            return True

    def cancel(self) -> None:
        """Request cancellation; only the download phase is cancellable."""
        self._cancel_event.set()

    def snapshot(self) -> UpdateProgress:
        with self._lock:
            return self._progress

    def _set_progress(self, **fields) -> None:
        with self._lock:
            self._progress = replace(self._progress, **fields)

    def _wait_for_running_tasks(self) -> None:
        """Hold the handoff until app tasks finish (never quit mid-task).

        Polls the tray's task gate; cancellable while waiting. Tasks started
        after the wait began are covered too — the gate is re-evaluated every
        poll, so the handoff only happens on a genuinely idle app.
        """
        if self._wait_for_tasks is None or not self._wait_for_tasks():
            return

        logger.info("Update ready but tasks are running — waiting for them to finish")
        self._set_progress(phase=PHASE_WAITING, downloaded=None, total=None, message="Waiting for running tasks to finish…")
        if self._on_waiting is not None:
            try:
                self._on_waiting()
            except Exception:
                logger.error("Update waiting-notification callback failed", exc_info=True)

        while self._wait_for_tasks():
            if self._cancel_event.is_set():
                raise UpdateCancelled()
            time.sleep(_TASK_POLL_SECONDS)
        logger.info("Tasks finished — proceeding with the update handoff")

    def _run(self) -> None:
        assert self._update_info is not None
        info = self._update_info
        version = info.latest_version  # display-ready: UpdateInfo normalized it
        try:
            wheel = download_wheel(
                info,
                Path(tempfile.gettempdir()),
                progress=lambda done, total: self._set_progress(downloaded=done, total=total),
                cancel=self._cancel_event,
            )

            if self._cancel_event.is_set():
                raise UpdateCancelled()
            self._set_progress(phase=PHASE_VERIFYING, downloaded=None, total=None, message="Verifying download…")
            verify_wheel(wheel, version)

            self._wait_for_running_tasks()

            if self._restart:
                self._set_progress(phase=PHASE_INSTALLING, message="Closing FileSqueeze to install the update…")
            else:
                self._set_progress(phase=PHASE_INSTALLING, message="Update prepared — installing when FileSqueeze exits.")
            spawn_updater(
                wheel,
                build_relaunch_command() if self._restart else None,
                previous_version=info.current_version,
                target_version=version,
                status_file=update_status_path(),
            )

            # Honest wording: at handoff pip has not run yet — the detached
            # updater installs after this process exits. The restart path
            # quits within a second (on_applied below), so this message is a
            # brief flash; the non-restart path leaves it up.
            if self._restart:
                message = f"Update ready — FileSqueeze is closing to install v{version}; it will restart automatically."
            else:
                message = f"Update ready — v{version} will install when FileSqueeze exits."
            self._set_progress(phase=PHASE_DONE, message=message)
        except UpdateCancelled:
            logger.info("FileSqueeze update cancelled by user")
            self._set_progress(phase=PHASE_CANCELLED, downloaded=None, total=None, message="Update cancelled.")
        except UpdateError as e:
            logger.warning("FileSqueeze update failed: %s", e)
            self._set_progress(phase=PHASE_FAILED, message=f"Could not update automatically: {e}")
        except Exception as e:  # never let the thread die silently
            logger.error("Unexpected FileSqueeze update failure", exc_info=True)
            self._set_progress(phase=PHASE_FAILED, message=f"Could not update automatically: {e}")

        if self._restart and self.snapshot().phase == PHASE_DONE and self._on_applied is not None:
            try:
                self._on_applied()
            except Exception:
                logger.error("Update completion callback failed", exc_info=True)


def _unlink_quietly(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError:
        logger.debug("Could not remove %s", path, exc_info=True)
