"""filesqueeze.autostart

Windows auto-start installation for FileSqueeze service.
"""

import os
import sys
from pathlib import Path


def is_windows() -> bool:
    """Check if running on Windows.

    Returns:
        True if on Windows, False otherwise.
    """
    return sys.platform == "win32"


def is_admin() -> bool:
    """Check if running with administrator privileges on Windows.

    Returns:
        True if running with admin privileges, False otherwise.
    """
    if not is_windows():
        return False

    try:
        import ctypes

        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        # If we can't check, assume not admin
        return False


def get_startup_folder(system_wide: bool = True) -> Path:
    """Get the Windows startup folder path.

    Args:
        system_wide: If True, use system-wide startup folder (runs for all users).
                    If False, use user-specific startup folder (runs for current user only).

    Returns:
        Path to startup folder.

    Raises:
        RuntimeError: If not on Windows or startup folder cannot be found.
    """
    if not is_windows():
        raise RuntimeError("Auto-start is only supported on Windows")

    # Choose startup folder based on system_wide parameter
    # System-wide: %ProgramData% (runs for all users)
    # User-specific: %APPDATA% (runs for current user only)
    if system_wide:
        startup_folder = os.path.expandvars(r"%ProgramData%\Microsoft\Windows\Start Menu\Programs\Startup")
    else:
        startup_folder = os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup")

    startup_path = Path(startup_folder)

    if not startup_path.exists():
        raise RuntimeError(f"Startup folder not found: {startup_path}")

    return startup_path


def create_batch_file(input_dir: Path, output_dir: Path, startup_folder: Path, system_wide: bool = True) -> Path:
    """Create a PowerShell wrapper and shortcut to start FileSqueeze service without console.

    Args:
        input_dir: Input directory to watch.
        output_dir: Output directory for compressed files.
        startup_folder: Path to startup folder.
        system_wide: Whether this is a system-wide installation (for logging purposes).

    Returns:
        Path to created shortcut (.lnk) file.
    """
    import subprocess
    import tempfile

    # Get the filesqueeze module path
    filesqueeze_module = Path(__file__).parent.parent

    # Create a PowerShell wrapper script in the module directory
    # This wrapper detects if FileSqueeze is installed system-wide or in development mode
    ps_wrapper = filesqueeze_module / "filesqueeze-autostart.ps1"
    ps_wrapper_content = f"""# FileSqueeze Auto-start Wrapper
# This script is launched automatically on Windows startup
# It detects whether FileSqueeze is installed system-wide or in development mode
# and launches the appropriate command

$ErrorActionPreference = "SilentlyContinue"

# Check if FileSqueeze is installed system-wide
$SystemInstalled = $null -ne (Get-Command filesqueeze -ErrorAction SilentlyContinue)

if ($SystemInstalled) {{
    # System-wide installation: use filesqueeze command directly
    & filesqueeze service run --input "{input_dir}" --output "{output_dir}"
}} else {{
    # Development installation: check if Poetry is available
    $PoetryAvailable = $null -ne (Get-Command poetry -ErrorAction SilentlyContinue)

    if ($PoetryAvailable) {{
        # Development mode with Poetry
        Set-Location "{filesqueeze_module}"
        & poetry run python -m filesqueeze service run --input "{input_dir}" --output "{output_dir}"
    }} else {{
        # Fallback: try python -m directly
        Set-Location "{filesqueeze_module}"
        & python -m filesqueeze service run --input "{input_dir}" --output "{output_dir}"
    }}
}}
"""
    with open(ps_wrapper, "w", encoding="utf-8") as f:
        f.write(ps_wrapper_content)

    # Create shortcut
    shortcut_path = startup_folder / "FileSqueeze.lnk"

    # Write PowerShell script to create shortcut to a temp file
    # This avoids quoting issues with inline scripts
    ps_script_content = f"""
    $WshShell = New-Object -ComObject WScript.Shell
    $Shortcut = $WshShell.CreateShortcut('{shortcut_path}')
    $Shortcut.TargetPath = 'powershell.exe'
    $Shortcut.Arguments = '-ExecutionPolicy Bypass -WindowStyle Hidden -File "{ps_wrapper}"'
    $Shortcut.WorkingDirectory = '{filesqueeze_module}'
    $Shortcut.WindowStyle = 7
    $Shortcut.Description = "FileSqueeze Compression Service"
    $Shortcut.Save()
    """

    with tempfile.NamedTemporaryFile(mode="w", suffix=".ps1", delete=False) as tmp:
        tmp.write(ps_script_content)
        tmp_path = tmp.name

    try:
        # Run the temp PowerShell script
        result = subprocess.run(
            ["powershell", "-ExecutionPolicy", "Bypass", "-File", tmp_path], capture_output=True, text=True
        )

        if result.returncode != 0:
            error_msg = f"Failed to create shortcut. Return code: {result.returncode}"
            if result.stderr:
                error_msg += f"\nStderr: {result.stderr}"
            if result.stdout:
                error_msg += f"\nStdout: {result.stdout}"
            raise RuntimeError(error_msg)

        # Verify shortcut was actually created
        if not shortcut_path.exists():
            raise RuntimeError(f"Shortcut creation reported success but file not found at: {shortcut_path}")

    finally:
        # Clean up temp file
        try:
            Path(tmp_path).unlink()
        except Exception:
            pass

    return shortcut_path


def install_autostart(input_dir: Path, output_dir: Path, system_wide: bool = True) -> Path:
    """Install FileSqueeze to start automatically on boot.

    Args:
        input_dir: Input directory to watch.
        output_dir: Output directory for compressed files.
        system_wide: If True, install for all users (requires admin privileges).
                    If False, install for current user only.

    Returns:
        Path to created batch file.

    Raises:
        RuntimeError: If not on Windows or installation fails.
    """
    if not is_windows():
        raise RuntimeError("Auto-start is only supported on Windows")

    # Check admin privileges for system-wide installation
    if system_wide and not is_admin():
        print("! ADMINISTRATOR PRIVILEGES REQUIRED")
        print("  System-wide installation requires administrator privileges.")
        print("  Falling back to user-specific installation (current user only).")
        print()
        print("To install for all users:")
        print("  1. Right-click on PowerShell or Command Prompt")
        print("  2. Select 'Run as Administrator'")
        print("  3. Run: filesqueeze service install --system-wide")
        print()
        system_wide = False

    startup_folder = get_startup_folder(system_wide=system_wide)

    try:
        # Create shortcut
        shortcut_path = create_batch_file(input_dir, output_dir, startup_folder, system_wide)

        scope = "all users" if system_wide else "current user"
        print(f"[OK] Auto-start installed successfully for {scope}!")
        print(f"  Shortcut location: {shortcut_path}")
        print(f"  Input directory: {input_dir}")
        print(f"  Output directory: {output_dir}")
        print()
        print("FileSqueeze will start automatically when you log in to Windows (no console window).")
        print("To uninstall, simply delete the shortcut from the Startup folder.")

        return shortcut_path

    except RuntimeError as e:
        if "Shortcut creation reported success but file not found" in str(e):
            # This is likely a permissions issue
            if system_wide:
                print("[ERROR] SYSTEM-WIDE INSTALLATION FAILED")
                print("  Reason: Insufficient permissions to write to system-wide startup folder")
                print("  Required: Administrator privileges")
                print()
                print("=> Falling back to user-specific installation (current user only)")
                print("=> To install system-wide: Run PowerShell/CMD as Administrator")
                print()
                return install_autostart(input_dir, output_dir, system_wide=False)
            else:
                print("[ERROR] USER-SPECIFIC INSTALLATION FAILED")
                print(f"  Reason: {e}")
                print()
                print("Troubleshooting:")
                print("  1. Make sure the startup folder exists")
                print("  2. Check file permissions")
                print("  3. Try running as Administrator")
                raise
        else:
            print(f"[ERROR] INSTALLATION FAILED: {e}")
            raise


def uninstall_autostart(system_wide: bool = True) -> bool:
    """Uninstall FileSqueeze auto-start.

    Removes all FileSqueeze-related files from the startup folder including:
    - FileSqueeze.lnk (new shortcut)
    - filesqueeze-start.bat (old batch file)
    - filesqueeze-start.vbs (old VBScript wrapper, if exists)

    Also removes the PowerShell wrapper script (filesqueeze-autostart.ps1).

    Args:
        system_wide: If True, uninstall from system-wide startup folder.
                    If False, uninstall from user-specific startup folder.

    Returns:
        True if uninstalled successfully, False otherwise.

    Raises:
        RuntimeError: If not on Windows.
    """
    if not is_windows():
        raise RuntimeError("Auto-start is only supported on Windows")

    startup_folder = get_startup_folder(system_wide=system_wide)
    removed_files = []

    # Remove new shortcut
    shortcut_path = startup_folder / "FileSqueeze.lnk"
    if shortcut_path.exists():
        shortcut_path.unlink()
        removed_files.append(str(shortcut_path))

    # Remove old batch file (if exists from previous installation)
    batch_file = startup_folder / "filesqueeze-start.bat"
    if batch_file.exists():
        batch_file.unlink()
        removed_files.append(str(batch_file))

    # Remove old VBScript file (if exists from previous installation)
    vbs_file = startup_folder / "filesqueeze-start.vbs"
    if vbs_file.exists():
        vbs_file.unlink()
        removed_files.append(str(vbs_file))

    # Remove PowerShell wrapper script
    filesqueeze_module = Path(__file__).parent.parent
    ps_wrapper = filesqueeze_module / "filesqueeze-autostart.ps1"
    if ps_wrapper.exists():
        ps_wrapper.unlink()
        removed_files.append(str(ps_wrapper))

    if removed_files:
        print("Auto-start uninstalled successfully!")
        for f in removed_files:
            print(f"  Removed: {f}")
        return True
    else:
        print("Auto-start is not installed.")
        print(f"No FileSqueeze files found in: {startup_folder}")
        return False


def check_autostart_installed(system_wide: bool = True) -> bool:
    """Check if FileSqueeze auto-start is installed.

    Args:
        system_wide: If True, check system-wide startup folder.
                    If False, check user-specific startup folder.

    Returns:
        True if installed, False otherwise.

    Raises:
        RuntimeError: If not on Windows.
    """
    if not is_windows():
        return False

    startup_folder = get_startup_folder(system_wide=system_wide)
    shortcut_path = startup_folder / "FileSqueeze.lnk"

    return shortcut_path.exists()
