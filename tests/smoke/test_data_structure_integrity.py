"""Smoke test: Data structure integrity.

This test verifies that core data structures are properly defined and
maintain critical invariants. Data structure corruption indicates
show-stopper issues like:
- Broken dataclass definitions
- Missing required fields
- Incorrect type annotations
- Corrupted internal state management

Users cannot fix these issues themselves - they indicate broken code.
"""

import pytest
from pathlib import Path


def test_service_state_fields():
    """ServiceState must have all required fields."""
    from filesqueeze.service import ServiceState

    state = ServiceState(
        running=False,
        uptime=None,
        completed_count=0,
        failed_count=0,
        input_dir=Path("/test/input"),
        output_dir=Path("/test/output"),
        processing_files=[],
        processed_files=[],
        cleanup_stats=None
    )

    # Verify all critical fields exist and are accessible
    assert hasattr(state, 'running')
    assert hasattr(state, 'uptime')
    assert hasattr(state, 'completed_count')
    assert hasattr(state, 'failed_count')
    assert hasattr(state, 'input_dir')
    assert hasattr(state, 'output_dir')
    assert hasattr(state, 'processing_files')
    assert hasattr(state, 'processed_files')
    assert hasattr(state, 'cleanup_stats')


def test_processed_file_fields():
    """ProcessedFile must have all required fields."""
    from filesqueeze.service import ProcessedFile

    processed = ProcessedFile(
        filename="test.mp4",
        timestamp="2026-04-28T10:00:00",
        success=True
    )

    # Verify all critical fields exist
    assert hasattr(processed, 'filename')
    assert hasattr(processed, 'timestamp')
    assert hasattr(processed, 'success')
    assert processed.filename == "test.mp4"
    assert processed.success is True


def test_cleanup_stats_fields():
    """CleanupStats must have all required fields."""
    from filesqueeze.service import CleanupStats

    stats = CleanupStats(
        last_cleanup_time="2026-04-28T10:00:00",
        compressed_files_deleted=5,
        archived_files_deleted=2,
        total_space_freed=1024000
    )

    # Verify all critical fields exist
    assert hasattr(stats, 'last_cleanup_time')
    assert hasattr(stats, 'compressed_files_deleted')
    assert hasattr(stats, 'archived_files_deleted')
    assert hasattr(stats, 'total_space_freed')
    assert stats.compressed_files_deleted == 5
    assert stats.total_space_freed == 1024000


def test_state_object_mutability():
    """State object must support required mutations."""
    from filesqueeze.fsm.default import State
    import tempfile

    # Use actual file instead of non-existent path
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        test_file = f.name
        f.write(b"test content")

    try:
        state = State(str(test_file))

        # Verify we can modify critical state properties
        assert hasattr(state, 'status')
        assert hasattr(state, 'format')
        assert hasattr(state, 'metadata')

        # State should be mutable (this is expected behavior)
        state.metadata['test'] = 'value'
        assert state.metadata['test'] == 'value'
    finally:
        # Clean up
        Path(test_file).unlink(missing_ok=True)


def test_enum_values_completeness():
    """Critical enums must have expected values."""
    from filesqueeze.fsm.enums import Document, Video

    # Verify critical enum values exist
    # Document enum
    assert Document.PDF is not None
    assert Document.PNG is not None
    assert Document.JPEG is not None

    # Video enum
    assert Video.MP4 is not None
    assert Video.WMV is not None
    assert Video.AVI is not None


def test_config_get_method():
    """Config.get() method must work with various input types."""
    from filesqueeze.config import Config

    config = Config()

    # Test that get method exists and handles missing keys gracefully
    assert hasattr(config, 'get')
    assert callable(config.get)

    # Should return default for missing keys
    result = config.get('nonexistent.key', 'default_value')
    assert result == 'default_value'