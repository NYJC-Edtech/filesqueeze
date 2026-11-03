"""Unit tests for the doctor's config-aware binary and config checks.

Doctor must check binaries the way compression does (config path first,
validated; auto-detect fallback) and report which config file it loaded.
Imports of ``filesqueeze`` modules happen INSIDE the test functions
(circular-import test discipline).
"""

from pathlib import Path


def test_check_binary_labels_configured_path():
    """A binary resolved via config is reported as '(from config)'."""
    from filesqueeze.config import Config
    from filesqueeze.doctor import Doctor

    doctor = Doctor(config=Config(config_path={"ffmpeg": {"path": "C:/tools/ffmpeg/bin/ffmpeg.exe"}}))
    doctor.detector.get_ffmpeg_path = lambda: Path("C:/tools/ffmpeg/bin/ffmpeg.exe")

    assert doctor.check_binary("ffmpeg", "FFmpeg") is True
    assert any("(from config)" in p and "FFmpeg" in p for p in doctor.passed)


def test_check_binary_labels_auto_detected_path():
    from filesqueeze.config import Config
    from filesqueeze.doctor import Doctor

    doctor = Doctor(config=Config({}))
    doctor.detector.get_ffmpeg_path = lambda: Path("C:/ffmpeg/bin/ffmpeg.exe")

    assert doctor.check_binary("ffmpeg", "FFmpeg") is True
    assert any("(auto-detected)" in p for p in doctor.passed)


def test_check_binary_missing_reports_parseable_issue():
    from filesqueeze.config import Config
    from filesqueeze.doctor import Doctor
    from filesqueeze.system.binaries import BinaryNotFoundError

    doctor = Doctor(config=Config(config_path={"ffmpeg": {"path": "C:/APPS/ffmpeg/bin"}}))
    doctor.detector.get_ffmpeg_path = lambda: (_ for _ in ()).throw(
        BinaryNotFoundError(
            "binary_not_found: ffmpeg (configured ffmpeg.path 'C:/APPS/ffmpeg/bin' "
            "does not exist or is not a file; point it at the executable itself)"
        )
    )

    assert doctor.check_binary("ffmpeg", "FFmpeg") is False
    assert any("[FAIL] FFmpeg not found" in i for i in doctor.issues)
    assert any("configured ffmpeg.path" in i for i in doctor.issues)


def test_check_binary_optional_missing_is_warning():
    from filesqueeze.config import Config
    from filesqueeze.doctor import Doctor
    from filesqueeze.system.binaries import BinaryNotFoundError

    doctor = Doctor(config=Config({}))
    doctor.detector.get_tesseract_path = lambda: (_ for _ in ()).throw(
        BinaryNotFoundError("binary_not_found: tesseract (not found; searched: PATH, common locations)")
    )

    assert doctor.check_binary("tesseract", "Tesseract OCR (optional)", optional=True) is False
    assert doctor.issues == []
    assert any("[WARN] Tesseract" in w for w in doctor.warnings)


def test_check_config_file_reports_loaded_sources(tmp_path):
    from types import SimpleNamespace

    from filesqueeze.doctor import Doctor

    loaded = tmp_path / "config.toml"

    doctor = Doctor.__new__(Doctor)
    doctor.issues = []
    doctor.warnings = []
    doctor.passed = []
    doctor.config = SimpleNamespace(sources=[loaded])
    doctor.check_config_file()

    assert any("[OK] Configuration loaded:" in p and str(loaded) in p for p in doctor.passed)


def test_check_config_file_warns_when_nothing_loaded():
    from types import SimpleNamespace

    from filesqueeze.doctor import Doctor

    doctor = Doctor.__new__(Doctor)
    doctor.issues = []
    doctor.warnings = []
    doctor.passed = []
    doctor.config = SimpleNamespace(sources=[])
    found = doctor.check_config_file()

    assert found is False
    assert any("No configuration file loaded" in w for w in doctor.warnings)


def test_failure_reason_extracts_parenthetical():
    from filesqueeze.doctor import _failure_reason
    from filesqueeze.system.binaries import BinaryNotFoundError

    exc = BinaryNotFoundError("binary_not_found: ffmpeg (some reason; searched: PATH)")
    assert _failure_reason(exc) == "some reason; searched: PATH"
    assert _failure_reason(ValueError("plain")) == "plain"
