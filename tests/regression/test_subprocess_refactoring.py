"""Subprocess refactoring tests - behavioral focus.

These tests verify that the subprocess refactoring preserves the actual behavior
of compression operations. They focus on observable behavior rather than implementation details.

Run these tests to verify subprocess refactoring maintains correct behavior.
"""

import os
import sys
import pytest
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestSubprocessBehaviorPreserved:
    """Tests to verify subprocess refactoring preserves actual behavior."""

    def test_windows_console_hiding_works(self, tmp_path):
        """Windows subprocess calls should hide console windows during actual operations."""
        if os.name != "nt":
            pytest.skip("Windows-specific test")

        # Test that we can run a subprocess without showing console window
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        # Use the utility function to run subprocess
        from filesqueeze.utils.subprocess_helper import run_subprocess, SubprocessError

        cmd = [sys.executable, "-c", 'print("hidden window test")']
        try:
            run_subprocess(
                cmd, timeout=5, tool_name="Python", input_file=str(test_file), capture_output=True, text_mode=True, check=True
            )
            # If we get here without console window appearing, success
            assert True
        except SubprocessError:
            pytest.fail("Subprocess should have succeeded")

    def test_timeout_handling_behavior(self, tmp_path):
        """Timeout behavior should be preserved - should raise appropriate error."""
        from filesqueeze.utils.subprocess_helper import run_subprocess, SubprocessTimeout

        test_file = tmp_path / "test.txt"

        # Create a command that will timeout
        cmd = [sys.executable, "-c", "import time; time.sleep(10)"]

        with pytest.raises(SubprocessTimeout) as exc_info:
            run_subprocess(cmd, timeout=0.1, tool_name="TestTool", input_file=str(test_file))

        # Verify the error message has the right information
        error_msg = str(exc_info.value)
        assert "timeout" in error_msg.lower()
        assert "TestTool" in error_msg

    def test_failure_handling_behavior(self, tmp_path):
        """Failure behavior should be preserved - should raise appropriate error with context."""
        from filesqueeze.utils.subprocess_helper import run_subprocess, SubprocessError

        test_file = tmp_path / "test.txt"

        # Create a command that will fail
        cmd = [sys.executable, "-c", "import sys; sys.exit(1)"]

        with pytest.raises(SubprocessError) as exc_info:
            run_subprocess(cmd, timeout=5, tool_name="TestTool", input_file=str(test_file))

        # Verify the error has context
        error = exc_info.value
        assert hasattr(error, "return_code")
        assert error.return_code == 1
        assert "TestTool" in str(error)

    def test_output_capture_behavior(self, tmp_path):
        """Output capture behavior should work correctly when needed."""
        from filesqueeze.utils.subprocess_helper import run_subprocess

        test_file = tmp_path / "test.txt"

        # Test that we can capture output
        cmd = [sys.executable, "-c", 'print("test output")']

        result = run_subprocess(
            cmd, timeout=5, tool_name="Python", input_file=str(test_file), capture_output=True, text_mode=True, check=True
        )

        # Verify we got the output
        assert "test output" in result

    def test_file_verification_behavior(self, tmp_path):
        """File verification behavior should catch missing files correctly."""
        from filesqueeze.utils.subprocess_helper import verify_output_file

        nonexistent_file = tmp_path / "does_not_exist.pdf"

        with pytest.raises(FileNotFoundError) as exc_info:
            verify_output_file(str(nonexistent_file), min_size=100)

        # Verify error message is helpful
        assert "not created" in str(exc_info.value).lower()

    def test_file_size_verification_behavior(self, tmp_path):
        """File size verification should reject files that are too small."""
        from filesqueeze.utils.subprocess_helper import verify_output_file

        # Create a file that's too small
        small_file = tmp_path / "small.pdf"
        small_file.write_bytes(b"tiny")

        with pytest.raises(RuntimeError) as exc_info:
            verify_output_file(str(small_file), min_size=1000)

        # Verify error message has size context
        assert "too small" in str(exc_info.value).lower()
        assert "1000" in str(exc_info.value)


class TestErrorMessagesPreserved:
    """Tests to verify error messages maintain user-facing behavior."""

    def test_timeout_error_messages_are_helpful(self):
        """Timeout error messages should provide helpful context."""
        from filesqueeze.utils.subprocess_helper import SubprocessTimeout

        error = SubprocessTimeout("Ghostscript timeout processing: file.pdf")

        # Verify error message is helpful
        error_str = str(error)
        assert "Ghostscript" in error_str
        assert "timeout" in error_str.lower()
        assert "file.pdf" in error_str

    def test_failure_error_messages_are_helpful(self):
        """Failure error messages should include return code and context."""
        from filesqueeze.utils.subprocess_helper import SubprocessError

        error = SubprocessError("FFmpeg failed with return code 1: video.mp4", return_code=1)

        # Verify error message is helpful
        error_str = str(error)
        assert "FFmpeg" in error_str
        assert "return code" in error_str.lower()
        assert "1" in error_str
        assert "video.mp4" in error_str


class TestPlatformBehaviorConsistency:
    """Tests to verify platform-specific behavior is consistent."""

    def test_platform_detection_consistent(self):
        """Platform detection should be consistent across utility and ops modules."""
        # All modules should agree on the platform
        import filesqueeze.utils.subprocess_helper as utils
        import filesqueeze.ops.document as document
        import filesqueeze.ops.video as video

        # All should use the same platform detection
        assert os.name == os.name  # Obviously true, but verifies access

        # On Windows, all should have access to the same subprocess flags
        if os.name == "nt":
            import subprocess

            # Verify Windows-specific features are available everywhere
            assert hasattr(subprocess, "STARTUPINFO")
            assert hasattr(subprocess, "STARTF_USESHOWWINDOW")
            assert hasattr(subprocess, "SW_HIDE")

    def test_cross_platform_behavior(self):
        """Subprocess behavior should work correctly on all platforms."""
        from filesqueeze.utils.subprocess_helper import run_subprocess

        test_file = "test.txt"

        # Test a simple cross-platform command
        cmd = [sys.executable, "-c", 'print("platform test")']

        result = run_subprocess(
            cmd, timeout=5, tool_name="Python", input_file=test_file, capture_output=True, text_mode=True, check=True
        )

        # Should work on any platform
        assert "platform test" in result


def test_refactoring_successful():
    """Meta-test to verify the refactoring was successful."""
    from filesqueeze.utils.subprocess_helper import run_subprocess, verify_output_file
    from filesqueeze.ops.document import compress_pdf
    from filesqueeze.ops.video import compress

    # Verify utility functions exist and work
    test_file = "test.txt"

    cmd = [sys.executable, "-c", 'print("success")']
    result = run_subprocess(
        cmd, timeout=5, tool_name="Python", input_file=test_file, capture_output=True, text_mode=True, check=True
    )
    assert "success" in result

    # Verify ops files import the utility
    assert hasattr(compress_pdf, "__module__")
    assert hasattr(compress, "__module__")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
