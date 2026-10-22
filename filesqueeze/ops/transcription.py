"""filesqueeze.ops.transcription

Speech-to-captions for compressed videos, powered by the bundled stcc
package (Fluid Speech Mini via parakeet.cpp — see the filesqueeze-stcc
repository). Gated by ``[transcription] enabled`` (default off). All
functions are best-effort: any gating mismatch or failure is logged and
returns None/False — compression results are never affected.

Config keys (see default.toml [transcription]):
- ``enabled``: master switch, default false
- ``stcc_path``: path to stcc.py, filled in by ``setup-deps``
- ``threads``: runtime threads (0 = stcc default)
"""

import logging
import os
import subprocess
import sys
from pathlib import Path

from filesqueeze.config import Config
from filesqueeze.ops.video import get_ffmpeg_path
from filesqueeze.system import get_logger

# containers that accept mov_text soft subtitles
_MUXABLE_SUFFIXES = {".mp4", ".m4v"}

_CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0


def is_enabled(config: Config | None) -> bool:
    """Whether transcription is switched on (default: off; None config = off)."""
    if config is None:
        return False
    return bool(config.get("transcription.enabled", False))


def resolve_stcc_path(config: Config) -> Path | None:
    """Configured stcc.py path, or None when unconfigured or absent on disk."""
    raw = str(config.get("transcription.stcc_path", "") or "").strip()
    if not raw:
        return None
    path = Path(raw)
    return path if path.exists() else None


def build_stcc_command(stcc_path: Path, video: Path, output_dir: Path, name: str, threads: int = 0) -> list[str]:
    """Build the stcc transcribe invocation (see the stcc contract)."""
    cmd = [
        sys.executable,
        str(stcc_path),
        "transcribe",
        "--formats",
        "srt",
        "--name",
        name,
        "--output-dir",
        str(output_dir),
    ]
    if threads > 0:
        cmd += ["--threads", str(threads)]
    cmd.append(str(video))
    return cmd


def mux_subtitles(video: Path, srt: Path, ffmpeg: Path) -> bool:
    """Embed the SRT into a video as a soft mov_text track (stream copy, in place).

    Returns False on any failure; the original video is left untouched.
    """
    tmp = video.with_name(video.stem + ".muxtmp" + video.suffix)
    try:
        result = subprocess.run(
            [
                str(ffmpeg),
                "-v",
                "error",
                "-y",
                "-i",
                str(video),
                "-i",
                str(srt),
                "-map",
                "0:v",
                "-map",
                "0:a",
                "-map",
                "1:0",
                "-c",
                "copy",
                "-c:s",
                "mov_text",
                "-metadata:s:s:0",
                "language=eng",
                str(tmp),
            ],
            capture_output=True,
            text=True,
            creationflags=_CREATE_NO_WINDOW,
        )
        if result.returncode != 0 or not tmp.exists() or tmp.stat().st_size == 0:
            tmp.unlink(missing_ok=True)
            return False
        os.replace(tmp, video)
        return True
    except Exception:
        tmp.unlink(missing_ok=True)
        return False


def transcribe_after_compress(original: Path, compressed: Path, config: Config) -> Path | None:
    """Produce captions for a freshly compressed video. Never raises.

    Transcribes the ORIGINAL video (better source audio), writes
    ``<compressed-stem>.srt`` next to the compressed output and, for MP4
    outputs, embeds it as a soft mov_text track. Returns the SRT path, or
    None when disabled/skipped/failed (reason logged).
    """
    logger: logging.Logger = get_logger()
    original_name = getattr(original, "name", str(original))
    try:
        if config is None or not is_enabled(config):
            return None
        stcc_path = resolve_stcc_path(config)
        if stcc_path is None:
            raw = str(config.get("transcription.stcc_path", "") or "").strip()
            if raw:
                logger.warning("transcription enabled but stcc_path is missing on disk: %s", raw)
            else:
                logger.info(
                    "transcription enabled but stcc_path is not configured — "
                    "run 'filesqueeze setup-deps' to install the captions package"
                )
            return None

        threads = int(config.get("transcription.threads", 0) or 0)
        srt_target = compressed.with_suffix(".srt")
        cmd = build_stcc_command(stcc_path, original, compressed.parent, compressed.stem, threads)
        logger.info("transcribing %s via stcc", original_name)
        result = subprocess.run(cmd, capture_output=True, text=True, creationflags=_CREATE_NO_WINDOW)
        if result.returncode != 0:
            logger.warning(
                "stcc transcription failed (exit %d) for %s: %s",
                result.returncode,
                original_name,
                (result.stderr or "").strip()[-300:],
            )
            return None
        if not srt_target.exists():
            logger.warning("stcc reported success but %s was not created", srt_target.name)
            return None

        if compressed.suffix.lower() in _MUXABLE_SUFFIXES:
            try:
                ffmpeg = get_ffmpeg_path(str(config.get("ffmpeg.path", "") or ""))
                if mux_subtitles(compressed, srt_target, ffmpeg):
                    logger.info("embedded captions into %s", compressed.name)
                else:
                    logger.warning("could not embed captions into %s — sidecar kept", compressed.name)
            except Exception as exc:
                logger.warning("caption embedding skipped for %s: %s", compressed.name, exc)

        logger.info("captions ready: %s", srt_target.name)
        return srt_target
    except Exception as exc:
        logger.warning("transcription skipped for %s: %s", original_name, exc)
        return None
