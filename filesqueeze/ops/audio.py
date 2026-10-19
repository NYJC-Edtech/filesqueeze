"""filesqueeze.ops.audio

Audio compression functions using FFmpeg.

This module provides audio compression operations using FFmpeg, converting
uncompressed inputs (WAV) to AAC in an M4A container. It uses the system
package for binary detection and logging.
"""

from filesqueeze.config import Config
from filesqueeze.utils.subprocess_helper import SubprocessError, SubprocessTimeout, run_subprocess, verify_output_file

from .video import get_ffmpeg_path


def compress(
    infile: str,
    outfile: str,
    *,
    config: Config | None = None,
    audio_bitrate: str | None = None,
    threads: int | None = None,
    ffmpeg_path: str | None = None,
) -> None:
    """Compress an audio file to AAC in an M4A container using FFmpeg.

    Args:
        infile: Input audio file path.
        outfile: Output audio file path (``.m4a``).
        config: Optional Config object with settings.
        audio_bitrate: Audio bitrate (e.g., '96k').
        threads: Number of threads to use.
        ffmpeg_path: Optional path to FFmpeg executable.

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
            run_subprocess(
                cmd, timeout=timeout, tool_name="FFmpeg", input_file=infile, capture_output=True, text_mode=True, check=True
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
    )
