"""filesqueeze.binaries

Auto-detection of FFmpeg and Ghostscript binaries on Windows and Linux.
"""

import os
import platform
from pathlib import Path
from typing import Optional, Tuple
import subprocess


class BinaryDetector:
    """Detect FFmpeg and Ghostscript installation paths."""

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

    def __init__(self):
        """Initialize binary detector."""
        self.system = platform.system()
        self.machine = platform.machine()

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

    def detect_all(self) -> dict:
        """Detect all required binaries.

        Returns:
            Dictionary with detection results.
        """
        result = {
            "system": f"{self.system} {self.machine}",
            "ffmpeg": None,
            "ghostscript": None,
        }

        ffmpeg_path, ffmpeg_msg = self.find_ffmpeg()
        result["ffmpeg"] = {
            "path": ffmpeg_path,
            "message": ffmpeg_msg,
            "found": ffmpeg_path is not None
        }

        gs_path, gs_msg = self.find_ghostscript()
        result["ghostscript"] = {
            "path": gs_path,
            "message": gs_msg,
            "found": gs_path is not None
        }

        return result

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


def detect_binaries() -> dict:
    """Convenience function to detect all binaries.

    Returns:
        Dictionary with detection results.
    """
    detector = BinaryDetector()
    return detector.detect_all()


def print_detection_results():
    """Print binary detection results to console."""
    results = detect_binaries()

    print("=" * 60)
    print("FileSqueeze Binary Detection")
    print("=" * 60)
    print(f"System: {results['system']}")
    print()

    # FFmpeg
    ffmpeg = results['ffmpeg']
    if ffmpeg['found']:
        print(f"[OK] FFmpeg: {ffmpeg['path']}")
        print(f"     {ffmpeg['message']}")
    else:
        print(f"[X] FFmpeg: Not found")
        print(f"    {ffmpeg['message']}")
    print()

    # Ghostscript
    gs = results['ghostscript']
    if gs['found']:
        print(f"[OK] Ghostscript: {gs['path']}")
        print(f"     {gs['message']}")
    else:
        print(f"[X] Ghostscript: Not found")
        print(f"    {gs['message']}")
    print()

    # Summary
    if ffmpeg['found'] and gs['found']:
        print("[OK] All binaries found! FileSqueeze is ready to use.")
        print()
        print("To use these paths, add to your filesqueeze.toml:")
        print(f"[ffmpeg]")
        print(f"path = \"{ffmpeg['path']}\"")
        print()
        print(f"[document]")
        print(f"ghostscript_path = \"{gs['path']}\"")
    else:
        print("[X] Some binaries are missing. Please install:")
        if not ffmpeg['found']:
            print("  - FFmpeg: https://ffmpeg.org/download.html")
        if not gs['found']:
            print("  - Ghostscript: https://www.ghostscript.com/download.html")

    print("=" * 60)


def main():
    """Main entry point for binary detection CLI."""
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--json":
        # Output as JSON for programmatic use
        import json
        results = detect_binaries()
        print(json.dumps(results, indent=2))
    else:
        # Output as human-readable text
        print_detection_results()


if __name__ == "__main__":
    main()
