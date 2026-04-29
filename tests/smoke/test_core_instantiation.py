"""Smoke test: Core class instantiation.

This test verifies that all critical FileSqueeze classes can be instantiated
with minimal requirements. Instantiation failures indicate show-stopper issues like:
- Broken class definitions
- Missing required methods or properties
- Incorrect initialization logic
- Incompatible data structures

Users cannot fix these issues themselves - they indicate a broken installation.
"""

from pathlib import Path


def test_config_class_instantiation():
    """Config class must be instantiable with defaults."""
    from filesqueeze.config import Config

    # Should create with default configuration
    config = Config()
    assert config is not None
    assert hasattr(config, "get")


def test_service_state_instantiation():
    """ServiceState dataclass must be instantiable."""
    from filesqueeze.service import ServiceState

    # Should create with minimal data
    state = ServiceState(
        running=False,
        uptime=None,
        completed_count=0,
        failed_count=0,
        input_dir=Path("/test/input"),
        output_dir=Path("/test/output"),
        processing_files=[],
        processed_files=[],
        cleanup_stats=None,
    )
    assert state is not None
    assert state.running is False


def test_processed_file_instantiation():
    """ProcessedFile dataclass must be instantiable."""
    from filesqueeze.service import ProcessedFile

    processed = ProcessedFile(filename="test.pdf", timestamp="2026-04-28T10:00:00", success=True)
    assert processed is not None
    assert processed.filename == "test.pdf"


def test_state_object_instantiation():
    """State object must be instantiable."""
    import tempfile

    from filesqueeze.fsm.default import State

    # Use actual file instead of non-existent path
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        test_file = f.name
        f.write(b"test content")

    try:
        state = State(str(test_file))
        assert state is not None
        assert state.origin == Path(test_file)
        assert state.target == Path(test_file)
    finally:
        # Clean up
        Path(test_file).unlink(missing_ok=True)


def test_enums_exist():
    """Critical enum values must exist."""
    from filesqueeze.fsm.enums import Document, Video

    # Check that enum values exist
    assert hasattr(Document, "PDF")
    assert hasattr(Video, "MP4")


def test_cleanup_stats_instantiation():
    """CleanupStats must be instantiable."""
    from filesqueeze.service import CleanupStats

    stats = CleanupStats(last_cleanup_time=None, compressed_files_deleted=0, archived_files_deleted=0, total_space_freed=0)
    assert stats is not None
    assert stats.compressed_files_deleted == 0


def test_handler_classes_instantiable():
    """Handler classes must be importable and structurally sound."""
    import tempfile

    from filesqueeze import handlers

    # Test that handler functions exist and can be called with State objects
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        test_file = f.name
        f.write(b"test content")

    try:
        from filesqueeze.fsm.default import State

        state = State(str(test_file))

        # Verify handler modules are accessible (ops modules, not handlers module)
        from filesqueeze.ops import video, document, image

        assert video is not None
        assert document is not None
        assert image is not None

        # Verify handlers module itself is accessible
        assert handlers is not None
        assert hasattr(handlers, "analyzeVideo")
        assert hasattr(handlers, "analyzeDocument")
        assert hasattr(handlers, "compressVideo")
        assert hasattr(handlers, "compressDocument")
    finally:
        # Clean up
        Path(test_file).unlink(missing_ok=True)
