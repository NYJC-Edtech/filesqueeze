"""Test service module - StateProvider interface and DirectoryWatcher."""

import tempfile
import threading
import time
from datetime import timedelta
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from filesqueeze.config import Config
from filesqueeze.service import CompressionHandler, DirectoryWatcher


class TestServiceState:
    """Test ServiceState dataclass."""

    def test_service_state_creation(self):
        """Test that ServiceState can be created with all fields."""
        from filesqueeze.service import ServiceState, ProcessedFile

        processed_file = ProcessedFile(
            filename="test.mp4",
            timestamp="2026-01-27T10:30:00",
            success=True
        )

        state = ServiceState(
            running=True,
            input_dir=Path("/input"),
            output_dir=Path("/output"),
            processing_files=["file1.mp4", "file2.pdf"],
            processed_files=[processed_file],
            completed_count=5,
            failed_count=1,
            uptime=timedelta(hours=1)
        )

        assert state.running is True
        assert state.input_dir == Path("/input")
        assert state.output_dir == Path("/output")
        assert len(state.processing_files) == 2
        assert len(state.processed_files) == 1
        assert state.processed_files[0].filename == "test.mp4"
        assert state.completed_count == 5
        assert state.failed_count == 1
        assert state.uptime == timedelta(hours=1)

    def test_service_state_defaults(self):
        """Test that ServiceState has sensible defaults."""
        from filesqueeze.service import ServiceState

        state = ServiceState(
            running=False,
            input_dir=Path("/input"),
            output_dir=Path("/output")
        )

        assert state.processing_files == []
        assert state.completed_count == 0
        assert state.failed_count == 0
        assert state.uptime == timedelta()


class TestCompressionHandlerTracking:
    """Test CompressionHandler file tracking."""

    def test_handler_tracks_processing_files(self):
        """Test that handler tracks files being processed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_dir = Path(tmpdir) / "input"
            output_dir = Path(tmpdir) / "output"
            input_dir.mkdir()
            output_dir.mkdir()

            config = Config()
            watcher = Mock()
            handler = CompressionHandler(config, input_dir, output_dir, Mock(), watcher)

            # Simulate file being added to processing set
            with handler._lock:
                handler._processing.add("/path/to/file.mp4")

            # Verify it's tracked
            with handler._lock:
                assert "/path/to/file.mp4" in handler._processing
                assert len(handler._processing) == 1

    def test_handler_removes_processed_files(self):
        """Test that handler removes files after processing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_dir = Path(tmpdir) / "input"
            output_dir = Path(tmpdir) / "output"
            input_dir.mkdir()
            output_dir.mkdir()

            config = Config()
            watcher = Mock()
            handler = CompressionHandler(config, input_dir, output_dir, Mock(), watcher)

            # Add file to processing set
            with handler._lock:
                handler._processing.add("/path/to/file.mp4")
                assert len(handler._processing) == 1

            # Remove file
            with handler._lock:
                handler._processing.discard("/path/to/file.mp4")
                assert len(handler._processing) == 0

    def test_handler_thread_safety(self):
        """Test that handler's processing set is thread-safe."""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_dir = Path(tmpdir) / "input"
            output_dir = Path(tmpdir) / "output"
            input_dir.mkdir()
            output_dir.mkdir()

            config = Config()
            watcher = Mock()
            handler = CompressionHandler(config, input_dir, output_dir, Mock(), watcher)

            # Add multiple files concurrently
            files = [f"/path/to/file{i}.mp4" for i in range(100)]

            def add_files():
                for file in files:
                    with handler._lock:
                        handler._processing.add(file)

            threads = [threading.Thread(target=add_files) for _ in range(5)]

            for thread in threads:
                thread.start()

            for thread in threads:
                thread.join()

            # Verify all files were added
            with handler._lock:
                assert len(handler._processing) == 100


class TestDirectoryWatcherState:
    """Test DirectoryWatcher.get_state() method."""

    def test_watcher_state_when_idle(self):
        """Test state query returns correct idle status."""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_dir = Path(tmpdir) / "input"
            output_dir = Path(tmpdir) / "output"
            input_dir.mkdir()

            watcher = DirectoryWatcher(input_dir, output_dir)
            state = watcher.get_state()

            assert state.running is False
            assert state.input_dir == input_dir
            assert state.output_dir == output_dir
            assert len(state.processing_files) == 0
            assert state.completed_count == 0
            assert state.failed_count == 0

    def test_watcher_state_when_running(self):
        """Test state query returns correct running status."""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_dir = Path(tmpdir) / "input"
            output_dir = Path(tmpdir) / "output"
            input_dir.mkdir()

            watcher = DirectoryWatcher(input_dir, output_dir)
            watcher.start()
            watcher._running = True  # Ensure running flag is set

            try:
                state = watcher.get_state()
                assert state.running is True
                assert state.input_dir == input_dir
                assert state.output_dir == output_dir
            finally:
                watcher.stop()

    def test_watcher_state_when_processing(self):
        """Test state query shows files being processed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_dir = Path(tmpdir) / "input"
            output_dir = Path(tmpdir) / "output"
            input_dir.mkdir()

            watcher = DirectoryWatcher(input_dir, output_dir)

            # Simulate files being processed
            with watcher.event_handler._lock:
                watcher.event_handler._processing.add(str(input_dir / "file1.mp4"))
                watcher.event_handler._processing.add(str(input_dir / "file2.pdf"))

            state = watcher.get_state()

            assert len(state.processing_files) == 2
            assert any("file1.mp4" in f for f in state.processing_files)
            assert any("file2.pdf" in f for f in state.processing_files)

    def test_watcher_state_thread_safety(self):
        """Test state queries are thread-safe."""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_dir = Path(tmpdir) / "input"
            output_dir = Path(tmpdir) / "output"
            input_dir.mkdir()

            watcher = DirectoryWatcher(input_dir, output_dir)
            watcher.start()
            watcher._running = True

            try:
                # Concurrent queries from multiple threads
                states = []
                def query_state():
                    for _ in range(50):
                        states.append(watcher.get_state())

                threads = [threading.Thread(target=query_state) for _ in range(5)]

                for thread in threads:
                    thread.start()

                for thread in threads:
                    thread.join()

                # Verify all queries succeeded
                assert len(states) == 250
                assert all(s.running for s in states)
            finally:
                watcher.stop()

    def test_watcher_state_uptime_tracking(self):
        """Test that state tracks uptime correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_dir = Path(tmpdir) / "input"
            output_dir = Path(tmpdir) / "output"
            input_dir.mkdir()

            watcher = DirectoryWatcher(input_dir, output_dir)
            watcher.start()
            watcher._running = True

            try:
                # Wait a bit
                time.sleep(0.1)

                state = watcher.get_state()
                assert state.uptime > timedelta()
                assert state.uptime < timedelta(seconds=10)
            finally:
                watcher.stop()


class TestStateProviderInterface:
    """Test StateProvider interface compliance."""

    def test_directory_watcher_implements_state_provider(self):
        """Test that DirectoryWatcher implements StateProvider interface."""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_dir = Path(tmpdir) / "input"
            output_dir = Path(tmpdir) / "output"
            input_dir.mkdir()

            watcher = DirectoryWatcher(input_dir, output_dir)

            # Verify get_state method exists
            assert hasattr(watcher, 'get_state')
            assert callable(watcher.get_state)

            # Verify it returns ServiceState
            state = watcher.get_state()
            from filesqueeze.service import ServiceState
            assert isinstance(state, ServiceState)

    def test_state_is_immutable_snapshot(self):
        """Test that state is a snapshot (not affected by subsequent changes)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_dir = Path(tmpdir) / "input"
            output_dir = Path(tmpdir) / "output"
            input_dir.mkdir()

            watcher = DirectoryWatcher(input_dir, output_dir)

            # Get initial state
            state1 = watcher.get_state()

            # Simulate adding a file to processing
            with watcher.event_handler._lock:
                watcher.event_handler._processing.add(str(input_dir / "new_file.mp4"))

            # Get new state
            state2 = watcher.get_state()

            # Verify state1 is unchanged (immutable snapshot)
            assert len(state1.processing_files) == 0
            assert len(state2.processing_files) == 1
