"""filesqueeze.document

Document compression functions for PDF and images using Ghostscript and FFmpeg.
"""

import os
import subprocess
from pathlib import Path
from typing import Tuple, Optional


def get_ghostscript_path(config_path: str = '') -> str:
    """Get the Ghostscript executable path.

    Args:
        config_path: Path from config, or empty string to use PATH.

    Returns:
        Path to Ghostscript executable.
    """
    if config_path and Path(config_path).exists():
        return config_path

    # Try to find gs in PATH
    platform = os.name
    if platform == 'nt':  # Windows
        # Try common Ghostscript executable names
        for exe in ['gs', 'gswin64c', 'gswin32c']:
            try:
                result = subprocess.run(
                    [exe, '--version'],
                    capture_output=True,
                    timeout=5
                )
                if result.returncode == 0:
                    return exe
            except (subprocess.CalledProcessError, FileNotFoundError):
                continue
    else:  # Linux/Mac
        try:
            result = subprocess.run(
                ['gs', '--version'],
                capture_output=True,
                timeout=5
            )
            if result.returncode == 0:
                return 'gs'
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass

    raise RuntimeError(
        "Ghostscript not found. Please install Ghostscript or configure ghostscript_path in config."
    )


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


def compress_pdf(
    infile: str,
    outfile: str,
    quality: str = 'ebook',
    compression_level: int = 2,
    ghostscript_path: str = ''
) -> None:
    """Compress a PDF file using Ghostscript.

    Args:
        infile: Input PDF file path.
        outfile: Output PDF file path.
        quality: PDF quality setting (screen, ebook, printer, prepress, default).
        compression_level: Compression level (0-4).
        ghostscript_path: Optional path to Ghostscript executable.

    Raises:
        FileNotFoundError: If output file is not created.
        RuntimeError: If Ghostscript fails.
        ValueError: If quality setting is invalid.
    """
    # Map quality levels to Ghostscript PDFSETTINGS
    quality_settings = {
        'screen': '/screen',
        'ebook': '/ebook',
        'printer': '/printer',
        'prepress': '/prepress',
        'default': '/default'
    }

    # Validate quality parameter before trying to find Ghostscript
    if quality not in quality_settings:
        raise ValueError(f"Invalid quality setting: {quality}. Must be one of {list(quality_settings.keys())}")

    gs = get_ghostscript_path(ghostscript_path)

    cmd = [
        gs,
        '-sDEVICE=pdfwrite',
        '-dCompatibilityLevel=1.4',
        f'-dPDFSETTINGS={quality_settings[quality]}',
        f'-dCompressionLevel={compression_level}',
        '-dNOPAUSE',
        '-dQUIET',
        '-dBATCH',
        '-sOutputFile=' + outfile,
        infile,
    ]

    # Get input file size for comparison
    input_size = Path(infile).stat().st_size

    try:
        subprocess.run(cmd, timeout=300, check=True)
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"Ghostscript timeout compressing PDF: {infile}")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Ghostscript failed with return code {e.returncode}: {infile}")

    # Verify output file exists
    if not Path(outfile).exists():
        raise FileNotFoundError(f"Output file not created: {outfile}")

    # Verify compression actually reduced file size
    output_size = Path(outfile).stat().st_size
    if output_size >= input_size:
        import shutil
        # Compression didn't help, copy original instead
        shutil.copy2(infile, outfile)
        # Note: We could log this warning if logging was available


def get_image_size(infile: str, ffmpeg_path: str = '') -> Tuple[int, int]:
    """Get image dimensions using ffprobe.

    Args:
        infile: Input image file path.
        ffmpeg_path: Optional path to FFmpeg directory (for ffprobe).

    Returns:
        Tuple of (width, height).

    Raises:
        RuntimeError: If ffprobe fails.
    """
    # Find ffprobe
    if ffmpeg_path and Path(ffmpeg_path).exists():
        ffprobe = str(Path(ffmpeg_path).parent / 'ffprobe.exe')
    else:
        # Try bundled ffprobe
        package_dir = Path(__file__).parent
        bundled_ffprobe = package_dir / 'bin' / 'ffprobe.exe'
        if bundled_ffprobe.exists():
            ffprobe = str(bundled_ffprobe)
        else:
            ffprobe = 'ffprobe'

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
        raise RuntimeError(f"ffprobe timeout analyzing image: {infile}")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"ffprobe failed with return code {e.returncode}: {infile}")

    if data and 'x' in data:
        width, height = data.split('x')
        return int(width), int(height)

    raise RuntimeError(f"Could not determine image dimensions: {infile}")


def compress_image(
    infile: str,
    outfile: str,
    quality: int = 85,
    max_width: Optional[int] = None,
    max_height: Optional[int] = None,
    convert_to_jpeg: bool = False,
    ffmpeg_path: str = ''
) -> None:
    """Compress an image file using FFmpeg.

    Args:
        infile: Input image file path.
        outfile: Output image file path.
        quality: JPEG quality (1-100).
        max_width: Maximum width (None = no scaling).
        max_height: Maximum height (None = no scaling).
        convert_to_jpeg: Convert output to JPEG format.
        ffmpeg_path: Optional path to FFmpeg executable.

    Raises:
        FileNotFoundError: If output file is not created.
        RuntimeError: If FFmpeg fails.
    """
    ffmpeg = get_ffmpeg_path(ffmpeg_path)

    # Build FFmpeg command
    cmd = [
        ffmpeg,
        '-y',  # Overwrite output file
        '-hide_banner',
        '-loglevel', 'panic',
        '-i', infile,
    ]

    # Add scaling filter if dimensions specified
    if max_width or max_height:
        # Get current dimensions
        try:
            width, height = get_image_size(infile, ffmpeg_path)
        except RuntimeError:
            # If we can't get dimensions, skip scaling
            width, height = None, None

        if width and height:
            # Calculate scaling
            scale_filter = []
            if max_width and width > max_width:
                scale_filter.append(f'iw*min(1,{max_width}/iw)')
            else:
                scale_filter.append('iw')

            if max_height and height > max_height:
                scale_filter.append(f'ih*min(1,{max_height}/ih)')
            else:
                scale_filter.append('ih')

            cmd.extend(['-vf', f"scale={':'.join(scale_filter)}"])

    # Determine output format
    output_ext = Path(outfile).suffix.lower()
    if convert_to_jpeg or output_ext in ['.jpg', '.jpeg']:
        # Use JPEG codec with quality setting
        cmd.extend([
            '-q:v', str(quality),  # Quality 1-31 (lower is better)
            '-vcodec', 'mjpeg',
        ])
    elif output_ext == '.png':
        # Use PNG codec with compression
        cmd.extend([
            '-compression_level', '6',
            '-vcodec', 'png',
        ])

    cmd.append(outfile)

    # Get input file size for comparison
    input_size = Path(infile).stat().st_size

    try:
        subprocess.run(cmd, timeout=300, check=True)
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"FFmpeg timeout compressing image: {infile}")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"FFmpeg failed with return code {e.returncode}: {infile}")

    # Verify output file exists
    if not Path(outfile).exists():
        raise FileNotFoundError(f"Output file not created: {outfile}")

    # Verify output file is not too small
    output_size = Path(outfile).stat().st_size
    if output_size < 1024:
        raise RuntimeError(f"Output file is too small (< 1KB): {outfile}")

    # Verify compression actually reduced file size
    if output_size >= input_size:
        import shutil
        # Compression didn't help, copy original instead
        shutil.copy2(infile, outfile)
        # Note: We could log this warning if logging was available

