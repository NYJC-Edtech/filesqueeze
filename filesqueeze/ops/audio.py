"""filesqueeze.ops.audio

Audio compression functions using FFmpeg.

This module provides audio compression operations using FFmpeg, converting
uncompressed inputs (WAV) to AAC in an M4A container. It uses the system
package for binary detection and logging.
"""

from typing import Callable

from filesqueeze.config import Config
from filesqueeze.utils.subprocess_helper import (
    SubprocessError,
    SubprocessTimeout,
    run_subprocess,
    run_subprocess_with_progress,
    verify_output_file,
)

from .video import duration, ffmpeg_progress_handler, get_ffmpeg_path


def compress(
    infile: str,
    outfile: str,
    *,
    config: Config | None = None,
    audio_bitrate: str | None = None,
    threads: int | None = None,
    ffmpeg_path: str | None = None,
    progress_cb: Callable[[int], None] | None = None,
) -> None:
    """Compress an audio file to AAC in an M4A container using FFmpeg.

    Args:
        infile: Input audio file path.
        outfile: Output audio file path (``.m4a``).
        config: Optional Config object with settings.
        audio_bitrate: Audio bitrate (e.g., '96k').
        threads: Number of threads to use.
        ffmpeg_path: Optional path to FFmpeg executable.
        progress_cb: Optional callback receiving completion percentage
            (0-99) during the encode. Best-effort: silently omitted when
            the input duration cannot be probed.

    Raises:
        FileNotFoundError: If output file is not created.
        RuntimeError: If FFmpeg fails.
    """
    from filesqueeze.system.config_adapters import AudioConfig
    from filesqueeze.system.decorators import trace_function

    @trace_function
    def _compress(
        infile: str,
        outfile: str,
        *,
        config: Config | None = None,
        audio_bitrate: str | None = None,
        threads: int | None = None,
        ffmpeg_path: str | None = None,
        progress_cb: Callable[[int], None] | None = None,
    ) -> None:
        # Use config adapter if config provided
        if config:
            audio_config = AudioConfig(config)
            audio_bitrate = audio_bitrate or audio_config.audio_bitrate
            threads = threads or audio_config.threads
            ffmpeg_path = ffmpeg_path or config.ffmpeg_path
            timeout = audio_config.timeout
            min_size = audio_config.min_output_size_bytes
        else:
            # Use defaults
            audio_bitrate = audio_bitrate or "96k"
            threads = threads or 8
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

        # Audio content is transcoded faithfully: no dynaudnorm (unlike video,
        # where loudness normalization is desirable) and no resampling.
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
            "-vn",
            "-c:a",
            "aac",
            "-b:a",
            audio_bitrate,
            outfile,
        ]

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
            raise RuntimeError(f"FFmpeg timeout compressing audio: {infile}") from None
        except SubprocessError as e:
            # Include stderr in error message for better debugging
            error_msg = f"FFmpeg failed to compress audio: {infile}"
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
        audio_bitrate=audio_bitrate,
        threads=threads,
        ffmpeg_path=ffmpeg_path,
        progress_cb=progress_cb,
    )
