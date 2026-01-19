"""Pytest configuration for FileSqueeze tests."""

import sys
import shutil
import pytest
from pathlib import Path

# Add parent directory to path so we can import filesqueeze
sys.path.insert(0, str(Path(__file__).parent.parent))


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )


def pytest_collection_modifyitems(config, items):
    """Skip tests that require FFmpeg to be missing if FFmpeg is present."""
    ffmpeg_available = shutil.which('ffmpeg') is not None
    ffprobe_available = shutil.which('ffprobe') is not None
    gs_available = shutil.which('gs') is not None or shutil.which('gswin64c') is not None or shutil.which('gswin32c') is not None

    for item in items:
        # Skip tests that require FFmpeg to NOT be available
        if (ffmpeg_available and 'ffmpeg_path_not_found' in item.name) or \
           (ffprobe_available and 'ffprobe_path_not_found' in item.name) or \
           (gs_available and 'ghostscript_path_not_found' in item.name):
            item.add_marker(
                pytest.mark.skip(
                    reason=f"Binary is installed on system, cannot test 'not found' scenario"
                )
            )

        # Skip tests that try to compress without binaries but binaries are available
        # These tests expect RuntimeError from missing binaries, but binaries exist
        if (ffmpeg_available and 'without_ffmpeg' in item.name and 'compress' in item.name) or \
           (ffprobe_available and 'without_ffprobe' in item.name) or \
           (ffmpeg_available and 'without_ffmpeg' in item.name and 'invalid_config' in item.name):
            item.add_marker(
                pytest.mark.skip(
                    reason=f"FFmpeg/ffprobe is installed, cannot test error handling for missing binaries"
                )
            )

        # Skip tests that expect errors with invalid config when binary is in PATH
        if (ffmpeg_available and 'invalid_config' in item.name and 'ffmpeg' in item.name) or \
           (ffprobe_available and 'invalid_config' in item.name and 'ffprobe' in item.name) or \
           (ffmpeg_available and 'with_config' in item.name and 'ffmpeg' in item.name and item.parent.name == 'TestDocumentHelpers'):
            item.add_marker(
                pytest.mark.skip(
                    reason=f"Binary is in PATH, invalid config falls back successfully"
                )
            )

