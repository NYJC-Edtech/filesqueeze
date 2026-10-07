"""filesqueeze.ops.image

Image compression functions.

JPG output is produced with Pillow (exact libjpeg control: quality,
progressive, chroma subsampling). The legacy FFmpeg path is retained for
PNG-preserving output (`convert_to_jpeg = false`).

This module uses the system package for binary detection and logging.
"""

import os
import shutil
import tempfile
from pathlib import Path

from PIL import Image, ImageOps

# Import from system package
from filesqueeze.config import Config
from filesqueeze.constants import FileExtensions
from filesqueeze.system import get_binary_finder

# Import subprocess utilities
from filesqueeze.utils.subprocess_helper import SubprocessError, SubprocessTimeout, run_subprocess, verify_output_file


def _ensure_heif_support() -> None:
    """Register the pillow-heif opener so Pillow can read HEIC/HEIF files.

    Raises:
        RuntimeError: If the pillow-heif package is not installed.
    """
    try:
        from pillow_heif import register_heif_opener
    except ImportError as e:
        raise RuntimeError(
            "HEIC/HEIF support requires the 'pillow-heif' package. Install it with: pip install pillow-heif"
        ) from e
    register_heif_opener()


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


def get_image_size(infile: str, ffmpeg_path: str = "") -> tuple[int, int]:
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
    def _get_image_size(infile: str, ffmpeg_path: str = "") -> tuple[int, int]:
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
            raise RuntimeError(f"ffprobe timeout analyzing image: {infile}") from None
        except SubprocessError:
            raise

        # Type guard: when capture_output=True and text_mode=True, run_subprocess returns str
        if isinstance(data, str) and data and "x" in data:
            width, height = data.split("x")
            return int(width), int(height)

        raise RuntimeError(f"Could not determine image dimensions: {infile}")

    return _get_image_size(infile, ffmpeg_path)


def get_image_dimensions(infile: str) -> tuple[int, int]:
    """Get image dimensions using Pillow.

    Works for every accepted image format, including HEIC/HEIF (via
    pillow-heif), without shelling out to ffprobe.

    Args:
        infile: Input image file path.

    Returns:
        Tuple of (width, height).

    Raises:
        RuntimeError: If pillow-heif is needed but not installed.
        Exception: Propagates Pillow errors for unreadable images.
    """
    from filesqueeze.system.decorators import trace_function

    @trace_function
    def _get_image_dimensions(infile: str) -> tuple[int, int]:
        if Path(infile).suffix.lower().lstrip(".") in {"heic", "heif"}:
            _ensure_heif_support()
        with Image.open(infile) as im:
            return im.width, im.height

    return _get_image_dimensions(infile)


def compress_image_to_jpg(
    infile: str,
    outfile: str,
    *,
    quality: int | None = None,
    progressive: bool | None = None,
    subsampling: str | None = None,
    max_width: int | None = None,
    max_height: int | None = None,
    flatten_background: str | None = None,
    config: Config | None = None,
) -> Path:
    """Compress an image to JPEG with Pillow using exact libjpeg settings.

    Behaviour (see README "Image compression" section):
    - EXIF orientation is applied and the ICC colour profile preserved.
    - Alpha channels are flattened onto ``flatten_background`` (JPG has no
      transparency).
    - Images larger than ``max_width``/``max_height`` are downscaled.
    - WebP/HEIC/HEIF inputs are always converted (compatibility formats).
    - For every other input (including JPG re-encodes), the JPG is only used
      when it is strictly smaller than the original; otherwise the original
      file is copied to the output unchanged.

    Args:
        infile: Input image file path.
        outfile: Planned output path. The extension may be rewritten to the
            original one when the original is kept instead of the JPG.
        quality: JPEG quality 1-95 (libjpeg scale). None = config or 88.
        progressive: Write interlaced (progressive) JPEG. None = config or True.
        subsampling: Chroma subsampling: "4:2:0", "4:2:2" or "4:4:4".
            None = config or "4:2:2".
        max_width: Maximum width (None = config or no scaling).
        max_height: Maximum height (None = config or no scaling).
        flatten_background: Colour used behind transparency. None = config
            or "#ffffff".
        config: Optional Config object used to fill parameters that were not
            passed explicitly.

    Returns:
        Path to the file actually written (the JPG at ``outfile``, or a copy
        of the original when conversion did not reduce the size).

    Raises:
        RuntimeError: If the input is animated or HEIC support is missing.
    """
    from filesqueeze.system.config_adapters import ImageConfig
    from filesqueeze.system.decorators import trace_function

    @trace_function
    def _compress_image_to_jpg(
        infile: str,
        outfile: str,
        *,
        quality: int | None,
        progressive: bool | None,
        subsampling: str | None,
        max_width: int | None,
        max_height: int | None,
        flatten_background: str | None,
        config: Config | None,
    ) -> Path:
        if config is not None:
            img_config = ImageConfig(config)
            if quality is None:
                quality = img_config.quality
            if progressive is None:
                progressive = img_config.jpeg_progressive
            if subsampling is None:
                subsampling = img_config.jpeg_subsampling
            if flatten_background is None:
                flatten_background = img_config.jpeg_flatten_background
            if max_width is None:
                max_width = img_config.max_width
            if max_height is None:
                max_height = img_config.max_height
        quality = 88 if quality is None else quality
        progressive = True if progressive is None else progressive
        subsampling = "4:2:2" if subsampling is None else subsampling
        flatten_background = "#ffffff" if flatten_background is None else flatten_background

        infile_path = Path(infile)
        outfile_path = Path(outfile)
        input_ext = infile_path.suffix.lower()
        input_ext_no_dot = input_ext.lstrip(".")

        if input_ext_no_dot in {"heic", "heif"}:
            _ensure_heif_support()

        # Encode to a temporary JPG first; the keep-or-replace decision below
        # needs the encoded size before anything is committed to outfile.
        outfile_path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(suffix=".jpg", dir=outfile_path.parent)
        os.close(fd)
        tmp_path = Path(tmp_name)

        try:
            with Image.open(infile_path) as im:
                if getattr(im, "is_animated", False):
                    raise RuntimeError(f"Animated images are not supported: {infile_path.name}")

                im = ImageOps.exif_transpose(im)
                icc_profile = im.info.get("icc_profile")

                if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
                    im = im.convert("RGBA")
                    background = Image.new("RGB", im.size, flatten_background)
                    background.paste(im, mask=im.getchannel("A"))
                    im = background
                elif im.mode != "RGB":
                    im = im.convert("RGB")

                if max_width or max_height:
                    im.thumbnail((max_width or im.width, max_height or im.height), Image.Resampling.LANCZOS)

                save_kwargs: dict = {
                    "format": "JPEG",
                    "quality": quality,
                    "progressive": progressive,
                    "subsampling": subsampling,
                    "optimize": True,
                }
                if icc_profile:
                    save_kwargs["icc_profile"] = icc_profile
                im.save(tmp_path, **save_kwargs)

            input_size = infile_path.stat().st_size
            jpg_size = tmp_path.stat().st_size

            always_convert = input_ext_no_dot in FileExtensions.IMAGE_ALWAYS_CONVERT
            if always_convert or jpg_size < input_size:
                # The JPG outcome always lands on a .jpg name, even when the
                # caller planned a different extension (e.g. an explicit
                # --output carrying the original extension).
                final_path = outfile_path.with_suffix(".jpg")
                final_path.unlink(missing_ok=True)
                shutil.move(str(tmp_path), str(final_path))
                with Image.open(final_path) as check:
                    check.verify()
                return final_path

            # Compression did not help: keep the original bytes. Native JPG
            # inputs keep the planned name; other formats keep their extension.
            if input_ext_no_dot in FileExtensions.IMAGE_NATIVE_JPG:
                final_path = outfile_path
            else:
                final_path = outfile_path.with_suffix(input_ext)
            shutil.copy2(infile_path, final_path)
            return final_path
        finally:
            tmp_path.unlink(missing_ok=True)

    return _compress_image_to_jpg(
        infile,
        outfile,
        quality=quality,
        progressive=progressive,
        subsampling=subsampling,
        max_width=max_width,
        max_height=max_height,
        flatten_background=flatten_background,
        config=config,
    )


def compress_image(
    infile: str,
    outfile: str,
    *,
    quality: int = 85,
    max_width: int | None = None,
    max_height: int | None = None,
    convert_to_jpeg: bool = False,
    ffmpeg_path: str = "",
    config: Config | None = None,
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
    from filesqueeze.system.config_adapters import ImageConfig
    from filesqueeze.system.decorators import trace_function

    @trace_function
    def _compress_image(
        infile: str,
        outfile: str,
        *,
        quality: int = 85,
        max_width: int | None = None,
        max_height: int | None = None,
        convert_to_jpeg: bool = False,
        ffmpeg_path: str = "",
        config: Config | None = None,
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
            # NOTE: `quality` arrives on the 1-100 scale from config, but FFmpeg
            # -q:v uses 1-31 where lower is better. Values >31 are clamped by
            # FFmpeg to its worst quality. This legacy path is superseded by
            # compress_image_to_jpg (Pillow), which uses the libjpeg scale.
            cmd.extend(
                [
                    "-q:v",
                    str(quality),
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
            raise RuntimeError(f"FFmpeg timeout compressing image: {infile}") from None
        except SubprocessError:
            raise RuntimeError(f"FFmpeg failed to compress image: {infile}") from None

        # Verify output file exists and meets size requirements
        try:
            verify_output_file(outfile, min_size=min_size)
        except FileNotFoundError:
            raise
        except RuntimeError:
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
