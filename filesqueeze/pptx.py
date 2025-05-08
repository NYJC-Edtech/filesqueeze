import os, subprocess
from pathlib import Path


POWERSHELL = 'powershell.exe'
SCRIPTPATH = str(Path(os.path.realpath(__file__)).parent.joinpath('bin', 'pptx2mp4.ps1'))  # relative path


def to_mp4(infile: str, outfile: str = "") -> None:
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
        raise ChildProcessError
    else:
        if proc.returncode != 0:
            raise ChildProcessError
    
    # Verification
    if not Path(outfile).exists():
        raise FileNotFoundError(f'{infile}: Output file not found')