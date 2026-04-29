"""filesqueeze.ops.image

Image compression functions using FFmpeg.

This module provides image compression operations using FFmpeg.
It uses the system package for binary detection and logging.
"""

from pathlib import Path
from typing import Tuple, Optional

# Import from system package
from filesqueeze.system import get_binary_finder, logger

# Import subprocess utilities
from filesqueeze.utils.subprocess_helper import run_subprocess, verify_output_file, SubprocessTimeout, SubprocessError


def get_ffmpeg_path(config_path: str = "") -> str:
    """Get the FFmpeg executable path.

    Args:
        config_path: Path from config, or empty string to use PATH.

    Returns:
        Path to FFmpeg executable.

    Raises:
        RuntimeError: If FFmpeg is not found.

    Note:
        If config_path is provided and exists, it will be used.
        Otherwise, uses the registered BinaryFinder to auto-detect.
    """
    # If explicit path provided and it exists, use it
    if config_path and Path(config_path).exists():
        return config_path

    # Otherwise use registered finder
    finder = get_binary_finder()
    return finder.get_ffmpeg_path()


def get_ffprobe_path(ffmpeg_path: str = "") -> str:
    """Get the ffprobe executable path.

    Args:
        ffmpeg_path: Path to FFmpeg (for finding bundled ffprobe).

    Returns:
        Path to ffprobe executable.

    Raises:
        RuntimeError: If ffprobe is not found.

    Note:
        If ffmpeg_path is provided and ffprobe exists in that directory,
        it will be used. Otherwise, uses the registered BinaryFinder
        to auto-detect.
    """
    # If ffmpeg_path provided, try to find ffprobe in same directory
    if ffmpeg_path:
        ffprobe = str(Path(ffmpeg_path).parent / "ffprobe.exe")
        if Path(ffprobe).exists():
            return ffprobe

    # Otherwise use registered finder
    finder = get_binary_finder()
    return finder.get_ffprobe_path()


def get_image_size(infile: str, ffmpeg_path: str = "") -> Tuple[int, int]:
    """Get image dimensions using ffprobe.

    Args:
        infile: Input image file path.
        ffmpeg_path: Optional path to FFmpeg directory (for ffprobe).

    Returns:
        Tuple of (width, height).

    Raises:
        RuntimeError: If ffprobe fails.
    """
    from filesqueeze.system.decorators import trace_function

    @trace_function
    def _get_image_size(infile: str, ffmpeg_path: str = "") -> Tuple[int, int]:
        # Find ffprobe
        if ffmpeg_path and Path(ffmpeg_path).exists():
            ffprobe = str(Path(ffmpeg_path).parent / "ffprobe.exe")
        else:
            ffprobe = get_ffprobe_path(ffmpeg_path)
            ffprobe = str(Path(ffprobe).parent / "ffprobe.exe") if Path(ffprobe).exists() else "ffprobe"

        cmd = [
            ffprobe,
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height",
            "-of",
            "csv=s=x:p=0",
            infile,
        ]

        try:
            data = run_subprocess(cmd, timeout=60, tool_name="ffprobe", input_file=infile, capture_output=True, text_mode=True)
        except SubprocessTimeout:
            raise RuntimeError(f"ffprobe timeout analyzing image: {infile}")
        except SubprocessError:
            raise

        if data and "x" in data:
            width, height = data.split("x")
            return int(width), int(height)

        raise RuntimeError(f"Could not determine image dimensions: {infile}")

    return _get_image_size(infile, ffmpeg_path)


def compress_image(
    infile: str,
    outfile: str,
    *,
    quality: int = 85,
    max_width: Optional[int] = None,
    max_height: Optional[int] = None,
    convert_to_jpeg: bool = False,
    ffmpeg_path: str = "",
    config=None,
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
        config: Optional Config object with settings.

    Raises:
        FileNotFoundError: If output file is not created.
        RuntimeError: If FFmpeg fails.
    """
    from filesqueeze.system.decorators import trace_function
    from filesqueeze.system.config_adapters import ImageConfig

    @trace_function
    def _compress_image(
        infile: str,
        outfile: str,
        *,
        quality: int = 85,
        max_width: Optional[int] = None,
        max_height: Optional[int] = None,
        convert_to_jpeg: bool = False,
        ffmpeg_path: str = "",
        config=None,
    ) -> None:
        # Use config adapter if config provided
        if config:
            img_config = ImageConfig(config)
            quality = quality or img_config.quality
            max_width = max_width or img_config.max_width
            max_height = max_height or img_config.max_height
            ffmpeg_path = ffmpeg_path or config.ffmpeg_path
            timeout = img_config.timeout
            min_size = img_config.min_output_size_bytes
        else:
            timeout = 300
            min_size = 1024

        ffmpeg = get_ffmpeg_path(ffmpeg_path)

        # Build FFmpeg command
        cmd = [
            ffmpeg,
            "-y",  # Overwrite output file
            "-hide_banner",
            "-loglevel",
            "panic",
            "-i",
            infile,
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
                    scale_filter.append(f"iw*min(1,{max_width}/iw)")
                else:
                    scale_filter.append("iw")

                if max_height and height > max_height:
                    scale_filter.append(f"ih*min(1,{max_height}/ih)")
                else:
                    scale_filter.append("ih")

                cmd.extend(["-vf", f"scale={':'.join(scale_filter)}"])

        # Determine output format
        output_ext = Path(outfile).suffix.lower()
        if convert_to_jpeg or output_ext in [".jpg", ".jpeg"]:
            # Use JPEG codec with quality setting
            cmd.extend(
                [
                    "-q:v",
                    str(quality),  # Quality 1-31 (lower is better)
                    "-vcodec",
                    "mjpeg",
                ]
            )
        elif output_ext == ".png":
            # Use PNG codec with compression
            cmd.extend(
                [
                    "-compression_level",
                    "6",
                    "-vcodec",
                    "png",
                ]
            )

        cmd.append(outfile)

        # Get input file size for comparison
        input_size = Path(infile).stat().st_size

        try:
            run_subprocess(cmd, timeout=timeout, tool_name="FFmpeg", input_file=infile)
        except SubprocessTimeout:
            raise RuntimeError(f"FFmpeg timeout compressing image: {infile}")
        except SubprocessError:
            raise RuntimeError(f"FFmpeg failed to compress image: {infile}")

        # Verify output file exists and meets size requirements
        try:
            verify_output_file(outfile, min_size=min_size)
        except FileNotFoundError:
            raise
        except RuntimeError as e:
            raise

        output = verify_output_file(outfile, min_size=min_size)
        output_size = output.stat().st_size

        # Verify compression actually reduced file size
        if output_size >= input_size:
            import shutil

            # Compression didn't help, copy original instead
            shutil.copy2(infile, outfile)

    _compress_image(
        infile,
        outfile,
        quality=quality,
        max_width=max_width,
        max_height=max_height,
        convert_to_jpeg=convert_to_jpeg,
        ffmpeg_path=ffmpeg_path,
        config=config,
    )
