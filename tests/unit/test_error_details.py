"""Tests for failed-job error details: the report builder and storage.

The GUI's error-details dialog and its Copy-details action consume
``ErrorDetails`` produced by ``build_error_report`` in the service's
failure path — environment info plus error plus traceback, ready to
paste back for remote debugging. Imports of ``filesqueeze`` modules
happen INSIDE the test functions (see tests/unit/test_doctor_autostart.py
for why).
"""

import threading

import pytest


class TestBuildErrorReport:
    def test_report_from_exception_carries_summary_and_traceback(self):
        from filesqueeze.service import build_error_report

        try:
            raise RuntimeError(
                "FFmpeg could not be launched: 'C:/ffmpeg/bin' — The system cannot find the file specified (WinError 2)"
            )
        except RuntimeError as exc:
            details = build_error_report("C:/videos/NY041 Camera 1.MP4", exc)

        assert details.summary.startswith("RuntimeError: FFmpeg could not be launched")
        assert "NY041 Camera 1.MP4" in details.report
        assert "Error: RuntimeError: FFmpeg could not be launched" in details.report
        assert "Traceback:" in details.report
        assert "RuntimeError: FFmpeg could not be launched" in details.report

    def test_report_carries_environment_info(self):
        from filesqueeze.service import build_error_report

        try:
            raise RuntimeError("boom")
        except RuntimeError as exc:
            details = build_error_report("C:/f.mp4", exc)

        assert "Version:" in details.report
        assert "Platform:" in details.report
        assert "Time:" in details.report
        assert "File:     C:/f.mp4" in details.report

    def test_report_without_exception_uses_summary(self):
        from filesqueeze.service import build_error_report

        details = build_error_report("C:/f.mp4", summary="Output file not created: C:/out/f.mp4")

        assert details.summary == "Output file not created: C:/out/f.mp4"
        assert "Output file not created" in details.report
        assert "no traceback" in details.report

    def test_requires_exception_or_summary(self):
        from filesqueeze.service import build_error_report

        with pytest.raises(ValueError):
            build_error_report("C:/f.mp4")


class TestProcessedFileErrorDetails:
    def test_failed_record_defaults_to_none(self):
        from filesqueeze.service import ProcessedFile

        record = ProcessedFile(filename="ok.mp4", timestamp="2026-11-04T09:00:00", success=True)

        assert record.error_details is None

    def test_add_processed_file_stores_error_details(self):
        from filesqueeze.service import DirectoryWatcher, ErrorDetails

        watcher = object.__new__(DirectoryWatcher)
        watcher._processed_files = []
        watcher._max_processed_files = 100
        watcher._state_lock = threading.Lock()
        watcher._completed_count = 0
        watcher._failed_count = 0

        details = ErrorDetails(summary="RuntimeError: boom", report="report body")
        watcher._add_processed_file("bad.mp4", success=False, error_details=details)

        assert watcher._failed_count == 1
        record = watcher._processed_files[-1]
        assert record.filename == "bad.mp4"
        assert record.success is False
        assert record.error_details is details

    def test_add_processed_file_success_has_no_details(self):
        from filesqueeze.service import DirectoryWatcher

        watcher = object.__new__(DirectoryWatcher)
        watcher._processed_files = []
        watcher._max_processed_files = 100
        watcher._state_lock = threading.Lock()
        watcher._completed_count = 0
        watcher._failed_count = 0

        watcher._add_processed_file("ok.mp4", success=True)

        record = watcher._processed_files[-1]
        assert record.success is True
        assert record.error_details is None
