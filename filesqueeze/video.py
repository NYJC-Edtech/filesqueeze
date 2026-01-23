"""filesqueeze.video

Video compression functions using FFmpeg.
"""

import os
import subprocess
from pathlib import Path
from typing import Tuple, Optional


def get_ffmpeg_path(config_path: str = '') -> str:
    """Get the FFmpeg executable path.

    Args:
        config_path: Path from config, or empty string to use PATH.

    Returns:
        Path to FFmpeg executable.
    """
    if config_path and Path(config_path).exists():
        return config_path

    # Try bundled binaries
    package_dir = Path(__file__).parent
    bundled_ffmpeg = package_dir / 'bin' / 'ffmpeg.exe'
    if bundled_ffmpeg.exists():
        return str(bundled_ffmpeg)

    # Try to find ffmpeg in PATH
    try:
        result = subprocess.run(
            ['ffmpeg', '-version'],
            capture_output=True,
            timeout=5
        )
        if result.returncode == 0:
            return 'ffmpeg'
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    raise RuntimeError(
        "FFmpeg not found. Please install FFmpeg or configure ffmpeg_path in config."
    )


def get_ffprobe_path(ffmpeg_path: str = '') -> str:
    """Get the ffprobe executable path.

    Args:
        ffmpeg_path: Path to FFmpeg (for finding bundled ffprobe).

    Returns:
        Path to ffprobe executable.
    """
    # Try bundled ffprobe first
    package_dir = Path(__file__).parent
    bundled_ffprobe = package_dir / 'bin' / 'ffprobe.exe'
    if bundled_ffprobe.exists():
        return str(bundled_ffprobe)

    # If ffmpeg_path is specified, try to find ffprobe in the same directory
    if ffmpeg_path:
        ffprobe = str(Path(ffmpeg_path).parent / 'ffprobe.exe')
        if Path(ffprobe).exists():
            return ffprobe

    # Try to find ffprobe in PATH
    try:
        result = subprocess.run(
            ['ffprobe', '-version'],
            capture_output=True,
            timeout=5
        )
        if result.returncode == 0:
            return 'ffprobe'
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    raise RuntimeError(
        "ffprobe not found. Please install FFmpeg or configure ffmpeg_path in config."
    )


def width_height(infile: str, ffmpeg_path: str = '') -> Optional[Tuple[int, int]]:
    """Get video width and height using ffprobe.

    Args:
        infile: Input video file path.
        ffmpeg_path: Optional path to FFmpeg directory.

    Returns:
        Tuple of (width, height) or None if detection fails.

    Raises:
        RuntimeError: If ffprobe fails.
    """
    ffprobe = get_ffprobe_path(ffmpeg_path)

    cmd = [
        ffprobe,
        '-v', 'error',
        '-select_streams', 'v:0',
        '-show_entries', 'stream=width,height',
        '-of', 'csv=s=x:p=0',
        infile,
    ]

    try:
        data = subprocess.run(
            cmd,
            timeout=60,
            check=True,
            text=True,
            capture_output=True
        ).stdout.strip()
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"ffprobe timeout analyzing video: {infile}")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"ffprobe failed with return code {e.returncode}: {infile}")

    if data and 'x' in data:
        width, height = data.split('x')
        return int(width), int(height)

    return None


def duration(infile: str, ffmpeg_path: str = '') -> Optional[float]:
    """Get video duration using ffprobe.

    Args:
        infile: Input video file path.
        ffmpeg_path: Optional path to FFmpeg directory.

    Returns:
        Duration in seconds or None if detection fails.

    Raises:
        RuntimeError: If ffprobe fails.
    """
    ffprobe = get_ffprobe_path(ffmpeg_path)

    cmd = [
        ffprobe,
        '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'csv=p=0',
        infile,
    ]

    try:
        data = subprocess.run(
            cmd,
            timeout=60,
            check=True,
            text=True,
            capture_output=True
        ).stdout.strip()
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"ffprobe timeout analyzing video: {infile}")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"ffprobe failed with return code {e.returncode}: {infile}")

    return float(data) if data else None


def compress(
    infile: str,
    outfile: str,
    *,
    config=None,
    downscale: bool = False,
    crf: Optional[int] = None,
    threads: Optional[int] = None,
    preset: Optional[str] = None,
    max_height: Optional[int] = None,
    audio_bitrate: Optional[str] = None,
    ffmpeg_path: Optional[str] = None
) -> None:
    """Compress a video file using FFmpeg.

    Args:
        infile: Input video file path.
        outfile: Output video file path.
        config: Optional Config object with settings.
        downscale: Whether to downscale to max_height.
        crf: Constant Rate Factor (quality, lower = better).
        threads: Number of threads to use.
        preset: Encoding preset (ultrafast, superfast, veryfast, faster, fast, medium, slow, slower, veryslow).
        max_height: Maximum height for downscaling.
        audio_bitrate: Audio bitrate (e.g., '96k').
        ffmpeg_path: Optional path to FFmpeg executable.

    Raises:
        FileNotFoundError: If output file is not created.
        RuntimeError: If FFmpeg fails.
    """
    # Get parameters from config if provided
    if config:
        crf = crf or config.get('ffmpeg.crf', 28)
        threads = threads or config.get('ffmpeg.threads', 8)
        preset = preset or config.get('ffmpeg.preset', 'veryfast')
        max_height = max_height or config.get('ffmpeg.max_height', 720)
        audio_bitrate = audio_bitrate or config.get('ffmpeg.audio_bitrate', '96k')
        ffmpeg_path = ffmpeg_path or config.ffmpeg_path
    else:
        # Use defaults
        crf = crf or 28
        threads = threads or 8
        preset = preset or 'veryfast'
        max_height = max_height or 720
        audio_bitrate = audio_bitrate or '96k'

    ffmpeg = get_ffmpeg_path(ffmpeg_path or '')

    # Build FFmpeg command
    cmd = [
        ffmpeg,
        '-threads', str(threads),
        '-y',
        '-hide_banner',
        '-loglevel', 'panic',
        '-i', infile,
        '-crf', str(crf),
        '-c:v', 'libx264',
        '-profile:v', 'high',
        '-level', '4.2',
        '-preset', preset,
    ]

    # Add video filter
    vf_filter = 'format=yuv420p'
    if downscale:
        vf_filter += f',scale=-2:{max_height}'
    cmd.extend(['-vf', vf_filter, '-sws_flags', 'lanczos'])

    cmd.extend([
        '-movflags', 'faststart',
        '-c:a', 'aac',
        '-b:a', audio_bitrate,
        '-af', 'dynaudnorm',
        outfile,
    ])

    try:
        subprocess.run(
            cmd,
            timeout=1800,
            check=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"FFmpeg timeout compressing video: {infile}")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"FFmpeg failed with return code {e.returncode}: {infile}")

    # Verify output file exists
    if not Path(outfile).exists():
        raise FileNotFoundError(f"Output file not created: {outfile}")

    # Verify output file is not too small
    if Path(outfile).stat().st_size < 4096:
        raise RuntimeError(f"Output file is too small (< 4KB): {outfile}")
