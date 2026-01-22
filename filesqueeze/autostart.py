"""filesqueeze.autostart

Windows auto-start installation for FileSqueeze service.
"""

import sys
import os
from pathlib import Path


def is_windows() -> bool:
    """Check if running on Windows.

    Returns:
        True if on Windows, False otherwise.
    """
    return sys.platform == 'win32'


def get_startup_folder() -> Path:
    """Get the Windows startup folder path.

    Returns:
        Path to startup folder.

    Raises:
        RuntimeError: If not on Windows or startup folder cannot be found.
    """
    if not is_windows():
        raise RuntimeError("Auto-start is only supported on Windows")

    # Try to get startup folder from environment variables
    startup_folder = os.path.expandvars(r'%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup')
    startup_path = Path(startup_folder)

    if not startup_path.exists():
        raise RuntimeError(f"Startup folder not found: {startup_path}")

    return startup_path


def create_batch_file(input_dir: Path, output_dir: Path, startup_folder: Path) -> Path:
    """Create a batch file to start FileSqueeze service.

    Args:
        input_dir: Input directory to watch.
        output_dir: Output directory for compressed files.
        startup_folder: Path to startup folder.

    Returns:
        Path to created batch file.
    """
    batch_file = startup_folder / 'filesqueeze-start.bat'

    # Get the Python executable path
    python_exe = sys.executable

    # Use pythonw.exe instead of python.exe for background service (no console window)
    pythonw_exe = python_exe.replace('python.exe', 'pythonw.exe')

    # Get the filesqueeze module path
    filesqueeze_module = Path(__file__).parent.parent

    # Create batch file content (no echo - console won't be visible anyway)
    batch_content = f"""@echo off
cd /d "{filesqueeze_module}"
"{pythonw_exe}" -m filesqueeze service --input "{input_dir}" --output "{output_dir}"
"""

    # Write batch file
    with open(batch_file, 'w') as f:
        f.write(batch_content)

    return batch_file


def install_autostart(input_dir: Path, output_dir: Path) -> Path:
    """Install FileSqueeze to start automatically on boot.

    Args:
        input_dir: Input directory to watch.
        output_dir: Output directory for compressed files.

    Returns:
        Path to created batch file.

    Raises:
        RuntimeError: If not on Windows or installation fails.
    """
    if not is_windows():
        raise RuntimeError("Auto-start is only supported on Windows")

    startup_folder = get_startup_folder()

    # Create batch file
    batch_file = create_batch_file(input_dir, output_dir, startup_folder)

    print(f"Auto-start installed successfully!")
    print(f"Batch file created at: {batch_file}")
    print(f"Input directory: {input_dir}")
    print(f"Output directory: {output_dir}")
    print()
    print("FileSqueeze will start automatically when you log in to Windows.")
    print("To uninstall, simply delete the batch file from the Startup folder.")

    return batch_file


def uninstall_autostart() -> bool:
    """Uninstall FileSqueeze auto-start.

    Returns:
        True if uninstalled successfully, False otherwise.

    Raises:
        RuntimeError: If not on Windows.
    """
    if not is_windows():
        raise RuntimeError("Auto-start is only supported on Windows")

    startup_folder = get_startup_folder()
    batch_file = startup_folder / 'filesqueeze-start.bat'

    if batch_file.exists():
        batch_file.unlink()
        print(f"Auto-start uninstalled successfully!")
        print(f"Removed: {batch_file}")
        return True
    else:
        print(f"Auto-start is not installed.")
        print(f"Batch file not found: {batch_file}")
        return False


def check_autostart_installed() -> bool:
    """Check if FileSqueeze auto-start is installed.

    Returns:
        True if installed, False otherwise.

    Raises:
        RuntimeError: If not on Windows.
    """
    if not is_windows():
        return False

    startup_folder = get_startup_folder()
    batch_file = startup_folder / 'filesqueeze-start.bat'

    return batch_file.exists()
