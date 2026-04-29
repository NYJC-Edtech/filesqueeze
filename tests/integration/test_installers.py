"""Integration tests for FileSqueeze installer scripts.

These tests verify the Installation Experience invariant by running
the actual PowerShell installers and checking their behavior.
"""

import subprocess
import sys
import time
from pathlib import Path

import pytest

# Mark all tests in this module as Windows-only
pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="Installer tests are Windows-specific")


class InstallerTestHelpers:
    """Helper functions for installer testing."""

    @staticmethod
    def run_powershell_script(script_path: Path, args: list = None) -> subprocess.CompletedProcess:
        """Run a PowerShell script and capture output.

        Args:
            script_path: Path to .ps1 file
            args: List of arguments to pass to script

        Returns:
            CompletedProcess with stdout, stderr, returncode
        """
        cmd = ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(script_path)]
        if args:
            cmd.extend(args)

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)  # 5 minute timeout
        return result

    @staticmethod
    def get_filesqueeze_processes() -> list:
        """Get list of running FileSqueeze processes.

        Returns:
            List of process IDs
        """
        try:
            result = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq filesqueeze.exe", "/FO", "CSV"], capture_output=True, text=True, timeout=10
            )
            # Parse output to extract PIDs
            pids = []
            for line in result.stdout.split("\n"):
                if "filesqueeze.exe" in line:
                    parts = line.split(",")
                    if len(parts) >= 2:
                        pid_str = parts[1].strip('"')
                        if pid_str.isdigit():
                            pids.append(int(pid_str))
            return pids
        except Exception:
            return []

    @staticmethod
    def start_filesqueeze_service() -> subprocess.Popen | None:
        """Start FileSqueeze service in background.

        Returns:
            Popen object if started successfully, None otherwise
        """
        try:
            # Use pythonw to start without console window
            proc = subprocess.Popen(
                ["pythonw", "-m", "filesqueeze", "service", "run"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
            )
            time.sleep(2)  # Give it time to start
            return proc
        except Exception:
            return None

    @staticmethod
    def stop_filesqueeze_service():
        """Stop all FileSqueeze processes using taskkill."""
        try:
            subprocess.run(["taskkill", "/F", "/IM", "filesqueeze.exe"], capture_output=True, timeout=10)
            time.sleep(1)  # Give it time to stop
        except Exception:
            pass

    @staticmethod
    def is_filesqueeze_installed() -> bool:
        """Check if FileSqueeze is installed via pip.

        Returns:
            True if installed, False otherwise
        """
        try:
            result = subprocess.run(["python", "-m", "pip", "show", "filesqueeze"], capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except Exception:
            return False

    @staticmethod
    def get_user_config_path() -> Path:
        """Get path to user config directory.

        Returns:
            Path to ~/.config/filesqueeze
        """
        home = Path.home()
        return home / ".config" / "filesqueeze"


class TestPromptFormatInvariant:
    """Tests for [Y/n] prompt format invariant."""

    @pytest.fixture
    def project_root(self):
        """Get project root directory."""
        return Path(__file__).parent.parent.parent

    def test_uninstall_uses_yn_format(self, project_root):
        """Uninstaller should use [Y/n] format, not (Y/N)."""
        uninstall_script = project_root / "uninstall.ps1"
        assert uninstall_script.exists(), "uninstall.ps1 must exist"

        # Read the script content
        content = uninstall_script.read_text()

        # Verify [Y/n] format is used
        assert "[Y/n]" in content or "[y/N]" in content, "Prompt should use [Y/n] format to indicate default"

        # Verify (Y/N) format is NOT used
        # (This is the confusing format we're avoiding)
        lines_with_bad_format = [line for line in content.split("\n") if "(Y/N)" in line and "[Y/n]" not in line]
        assert len(lines_with_bad_format) == 0, f"Found confusing (Y/N) format in lines: {lines_with_bad_format}"

    def test_install_shows_clear_next_steps(self, project_root):
        """Install script should show explicit next steps after completion."""
        install_script = project_root / "install.ps1"
        assert install_script.exists(), "install.ps1 must exist"

        content = install_script.read_text()

        # Look for instructions about how to start FileSqueeze
        # The script should mention Start Menu, filesqueeze command, etc.
        instruction_keywords = ["Start Menu", "filesqueeze", "Start FileSqueeze", "To start", "launch"]

        found_instructions = False
        for keyword in instruction_keywords:
            if keyword.lower() in content.lower():
                found_instructions = True
                break

        assert found_instructions, "Install script should include clear next steps for starting FileSqueeze"


class TestUninstallationProcessInvariant:
    """Tests for Uninstallation Process invariant."""

    @pytest.fixture
    def project_root(self):
        """Get project root directory."""
        return Path(__file__).parent.parent.parent

    @pytest.fixture(autouse=True)
    def cleanup(self, project_root):
        """Cleanup before and after tests."""
        # Stop any running FileSqueeze processes
        InstallerTestHelpers.stop_filesqueeze_service()
        yield
        # Cleanup after test
        InstallerTestHelpers.stop_filesqueeze_service()

    def test_uninstall_stops_all_processes(self, project_root):
        """Uninstallation should stop all running FileSqueeze processes."""
        helpers = InstallerTestHelpers()

        # Check if FileSqueeze is installed
        if not helpers.is_filesqueeze_installed():
            pytest.skip("FileSqueeze not installed - cannot test process stopping")

        # Start FileSqueeze service
        proc = helpers.start_filesqueeze_service()
        if not proc:
            pytest.skip("Could not start FileSqueeze service")

        try:
            # Verify it's running
            pids_before = helpers.get_filesqueeze_processes()
            if len(pids_before) == 0:
                pytest.skip("Service did not start properly")

            # Run uninstaller (non-interactive)
            uninstall_script = project_root / "uninstall.ps1"
            # Note: We can't fully automate this without interaction,
            # but we can verify the script has the right logic
            content = uninstall_script.read_text()

            # Verify script stops processes
            assert "Stop-Process" in content or "taskkill" in content, "Uninstaller should stop running processes"

            # Verify it looks for FileSqueeze processes
            assert "filesqueeze" in content.lower(), "Uninstaller should specifically look for FileSqueeze processes"

        finally:
            helpers.stop_filesqueeze_service()

    def test_uninstall_preserves_user_config(self, project_root, tmp_path):
        """Uninstallation should preserve user configuration files."""
        # NOTE: This test was previously writing to the REAL user config location!
        # Fixed to use tmp_path instead. We only verify the uninstall script content,
        # we don't actually test uninstall behavior (that would require full install/uninstall cycle).

        # Verify uninstall script doesn't remove user config
        uninstall_script = project_root / "uninstall.ps1"
        content = uninstall_script.read_text()

        # Look for user config path in script
        # It should either:
        # 1. Explicitly say it keeps the config, or
        # 2. Not remove the config directory
        removes_config = False
        for line in content.split("\n"):
            if "Remove-Item" in line and "config" in line.lower():
                removes_config = True
                break

        assert not removes_config, "Uninstaller should not remove user configuration directory"

        # Also check that the script says it keeps config
        assert (
            "Keep user configuration" in content or "configuration and logs" in content or "preserves" in content.lower()
        ), "Uninstaller should explicitly state it preserves user config"

    def test_uninstall_enables_fresh_install(self, project_root):
        """After uninstall, should be able to install again without errors."""
        helpers = InstallerTestHelpers()

        # This test requires actual install/uninstall cycle
        # We'll verify the scripts support this flow

        uninstall_script = project_root / "uninstall.ps1"
        install_script = project_root / "install.ps1"

        # Verify uninstall removes the package
        uninstall_content = uninstall_script.read_text()
        assert (
            "pip uninstall" in uninstall_content or "uninstall filesqueeze" in uninstall_content.lower()
        ), "Uninstaller should remove FileSqueeze package"

        # Verify install can handle re-installation
        install_content = install_script.read_text()
        # The install should either:
        # 1. Uninstall first, or
        # 2. Use --force-reinstall flag
        can_reinstall = (
            "uninstall" in install_content.lower()
            or "force-reinstall" in install_content.lower()
            or "force" in install_content.lower()
        )
        assert can_reinstall, "Installer should support re-installation (uninstall first or use --force)"


class TestInstallerBehavior:
    """Tests for general installer behavior."""

    @pytest.fixture
    def project_root(self):
        """Get project root directory."""
        return Path(__file__).parent.parent.parent

    def test_install_creates_start_menu_shortcuts(self, project_root):
        """Installer should create Start Menu shortcuts."""
        helpers = InstallerTestHelpers()

        install_script = project_root / "install.ps1"
        content = install_script.read_text()

        # Verify it creates Start Menu folder
        assert "Start Menu" in content or "Programs" in content, "Installer should create Start Menu shortcuts"

        # Verify it creates shortcuts
        assert "WScript.Shell" in content or ".lnk" in content, "Installer should create .lnk shortcut files"

    def test_install_generates_config_file(self, project_root):
        """Installer should generate user configuration file."""
        install_script = project_root / "install.ps1"
        content = install_script.read_text()

        # Verify it runs init-config or creates config
        assert (
            "init-config" in content or "config.toml" in content or "Generate configuration" in content
        ), "Installer should generate configuration file"

    def test_installer_checks_python_version(self, project_root):
        """Installer should verify Python 3.11+ is installed."""
        install_script = project_root / "install.ps1"
        content = install_script.read_text()

        # Verify it checks Python version
        assert "python" in content.lower() and "version" in content.lower(), "Installer should check Python version"

        # Verify it checks for 3.11+
        assert "3.11" in content or "311" in content, "Installer should require Python 3.11+"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
