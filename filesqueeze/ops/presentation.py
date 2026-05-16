"""filesqueeze.ops.presentation

Presentation compression functions for PowerPoint files.

This module provides PowerPoint to MP4 conversion operations using PowerShell.
It uses the system package for logging and subprocess utilities.
"""

from pathlib import Path

# Import from system package
from filesqueeze.system import get_binary_finder

# Import subprocess utilities
from filesqueeze.utils.subprocess_helper import SubprocessError, SubprocessTimeout, run_subprocess, verify_output_file

# Constants
SCRIPTPATH = str(Path(__file__).parent.parent.joinpath("bin", "pptx2mp4.ps1"))


def get_powershell_path(config_path: str = "") -> str:
    """Get the PowerShell executable path.

    Args:
        config_path: Path from config, or empty string to use PATH.

    Returns:
        Path to PowerShell executable.

    Raises:
        RuntimeError: If PowerShell is not found.

    Note:
        If config_path is provided and it exists, it will be used.
        Otherwise, uses the registered BinaryFinder to auto-detect.
    """
    # If explicit path provided and it exists, use it
    if config_path and Path(config_path).exists():
        return config_path

    # Otherwise use registered finder
    finder = get_binary_finder()
    return finder.get_powershell_path()


def to_mp4(infile: str, outfile: str = "", *, config: object = None) -> None:
    """Convert a PowerPoint presentation to MP4 video.

    Args:
        infile: Input PowerPoint file path.
        outfile: Output MP4 file path. If not provided, uses input filename with .mp4 extension.
        config: Optional Config object with settings.

    Raises:
        FileNotFoundError: If input file doesn't exist or output file is not created.
        RuntimeError: If PowerShell script fails or times out.
    """
    from filesqueeze.system.config_adapters import PresentationConfig
    from filesqueeze.system.decorators import trace_function

    @trace_function
    def _to_mp4(infile: str, outfile: str = "", *, config: object = None) -> None:
        # Validation & defaults
        infile = Path(infile)
        if not infile.exists():
            raise FileNotFoundError(f"{infile}: Input file not found")
        outfile = Path(outfile) if outfile else infile.parent.joinpath(infile.stem + ".mp4")

        # Use config adapter if config provided
        if config:
            pres_config = PresentationConfig(config)
            timeout = pres_config.timeout
            powershell_path = config.powershell_path if hasattr(config, "powershell_path") else ""
        else:
            timeout = 1800  # 30 minutes default for PPT conversion
            powershell_path = ""

        # Get PowerShell path with fallback to PATH detection
        powershell = get_powershell_path(powershell_path)

        cmd = [
            powershell,
            SCRIPTPATH,
            str(infile),
            str(outfile),
        ]

        try:
            run_subprocess(cmd, timeout=timeout, tool_name="PowerShell", input_file=str(infile))
        except SubprocessTimeout:
            raise RuntimeError(f"PowerShell timeout converting presentation: {infile}") from None
        except SubprocessError as e:
            raise RuntimeError(f"PowerShell failed to convert presentation: {infile}") from e

        # Verify output file exists and has reasonable size
        try:
            verify_output_file(str(outfile), min_size=1000)
        except FileNotFoundError:
            raise

    _to_mp4(infile, outfile, config=config)


# Backward compatibility alias
convert_pptx = to_mp4
