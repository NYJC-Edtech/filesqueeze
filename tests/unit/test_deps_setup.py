"""Unit tests for deps_setup (external-dependency setup flow).

All network and subprocess activity is mocked: downloads are served from
in-memory archives, the 7-Zip chain is faked with stub archives and a
monkeypatched subprocess.run. A real-network end-to-end run is exercised
separately (sandbox), not here.
"""

import io
import json
import sys
import zipfile
from pathlib import Path
from unittest.mock import patch

import pytest

# The portable-install machinery is Windows-only: on Linux run_setup refuses
# installs with "no portable build is available on this platform", so tests
# that exercise installs are skipped on the Linux CI leg.
windows_only = pytest.mark.skipif(sys.platform != "win32", reason="portable install flow is Windows-only")

# --------------------------------------------------------------------------
# Helpers


class _FakeResponse:
    """Fake urlopen() return value serving fixed bytes with a Content-Length."""

    def __init__(self, payload: bytes):
        self._stream = io.BytesIO(payload)
        self.headers = {"Content-Length": str(len(payload))}

    def read(self, n=-1):
        return self._stream.read(n)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _zip_bytes(entries: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, data in entries.items():
            zf.writestr(name, data)
    return buf.getvalue()


def _fake_installer_payload() -> bytes:
    """A stand-in for the 7-Zip official installer (a 7z SFX in reality).

    The fake 7zr subprocess (see _fake_7zr_run) unpacks this zip when asked
    to extract it, yielding the full 7z.exe + 7z.dll.
    """
    return _zip_bytes({"7z.exe": b"MZ-full-7z", "7z.dll": b"dll", "Lang/en.txt": b"lang"})


def _fake_7zr_run():
    """subprocess.run stub emulating 7zr/7z extracting our fake archives."""

    def run(cmd, *args, **kwargs):
        out_dir = None
        archive = None
        for i, part in enumerate(cmd):
            if part.startswith("-o"):
                out_dir = Path(part[2:])
            if i > 0 and not part.startswith("-") and Path(part).suffix in (".7z", ".exe"):
                archive = Path(part)

        payload = None
        if archive is not None and out_dir is not None:
            if archive.name == "7z-installer.exe":
                payload = _fake_installer_payload()
            elif archive.name in ("gs.exe", "gs10080w64.exe", "dep-installer.exe"):
                payload = _zip_bytes({"bin/gswin64c.exe": b"MZ-gs"})
            if payload is not None:
                out_dir.mkdir(parents=True, exist_ok=True)
                with zipfile.ZipFile(io.BytesIO(payload)) as zf:
                    zf.extractall(out_dir)

        class Result:
            returncode = 0
            stdout = "Everything is Ok"
            stderr = ""

        return Result()

    return run


def _gyan_style_ffmpeg_zip() -> bytes:
    return _zip_bytes(
        {
            "ffmpeg-9.9.9-essentials_build/bin/ffmpeg.exe": b"MZ-ffmpeg",
            "ffmpeg-9.9.9-essentials_build/bin/ffprobe.exe": b"MZ-ffprobe",
        }
    )


def _serve(downloads: dict[str, bytes]):
    """Patch urlopen so each URL serves its canned payload."""

    def fake_urlopen(request, timeout=None):
        url = request.full_url if hasattr(request, "full_url") else str(request)
        for prefix, payload in downloads.items():
            if url.startswith(prefix):
                return _FakeResponse(payload)
        raise AssertionError(f"unexpected URL requested in test: {url}")

    return patch("filesqueeze.deps_setup.urllib.request.urlopen", side_effect=fake_urlopen)


# --------------------------------------------------------------------------
# Detection


class TestDetection:
    def test_find_in_dir_locates_nested_exe(self, tmp_path):
        from filesqueeze.deps_setup import find_in_dir

        (tmp_path / "ffmpeg-9.9" / "bin").mkdir(parents=True)
        (tmp_path / "ffmpeg-9.9" / "bin" / "ffmpeg.exe").write_bytes(b"MZ")
        assert find_in_dir(tmp_path, ("ffmpeg.exe",)) == tmp_path / "ffmpeg-9.9" / "bin" / "ffmpeg.exe"

    def test_find_in_dir_case_insensitive_and_missing(self, tmp_path):
        from filesqueeze.deps_setup import find_in_dir

        (tmp_path / "gs").mkdir()
        (tmp_path / "gs" / "GSWIN64C.EXE").write_bytes(b"MZ")
        assert find_in_dir(tmp_path, ("gswin64c.exe", "gswin32c.exe")) is not None
        assert find_in_dir(tmp_path, ("tesseract.exe",)) is None

    def test_find_in_dir_depth_limited(self, tmp_path):
        from filesqueeze.deps_setup import find_in_dir

        deep = tmp_path
        for i in range(8):
            deep = deep / f"d{i}"
        deep.mkdir(parents=True)
        (deep / "ffmpeg.exe").write_bytes(b"MZ")
        assert find_in_dir(tmp_path, ("ffmpeg.exe",)) is None

    def test_detect_dependencies_reports_all(self, tmp_path):
        from filesqueeze.deps_setup import detect_dependencies

        # Platform-appropriate names so the test holds on Windows and Linux
        (tmp_path / "ffmpeg").mkdir()
        (tmp_path / "ffmpeg" / "ffmpeg.exe").write_bytes(b"MZ")
        (tmp_path / "ffmpeg" / "ffmpeg").write_bytes(b"MZ")
        found = detect_dependencies(tmp_path)
        assert found["ffmpeg"] is not None
        assert found["ghostscript"] is None
        assert found["tesseract"] is None


# --------------------------------------------------------------------------
# Source resolution


class TestSourceResolution:
    def test_resolve_ghostscript_url(self):
        from filesqueeze.deps_setup import _resolve_ghostscript_url

        payload = json.dumps(
            {
                "assets": [
                    {"name": "ghostscript-10.08.0.tar.gz", "browser_download_url": "x"},
                    {"name": "gs10080w64.exe", "browser_download_url": "https://dl/gs10080w64.exe"},
                ]
            }
        ).encode()
        with _serve({"https://api.github.com/repos/ArtifexSoftware": payload}):
            url, name = _resolve_ghostscript_url()
        assert (url, name) == ("https://dl/gs10080w64.exe", "gs10080w64.exe")

    def test_resolve_tesseract_url_picks_highest_version(self):
        from filesqueeze.deps_setup import _resolve_tesseract_url

        html = (
            b'<a href="tesseract-ocr-w64-setup-5.3.4.20231005.exe">5.3.4</a>'
            b'<a href="tesseract-ocr-w64-setup-5.4.0.20240606.exe">5.4.0</a>'
            b'<a href="tesseract-ocr-w64-setup-5.3.0.20221222.exe">5.3.0</a>'
        )
        with _serve({"https://digi.bib.uni-mannheim.de/tesseract/": html}):
            url, name = _resolve_tesseract_url()
        assert name == "tesseract-ocr-w64-setup-5.4.0.20240606.exe"
        assert url.endswith(name)

    def test_resolve_sevenzip_installer_url(self):
        from filesqueeze.deps_setup import _resolve_sevenzip_installer_url

        payload = json.dumps(
            {
                "assets": [
                    {"name": "7z2604-arm64.exe", "browser_download_url": "https://dl/arm"},
                    {"name": "7z2604-x64.exe", "browser_download_url": "https://dl/7z2604-x64.exe"},
                ]
            }
        ).encode()
        with _serve({"https://api.github.com/repos/ip7z": payload}):
            assert _resolve_sevenzip_installer_url() == "https://dl/7z2604-x64.exe"


# --------------------------------------------------------------------------
# Download / unpack


class TestDownloadUnpack:
    def test_download_file_writes_and_verifies(self, tmp_path):
        from filesqueeze.deps_setup import download_file

        with _serve({"https://example.com/": b"ABCDEF"}):
            dest = download_file("https://example.com/x.zip", tmp_path, "x.zip")
        assert dest.read_bytes() == b"ABCDEF"

    def test_download_file_truncated_raises(self, tmp_path, monkeypatch):
        from filesqueeze.deps_setup import SetupError, download_file

        monkeypatch.setattr("filesqueeze.deps_setup._RETRY_DELAY_SECONDS", 0)

        def lying(request, timeout=None):
            resp = _FakeResponse(b"SHORT")
            resp.headers = {"Content-Length": "100"}
            return resp

        with patch("filesqueeze.deps_setup.urllib.request.urlopen", side_effect=lying):
            with pytest.raises(SetupError, match="truncated"):
                download_file("https://example.com/x.zip", tmp_path, "x.zip")
        assert not (tmp_path / "x.zip").exists()

    def test_download_retries_transient_failures(self, tmp_path, monkeypatch):
        from filesqueeze.deps_setup import download_file

        monkeypatch.setattr("filesqueeze.deps_setup._RETRY_DELAY_SECONDS", 0)
        import urllib.error

        attempts = []

        def flaky(request, timeout=None):
            attempts.append(1)
            if len(attempts) < 3:
                raise urllib.error.URLError("connection reset")
            return _FakeResponse(b"RECOVERED")

        with patch("filesqueeze.deps_setup.urllib.request.urlopen", side_effect=flaky):
            dest = download_file("https://example.com/x.bin", tmp_path, "x.bin")
        assert dest.read_bytes() == b"RECOVERED"
        assert len(attempts) == 3

    def test_unpack_zip_gyan_layout(self, tmp_path):
        from filesqueeze.deps_setup import find_in_dir, unpack_zip

        archive = tmp_path / "ffmpeg.zip"
        archive.write_bytes(_gyan_style_ffmpeg_zip())
        out = tmp_path / "out"
        out.mkdir()
        unpack_zip(archive, out)
        assert find_in_dir(out, ("ffmpeg.exe",)) is not None

    def test_unpack_inno_with_7z_invokes_extractor(self, tmp_path):
        from filesqueeze.deps_setup import unpack_inno_with_7z

        archive = tmp_path / "dep-installer.exe"
        archive.write_bytes(b"fake-installer")
        out = tmp_path / "out"
        with patch("filesqueeze.deps_setup.subprocess.run", side_effect=_fake_7zr_run()):
            unpack_inno_with_7z(tmp_path / "7z.exe", archive, out)
        assert (out / "bin" / "gswin64c.exe").exists()

    def test_unpack_inno_failure_raises(self, tmp_path):
        from filesqueeze.deps_setup import SetupError, unpack_inno_with_7z

        def failing(cmd, *a, **k):
            class R:
                returncode = 2
                stdout = ""
                stderr = "Cannot open"

            return R()

        with patch("filesqueeze.deps_setup.subprocess.run", side_effect=failing):
            with pytest.raises(SetupError, match="7-Zip extraction failed"):
                unpack_inno_with_7z(Path("7z.exe"), tmp_path / "a.exe", tmp_path)


# --------------------------------------------------------------------------
# Config wiring


class TestConfigWiring:
    def test_update_user_config_preserves_and_backs_up(self, tmp_path):
        from filesqueeze.deps_setup import update_user_config

        config = tmp_path / "config.toml"
        config.write_text('[ffmpeg]\ncrf = 28\n\n[logging]\nfile = "C:/log"\n', encoding="utf-8")
        update_user_config(config, {("ffmpeg", "path"): "C:/bin/ffmpeg/ffmpeg.exe"})
        import tomllib

        with open(config, "rb") as f:
            data = tomllib.load(f)
        assert data["ffmpeg"]["path"] == "C:/bin/ffmpeg/ffmpeg.exe"
        assert data["ffmpeg"]["crf"] == 28  # preserved
        assert data["logging"]["file"] == "C:/log"  # preserved
        backups = list(tmp_path.glob("config.toml.backup.*"))
        assert len(backups) == 1

    def test_config_values_for_normalizes_paths(self, tmp_path):
        from filesqueeze.deps_setup import config_values_for

        values = config_values_for({"ffmpeg": tmp_path / "ffmpeg" / "ffmpeg.exe", "ghostscript": None})
        assert values == {("ffmpeg", "path"): str(tmp_path / "ffmpeg" / "ffmpeg.exe").replace("\\", "/")}


# --------------------------------------------------------------------------
# Orchestration (headless run_setup)


class TestRunSetup:
    def _network(self, monkeypatch, tmp_path, *, with_gs=False):
        downloads = {
            "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip": _gyan_style_ffmpeg_zip(),
            "https://github.com/ip7z/7zip/releases/latest/download/7zr.exe": b"MZ-7zr",
            "https://api.github.com/repos/ip7z": json.dumps(
                {"assets": [{"name": "7z2604-x64.exe", "browser_download_url": "https://dl/7z-installer.exe"}]}
            ).encode(),
            "https://dl/7z-installer.exe": _fake_installer_payload(),
        }
        if with_gs:
            downloads["https://api.github.com/repos/ArtifexSoftware"] = json.dumps(
                {"assets": [{"name": "gs10080w64.exe", "browser_download_url": "https://dl/gs.exe"}]}
            ).encode()
            downloads["https://dl/gs.exe"] = b"NSIS-payload-gs"

        def fake_urlopen(request, timeout=None):
            url = request.full_url if hasattr(request, "full_url") else str(request)
            for prefix, payload in downloads.items():
                if url.startswith(prefix):
                    return _FakeResponse(payload)
            raise AssertionError(f"unexpected URL requested in test: {url}")

        monkeypatch.setattr("filesqueeze.deps_setup.urllib.request.urlopen", fake_urlopen)
        monkeypatch.setattr("filesqueeze.deps_setup.subprocess.run", _fake_7zr_run())

    @windows_only
    def test_installs_ffmpeg_and_wires_config(self, tmp_path, monkeypatch):
        from filesqueeze.deps_setup import run_setup

        self._network(monkeypatch, tmp_path)
        base = tmp_path / "bin"
        base.mkdir()
        config = tmp_path / "config.toml"
        report = run_setup(base_dir=base, requested={"ffmpeg"}, config_path=config, assume_yes=True, wire_config=True)
        assert report.failed == {}
        assert report.installed["ffmpeg"] is not None
        assert report.found["ghostscript"] is None
        import tomllib

        with open(config, "rb") as f:
            data = tomllib.load(f)
        assert data["ffmpeg"]["path"].endswith("ffmpeg.exe")

    @windows_only
    def test_installs_gs_with_bootstrapped_sevenzip(self, tmp_path, monkeypatch):
        from filesqueeze.deps_setup import run_setup

        self._network(monkeypatch, tmp_path, with_gs=True)
        base = tmp_path / "bin"
        base.mkdir()
        config = tmp_path / "config.toml"
        with patch("filesqueeze.deps_setup.find_sevenzip", return_value=None):
            report = run_setup(base_dir=base, requested={"ghostscript"}, config_path=config, assume_yes=True)
        assert report.failed == {}
        assert (base / "7-Zip" / "7z.exe").exists()  # bootstrapped portable 7-Zip
        assert report.installed["ghostscript"] == base / "ghostscript" / "bin" / "gswin64c.exe"
        assert any("7-Zip" in note for note in report.notes)

    @windows_only
    def test_uses_cached_sevenzip(self, tmp_path, monkeypatch):
        from filesqueeze.deps_setup import run_setup

        self._network(monkeypatch, tmp_path, with_gs=True)
        base = tmp_path / "bin"
        (base / "7-Zip").mkdir(parents=True)
        (base / "7-Zip" / "7z.exe").write_bytes(b"MZ")
        with patch("filesqueeze.deps_setup.find_sevenzip", return_value=None) as fs:
            report = run_setup(base_dir=base, requested={"ghostscript"}, config_path=tmp_path / "c.toml", assume_yes=True)
        assert report.failed == {}
        fs.assert_not_called()  # cache hit, no discovery needed

    def test_install_none_skips_everything(self, tmp_path, monkeypatch):
        from filesqueeze.deps_setup import run_setup

        self._network(monkeypatch, tmp_path)
        base = tmp_path / "bin"
        base.mkdir()
        report = run_setup(
            base_dir=base, requested={"none"}, config_path=tmp_path / "c.toml", assume_yes=True, wire_config=False
        )
        assert report.installed == {}
        assert report.failed == {}
        assert set(report.skipped) == {"ffmpeg", "ghostscript", "tesseract", "stcc"}

    @windows_only
    def test_existing_binaries_are_wired_not_reinstalled(self, tmp_path, monkeypatch):
        from filesqueeze.deps_setup import run_setup

        self._network(monkeypatch, tmp_path)
        base = tmp_path / "bin"
        (base / "ffmpeg").mkdir(parents=True)
        (base / "ffmpeg" / "ffmpeg.exe").write_bytes(b"MZ")
        report = run_setup(base_dir=base, requested={"none"}, config_path=tmp_path / "c.toml", assume_yes=True)
        assert report.installed == {}
        assert report.found["ffmpeg"] == base / "ffmpeg" / "ffmpeg.exe"

    def test_unknown_dependency_raises(self, tmp_path):
        from filesqueeze.deps_setup import SetupError, run_setup

        with pytest.raises(SetupError, match="Unknown dependency"):
            run_setup(base_dir=tmp_path, requested={"imagemagick"}, assume_yes=True)

    def test_bad_base_dir_raises(self, tmp_path):
        from filesqueeze.deps_setup import SetupError, run_setup

        with pytest.raises(SetupError, match="Not a directory"):
            run_setup(base_dir=tmp_path / "nope", assume_yes=True)

    def test_summary_lines_shape(self, tmp_path, monkeypatch):
        from filesqueeze.deps_setup import run_setup

        self._network(monkeypatch, tmp_path)
        base = tmp_path / "bin"
        base.mkdir()
        report = run_setup(base_dir=base, requested={"none"}, config_path=tmp_path / "c.toml", assume_yes=True)
        lines = "\n".join(report.summary_lines())
        assert "not installed (skipped)" in lines or "not present" in lines


# --------------------------------------------------------------------------
# stcc speech-to-captions package


class TestStccDependency:
    def test_stcc_registered_with_expected_shape(self):
        from filesqueeze.deps_setup import DEPS_BY_KEY

        dep = DEPS_BY_KEY["stcc"]
        assert dep.required is False
        assert dep.windows_only is True
        assert dep.exe_names == ("stcc.py",)
        assert dep.exe_names_posix == ("stcc.py",)
        assert (dep.config_section, dep.config_key) == ("transcription", "stcc_path")
        assert dep.install_subdir == ""  # zip carries its own top-level stcc/ folder
        assert dep.sha256 and len(dep.sha256) == 64
        assert dep.portable_source and "filesqueeze-stcc/releases" in dep.portable_source

    def _stcc_zip_bytes(self) -> bytes:
        import io
        import zipfile

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr("stcc/stcc.py", "# stcc entry point\n")
            z.writestr("stcc/VERSION", "0.1.0\n")
        return buf.getvalue()

    def test_install_portable_verifies_checksum(self, tmp_path, monkeypatch):
        import dataclasses

        from filesqueeze.deps_setup import DEPS_BY_KEY, SetupError, _install_portable

        dep = DEPS_BY_KEY["stcc"]
        payload = self._stcc_zip_bytes()

        def fake_download(url, dest_dir, filename, progress=None):
            dest = dest_dir / filename
            dest.write_bytes(b"corrupted-payload")
            return dest

        monkeypatch.setattr("filesqueeze.deps_setup.download_file", fake_download)
        with pytest.raises(SetupError, match="checksum mismatch"):
            _install_portable(dataclasses.replace(dep, sha256="0" * 64), tmp_path)
        # nothing unpacked on failure
        assert not (tmp_path / "stcc").exists()

    def test_install_portable_unpacks_stcc_layout(self, tmp_path, monkeypatch):
        import dataclasses
        import hashlib

        from filesqueeze.deps_setup import DEPS_BY_KEY, _install_portable

        dep = DEPS_BY_KEY["stcc"]
        payload = self._stcc_zip_bytes()

        def fake_download(url, dest_dir, filename, progress=None):
            dest = dest_dir / filename
            dest.write_bytes(payload)
            return dest

        monkeypatch.setattr("filesqueeze.deps_setup.download_file", fake_download)
        pinned = dataclasses.replace(dep, sha256=hashlib.sha256(payload).hexdigest())
        found, _notes = _install_portable(pinned, tmp_path)
        assert found == tmp_path / "stcc" / "stcc.py"

    def test_config_values_for_maps_stcc(self, tmp_path):
        from filesqueeze.deps_setup import config_values_for

        values = config_values_for({"stcc": tmp_path / "stcc" / "stcc.py"})
        assert values == {("transcription", "stcc_path"): str(tmp_path / "stcc" / "stcc.py").replace("\\", "/")}

    def test_stcc_default_toml_documents_transcription_section(self):
        import tomllib
        from pathlib import Path

        data = tomllib.loads(Path("filesqueeze/default.toml").read_text(encoding="utf-8"))
        assert data["transcription"]["stcc_path"] == ""
