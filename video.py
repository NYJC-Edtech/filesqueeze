from typing import Tuple
import os, subprocess
from pathlib import Path

FFMPEGPATH = str(Path(os.path.realpath(__file__)).parent.joinpath('bin', 'ffmpeg.exe'))
FFPROBEPATH = str(Path(os.path.realpath(__file__)).parent.joinpath('bin', 'ffprobe.exe'))

CRF = '28'

def width_height(infile: str) -> Tuple[int, int]:
    cmd = [
        FFPROBEPATH, '-v', 'error',  # hide default output
        '-select_streams', 'v:0',  # hide audio stream info
        '-show_entries', 'stream=width,height',  # show stream data
        '-of', 'csv=s=x:p=0',  # format output <width>x<height>
        infile,
    ]
    try:
        data = subprocess.run(
            cmd,
            timeout=60,
            check=True,  # raise CalledProcessError on fail
            text=True,  # open stdout in text mode
        ).stdout.strip()
    except (subprocess.CalledProcessError, Exception):
        raise

    if data and ('x' in data):
        return map(data.split('x'), int)  # convert to int
    return None



def duration(infile):
    cmd = [
        FFPROBEPATH, '-v', 'error',  # hide default output
        '-show_entries', 'format=duration',  # set output format to display duration
        '-of', 'csv=p=0',  # remove wrapping tags
        infile,
    ]
    try:
        data = subprocess.run(
            cmd,
            timeout=60,
            check=True,  # raise CalledProcessError on fail
            text=True,  # open stdout in text mode
        ).stdout.strip()
    except (subprocess.CalledProcessError, Exception):
        raise
    
    return float(data) if data else None



def compress(infile, outfile, *, downscale=False):
    cmd = [
        FFMPEGPATH,
        '-threads', '8',
        '-y', '-hide_banner', '-loglevel', 'panic',  # hide default output
        '-i', infile,
        '-crf', CRF,  # video quality
        '-c:v', 'libx264', '-profile:v', 'high', '-level', '4.2',  # video settings
        '-preset', 'veryfast',  # speed settings
        '-vf', 'format=yuv420p' + (',scale=-2:720' if downscale else ''), '-sws_flags', 'lanczos',  # video filters
        '-movflags', 'faststart',  # optimisations
        '-c:a', 'aac', '-b:a', '96k',  # audio settings
        '-af', 'dynaudnorm',  # dynamic audio normalisation
        outfile,
    ]

    try:
        subprocess.run(cmd, timeout=1800)
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, Exception):
        raise
    else:
        # FFMPEG returns returncode 1 even if compression was successful
        # TODO: may need to check that outfile filesize is not changing
        pass
    
    # Verification
    if not Path(outfile).exists():
        raise FileNotFoundError(outfile + ': Output file not found')
    if Path(outfile).stat().st_size < 4096:
        raise ChildProcessError(outfile + ': Invalid output file (too small)')