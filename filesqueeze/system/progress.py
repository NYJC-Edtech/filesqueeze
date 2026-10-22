"""filesqueeze.system.progress

Progress reporting infrastructure for long-running operations.

Ops code reports completion percentages (e.g. parsed from FFmpeg's
``-progress pipe:1`` output) through the registered tracker. The watch
service registers a :class:`ProgressTracker` at startup so the GUI can
display per-file progress; without registration the no-op
:class:`NullProgressTracker` keeps ops callers working unchanged.

Dependency direction: ops -> system (OK). This module must never import
from ops.
"""

import threading


class ProgressTracker:
    """Thread-safe registry of per-file progress percentages.

    Percentages are keyed by the file path the user sees (the original
    input file), so consumers can join against ``ServiceState.processing_files``.
    Operations may run against a different physical path than the displayed
    one (Google Drive temp copies, PPTX->MP4 intermediates); register those
    with :meth:`alias` so reports land under the displayed key.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._progress: dict[str, int] = {}
        self._aliases: dict[str, str] = {}

    def report(self, path: str, percent: int) -> None:
        """Record the latest progress percentage for a file.

        Args:
            path: Path of the file being processed (resolved through
                registered aliases).
            percent: Completion percentage (0-100).
        """
        with self._lock:
            key = self._aliases.get(path, path)
            self._progress[key] = percent

    def alias(self, actual: str, display: str) -> None:
        """Map a processing-time path onto the path the user sees.

        Args:
            actual: Path passed to the operation (e.g. temp copy).
            display: Path shown to the user (original input file).
        """
        with self._lock:
            self._aliases[actual] = display

    def clear(self, path: str) -> None:
        """Drop all progress state for a file once processing ends.

        Removes the progress entry plus any aliases pointing at or from
        this path, so temp-copy mappings cannot leak between files.

        Args:
            path: Displayed (original) file path.
        """
        with self._lock:
            self._progress.pop(path, None)
            self._aliases = {a: d for a, d in self._aliases.items() if a != path and d != path}

    def snapshot(self) -> dict[str, int]:
        """Get a copy of current progress entries.

        Returns:
            Dict mapping displayed file path to percentage.
        """
        with self._lock:
            return dict(self._progress)


class NullProgressTracker:
    """No-op tracker used when no component has registered one."""

    def report(self, path: str, percent: int) -> None:
        pass

    def alias(self, actual: str, display: str) -> None:
        pass

    def clear(self, path: str) -> None:
        pass

    def snapshot(self) -> dict[str, int]:
        return {}


_tracker: ProgressTracker | NullProgressTracker = NullProgressTracker()


def register_progress_tracker(tracker: ProgressTracker | NullProgressTracker) -> None:
    """Register the progress tracker for cross-module progress reporting.

    Args:
        tracker: Tracker instance (typically a ProgressTracker created by
            the watch service at startup).
    """
    global _tracker
    _tracker = tracker


def get_progress_tracker() -> ProgressTracker | NullProgressTracker:
    """Get the registered progress tracker.

    Returns:
        The registered tracker, or the no-op tracker if none was registered.
    """
    return _tracker
