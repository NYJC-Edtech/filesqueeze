"""Interactive setup of external dependencies (FFmpeg, Ghostscript, Tesseract, stcc).

``filesqueeze setup-deps`` walks the user through pointing FileSqueeze at
their portable-binaries directory and, optionally, installing missing
dependencies there:

1. Ask for an existing directory (native dialog, or ``--dir``).
2. Detect which dependencies already live in it.
3. Offer to install the missing ones as portable builds — the user chooses,
   including "install none".
4. Download and unpack portable builds into the directory, then wire the
   found paths into the user config so they take priority over PATH
   auto-detection.

Sources (Windows): FFmpeg unpacks directly from the official gyan.dev
release zip. Ghostscript and Tesseract publish no official portable
archives — their Inno Setup installers are extracted with 7-Zip when
available (the same 7-Zip *Open archive* route documented in the README's
Locked-Down Machines section). stcc (speech-to-captions) ships as a
self-contained zip from the FileSqueeze project's own releases. On Linux
the flow detects and advises package-manager installs.

The orchestrator (:func:`run_setup`) is UI-free and network-injectable so
the whole flow is testable headless; :class:`TkSetupUI` supplies the
native dialogs, and the CLI's ``--dir/--install/--yes`` flags drive the
same flow without any GUI.
"""

import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
import tomllib
import urllib.error
import urllib.request
import zipfile
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path, PureWindowsPath
from typing import Any

try:
    import tomli_w
except ImportError:  # pragma: no cover - tomli-w is a hard dependency
    tomli_w = None

_USER_AGENT = "FileSqueeze-SetupDeps/1.0"
_DOWNLOAD_CHUNK_BYTES = 256 * 1024
_DOWNLOAD_TIMEOUT_SECONDS = 60.0
_MAX_WALK_DEPTH = 4
_MAX_SCANNED_DIRS = 2000

_FFMPEG_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
_GS_LATEST_API = "https://api.github.com/repos/ArtifexSoftware/ghostpdl-downloads/releases/latest"
_GS_ASSET_RE = re.compile(r"^gs\d+w64\.exe$")
_TESSERACT_DIR_URL = "https://digi.bib.uni-mannheim.de/tesseract/"
_TESSERACT_ASSET_RE = re.compile(r"tesseract-ocr-w64-setup-([0-9]+(?:\.[0-9]+)*)\.exe")
# 7-Zip bootstrapping (all linked from https://www.7-zip.org/download.html):
# 7zr.exe is a bare standalone executable with a stable asset name; the full
# 7z.exe + 7z.dll (needed for Inno/NSIS installers) ships inside the official
# 7z<ver>-x64.exe installer, which is itself a 7z SFX that 7zr can extract.
_SEVENZIPR_URL = "https://github.com/ip7z/7zip/releases/latest/download/7zr.exe"
_SEVENZIP_LATEST_API = "https://api.github.com/repos/ip7z/7zip/releases/latest"
_SEVENZIP_ASSET_RE = re.compile(r"^7z\d+-x64\.exe$")

# stcc speech-to-captions package (our own release, checksum-pinned).
# Bump both together when a new stcc release is validated.
_STCC_RELEASE_URL = "https://github.com/NYJC-Edtech/filesqueeze-stcc/releases/download/v0.1.0/stcc-0.1.0-win-x64-cpu.zip"
_STCC_SHA256 = "d419735a5aee4fc2a1d8e7121008713c75e5c33a7d9b618f1e7248656dfdb713"


class SetupError(RuntimeError):
    """A dependency-setup step failed with a user-actionable message."""


_NETWORK_ATTEMPTS = 3
_RETRY_DELAY_SECONDS = 2.0


def _fetch_with_retry(label: str, fetch: Callable[[], Any]):
    """Run a network ``fetch`` callable, retrying transient failures.

    The mirrors involved (notably the university-hosted Tesseract listing)
    occasionally reset connections; a short retry smooths that over.
    """
    last_error: Exception | None = None
    for attempt in range(1, _NETWORK_ATTEMPTS + 1):
        try:
            return fetch()
        except (urllib.error.URLError, OSError) as e:
            last_error = e
            if attempt < _NETWORK_ATTEMPTS:
                time.sleep(_RETRY_DELAY_SECONDS)
    raise SetupError(f"Could not {label} (tried {_NETWORK_ATTEMPTS} times): {last_error}") from last_error


@dataclass(frozen=True)
class Dependency:
    key: str
    display: str
    required: bool
    exe_names: tuple[str, ...]
    exe_names_posix: tuple[str, ...]
    config_section: str
    config_key: str
    install_subdir: str
    linux_package: str
    portable_source: str | None = None  # direct URL (zip) when one exists
    resolved_source: object = None  # callable() -> (url, filename) for lookups
    sha256: str | None = None  # expected digest of the downloaded archive, when pinned
    windows_only: bool = False  # the portable build exists for Windows only

    @property
    def is_windows_portable(self) -> bool:
        return self.portable_source is not None or self.resolved_source is not None

    def exe_names_for_platform(self) -> tuple[str, ...]:
        return self.exe_names if sys.platform == "win32" else self.exe_names_posix


def _resolve_ghostscript_url(timeout: float = _DOWNLOAD_TIMEOUT_SECONDS) -> tuple[str, str]:
    """Latest Ghostscript Windows installer (url, filename) from the GitHub API."""

    def fetch():
        request = urllib.request.Request(
            _GS_LATEST_API, headers={"User-Agent": _USER_AGENT, "Accept": "application/vnd.github+json"}
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.load(response)

    try:
        data = _fetch_with_retry("look up the latest Ghostscript release", fetch)
    except json.JSONDecodeError as e:
        raise SetupError(f"Could not look up the latest Ghostscript release: {e}") from e
    for asset in data.get("assets", []):
        if _GS_ASSET_RE.match(asset.get("name", "")):
            return asset["browser_download_url"], asset["name"]
    raise SetupError("No Windows installer found in the latest Ghostscript release")


def _resolve_tesseract_url(timeout: float = _DOWNLOAD_TIMEOUT_SECONDS) -> tuple[str, str]:
    """Latest Tesseract Windows build (url, filename) from the UB-Mannheim listing."""

    def fetch():
        request = urllib.request.Request(_TESSERACT_DIR_URL, headers={"User-Agent": _USER_AGENT})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read().decode("utf-8", errors="replace")

    html = _fetch_with_retry("look up the latest Tesseract build", fetch)
    matches = _TESSERACT_ASSET_RE.findall(html)
    if not matches:
        raise SetupError("No Tesseract Windows build found in the UB-Mannheim listing")
    best = max(matches, key=lambda v: tuple(int(p) for p in v.split(".")))
    filename = f"tesseract-ocr-w64-setup-{best}.exe"
    return _TESSERACT_DIR_URL + filename, filename


DEPENDENCIES: tuple[Dependency, ...] = (
    Dependency(
        key="ffmpeg",
        display="FFmpeg",
        required=True,
        exe_names=("ffmpeg.exe",),
        exe_names_posix=("ffmpeg",),
        config_section="ffmpeg",
        config_key="path",
        install_subdir="ffmpeg",
        linux_package="ffmpeg",
        portable_source=_FFMPEG_URL,
    ),
    Dependency(
        key="ghostscript",
        display="Ghostscript",
        required=True,
        exe_names=("gswin64c.exe", "gswin32c.exe", "gs.exe"),
        exe_names_posix=("gs",),
        config_section="document",
        config_key="ghostscript_path",
        install_subdir="ghostscript",
        linux_package="ghostscript",
        resolved_source=_resolve_ghostscript_url,
    ),
    Dependency(
        key="tesseract",
        display="Tesseract OCR (optional)",
        required=False,
        exe_names=("tesseract.exe",),
        exe_names_posix=("tesseract",),
        config_section="ocr",
        config_key="tesseract_path",
        install_subdir="tesseract",
        linux_package="tesseract-ocr",
        resolved_source=_resolve_tesseract_url,
    ),
    Dependency(
        key="stcc",
        display="stcc speech-to-captions (optional)",
        required=False,
        exe_names=("stcc.py",),
        exe_names_posix=("stcc.py",),
        config_section="transcription",
        config_key="stcc_path",
        install_subdir="",  # the zip already contains a top-level stcc/ folder
        linux_package="",
        portable_source=_STCC_RELEASE_URL,
        sha256=_STCC_SHA256,
        windows_only=True,
    ),
)

DEPS_BY_KEY = {dep.key: dep for dep in DEPENDENCIES}


# --------------------------------------------------------------------------
# Detection


def _sha256_of(path: Path) -> str:
    """Stream a file through SHA256 (portable installs can be hundreds of MB)."""
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def find_in_dir(base: Path, exe_names: tuple[str, ...]) -> Path | None:
    """Find one of ``exe_names`` under ``base`` (bounded depth walk)."""
    wanted = {name.lower() for name in exe_names}
    base = Path(base)
    if not base.is_dir():
        return None
    scanned = 0
    for dirpath, _dirnames, filenames in _walk_bounded(base, _MAX_WALK_DEPTH):
        scanned += 1
        if scanned > _MAX_SCANNED_DIRS:
            return None
        for filename in filenames:
            if filename.lower() in wanted:
                return Path(dirpath) / filename
    return None


def _walk_bounded(base: Path, max_depth: int):
    """os.walk pruned to ``max_depth`` levels below ``base``."""
    import os

    base_depth = len(base.parts)
    for dirpath, dirnames, filenames in os.walk(base):
        depth = len(Path(dirpath).parts) - base_depth
        if depth >= max_depth:
            dirnames[:] = []
        yield dirpath, dirnames, filenames


def detect_dependencies(base: Path) -> dict[str, Path | None]:
    """Locate each dependency's executable under ``base``."""
    return {dep.key: find_in_dir(base, dep.exe_names_for_platform()) for dep in DEPENDENCIES}


# --------------------------------------------------------------------------
# Download / unpack


def download_file(url: str, dest_dir: Path, filename: str, progress: Callable[[int, int | None], None] | None = None) -> Path:
    """Stream ``url`` to ``dest_dir/filename`` with truncation checks and retries."""

    dest = Path(dest_dir) / filename

    def fetch() -> Path:
        dest.unlink(missing_ok=True)
        request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
        with urllib.request.urlopen(request, timeout=_DOWNLOAD_TIMEOUT_SECONDS) as response:
            length = response.headers.get("Content-Length")
            total = int(length) if length and length.isdigit() else None
            done = 0
            with open(dest, "wb") as f:
                while True:
                    chunk = response.read(_DOWNLOAD_CHUNK_BYTES)
                    if not chunk:
                        break
                    f.write(chunk)
                    done += len(chunk)
                    if progress is not None:
                        progress(done, total)
        if total is not None and done != total:
            raise urllib.error.URLError(f"truncated download: received {done} of {total} bytes")
        return dest

    try:
        return _fetch_with_retry(f"download {filename}", fetch)
    except SetupError:
        dest.unlink(missing_ok=True)
        raise


def find_sevenzip() -> Path | None:
    """Locate 7-Zip's 7z executable (PATH + standard install locations)."""
    for name in ("7z", "7z.exe", "7za", "7za.exe"):
        found = shutil.which(name)
        if found:
            return Path(found)
    candidates = [
        Path.cwd() / "7-Zip" / "7z.exe",
        Path.home() / "AppData" / "Local" / "Programs" / "7-Zip" / "7z.exe",
        Path("C:/Program Files/7-Zip/7z.exe"),
        Path("C:/Program Files (x86)/7-Zip/7z.exe"),
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def _resolve_sevenzip_installer_url(timeout: float = _DOWNLOAD_TIMEOUT_SECONDS) -> str:
    """Latest official 7-Zip x64 installer URL from the GitHub API."""

    def fetch():
        request = urllib.request.Request(
            _SEVENZIP_LATEST_API, headers={"User-Agent": _USER_AGENT, "Accept": "application/vnd.github+json"}
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.load(response)

    try:
        data = _fetch_with_retry("look up the latest 7-Zip release", fetch)
    except json.JSONDecodeError as e:
        raise SetupError(f"Could not look up the latest 7-Zip release: {e}") from e
    for asset in data.get("assets", []):
        if _SEVENZIP_ASSET_RE.match(asset.get("name", "")):
            return asset["browser_download_url"]
    raise SetupError("No x64 installer found in the latest 7-Zip release")


def ensure_sevenzip(base: Path, progress: Callable[[int, int | None], None] | None = None) -> tuple[Path, bool]:
    """Return a full 7-Zip 7z.exe path, downloading a portable copy if needed.

    The returned executable understands Inno Setup/NSIS installers (what
    Ghostscript and Tesseract distribute). Bootstrapping downloads 7zr.exe
    (a standalone 7z-only tool) plus the official 7-Zip installer — itself a
    7z SFX — and unpacks the full 7z.exe/7z.dll from it into
    ``<base>/7-Zip``. Returns ``(path, bootstrapped)``.
    """
    cached = base / "7-Zip" / "7z.exe"
    if cached.is_file():
        return cached, False
    existing = find_sevenzip()
    if existing is not None:
        return existing, False

    with tempfile.TemporaryDirectory(prefix="filesqueeze-7zip-") as tmp:
        tmp_path = Path(tmp)
        sevenzr = download_file(_SEVENZIPR_URL, tmp_path, "7zr.exe", progress=progress)
        installer_url = _resolve_sevenzip_installer_url()
        installer = download_file(installer_url, tmp_path, installer_url.rsplit("/", 1)[-1], progress=progress)

        dest = base / "7-Zip"
        dest.mkdir(parents=True, exist_ok=True)
        result = subprocess.run(
            [str(sevenzr), "x", "-y", f"-o{dest}", str(installer)], capture_output=True, text=True, timeout=300
        )
        if result.returncode != 0 or not (dest / "7z.exe").is_file():
            detail = (result.stderr or result.stdout or "").strip().splitlines()
            raise SetupError(f"Could not unpack the 7-Zip installer: {detail[-1] if detail else 'unknown error'}")
    return dest / "7z.exe", True


def unpack_zip(archive: Path, dest_dir: Path) -> None:
    """Extract a portable zip (e.g. gyan.dev FFmpeg) into ``dest_dir``."""
    try:
        with zipfile.ZipFile(archive) as zf:
            zf.extractall(dest_dir)
    except (zipfile.BadZipFile, OSError) as e:
        raise SetupError(f"Could not unpack {archive.name}: {e}") from e


def unpack_inno_with_7z(sevenzip: Path, archive: Path, dest_dir: Path) -> None:
    """Extract an Inno Setup installer (Ghostscript/Tesseract) with 7-Zip.

    7-Zip exposes the installer's payload (the ``{app}`` tree) as archive
    members; the executable is located afterwards by re-detecting in
    ``dest_dir``, so the exact internal layout does not matter here.
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    cmd = [str(sevenzip), "x", "-y", f"-o{dest_dir}", str(archive)]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    except (OSError, subprocess.TimeoutExpired) as e:
        raise SetupError(f"Could not run 7-Zip ({sevenzip}): {e}") from e
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip().splitlines()
        raise SetupError(f"7-Zip extraction failed: {detail[-1] if detail else 'unknown error'}")


# --------------------------------------------------------------------------
# Config wiring


def update_user_config(config_path: Path, values: dict[tuple[str, str], str]) -> Path:
    """Set ``(section, key) -> value`` strings in the user config, backing it up.

    Missing sections are created; unrelated keys are preserved untouched.
    """
    config_path = Path(config_path)
    if tomli_w is None:
        raise SetupError("tomli-w is not installed; cannot update the config")

    data: dict = {}
    if config_path.exists():
        with open(config_path, "rb") as f:
            data = tomllib.load(f)
        import shutil as _shutil
        from datetime import datetime

        backup = config_path.with_suffix(f".toml.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        _shutil.copy2(config_path, backup)

    for (section, key), value in values.items():
        data.setdefault(section, {})[key] = value

    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, "wb") as f:
        tomli_w.dump(data, f)
    return config_path


def config_values_for(found: dict[str, Path | None]) -> dict[tuple[str, str], str]:
    """Config (section, key) -> posix-normalized path for each located dep."""
    values: dict[tuple[str, str], str] = {}
    for dep in DEPENDENCIES:
        path = found.get(dep.key)
        if path is not None:
            values[(dep.config_section, dep.config_key)] = str(PureWindowsPath(path).as_posix())
    return values


# --------------------------------------------------------------------------
# Orchestration


@dataclass
class SetupReport:
    base_dir: Path
    found: dict[str, Path | None] = field(default_factory=dict)
    installed: dict[str, Path | None] = field(default_factory=dict)
    failed: dict[str, str] = field(default_factory=dict)
    skipped: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    config_written: Path | None = None

    def summary_lines(self) -> list[str]:
        lines = [f"Binaries directory: {self.base_dir}"]
        for dep in DEPENDENCIES:
            path = self.found.get(dep.key)
            if dep.key in self.failed:
                lines.append(f"  [X] {dep.display}: install failed — {self.failed[dep.key]}")
            elif path is not None:
                where = "installed" if dep.key in self.installed else "found"
                lines.append(f"  [OK] {dep.display} ({where}): {path}")
            elif dep.key in self.skipped:
                lines.append(f"  [--] {dep.display}: not installed (skipped)")
            else:
                lines.append(f"  [ ] {dep.display}: not present")
        lines.extend(f"  note: {note}" for note in self.notes)
        if self.config_written:
            lines.append(f"Config updated: {self.config_written}")
        return lines


def _install_portable(
    dep: Dependency, base: Path, progress: Callable[[int, int | None], None] | None = None
) -> tuple[Path | None, list[str]]:
    """Download and unpack one dependency; returns (executable, notes) or raises SetupError."""
    notes: list[str] = []
    target = base / dep.install_subdir if dep.install_subdir else Path(base)
    target.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f"filesqueeze-{dep.key}-") as tmp:
        if dep.portable_source is not None:
            filename = dep.portable_source.rsplit("/", 1)[-1]
            url = dep.portable_source
        else:
            url, filename = dep.resolved_source()
        archive = download_file(url, Path(tmp), filename, progress=progress)

        if dep.sha256 is not None:
            actual = _sha256_of(archive)
            if actual != dep.sha256:
                raise SetupError(f"checksum mismatch for {filename}: expected {dep.sha256}, got {actual}")

        if archive.suffix.lower() == ".zip":
            unpack_zip(archive, target)
        else:
            sevenzip, bootstrapped = ensure_sevenzip(base, progress=progress)
            if bootstrapped:
                notes.append(f"7-Zip (portable) installed at {sevenzip.parent} — used to unpack installer-based builds")
            unpack_inno_with_7z(sevenzip, archive, target)

    found = find_in_dir(target, dep.exe_names_for_platform())
    if found is None:
        raise SetupError("archive unpacked but no executable was found inside it")
    return found, notes


def run_setup(
    ui: Any = None,
    *,
    base_dir: Path | str | None = None,
    requested: set[str] | None = None,
    config_path: Path | str | None = None,
    assume_yes: bool = False,
    wire_config: bool = True,
    progress: Callable[[int, int | None], None] | None = None,
) -> SetupReport:
    """Run the full setup flow. See module docstring; ``ui`` supplies dialogs.

    ``base_dir``/``requested`` bypass the corresponding dialogs (headless /
    tests); ``requested`` may contain any dependency key plus ``"none"``.
    """
    if config_path is None:
        config_path = Path.home() / ".config" / "filesqueeze" / "config.toml"

    # 1. Choose the directory
    if base_dir is not None:
        base = Path(base_dir)
        if not base.is_dir():
            raise SetupError(f"Not a directory: {base}")
    else:
        base = ui.ask_directory(_default_binaries_dir())
        if base is None:
            report = SetupReport(base_dir=Path("<cancelled>"))
            report.skipped = ["cancelled by user"]
            return report

    report = SetupReport(base_dir=base)

    # 2. Detect what is already there
    report.found = detect_dependencies(base)

    # 3. Offer installs for the missing, portable-installable ones
    missing = [dep for dep in DEPENDENCIES if report.found[dep.key] is None]
    on_windows = sys.platform == "win32"
    installable = [dep for dep in missing if on_windows and dep.is_windows_portable]
    # Platform without a portable build (Linux): advise the package manager
    for dep in missing:
        if dep not in installable:
            if dep.windows_only and not on_windows:
                report.notes.append(f"{dep.display}: only distributed for Windows — skipped on this platform")
            else:
                report.notes.append(
                    f"{dep.display}: no portable build on this platform — install it via your package manager (e.g. '{dep.linux_package}')"
                )

    if requested is not None:
        if "none" in requested:
            chosen: list[Dependency] = []
        else:
            unknown = requested - set(DEPS_BY_KEY)
            if unknown:
                raise SetupError(f"Unknown dependency: {', '.join(sorted(unknown))}")
            chosen = [DEPS_BY_KEY[key] for key in DEPS_BY_KEY if key in requested and DEPS_BY_KEY[key] in installable]
            skipped_requested = [
                DEPS_BY_KEY[key] for key in requested if DEPS_BY_KEY[key] in missing and DEPS_BY_KEY[key] not in installable
            ]
            for dep in skipped_requested:
                report.failed[dep.key] = "no portable build is available on this platform"
    elif installable:
        chosen = ui.choose_installs(installable)
    else:
        chosen = []

    for dep in [d for d in missing if d not in chosen]:
        report.skipped.append(dep.key)

    # 4. Install the chosen ones
    for dep in chosen:
        try:
            path, notes = _install_portable(dep, base, progress=progress)
            report.installed[dep.key] = path
            report.notes.extend(notes)
        except SetupError as e:
            report.failed[dep.key] = str(e)

    # Re-detect so found reflects post-install reality
    report.found = detect_dependencies(base)

    # 5. Wire located paths into the user config
    if wire_config and report.found:
        values = config_values_for(report.found)
        if values:
            do_write = assume_yes or ui is None or ui.confirm_wiring(values)
            if do_write:
                report.config_written = update_user_config(Path(config_path), values)

    if ui is not None:
        ui.show_summary(report)
    return report


def _default_binaries_dir() -> Path:
    home = Path.home()
    for candidate in (home / "FileSqueeze" / "bin", home / "FileSqueeze", home):
        if candidate.is_dir():
            return candidate
    return home


class TkSetupUI:
    """Native-dialog UI for run_setup (tkinter).

    The Tk root is created eagerly so environments without a display fail
    at construction — callers can then fall back to headless flags.
    """

    def __init__(self) -> None:
        import tkinter as tk

        self._root = tk.Tk()
        self._root.withdraw()

    def _tk(self):
        return self._root

    def ask_directory(self, initialdir: Path) -> Path | None:
        import tkinter.filedialog as filedialog

        chosen = filedialog.askdirectory(
            title="Choose your portable-binaries folder (FFmpeg, Ghostscript, Tesseract)",
            initialdir=str(initialdir),
            mustexist=True,
        )
        return Path(chosen) if chosen else None

    def choose_installs(self, deps: list[Dependency]) -> list[Dependency]:
        import tkinter as tk

        root = self._tk()
        dialog = tk.Toplevel(root)
        dialog.title("Install external dependencies")
        dialog.grab_set()
        dialog.resizable(False, False)

        tk.Label(
            dialog,
            text=(
                "FileSqueeze can install portable builds of the missing\n"
                "dependencies into your binaries folder.\n\n"
                "Nothing is installed system-wide; no admin rights needed.\n"
                "(Ghostscript/Tesseract are unpacked from their official\n"
                "installers — 7-Zip is downloaded too if it's missing.)"
            ),
            justify="left",
            padx=12,
            pady=8,
        ).pack()
        vars_ = {}
        for dep in deps:
            var = tk.BooleanVar(value=dep.required)
            vars_[dep.key] = var
            tk.Checkbutton(dialog, text=dep.display, variable=var, anchor="w", padx=20).pack(fill="x")
        result: list[Dependency] = []

        def finish(selected: bool):
            nonlocal result
            if selected:
                result = [dep for dep in deps if vars_[dep.key].get()]
            dialog.destroy()

        buttons = tk.Frame(dialog, pady=8)
        buttons.pack()
        tk.Button(buttons, text="Install selected", width=16, command=lambda: finish(True)).pack(side="left", padx=6)
        tk.Button(buttons, text="Install none", width=16, command=lambda: finish(False)).pack(side="left", padx=6)
        dialog.protocol("WM_DELETE_WINDOW", lambda: finish(False))
        dialog.wait_window()
        return result

    def confirm_wiring(self, values: dict[tuple[str, str], str]) -> bool:
        import tkinter.messagebox as messagebox

        lines = "\n".join(f"{section}.{key} = {value}" for (section, key), value in values.items())
        return messagebox.askyesno(
            "Update configuration?",
            f"Point FileSqueeze at the binaries found in your folder?\n\n{lines}\n\n(Your config is backed up first.)",
        )

    def show_summary(self, report: SetupReport) -> None:
        import tkinter.messagebox as messagebox

        messagebox.showinfo("External dependencies", "\n".join(report.summary_lines()))
