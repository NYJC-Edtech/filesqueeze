"""Binary finder registration with lazy access pattern.

This module provides binary path detection for FFmpeg, Ghostscript,
and Tesseract with a registration pattern for dependency injection.
"""

import os
import platform
import subprocess
import threading
from pathlib import Path
from typing import Optional, Tuple

# Global binary finder instance (None until registered)
_binary_finder: Optional['BinaryFinder'] = None
# Lock for thread-safe registration
_binary_finder_lock = threading.Lock()


def register_binary_finder(finder: 'BinaryFinder') -> None:
    """Register the binary finder instance.

    Called once at startup to inject binary finder dependency.

    Args:
        finder: Configured BinaryFinder instance

    Raises:
        RuntimeError: If binary finder is already registered
    """
    global _binary_finder

    with _binary_finder_lock:
        if _binary_finder is not None:
            raise RuntimeError(
                "Binary finder already registered. "
                "Check import order - binary finder should only be registered once at startup."
            )
        _binary_finder = finder


def get_binary_finder() -> 'BinaryFinder':
    """Get the registered binary finder.

    Returns:
        BinaryFinder instance (or default if not registered)

    Note:
        If called before registration, returns a default BinaryFinder instance.
    """
    global _binary_finder

    # Return registered finder if available
    if _binary_finder is not None:
        return _binary_finder

    # Return default finder if not yet registered
    return BinaryFinder()


class BinaryFinder:
    """Find FFmpeg, Ghostscript, and Tesseract installation paths."""

    # Common installation directories
    WINDOWS_FFMPEG_PATHS = [
        Path("C:/Program Files/ffmpeg/bin"),
        Path("C:/Program Files (x86)/ffmpeg/bin"),
        Path("C:/ffmpeg/bin"),
        Path("C:/tools/ffmpeg/bin"),
    ]

    WINDOWS_GHOSTSCRIPT_PATHS = [
        Path("C:/Program Files/gs"),
        Path("C:/Program Files (x86)/gs"),
    ]

    WINDOWS_TESSERACT_PATHS = [
        Path("C:/Program Files/Tesseract-OCR"),
        Path("C:/Program Files (x86)/Tesseract-OCR"),
        Path("C:/Tesseract-OCR"),
    ]

    LINUX_FFMPEG_PATHS = [
        Path("/usr/bin"),
        Path("/usr/local/bin"),
        Path("/opt/ffmpeg/bin"),
    ]

    LINUX_GHOSTSCRIPT_PATHS = [
        Path("/usr/bin"),
        Path("/usr/local/bin"),
        Path("/opt/gs/bin"),
    ]

    LINUX_TESSERACT_PATHS = [
        Path("/usr/bin"),
        Path("/usr/local/bin"),
        Path("/opt/tesseract/bin"),
    ]

    def __init__(self, config=None):
        """Initialize binary finder.

        Args:
            config: Optional Config object with binary paths
        """
        self.system = platform.system()
        self.machine = platform.machine()
        self.config = config
        self._cached_paths = {}

    @property
    def platform(self) -> str:
        """Get the platform name."""
        return self.system

    @property
    def architecture(self) -> str:
        """Get the architecture name."""
        return self.machine

    def get_ffmpeg_path(self) -> str:
        """Get FFmpeg executable path.

        Returns:
            Path to FFmpeg executable

        Raises:
            RuntimeError: If FFmpeg not found
        """
        if 'ffmpeg' not in self._cached_paths:
            # Check config first
            if self.config:
                config_path = self.config.get('ffmpeg.path')
                if config_path:
                    self._cached_paths['ffmpeg'] = config_path
                    return config_path

            # Auto-detect
            path, msg = self.find_ffmpeg()
            if path is None:
                raise RuntimeError(f"FFmpeg not found: {msg}")
            self._cached_paths['ffmpeg'] = path

        return self._cached_paths['ffmpeg']

    def get_ffprobe_path(self) -> str:
        """Get ffprobe executable path.

        Returns:
            Path to ffprobe executable

        Raises:
            RuntimeError: If ffprobe not found
        """
        if 'ffprobe' not in self._cached_paths:
            # Try to find ffprobe in the same directory as ffmpeg
            try:
                ffmpeg_path = self.get_ffmpeg_path()
                ffprobe = str(Path(ffmpeg_path).parent / 'ffprobe.exe')
                if Path(ffprobe).exists():
                    self._cached_paths['ffprobe'] = ffprobe
                    return ffprobe
            except RuntimeError:
                pass  # Fall through to PATH detection

            # Try to find ffprobe in PATH
            if self._check_command("ffprobe"):
                self._cached_paths['ffprobe'] = 'ffprobe'
                return 'ffprobe'

            raise RuntimeError("ffprobe not found. Please install FFmpeg or configure ffmpeg_path in config.")

        return self._cached_paths['ffprobe']

    def get_ghostscript_path(self) -> str:
        """Get Ghostscript executable path.

        Returns:
            Path to Ghostscript executable

        Raises:
            RuntimeError: If Ghostscript not found
        """
        if 'ghostscript' not in self._cached_paths:
            # Check config first
            if self.config:
                config_path = self.config.get('document.ghostscript_path')
                if config_path:
                    self._cached_paths['ghostscript'] = config_path
                    return config_path

            # Auto-detect
            path, msg = self.find_ghostscript()
            if path is None:
                raise RuntimeError(f"Ghostscript not found: {msg}")
            self._cached_paths['ghostscript'] = path

        return self._cached_paths['ghostscript']

    def get_tesseract_path(self) -> str:
        """Get Tesseract executable path.

        Returns:
            Path to Tesseract executable

        Raises:
            RuntimeError: If Tesseract not found
        """
        if 'tesseract' not in self._cached_paths:
            # Check config first
            if self.config:
                config_path = self.config.get('ocr.tesseract_path')
                if config_path:
                    self._cached_paths['tesseract'] = config_path
                    return config_path

            # Auto-detect
            path, msg = self.find_tesseract()
            if path is None:
                raise RuntimeError(f"Tesseract not found: {msg}")
            self._cached_paths['tesseract'] = path

        return self._cached_paths['tesseract']

    def verify_all(self) -> dict:
        """Verify all binaries are available.

        Returns:
            Dictionary with verification results

        Raises:
            RuntimeError: If any binary is not found
        """
        results = {}

        try:
            results['ffmpeg'] = self.get_ffmpeg_path()
        except RuntimeError as e:
            results['ffmpeg'] = f"Error: {e}"

        try:
            results['ghostscript'] = self.get_ghostscript_path()
        except RuntimeError as e:
            results['ghostscript'] = f"Error: {e}"

        try:
            results['tesseract'] = self.get_tesseract_path()
        except RuntimeError as e:
            results['tesseract'] = f"Error: {e}"

        return results

    def find_ffmpeg(self) -> Tuple[Optional[str], str]:
        """Find FFmpeg executable.

        Returns:
            Tuple of (path to ffmpeg, status message).
        """
        # First, check if ffmpeg is in PATH
        if self._check_command("ffmpeg"):
            return "ffmpeg", "Found in PATH"

        # If not in PATH, search common installation directories
        if self.system == "Windows":
            return self._find_ffmpeg_windows()
        else:
            return self._find_ffmpeg_linux()

    def find_ghostscript(self) -> Tuple[Optional[str], str]:
        """Find Ghostscript executable.

        Returns:
            Tuple of (path to ghostscript, status message).
        """
        # First, check if gs is in PATH
        if self._check_command("gs"):
            return "gs", "Found in PATH"

        # If not in PATH, search common installation directories
        if self.system == "Windows":
            return self._find_ghostscript_windows()
        else:
            return self._find_ghostscript_linux()

    def find_tesseract(self) -> Tuple[Optional[str], str]:
        """Find Tesseract OCR executable.

        Returns:
            Tuple of (path to tesseract, status message).
        """
        # First, check if tesseract is in PATH
        if self._check_command("tesseract"):
            return "tesseract", "Found in PATH"

        # If not in PATH, search common installation directories
        if self.system == "Windows":
            return self._find_tesseract_windows()
        else:
            return self._find_tesseract_linux()

    def _check_command(self, command: str) -> bool:
        """Check if a command is available in PATH.

        Args:
            command: Command to check.

        Returns:
            True if command is found, False otherwise.
        """
        try:
            subprocess.run(
                [command, "--version"],
                capture_output=True,
                timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW if self.system == "Windows" else 0
            )
            return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def _find_ffmpeg_windows(self) -> Tuple[Optional[str], str]:
        """Find FFmpeg on Windows.

        Returns:
            Tuple of (path to ffmpeg, status message).
        """
        for base_path in self.WINDOWS_FFMPEG_PATHS:
            if base_path.exists():
                # Try ffmpeg.exe
                ffmpeg_exe = base_path / "ffmpeg.exe"
                if ffmpeg_exe.exists():
                    return str(ffmpeg_exe), f"Found at {ffmpeg_exe}"

                # Try searching subdirectories (for versioned installations)
                for exe in base_path.rglob("ffmpeg.exe"):
                    if exe.exists():
                        return str(exe), f"Found at {exe}"

        return None, "Not found in common locations"

    def _find_ffmpeg_linux(self) -> Tuple[Optional[str], str]:
        """Find FFmpeg on Linux.

        Returns:
            Tuple of (path to ffmpeg, status message).
        """
        for base_path in self.LINUX_FFMPEG_PATHS:
            if base_path.exists():
                ffmpeg_bin = base_path / "ffmpeg"
                if ffmpeg_bin.exists() and os.access(ffmpeg_bin, os.X_OK):
                    return str(ffmpeg_bin), f"Found at {ffmpeg_bin}"

        return None, "Not found in common locations"

    def _find_ghostscript_windows(self) -> Tuple[Optional[str], str]:
        """Find Ghostscript on Windows.

        Returns:
            Tuple of (path to ghostscript, status message).
        """
        for base_path in self.WINDOWS_GHOSTSCRIPT_PATHS:
            if base_path.exists():
                # Try subdirectories (versioned installations like gs10.06.0)
                for gs_dir in base_path.iterdir():
                    if gs_dir.is_dir() and gs_dir.name.startswith("gs"):
                        # Try bin subdirectory
                        bin_dir = gs_dir / "bin"
                        if bin_dir.exists():
                            # Try gswin64c.exe first (64-bit)
                            for exe_name in ["gswin64c.exe", "gswin32c.exe", "gs.exe"]:
                                gs_exe = bin_dir / exe_name
                                if gs_exe.exists():
                                    return str(gs_exe), f"Found at {gs_exe}"

                        # Try root directory
                        for exe_name in ["gswin64c.exe", "gswin32c.exe", "gs.exe"]:
                            gs_exe = gs_dir / exe_name
                            if gs_exe.exists():
                                return str(gs_exe), f"Found at {gs_exe}"

        return None, "Not found in common locations"

    def _find_ghostscript_linux(self) -> Tuple[Optional[str], str]:
        """Find Ghostscript on Linux.

        Returns:
            Tuple of (path to ghostscript, status message).
        """
        for base_path in self.LINUX_GHOSTSCRIPT_PATHS:
            if base_path.exists():
                gs_bin = base_path / "gs"
                if gs_bin.exists() and os.access(gs_bin, os.X_OK):
                    return str(gs_bin), f"Found at {gs_bin}"

        return None, "Not found in common locations"

    def _find_tesseract_windows(self) -> Tuple[Optional[str], str]:
        """Find Tesseract on Windows.

        Returns:
            Tuple of (path to tesseract, status message).
        """
        for base_path in self.WINDOWS_TESSERACT_PATHS:
            if base_path.exists():
                # Try tesseract.exe in base directory
                tesseract_exe = base_path / "tesseract.exe"
                if tesseract_exe.exists():
                    return str(tesseract_exe), f"Found at {tesseract_exe}"

        return None, "Not found in common locations"

    def _find_tesseract_linux(self) -> Tuple[Optional[str], str]:
        """Find Tesseract on Linux.

        Returns:
            Tuple of (path to tesseract, status message).
        """
        for base_path in self.LINUX_TESSERACT_PATHS:
            if base_path.exists():
                tesseract_bin = base_path / "tesseract"
                if tesseract_bin.exists() and os.access(tesseract_bin, os.X_OK):
                    return str(tesseract_bin), f"Found at {tesseract_bin}"

        return None, "Not found in common locations"


def print_detection_results() -> None:
    """Print binary detection results to console.

    This is a convenience function for the CLI detect command.
    """
    import platform as platform_module

    print(f"Platform: {platform_module.system()} {platform_module.machine()}")
    print()

    finder = BinaryFinder()
    results = finder.verify_all()

    for binary_name, result in results.items():
        if isinstance(result, str) and result.startswith("Error:"):
            print(f"[X] {binary_name.capitalize()}: {result}")
        else:
            print(f"[OK] {binary_name.capitalize()}: {result}")
