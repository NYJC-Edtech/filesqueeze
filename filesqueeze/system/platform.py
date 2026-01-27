"""Platform detection utilities.

Provides platform detection functions for Windows, Linux, and macOS.
"""

import sys
import platform as platform_module


def is_windows() -> bool:
    """Check if running on Windows.

    Returns:
        True if on Windows, False otherwise.
    """
    return sys.platform == 'win32'


def is_linux() -> bool:
    """Check if running on Linux.

    Returns:
        True if on Linux, False otherwise.
    """
    return sys.platform.startswith('linux')


def is_mac() -> bool:
    """Check if running on macOS.

    Returns:
        True if on macOS, False otherwise.
    """
    return sys.platform == 'darwin'


def get_platform() -> str:
    """Get the current platform name.

    Returns:
        Platform name: 'windows', 'linux', or 'macos'
    """
    if is_windows():
        return 'windows'
    elif is_linux():
        return 'linux'
    elif is_mac():
        return 'macos'
    else:
        return 'unknown'


def get_architecture() -> str:
    """Get the system architecture.

    Returns:
        Architecture string (e.g., 'AMD64', 'x86_64', 'arm64')
    """
    return platform_module.machine()


def is_64bit() -> bool:
    """Check if running on 64-bit architecture.

    Returns:
        True if 64-bit, False if 32-bit.
    """
    return sys.maxsize > 2**32
