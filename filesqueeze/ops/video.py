"""filesqueeze.ops.video

Video compression functions using FFmpeg.

This module provides video compression operations using FFmpeg.
It uses the system package for binary detection and logging.
"""

import subprocess
from pathlib import Path
from typing import Callable

# Import from system package
from filesqueeze.config import Config
from filesqueeze.system import get_binary_finder

# Import subprocess utilities
from filesqueeze.utils.subprocess_helper import (
    SubprocessError,
    SubprocessTimeout,
    run_subprocess,
    run_subprocess_with_progress,
    verify_output_file,
)


def get_ffmpeg_path(config_path: str = "") -> Path:
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
        return Path(config_path)

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


def width_height(infile: str, ffmpeg_path: str = "") -> tuple[int, int] | None:
    """Get video width and height using ffprobe.

    Args:
        infile: Input video file path.
        ffmpeg_path: Optional path to FFmpeg directory.

    Returns:
        Tuple of (width, height) or None if detection fails.

    Raises:
        RuntimeError: If ffprobe fails.
    """
    from filesqueeze.system.decorators import trace_function

    @trace_function
    def _width_height(infile: str, ffmpeg_path: str = "") -> tuple[int, int] | None:
        ffprobe = get_ffprobe_path(ffmpeg_path)

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
            data = subprocess.run(cmd, timeout=60, check=True, text=True, capture_output=True).stdout.strip()
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"ffprobe timeout analyzing video: {infile}") from None
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"ffprobe failed with return code {e.returncode}: {infile}") from None

        if data and "x" in data:
            # Handle trailing 'x' in ffprobe output (e.g., "1920x1080x")
            parts = [p for p in data.split("x") if p]
            if len(parts) >= 2:
                return int(parts[0]), int(parts[1])

        return None

    return _width_height(infile, ffmpeg_path)


def duration(infile: str, ffmpeg_path: str = "") -> float | None:
    """Get video duration using ffprobe.

    Args:
        infile: Input video file path.
        ffmpeg_path: Optional path to FFmpeg directory.

    Returns:
        Duration in seconds or None if detection fails.

    Raises:
        RuntimeError: If ffprobe fails.
    """
    from filesqueeze.system.decorators import trace_function

    @trace_function
    def _duration(infile: str, ffmpeg_path: str = "") -> float | None:
        ffprobe = get_ffprobe_path(ffmpeg_path)

        cmd = [
            ffprobe,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "csv=p=0",
            infile,
        ]

        try:
            data = subprocess.run(cmd, timeout=60, check=True, text=True, capture_output=True).stdout.strip()
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"ffprobe timeout analyzing video: {infile}") from None
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"ffprobe failed with return code {e.returncode}: {infile}") from None

        return float(data) if data else None

    return _duration(infile, ffmpeg_path)


def ffmpeg_progress_handler(
    total_duration: float | None,
    report: Callable[[int], None],
) -> Callable[[str], None]:
    """Build an stdout-line handler for FFmpeg ``-progress pipe:1`` output.

    Args:
        total_duration: Total media duration in seconds. When None or
            non-positive, no percentages are reported.
        report: Callback invoked with each new percentage (monotonically
            increasing, clamped to 0-99 until the run actually finishes).

    Returns:
        Handler suitable as ``on_stdout_line`` for run_subprocess_with_progress.
    """
    last_percent = -1

    def handle(line: str) -> None:
        nonlocal last_percent
        line = line.strip()
        # Both out_time_us and out_time_ms carry microseconds (the latter
        # is misnamed in FFmpeg); out_time_us is the modern spelling
        for key in ("out_time_us", "out_time_ms"):
            if line.startswith(key + "="):
                raw = line.split("=", 1)[1]
                try:
                    out_micros = float(raw)
                except ValueError:
                    return  # "N/A" and other non-numeric values
                if not total_duration or total_duration <= 0:
                    return
                percent = int(out_micros / 1_000_000 / total_duration * 100)
                percent = max(0, min(99, percent))
                if percent > last_percent:
                    last_percent = percent
                    report(percent)
                return

    return handle


def compress(
    infile: str,
    outfile: str,
    *,
    config: Config | None = None,
    downscale: bool = False,
    crf: int | None = None,
    threads: int | None = None,
    preset: str | None = None,
    max_height: int | None = None,
    audio_bitrate: str | None = None,
    ffmpeg_path: str | None = None,
    progress_cb: Callable[[int], None] | None = None,
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
        progress_cb: Optional callback receiving completion percentage
            (0-99) during the encode. Best-effort: silently omitted when
            the input duration cannot be probed.

    Raises:
        FileNotFoundError: If output file is not created.
        RuntimeError: If FFmpeg fails.
    """
    from filesqueeze.system.config_adapters import VideoConfig
    from filesqueeze.system.decorators import trace_function

    @trace_function
    def _compress(
        infile: str,
        outfile: str,
        *,
        config: Config | None = None,
        downscale: bool = False,
        crf: int | None = None,
        threads: int | None = None,
        preset: str | None = None,
        max_height: int | None = None,
        audio_bitrate: str | None = None,
        ffmpeg_path: str | None = None,
        progress_cb: Callable[[int], None] | None = None,
    ) -> None:
        # Use config adapter if config provided
        if config:
            video_config = VideoConfig(config)
            crf = crf or video_config.crf
            threads = threads or video_config.threads
            preset = preset or video_config.preset
            max_height = max_height or video_config.max_height
            audio_bitrate = audio_bitrate or video_config.audio_bitrate
            ffmpeg_path = ffmpeg_path or config.ffmpeg_path
            timeout = video_config.timeout
            min_size = video_config.min_output_size_bytes
        else:
            # Use defaults
            crf = crf or 28
            threads = threads or 8
            preset = preset or "veryfast"
            max_height = max_height or 720
            audio_bitrate = audio_bitrate or "96k"
            timeout = 1800
            min_size = 4096

        ffmpeg = get_ffmpeg_path(ffmpeg_path or "")

        # Progress reporting is best-effort: it needs the input duration,
        # and a failed probe just means no percentages (compression itself
        # is unaffected)
        on_stdout_line = None
        if progress_cb is not None:
            try:
                total_duration = duration(infile, str(ffmpeg))
            except Exception:
                total_duration = None
            if total_duration and total_duration > 0:
                on_stdout_line = ffmpeg_progress_handler(total_duration, progress_cb)

        # Build FFmpeg command
        cmd = [
            ffmpeg,
            "-threads",
            str(threads),
            "-y",
            "-hide_banner",
            "-loglevel",
            "panic",
        ]
        if on_stdout_line is not None:
            # Machine-readable progress on stdout, ~every 0.5s
            cmd += ["-progress", "pipe:1", "-nostats"]
        cmd += [
            "-i",
            infile,
            "-crf",
            str(crf),
            "-c:v",
            "libx264",
            "-profile:v",
            "high",
            "-level",
            "4.2",
            "-preset",
            preset,
            # Handle 10-bit and 12-bit videos by forcing 8-bit (yuv420p) output
            "-vf",
            "format=yuv420p",
            "-pix_fmt",
            "yuv420p",
        ]

        # Add video filter
        vf_filter = "format=yuv420p"
        if downscale:
            vf_filter += f",scale=-2:{max_height}"
        cmd.extend(["-vf", vf_filter, "-sws_flags", "lanczos"])

        cmd.extend(
            [
                "-movflags",
                "faststart",
                "-c:a",
                "aac",
                "-b:a",
                audio_bitrate,
                "-af",
                "dynaudnorm",
                outfile,
            ]
        )

        try:
            if on_stdout_line is not None:
                run_subprocess_with_progress(
                    cmd,
                    timeout=timeout,
                    tool_name="FFmpeg",
                    input_file=infile,
                    on_stdout_line=on_stdout_line,
                )
            else:
                run_subprocess(
                    cmd,
                    timeout=timeout,
                    tool_name="FFmpeg",
                    input_file=infile,
                    capture_output=True,
                    text_mode=True,
                    check=True,
                )
        except SubprocessTimeout:
            raise RuntimeError(f"FFmpeg timeout compressing video: {infile}") from None
        except SubprocessError as e:
            # Include stderr in error message for better debugging
            error_msg = f"FFmpeg failed to compress video: {infile}"
            if e.stderr:
                error_msg += f"\nFFmpeg error: {e.stderr.strip()}"
            raise RuntimeError(error_msg) from None

        # Verify output file exists and meets size requirements
        try:
            verify_output_file(outfile, min_size=min_size)
        except FileNotFoundError:
            raise
        except RuntimeError:
            raise

    _compress(
        infile,
        outfile,
        config=config,
        downscale=downscale,
        crf=crf,
        threads=threads,
        preset=preset,
        max_height=max_height,
        audio_bitrate=audio_bitrate,
        ffmpeg_path=ffmpeg_path,
        progress_cb=progress_cb,
    )
