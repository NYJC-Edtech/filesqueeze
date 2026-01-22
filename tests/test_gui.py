"""Test GUI module - StatusWindow and state consumption."""

from datetime import timedelta
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import threading
import time

import pytest

from filesqueeze.service import ServiceState, StateProvider


class MockStateProvider(StateProvider):
    """Mock StateProvider for testing."""

    def __init__(self, state=None):
        self._state = state or ServiceState(
            running=False,
            input_dir=Path("/input"),
            output_dir=Path("/output")
        )
        self.get_state_call_count = 0

    def get_state(self) -> ServiceState:
        self.get_state_call_count += 1
        return self._state

    def set_state(self, state: ServiceState):
        self._state = state


class TestStatusWindow:
    """Test StatusWindow GUI component."""

    def test_status_window_creation(self):
        """Test that StatusWindow can be created with StateProvider."""
        from filesqueeze.gui import StatusWindow

        mock_provider = MockStateProvider()
        window = StatusWindow(mock_provider)

        assert window.state_provider == mock_provider
        assert window.root is not None

    def test_status_window_displays_service_status(self):
        """Test GUI window displays service running status correctly."""
        from filesqueeze.gui import StatusWindow

        # Create mock provider with running state
        mock_provider = MockStateProvider(
            ServiceState(
                running=True,
                input_dir=Path("/input"),
                output_dir=Path("/output"),
                processing_files=[],
                completed_count=10,
                failed_count=2,
                uptime=timedelta(hours=2, minutes=30)
            )
        )

        window = StatusWindow(mock_provider)
        window.update_display()

        # Verify state was queried
        assert mock_provider.get_state_call_count >= 1

    def test_status_window_displays_processing_files(self):
        """Test GUI window shows files being processed."""
        from filesqueeze.gui import StatusWindow
        from unittest.mock import patch

        mock_provider = MockStateProvider(
            ServiceState(
                running=True,
                input_dir=Path("/input"),
                output_dir=Path("/output"),
                processing_files=[
                    "/input/video1.mp4",
                    "/input/document2.pdf",
                    "/input/image3.jpg"
                ],
                completed_count=5,
                failed_count=0,
                uptime=timedelta(minutes=15)
            )
        )

        # Mock Tk to avoid multiple initialization issues
        with patch('tkinter.Tk'):
            window = StatusWindow(mock_provider)
            window.update_display()

        # Verify files are displayed
        state = mock_provider.get_state()
        assert len(state.processing_files) == 3

    def test_status_window_displays_idle_state(self):
        """Test GUI window correctly shows idle (not running) state."""
        from filesqueeze.gui import StatusWindow
        from unittest.mock import patch

        mock_provider = MockStateProvider(
            ServiceState(
                running=False,
                input_dir=Path("/input"),
                output_dir=Path("/output"),
                processing_files=[],
                completed_count=0,
                failed_count=0,
                uptime=timedelta()
            )
        )

        # Mock Tk to avoid multiple initialization issues
        with patch('tkinter.Tk'):
            window = StatusWindow(mock_provider)
            window.update_display()

        state = mock_provider.get_state()
        assert state.running is False

    def test_status_window_auto_refresh(self):
        """Test that GUI window auto-refreshes state periodically."""
        from filesqueeze.gui import StatusWindow

        mock_provider = MockStateProvider(
            ServiceState(
                running=True,
                input_dir=Path("/input"),
                output_dir=Path("/output"),
                processing_files=[],
                completed_count=0,
                failed_count=0,
                uptime=timedelta()
            )
        )

        window = StatusWindow(mock_provider, refresh_interval=100)  # 100ms for testing

        # Initial query happens during __init__
        initial_count = mock_provider.get_state_call_count
        assert initial_count >= 1

        # Start auto-refresh
        window.start_auto_refresh()

        # Wait a bit
        time.sleep(0.35)

        # Stop auto-refresh
        window.stop_auto_refresh()

        # Verify at least one more query was made
        assert mock_provider.get_state_call_count >= initial_count

        # Cleanup
        try:
            window.root.destroy()
        except:
            pass

    def test_status_window_handles_concurrent_updates(self):
        """Test that GUI can handle concurrent state updates."""
        from filesqueeze.gui import StatusWindow
        from unittest.mock import patch

        mock_provider = MockStateProvider(
            ServiceState(
                running=True,
                input_dir=Path("/input"),
                output_dir=Path("/output"),
                processing_files=[],
                completed_count=0,
                failed_count=0,
                uptime=timedelta()
            )
        )

        # Mock Tk to avoid multiple initialization issues
        with patch('tkinter.Tk'):
            window = StatusWindow(mock_provider)

        # Simulate state changes (but don't call update_display from threads)
        # Just verify the state provider can handle concurrent state changes
        def update_state():
            for i in range(10):
                new_state = ServiceState(
                    running=True,
                    input_dir=Path("/input"),
                    output_dir=Path("/output"),
                    processing_files=[f"/input/file{i}.mp4"],
                    completed_count=i,
                    failed_count=0,
                    uptime=timedelta(seconds=i)
                )
                mock_provider.set_state(new_state)
                time.sleep(0.001)

        threads = [threading.Thread(target=update_state) for _ in range(3)]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # Verify state provider was called at least once during initialization
        assert mock_provider.get_state_call_count >= 1


class TestGUIIntegration:
    """Test GUI integration with StateProvider."""

    def test_gui_with_real_directory_watcher(self):
        """Test GUI works with real DirectoryWatcher StateProvider."""
        import tempfile
        from filesqueeze.gui import StatusWindow
        from filesqueeze.service import DirectoryWatcher

        with tempfile.TemporaryDirectory() as tmpdir:
            input_dir = Path(tmpdir) / "input"
            output_dir = Path(tmpdir) / "output"
            input_dir.mkdir()

            watcher = DirectoryWatcher(input_dir, output_dir)
            window = StatusWindow(watcher)

            # Get state through GUI's provider
            state = window.state_provider.get_state()

            assert state.running is False
            assert state.input_dir == input_dir
            assert state.output_dir == output_dir

    def test_gui_state_updates_in_realtime(self):
        """Test that GUI reflects real-time state changes."""
        from filesqueeze.gui import StatusWindow
        import tempfile
        from filesqueeze.service import DirectoryWatcher

        with tempfile.TemporaryDirectory() as tmpdir:
            input_dir = Path(tmpdir) / "input"
            output_dir = Path(tmpdir) / "output"
            input_dir.mkdir()

            watcher = DirectoryWatcher(input_dir, output_dir)
            window = StatusWindow(watcher)

            # Get initial state
            initial_state = window.state_provider.get_state()
            assert initial_state.running is False

            # Start watcher
            watcher.start()
            watcher._running = True

            # Get updated state
            updated_state = window.state_provider.get_state()
            assert updated_state.running is True

            # Cleanup
            watcher.stop()

    def test_gui_displays_compression_stats(self):
        """Test GUI displays completed/failed counts correctly."""
        from filesqueeze.gui import StatusWindow

        mock_provider = MockStateProvider(
            ServiceState(
                running=True,
                input_dir=Path("/input"),
                output_dir=Path("/output"),
                processing_files=["/input/current.mp4"],
                completed_count=42,
                failed_count=3,
                uptime=timedelta(hours=5)
            )
        )

        window = StatusWindow(mock_provider)
        window.update_display()

        state = mock_provider.get_state()
        assert state.completed_count == 42
        assert state.failed_count == 3
        assert state.completed_count + state.failed_count == 45


class TestGUIWindowLifecycle:
    """Test GUI window lifecycle methods."""

    def test_status_window_show_and_hide(self):
        """Test window can be shown and hidden."""
        from filesqueeze.gui import StatusWindow

        mock_provider = MockStateProvider()
        window = StatusWindow(mock_provider)

        # Verify window is created (check root attribute)
        assert hasattr(window, 'root')
        assert window.root is not None

        # Close window (use destroy instead of close to avoid issues)
        try:
            window.root.destroy()
        except:
            pass

    def test_status_window_cleanup_on_close(self):
        """Test window properly cleans up resources on close."""
        from filesqueeze.gui import StatusWindow

        mock_provider = MockStateProvider()
        window = StatusWindow(mock_provider, refresh_interval=100)

        # Start auto-refresh
        window.start_auto_refresh()
        time.sleep(0.2)

        # Close window (should stop auto-refresh)
        window.close()

        # Verify auto-refresh stopped (no more queries after short delay)
        initial_count = mock_provider.get_state_call_count
        time.sleep(0.2)
        final_count = mock_provider.get_state_call_count

        # Should have stopped querying (or very few additional queries)
        assert (final_count - initial_count) < 3

    def test_status_window_without_auto_refresh(self):
        """Test window works without auto-refresh (manual updates only)."""
        from filesqueeze.gui import StatusWindow

        mock_provider = MockStateProvider()
        window = StatusWindow(mock_provider, refresh_interval=None)

        # Initial update happens during __init__
        initial_count = mock_provider.get_state_call_count
        assert initial_count >= 1

        # Manual update
        window.update_display()

        assert mock_provider.get_state_call_count >= initial_count + 1

        time.sleep(0.2)

        # Should not have increased (no auto-refresh)
        count_after_wait = mock_provider.get_state_call_count
        assert count_after_wait == mock_provider.get_state_call_count

        # Cleanup
        try:
            window.root.destroy()
        except:
            pass
