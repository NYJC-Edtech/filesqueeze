"""filesqueeze.doctor

Troubleshooting and diagnostic tool for FileSqueeze.
Checks installation status, dependencies, and configuration.
"""

import sys
import os
from pathlib import Path
from typing import Dict, List, Tuple

from .config import Config
from .binaries import BinaryDetector


class Colors:
    """ANSI color codes for terminal output."""

    # ANSI escape codes
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    # Colors
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    # Bright colors
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_WHITE = "\033[97m"

    @classmethod
    def enable(cls):
        """Enable colors."""
        # Check if we should use colors
        # Disable on Windows unless modern terminal (Windows 10+)
        # Disable when output is redirected to a file
        if sys.platform == "win32":
            # Windows 10+ supports ANSI codes
            try:
                import ctypes
                kernel32 = ctypes.windll.kernel32
                kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
                cls._enabled = True
            except:
                cls._enabled = False
        else:
            # Unix-like systems generally support colors
            cls._enabled = sys.stdout.isatty()

    @classmethod
    def disable(cls):
        """Disable colors."""
        cls._enabled = False

    @classmethod
    def _colorize(cls, text: str, color: str) -> str:
        """Apply color to text if enabled.

        Args:
            text: Text to colorize.
            color: ANSI color code.

        Returns:
            Colorized text if enabled, otherwise plain text.
        """
        if not getattr(cls, '_enabled', False):
            return text
        return f"{color}{text}{cls.RESET}"

    @classmethod
    def ok(cls, text: str) -> str:
        """Colorize success message (green)."""
        return cls._colorize(text, cls.GREEN)

    @classmethod
    def fail(cls, text: str) -> str:
        """Colorize failure message (red)."""
        return cls._colorize(text, cls.RED)

    @classmethod
    def warn(cls, text: str) -> str:
        """Colorize warning message (yellow)."""
        return cls._colorize(text, cls.YELLOW)

    @classmethod
    def header(cls, text: str) -> str:
        """Colorize header (cyan)."""
        return cls._colorize(text, cls.CYAN)

    @classmethod
    def bold(cls, text: str) -> str:
        """Bold text."""
        return cls._colorize(text, cls.BOLD)


# Initialize colors based on environment
Colors.enable()


class Doctor:
    """Diagnostic tool for FileSqueeze installation."""

    def __init__(self):
        """Initialize the doctor."""
        self.detector = BinaryDetector()
        self.issues = []
        self.warnings = []
        self.passed = []

    def check_python_version(self) -> bool:
        """Check Python version.

        Returns:
            True if Python version is compatible, False otherwise.
        """
        version = sys.version_info
        major, minor = version.major, version.minor

        if major > 3 or (major == 3 and minor >= 11):
            self.passed.append(f"[OK] Python {major}.{minor}.{version.micro}")
            return True
        else:
            self.issues.append(f"[FAIL] Python {major}.{minor}.{version.micro} (requires 3.11+)")
            return False

    def check_module(self, module_name: str, display_name: str = None) -> bool:
        """Check if a Python module is installed.

        Args:
            module_name: Name of the module to check.
            display_name: Optional display name for the module.

        Returns:
            True if module is installed, False otherwise.
        """
        name = display_name or module_name

        try:
            __import__(module_name)
            self.passed.append(f"[OK] {name} installed")
            return True
        except ImportError:
            self.issues.append(f"[FAIL] {name} not installed")
            return False

    def check_binary(self, binary_type: str, binary_name: str) -> bool:
        """Check if a binary tool is installed.

        Args:
            binary_type: Type of binary ('ffmpeg', 'ghostscript', 'tesseract').
            binary_name: Display name for the binary.

        Returns:
            True if binary is found, False otherwise.
        """
        if binary_type == 'ffmpeg':
            path, msg = self.detector.find_ffmpeg()
        elif binary_type == 'ghostscript':
            path, msg = self.detector.find_ghostscript()
        elif binary_type == 'tesseract':
            path, msg = self.detector.find_tesseract()
        else:
            self.warnings.append(f"[?] Unknown binary type: {binary_type}")
            return False

        if path:
            self.passed.append(f"[OK] {binary_name} found: {path}")
            return True
        else:
            self.issues.append(f"[FAIL] {binary_name} not found ({msg})")
            return False

    def check_config_file(self) -> bool:
        """Check if configuration file exists.

        Returns:
            True if config file exists, False otherwise.
        """
        config_paths = [
            Path.cwd() / 'filesqueeze.toml',
            Path.home() / '.config' / 'filesqueeze' / 'config.toml',
        ]

        for config_path in config_paths:
            if config_path.exists():
                self.passed.append(f"[OK] Configuration file found: {config_path}")
                return True

        self.warnings.append("[WARN] No configuration file found (will use defaults)")
        return False

    def check_directories(self, config: Config) -> bool:
        """Check if configured directories exist.

        Args:
            config: Config object.

        Returns:
            True if all directories exist, False otherwise.
        """
        all_exist = True

        input_dir = config.get('directories.input')
        output_dir = config.get('directories.output')
        log_file = config.get('logging.file')

        if input_dir:
            input_path = Path(input_dir)
            if input_path.exists():
                self.passed.append(f"[OK] Input directory exists: {input_dir}")
            else:
                self.warnings.append(f"[WARN] Input directory does not exist: {input_dir}")
                all_exist = False

        if output_dir:
            output_path = Path(output_dir)
            if output_path.exists():
                self.passed.append(f"[OK] Output directory exists: {output_dir}")
            else:
                self.warnings.append(f"[WARN] Output directory does not exist: {output_dir}")
                all_exist = False

        if log_file:
            log_path = Path(log_file)
            if log_path.parent.exists():
                self.passed.append(f"[OK] Log directory exists: {log_path.parent}")
            else:
                self.warnings.append(f"[WARN] Log directory does not exist: {log_path.parent}")
                all_exist = False

        return all_exist

    def check_permissions(self) -> bool:
        """Check if user has necessary permissions.

        Returns:
            True if permissions are OK, False otherwise.
        """
        # Check write permissions in current directory
        try:
            test_file = Path.cwd() / '.filesqueeze_test_write'
            test_file.touch()
            test_file.unlink()
            self.passed.append("[OK] Write permissions OK")
            return True
        except Exception as e:
            self.issues.append(f"[FAIL] No write permissions: {e}")
            return False

    def run_all_checks(self) -> Tuple[int, int, int]:
        """Run all diagnostic checks.

        Returns:
            Tuple of (issues_count, warnings_count, passed_count).
        """
        print("=" * 60)
        print("FileSqueeze Doctor - Diagnostic Tool")
        print("=" * 60)

        # Check Python version
        self.check_python_version()

        # Check required Python modules
        self.check_module('watchdog', 'Watchdog')
        self.check_module('pystray', 'PyStray')

        # Check TOML library (tomllib built-in on Python 3.11+, tomli/tomli_w for older)
        if sys.version_info >= (3, 11):
            # Python 3.11+ has tomllib built-in
            try:
                import tomllib
                self.passed.append("[OK] TOML library (built-in tomllib)")
            except ImportError:
                self.issues.append("[FAIL] TOML library (built-in tomllib not available)")
        else:
            # Python < 3.11 needs tomli or tomli_w
            has_tomli = self.check_module('tomli', 'TOML library (tomli)')
            if not has_tomli:
                self.check_module('tomli_w', 'TOML library (tomli_w)')

        # Check optional Python modules
        self.check_module('pdfminer', 'PDFMiner (optional)')
        self.check_module('PIL', 'Pillow (optional)')

        # Check external binaries
        self.check_binary('ffmpeg', 'FFmpeg')
        self.check_binary('ghostscript', 'Ghostscript')
        self.check_binary('tesseract', 'Tesseract OCR (optional)')

        # Check configuration
        has_config = self.check_config_file()

        if has_config:
            try:
                config = Config()
                self.check_directories(config)
            except Exception as e:
                self.issues.append(f"[FAIL] Configuration error: {e}")

        # Check permissions
        self.check_permissions()

        return len(self.issues), len(self.warnings), len(self.passed)

    def print_summary(self):
        """Print diagnostic summary."""
        print("=" * 60)
        print(Colors.header("Summary"))
        print("=" * 60)

        if self.passed:
            print(f"\nPassed ({len(self.passed)}):")
            for item in self.passed:
                # Colorize [OK] in green
                colored_item = item.replace("[OK]", Colors.ok("[OK]"))
                print(f"  {colored_item}")

        if self.warnings:
            print(f"\nWarnings ({len(self.warnings)}):")
            for item in self.warnings:
                # Colorize [WARN] in yellow
                colored_item = item.replace("[WARN]", Colors.warn("[WARN]"))
                print(f"  {colored_item}")

        if self.issues:
            print(f"\nIssues ({len(self.issues)}):")
            for item in self.issues:
                # Colorize [FAIL] in red
                colored_item = item.replace("[FAIL]", Colors.fail("[FAIL]"))
                print(f"  {colored_item}")
            print()

            # Provide fix suggestions
            print(Colors.bold("Suggested fixes:"))
            print()

            # Python version issues
            if any("Python" in issue for issue in self.issues):
                print("• Install Python 3.11 or later from https://python.org")

            # Missing Python modules
            if any("Watchdog" in issue or "PyStray" in issue or "TOML" in issue for issue in self.issues):
                print("• Run: poetry install")
                print("  Or: pip install watchdog pystray tomli-w")

            # Missing FFmpeg
            if any("FFmpeg" in issue for issue in self.issues):
                print("• Install FFmpeg:")
                print("  Windows: choco install ffmpeg")
                print("  Linux: sudo apt-get install ffmpeg")

            # Missing Ghostscript
            if any("Ghostscript" in issue for issue in self.issues):
                print("• Install Ghostscript:")
                print("  Windows: choco install ghostscript")
                print("  Linux: sudo apt-get install ghostscript")

            # Missing Tesseract
            if any("Tesseract" in issue for issue in self.issues):
                print("• Install Tesseract OCR (optional):")
                print("  Windows: choco install tesseract")
                print("  Linux: sudo apt-get install tesseract-ocr")

            # Config issues
            if any("Configuration" in issue for issue in self.issues):
                print("• Generate configuration: poetry run python -m filesqueeze init-config")

            # Permission issues
            if any("permissions" in issue.lower() for issue in self.issues):
                print("• Check directory permissions")
                print("• Ensure you have write access to the working directory")

        print()

        # Overall status
        print("=" * 60)
        if not self.issues and not self.warnings:
            print(Colors.ok("[OK]") + " All checks passed! FileSqueeze is ready to use.")
        elif not self.issues:
            print(Colors.warn("[WARN]") + " FileSqueeze is ready, but there are some warnings.")
            print("  Review the warnings above for recommendations.")
        else:
            print(Colors.fail("[FAIL]") + " FileSqueeze has issues that need to be resolved.")
            print("  Follow the suggested fixes above.")

        print("=" * 60)


def run_doctor():
    """Run the diagnostic doctor."""
    doctor = Doctor()
    issues, warnings, passed = doctor.run_all_checks()
    doctor.print_summary()

    # Exit with error code if there are issues
    sys.exit(1 if issues > 0 else 0)


def main():
    """Main entry point for doctor command."""
    run_doctor()


if __name__ == "__main__":
    main()
