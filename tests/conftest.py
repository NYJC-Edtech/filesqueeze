"""Pytest configuration for FileSqueeze tests."""

import sys
import shutil
import pytest
from pathlib import Path

# Add parent directory to path so we can import filesqueeze
sys.path.insert(0, str(Path(__file__).parent.parent))

# Path to test fixtures
FIXTURES_DIR = Path(__file__).parent / "fixtures"

# Protected paths that should never be modified by tests
PROTECTED_CONFIG_PATHS = [
    Path.home() / ".config" / "filesqueeze" / "config.toml",
    Path.cwd() / "filesqueeze.toml",
]


@pytest.fixture
def sample_video():
    """Path to sample video file for testing."""
    video_path = FIXTURES_DIR / "testvideo61.mp4"
    if video_path.exists():
        return str(video_path)
    pytest.skip(f"Sample video not found: {video_path}")


@pytest.fixture
def sample_image():
    """Path to sample image file for testing."""
    image_path = FIXTURES_DIR / "TDD080.jpg"
    if image_path.exists():
        return str(image_path)
    pytest.skip(f"Sample image not found: {image_path}")


@pytest.fixture
def sample_generated_pdf():
    """Path to sample generated PDF for testing."""
    pdf_path = FIXTURES_DIR / "generated_pdf.pdf"
    if pdf_path.exists():
        return str(pdf_path)
    pytest.skip(f"Sample PDF not found: {pdf_path}")


@pytest.fixture
def sample_scanned_pdf():
    """Path to sample scanned PDF for testing."""
    pdf_path = FIXTURES_DIR / "scanned_pdf.pdf"
    if pdf_path.exists():
        return str(pdf_path)
    pytest.skip(f"Sample PDF not found: {pdf_path}")


@pytest.fixture(autouse=True)
def protect_user_config(monkeypatch):
    """Prevent tests from writing to user's actual config file.

    This is a critical safety measure to ensure tests never modify
    the user's production configuration. Any test that attempts to
    write to the protected config paths will fail immediately with
    a clear error message.
    """

    def safe_write_text(self, content, *args, **kwargs):
        # Check if this is a protected path
        for protected in PROTECTED_CONFIG_PATHS:
            if str(self) == str(protected):
                pytest.fail(
                    f"\n{'='*80}\n"
                    f"TEST SAFETY VIOLATION: Attempted to write to protected config file!\n"
                    f"{'='*80}\n"
                    f"Protected path: {protected}\n"
                    f"\n"
                    f"This test tried to modify the user's actual config file.\n"
                    f"CRITICAL RULE: Tests must NEVER modify production state!\n"
                    f"\n"
                    f"Solution: Use the 'tmp_path' fixture or create a temporary\n"
                    f"directory for test-specific config files.\n"
                    f"\n"
                    f"Example:\n"
                    f"  def test_something(tmp_path):\n"
                    f"      config_file = tmp_path / 'test_config.toml'\n"
                    f"      config_file.write_text('[test]\\nkey = \"value\"')\n"
                    f"      config = Config(config_path=config_file)\n"
                    f"{'='*80}\n"
                )
        # Call original write_text
        return original_write_text(self, content, *args, **kwargs)

    def safe_write_bytes(self, content, *args, **kwargs):
        # Check if this is a protected path
        for protected in PROTECTED_CONFIG_PATHS:
            if str(self) == str(protected):
                pytest.fail(
                    f"\n{'='*80}\n"
                    f"TEST SAFETY VIOLATION: Attempted to write to protected config file (bytes)!\n"
                    f"{'='*80}\n"
                    f"Protected path: {protected}\n"
                    f"\n"
                    f"This test tried to modify the user's actual config file.\n"
                    f"CRITICAL RULE: Tests must NEVER modify production state!\n"
                    f"\n"
                    f"Solution: Use the 'tmp_path' fixture or create a temporary\n"
                    f"directory for test-specific config files.\n"
                    f"{'='*80}\n"
                )
        # Call original write_bytes
        return original_write_bytes(self, content, *args, **kwargs)

    # Store original methods globally so they can be restored
    global original_write_text, original_write_bytes
    original_write_text = Path.write_text
    original_write_bytes = Path.write_bytes

    # Patch Path methods for this test session
    monkeypatch.setattr(Path, "write_text", safe_write_text)
    monkeypatch.setattr(Path, "write_bytes", safe_write_bytes)

    yield

    # Restoration happens automatically when monkeypatch undo is called


@pytest.fixture(autouse=True)
def cleanup_windows_mutex():
    """Clean up Windows FileSqueeze mutex before each test.

    This prevents tests from interfering with each other when they
    create TrayService instances. The Windows named mutex persists
    within a pytest session, so we need to clean it up before each test.

    Only runs on Windows.
    """
    if sys.platform != "win32":
        yield
        return

    import ctypes
    import time

    mutex_name = "Global\\FileSqueeze_SingleInstanceMutex"

    # Cleanup before test
    try:
        existing_mutex = ctypes.windll.kernel32.OpenMutexW(0x00100000, False, mutex_name)  # MUTEX_ALL_ACCESS
        if existing_mutex:
            ctypes.windll.kernel32.CloseHandle(existing_mutex)
            # Wait for mutex to be fully released
            time.sleep(0.15)
    except:
        pass

    yield

    # Cleanup after test
    try:
        existing_mutex = ctypes.windll.kernel32.OpenMutexW(0x00100000, False, mutex_name)
        if existing_mutex:
            ctypes.windll.kernel32.CloseHandle(existing_mutex)
    except:
        pass


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "unit: mark test as a unit test")
    config.addinivalue_line("markers", "integration: mark test as an integration test")


def pytest_collection_modifyitems(config, items):
    """Skip tests that require FFmpeg to be missing if FFmpeg is present."""
    ffmpeg_available = shutil.which("ffmpeg") is not None
    ffprobe_available = shutil.which("ffprobe") is not None
    gs_available = (
        shutil.which("gs") is not None or shutil.which("gswin64c") is not None or shutil.which("gswin32c") is not None
    )

    for item in items:
        # Skip tests that require FFmpeg to NOT be available
        if (
            (ffmpeg_available and "ffmpeg_path_not_found" in item.name)
            or (ffprobe_available and "ffprobe_path_not_found" in item.name)
            or (gs_available and "ghostscript_path_not_found" in item.name)
        ):
            item.add_marker(pytest.mark.skip(reason=f"Binary is installed on system, cannot test 'not found' scenario"))

        # Skip tests that try to compress without binaries but binaries are available
        # These tests expect RuntimeError from missing binaries, but binaries exist
        if (
            (ffmpeg_available and "without_ffmpeg" in item.name and "compress" in item.name)
            or (ffprobe_available and "without_ffprobe" in item.name)
            or (ffmpeg_available and "without_ffmpeg" in item.name and "invalid_config" in item.name)
        ):
            item.add_marker(
                pytest.mark.skip(reason=f"FFmpeg/ffprobe is installed, cannot test error handling for missing binaries")
            )

        # Skip tests that expect errors with invalid config when binary is in PATH
        if (
            (ffmpeg_available and "invalid_config" in item.name and "ffmpeg" in item.name)
            or (ffprobe_available and "invalid_config" in item.name and "ffprobe" in item.name)
            or (
                ffmpeg_available
                and "with_config" in item.name
                and "ffmpeg" in item.name
                and item.parent.name == "TestDocumentHelpers"
            )
        ):
            item.add_marker(pytest.mark.skip(reason=f"Binary is in PATH, invalid config falls back successfully"))

        # Note: OCR tests are NOT skipped when Tesseract is missing
        # They should FAIL to alert the team that OCR functionality is broken
        # This is intentional - OCR is a critical feature that should work


@pytest.fixture(autouse=True)
def reset_logger_state():
    """Reset logger state before each test to prevent pollution.

    This ensures that tests don't interfere with each other when they
    register custom loggers. The global _logger variable persists between
    tests, so we need to clean it up.
    """
    import sys

    # Reset before test
    try:
        logger_module = sys.modules["filesqueeze.system.logger"]
        logger_module._logger = None
    except (KeyError, AttributeError):
        # Module not yet imported or not yet created (during Phase 1)
        pass

    yield

    # Reset after test
    try:
        logger_module = sys.modules["filesqueeze.system.logger"]
        logger_module._logger = None
    except (KeyError, AttributeError):
        # Module not yet imported or not yet created (during Phase 1)
        pass


@pytest.fixture(autouse=True)
def reset_binary_finder_state():
    """Reset binary finder state before each test to prevent pollution.

    This ensures that tests don't interfere with each other when they
    register custom binary finders. The global _binary_finder variable
    persists between tests, so we need to clean it up.
    """
    import sys

    # Reset before test
    try:
        binaries_module = sys.modules["filesqueeze.system.binaries"]
        binaries_module._binary_finder = None
    except (KeyError, AttributeError):
        # Module not yet imported or not yet created (during Phase 1)
        pass

    yield

    # Reset after test
    try:
        binaries_module = sys.modules["filesqueeze.system.binaries"]
        binaries_module._binary_finder = None
    except (KeyError, AttributeError):
        # Module not yet imported or not yet created (during Phase 1)
        pass
