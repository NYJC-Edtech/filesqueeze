"""filesqueeze.ops.presentation

Presentation compression functions for PowerPoint files.

This module provides PowerPoint to MP4 conversion operations using PowerShell.
It uses the system package for logging.
"""

import os
import subprocess
from pathlib import Path

# Import from system package
from filesqueeze.system import logger


# Constants
POWERSHELL = 'powershell.exe'
SCRIPTPATH = str(Path(__file__).parent.parent.joinpath('bin', 'pptx2mp4.ps1'))


def to_mp4(
    infile: str,
    outfile: str = "",
    *,
    config=None
) -> None:
    """Convert a PowerPoint presentation to MP4 video.

    Args:
        infile: Input PowerPoint file path.
        outfile: Output MP4 file path. If not provided, uses input filename with .mp4 extension.
        config: Optional Config object with settings.

    Raises:
        FileNotFoundError: If input file doesn't exist or output file is not created.
        ChildProcessError: If PowerShell script fails.
    """
    from filesqueeze.system.decorators import trace_function
    from filesqueeze.system.config_adapters import PresentationConfig

    @trace_function
    def _to_mp4(
        infile: str,
        outfile: str = "",
        *,
        config=None
    ) -> None:
        # Validation & defaults
        infile = Path(infile)
        if not infile.exists():
            raise FileNotFoundError(f'{infile}: Input file not found')
        outfile = Path(outfile) if outfile else infile.parent.joinpath(infile.stem + '.mp4')

        cmd = [
            POWERSHELL,
            SCRIPTPATH,
            str(infile),
            str(outfile),
        ]

        try:
            proc = subprocess.run(
                cmd,
                cwd='.',
                check=True,
            )
        except subprocess.CalledProcessError:
            raise ChildProcessError("PowerShell script failed")
        else:
            if proc.returncode != 0:
                raise ChildProcessError(f"PowerShell script returned non-zero exit code: {proc.returncode}")

        # Verification
        if not Path(outfile).exists():
            raise FileNotFoundError(f'{infile}: Output file not created')

    _to_mp4(infile, outfile, config=config)


# Backward compatibility alias
convert_pptx = to_mp4
