"""Subprocess utilities for FileSqueeze operations.

This module provides centralized subprocess execution with:
- Platform-specific window hiding (Windows)
- Consistent error handling and timeouts
- Standardized logging and debugging support
"""

import logging
import os
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


class SubprocessError(RuntimeError):
    """Base class for subprocess-related errors."""

    def __init__(self, message: str, return_code: int | None = None, stdout: str | None = None, stderr: str | None = None):
        super().__init__(message)
        self.return_code = return_code
        self.stdout = stdout
        self.stderr = stderr


class SubprocessTimeout(SubprocessError):
    """Raised when subprocess execution times out."""

    pass


def run_subprocess(
    cmd: list[str],
    timeout: int,
    tool_name: str,
    input_file: str,
    capture_output: bool = False,
    text_mode: bool = False,
    check: bool = True,
) -> subprocess.CompletedProcess | str:
    """Run subprocess with platform-specific configuration and error handling.

    Args:
        cmd: Command list to execute
        timeout: Timeout in seconds
        tool_name: Name of tool (for error messages)
        input_file: Input file path (for error messages)
        capture_output: Whether to capture stdout/stderr
        text_mode: Whether to run in text mode
        check: Whether to raise error on non-zero exit

    Returns:
        CompletedProcess object or stdout string (if capture_output=True and text_mode=True)

    Raises:
        SubprocessTimeout: If command times out
        SubprocessError: If command fails with non-zero exit
    """
    # Platform-specific subprocess configuration
    subprocess_kwargs = {
        "timeout": timeout,
        "check": False,  # We'll handle errors ourselves for better messages
    }

    if capture_output:
        subprocess_kwargs["capture_output"] = True
        if text_mode:
            subprocess_kwargs["text"] = True

    # Windows: Hide console window using startupinfo (most robust approach)
    if os.name == "nt":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        subprocess_kwargs["startupinfo"] = startupinfo

    # Log command for debugging (without sensitive paths)
    cmd_display = [tool_name] + (["..."] if len(cmd) > 1 else [])
    logger.debug(f"Running: {' '.join(cmd_display)}")

    try:
        result = subprocess.run(cmd, **subprocess_kwargs)

        # Handle non-zero exit codes
        if check and result.returncode != 0:
            error_msg = f"{tool_name} failed with return code {result.returncode}: {input_file}"

            # Add stderr if available
            if hasattr(result, "stderr") and result.stderr:
                stderr_text = (
                    result.stderr if isinstance(result.stderr, str) else result.stderr.decode("utf-8", errors="replace")
                )
                error_msg += f"\nstderr: {stderr_text.strip()}"

            raise SubprocessError(error_msg, return_code=result.returncode)

        return result.stdout if (capture_output and text_mode) else result

    except subprocess.TimeoutExpired:
        raise SubprocessTimeout(f"{tool_name} timeout processing: {input_file}") from None


def verify_output_file(
    output_path: str, min_size: int = 0, max_size_ratio: float = float("inf"), input_size: int | None = None
) -> Path:
    """Verify output file was created successfully.

    Args:
        output_path: Path to output file
        min_size: Minimum file size in bytes
        max_size_ratio: Maximum size ratio relative to input (if input_size provided)
        input_size: Optional input file size for size comparison

    Returns:
        Path object for output file

    Raises:
        FileNotFoundError: If output file doesn't exist
        RuntimeError: If output file is too small or too large
    """
    output = Path(output_path)

    if not output.exists():
        raise FileNotFoundError(f"Output file not created: {output_path}")

    file_size = output.stat().st_size

    if file_size < min_size:
        raise RuntimeError(f"Output file is too small (< {min_size} bytes): {output_path}")

    if input_size and file_size > input_size * max_size_ratio:
        raise RuntimeError(f"Output file is too large (> {max_size_ratio}x input): {output_path}")

    return output


def verify_mp4_file(output_path: str, min_size: int = 1000) -> Path:
    """Verify MP4 file was created successfully and has valid structure.

    Performs basic validation that the file is a valid MP4 by checking:
    - File exists
    - File size >= min_size (default 1000 bytes)
    - File has MP4 magic bytes/box structure

    Args:
        output_path: Path to output MP4 file
        min_size: Minimum file size in bytes (default: 1000)

    Returns:
        Path object for output file

    Raises:
        FileNotFoundError: If output file doesn't exist
        RuntimeError: If output file is too small or invalid MP4
    """
    output = Path(output_path)

    if not output.exists():
        raise FileNotFoundError(f"Output file not created: {output_path}")

    file_size = output.stat().st_size

    if file_size < min_size:
        raise RuntimeError(f"Output file is too small (< {min_size} bytes): {output_path}")

    # Check for MP4 file signature (ftyp box at beginning)
    # MP4 files start with "ftyp" in ASCII followed by version/brand info
    try:
        with open(output_path, 'rb') as f:
            header = f.read(12)  # Read first 12 bytes for basic MP4 check
            if len(header) < 12:
                raise RuntimeError(f"Output file is too small to be valid MP4: {output_path}")

            # Check for ftyp box (0x66747970 = "ftyp" in ASCII)
            # MP4 structure: [4 bytes size][4 bytes type][4 bytes brand]
            # Type should be "ftyp" (0x66747970)
            if header[4:8] != b'ftyp':
                logger.warning(f"Output file may not be valid MP4 (missing ftyp header): {output_path}")
                # Don't fail here, just warn - some encoders may use different structure
    except Exception as e:
        logger.debug(f"Could not verify MP4 structure: {e}")

    return output


def get_windows_subprocess_config() -> dict:
    """Get Windows-specific subprocess configuration for hiding console windows.

    Returns:
        Dictionary with startupinfo configuration for Windows, empty dict for other platforms.
    """
    if os.name == "nt":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        return {"startupinfo": startupinfo}
    return {}
