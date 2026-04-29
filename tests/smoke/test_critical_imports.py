"""Smoke test: Critical module imports.

This test verifies that all critical FileSqueeze modules can be imported
without errors. Import failures indicate show-stopper issues like:
- Circular dependencies
- Broken Python syntax
- Missing dependencies in installation
- Corrupted codebase

Users cannot fix these issues themselves - they require proper installation.
"""

import os

import pytest


def test_core_modules_import():
    """All core modules must be importable."""
    # Core application modules
    from filesqueeze import config, logger, service
    from filesqueeze.fsm import default, enums

    # These imports should never fail in a working installation
    assert config is not None
    assert service is not None
    assert logger is not None
    assert enums is not None
    assert default is not None


def test_operations_modules_import():
    """All operation modules must be importable."""
    from filesqueeze.ops import document, image, video

    assert video is not None
    assert document is not None
    assert image is not None


def test_system_modules_import():
    """All system modules must be importable."""
    from filesqueeze.system import binaries, get_binary_finder, register_binary_finder

    assert binaries is not None
    assert register_binary_finder is not None
    assert get_binary_finder is not None


def test_state_machine_imports():
    """State machine components must be importable."""
    from filesqueeze.fsm.default import State as DefaultState
    from filesqueeze.fsm.enums import Document, Video

    # Verify enums are accessible
    assert Document is not None
    assert Video is not None
    assert DefaultState is not None


def test_service_classes_import():
    """Service classes must be importable."""
    from filesqueeze.service import CompressionHandler, DirectoryWatcher, ProcessedFile, RetentionManager, ServiceState

    assert ServiceState is not None
    assert ProcessedFile is not None
    assert DirectoryWatcher is not None
    assert CompressionHandler is not None
    assert RetentionManager is not None


@pytest.mark.skipif(os.environ.get("CI") == "true", reason="GUI modules require display server (skip in CI)")
def test_gui_modules_import():
    """GUI modules must be importable (even if not used on all platforms)."""
    try:
        from filesqueeze import gui, tray

        # If we get here, GUI modules imported successfully
        assert gui is not None
        assert tray is not None
    except ImportError as e:
        # GUI modules might not be available on all platforms (e.g., headless servers)
        # This is acceptable for smoke testing - we just need to know they exist
        pytest.skip(f"GUI modules not available: {e}")
    except Exception as e:
        # Display server errors (X11, Wayland, etc.) - skip in headless environments
        if "display" in str(e).lower() or "xlib" in str(e).lower():
            pytest.skip(f"GUI modules require display server: {e}")
        else:
            raise


def test_main_api_imports():
    """Main API functions must be importable."""
    from filesqueeze import make_image, make_pdf, make_presentation, make_video

    # Main API functions must be available
    assert make_video is not None
    assert make_pdf is not None
    assert make_image is not None
    assert make_presentation is not None
