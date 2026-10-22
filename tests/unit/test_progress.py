"""Tests for progress reporting infrastructure.

Covers system/progress.py (ProgressTracker, NullProgressTracker,
registration) and the FFmpeg ``-progress pipe:1`` stdout parser in
ops/video.py. No FFmpeg binary required.
"""

import threading

import pytest

from filesqueeze.ops.video import ffmpeg_progress_handler
from filesqueeze.system.progress import (
    NullProgressTracker,
    ProgressTracker,
    get_progress_tracker,
    register_progress_tracker,
)


@pytest.fixture
def restore_tracker():
    """Restore the previously registered tracker after each test."""
    previous = get_progress_tracker()
    yield
    register_progress_tracker(previous)


class TestProgressTracker:
    """Test ProgressTracker dict semantics."""

    def test_report_and_snapshot(self):
        tracker = ProgressTracker()
        tracker.report("C:/watch/a.mp4", 10)
        tracker.report("C:/watch/b.mp4", 99)
        assert tracker.snapshot() == {"C:/watch/a.mp4": 10, "C:/watch/b.mp4": 99}

    def test_snapshot_is_a_copy(self):
        tracker = ProgressTracker()
        tracker.report("a.mp4", 5)
        snap = tracker.snapshot()
        snap["a.mp4"] = 100
        assert tracker.snapshot() == {"a.mp4": 5}

    def test_alias_redirects_reports_to_display_key(self):
        tracker = ProgressTracker()
        tracker.alias("C:/temp/copy.mp4", "C:/watch/a.mp4")
        tracker.report("C:/temp/copy.mp4", 42)
        assert tracker.snapshot() == {"C:/watch/a.mp4": 42}

    def test_unaliased_path_reports_under_itself(self):
        tracker = ProgressTracker()
        tracker.alias("x", "y")
        tracker.report("z", 7)
        assert tracker.snapshot() == {"z": 7}

    def test_clear_removes_entry_and_aliases(self):
        tracker = ProgressTracker()
        tracker.alias("C:/temp/copy.mp4", "C:/watch/a.mp4")
        tracker.report("C:/watch/a.mp4", 42)
        tracker.clear("C:/watch/a.mp4")
        assert tracker.snapshot() == {}
        # Late reports from the temp copy no longer map to the display key
        tracker.report("C:/temp/copy.mp4", 50)
        assert tracker.snapshot() == {"C:/temp/copy.mp4": 50}

    def test_clear_only_touches_given_path(self):
        tracker = ProgressTracker()
        tracker.report("a.mp4", 1)
        tracker.report("b.mp4", 2)
        tracker.clear("a.mp4")
        assert tracker.snapshot() == {"b.mp4": 2}

    def test_concurrent_reports(self):
        tracker = ProgressTracker()

        def hammer(index):
            for percent in range(100):
                tracker.report(f"f{index}.mp4", percent)

        threads = [threading.Thread(target=hammer, args=(i,)) for i in range(4)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        assert tracker.snapshot() == {f"f{i}.mp4": 99 for i in range(4)}


class TestNullProgressTracker:
    """Test the no-op tracker used when nothing is registered."""

    def test_all_operations_are_noops(self):
        tracker = NullProgressTracker()
        tracker.report("a", 1)
        tracker.alias("a", "b")
        tracker.clear("a")
        assert tracker.snapshot() == {}


class TestTrackerRegistration:
    """Test the register/get service registration pattern."""

    def test_register_and_get(self, restore_tracker):
        tracker = ProgressTracker()
        register_progress_tracker(tracker)
        assert get_progress_tracker() is tracker

    def test_default_is_noop(self):
        # Whatever was registered before, the no-op tracker must behave
        register_progress_tracker(NullProgressTracker())
        tracker = get_progress_tracker()
        tracker.report("a", 1)
        assert tracker.snapshot() == {}
        # Restore for other tests in this process
        register_progress_tracker(NullProgressTracker())


class TestFfmpegProgressHandler:
    """Test parsing of FFmpeg -progress output into percentages."""

    @staticmethod
    def _feed(lines, total_duration):
        received = []
        handle = ffmpeg_progress_handler(total_duration, received.append)
        for line in lines:
            handle(line)
        return received

    def test_percent_from_out_time_us(self):
        # 10s and 50s into a 100s encode
        received = self._feed(["frame=1\n", "out_time_us=10000000\n", "out_time_us=50000000\n"], 100.0)
        assert received == [10, 50]

    def test_percent_from_out_time_ms_fallback(self):
        # FFmpeg's out_time_ms is misnamed: it also carries microseconds
        received = self._feed(["out_time_ms=25000000\n"], 100.0)
        assert received == [25]

    def test_percent_truncates_to_int(self):
        received = self._feed(["out_time_us=15900000\n"], 100.0)
        assert received == [15]

    def test_caps_at_99_until_run_finishes(self):
        # Output time can overshoot the container duration; never show 100%
        received = self._feed(["out_time_us=200000000\n"], 100.0)
        assert received == [99]

    def test_clamps_early_negative_to_zero(self):
        received = self._feed(["out_time_us=-10500000\n"], 100.0)
        assert received == [0]

    def test_ignores_na_and_garbage_lines(self):
        received = self._feed(
            ["out_time_us=N/A\n", "progress=continue\n", "total_size=1024\n", "not a pair\n", "out_time=00:00:05.00\n"],
            100.0,
        )
        assert received == []

    def test_reports_only_increases(self):
        # Duplicate and decreasing percentages are suppressed
        received = self._feed(
            ["out_time_us=50000000\n", "out_time_us=50000000\n", "out_time_us=20000000\n", "out_time_us=80000000\n"],
            100.0,
        )
        assert received == [50, 80]

    def test_no_duration_no_reports(self):
        received = self._feed(["out_time_us=50000000\n"], None)
        assert received == []

    def test_zero_duration_no_reports(self):
        received = self._feed(["out_time_us=50000000\n"], 0.0)
        assert received == []
