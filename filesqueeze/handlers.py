import tempfile
from pathlib import Path

from . import ocr
from .constants import Features, FileExtensions
from .fsm import Handler, State
from .fsm.enums import Document, Enum, EnumValue, Format, Slideshow, Video
from .ops import document, image, video
from .ops import presentation as pptx
from .system import logger

# Dotted image extensions (".jpg", ".png", ...) from the undotted constants list
_IMAGE_EXTENSIONS = {f".{ext}" for ext in FileExtensions.IMAGE}
_NATIVE_JPG_EXTENSIONS = {f".{ext}" for ext in FileExtensions.IMAGE_NATIVE_JPG}


def cleanupFiles(state: State) -> Handler | None:
    """
    Final transition of state machine.
    Removes origin file.
    """
    # state.origin.unlink()
    # Only mark as complete if not already in ERROR state
    from .fsm.enums import Status

    if state.status != Status.ERROR:
        state.status_complete()
    return None


def analyzeVideo(state: State) -> Handler:
    """
    Analyses a video file, fills in metadata, and returns an appropriate handler.
    """
    state.status_analyze()
    try:
        duration = video.duration(str(state.target))
        size = video.width_height(str(state.target))
    except Exception:
        state.error("Error during file analysis")
        # No need to terminate; can still proceed without metadata
    else:
        if duration:
            state.metadata["duration"] = duration
        if size:
            state.metadata["width"], state.metadata["height"] = size

    return compressVideo


def analyzeSlideshow(state: State) -> Handler:
    """
    Detects slideshow files and routes them to the PPTX-to-video converter.

    Skips files cleanly when the pptx_to_video feature is disabled
    (unsupported platform or turned off in config).
    """
    from .features import disabled_reason, is_enabled

    state.status_analyze()

    config = getattr(state, "config", None)
    if not is_enabled(Features.PPTX_TO_VIDEO, config=config):
        reason = disabled_reason(Features.PPTX_TO_VIDEO, config=config)
        logger.warning(f"Skipping slideshow {state.target.name}: {reason}")
        state.error(f"PPTX to video is not available: {reason}")
        return cleanupFiles

    state.set_target(state.origin)
    return pptxToVideo


def analyzeDocument(state: State) -> Handler:
    """
    Analyzes a document file (PDF or image), fills in metadata,
    and returns an appropriate handler.
    """
    state.status_analyze()
    try:
        # Get file extension
        ext = state.target.suffix.lower()

        if ext == ".pdf":
            # Check if PDF needs OCR
            config = getattr(state, "config", None)
            if config and ocr.needs_ocr(str(state.target), config):
                state.metadata["needs_ocr"] = True
                logger.info("PDF appears to be scanned (no text layer)")
            else:
                state.metadata["needs_ocr"] = False

            # For PDFs, we could extract metadata here
            # For now, just mark as analyzed
            pass
        elif ext in _IMAGE_EXTENSIONS:
            # Get image dimensions (Pillow first; ffprobe fallback for
            # anything Pillow cannot decode)
            try:
                width, height = image.get_image_dimensions(str(state.target))
            except Exception:
                width, height = image.get_image_size(str(state.target), ffmpeg_path=getattr(state.config, "ffmpeg_path", ""))
            state.metadata["width"] = width
            state.metadata["height"] = height
    except OSError as e:
        # File access errors - log but don't terminate
        logger.debug(f"File access error during analysis: {e}")
        state.metadata["error"] = "Error during document analysis"

    return compressDocument


def compressDocument(state: State) -> Handler:
    """
    Compresses a document file (PDF or image).
    """
    state.status_compress()

    # Get config if available
    config = getattr(state, "config", None)
    ext = state.target.suffix.lower()

    # Determine output path
    output_path = state.get_output_path()
    if output_path:
        outpath = output_path
    else:
        outpath = state.target.parent / f"compressed_{state.target.name}"

    try:
        if ext == ".pdf":
            # Check if PDF needs OCR
            needs_ocr = state.metadata.get("needs_ocr", False)

            if needs_ocr and config and config.get("ocr", {}).get("enable_ocr", True):
                # For scanned PDFs: OCR first, then compress
                logger.info("Processing scanned PDF with OCR...")

                # Create temporary file for OCR'd PDF
                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                    tmp_ocr_path = tmp.name

                try:
                    # Step 1: Run OCR
                    ocr_success, ocr_msg = ocr.process_pdf_with_ocr(
                        str(state.target), tmp_ocr_path, config=config, ocr_only=True
                    )

                    if ocr_success:
                        logger.info(ocr_msg)

                        # Step 2: Compress the OCR'd PDF
                        # Use 'ebook' quality for scanned PDFs (better compression)
                        quality = "ebook"
                        compression_level = config.get("document.pdf_compression_level", 2)
                        gs_path = config.ghostscript_path if config else ""

                        document.compress_pdf(
                            tmp_ocr_path,
                            str(outpath),
                            quality=quality,
                            compression_level=compression_level,
                            ghostscript_path=gs_path,
                        )
                    else:
                        logger.warning("OCR failed, compressing original...")
                        # Fallback: compress original PDF without OCR
                        quality = config.get("document.pdf_quality", "ebook")
                        compression_level = config.get("document.pdf_compression_level", 2)
                        gs_path = config.ghostscript_path if config else ""

                        document.compress_pdf(
                            str(state.target),
                            str(outpath),
                            quality=quality,
                            compression_level=compression_level,
                            ghostscript_path=gs_path,
                        )
                finally:
                    # Clean up temporary OCR file
                    try:
                        Path(tmp_ocr_path).unlink(missing_ok=True)
                    except Exception:
                        pass
            else:
                # For generated PDFs or OCR disabled: compress directly
                quality = config.get("document.pdf_quality", "ebook") if config else "ebook"
                compression_level = config.get("document.pdf_compression_level", 2) if config else 2
                gs_path = config.ghostscript_path if config else ""

                document.compress_pdf(
                    str(state.target),
                    str(outpath),
                    quality=quality,
                    compression_level=compression_level,
                    ghostscript_path=gs_path,
                )

        elif ext in _IMAGE_EXTENSIONS:
            convert_to_jpeg = config.get("document.convert_to_jpeg", True) if config else True

            if ext == ".png" and not convert_to_jpeg:
                # Legacy behaviour: keep PNG output via FFmpeg
                img_quality = config.get("document.image_quality", 85) if config else 85
                max_width = config.get("document.max_image_width", None) if config else None
                max_height = config.get("document.max_image_height", None) if config else None
                ffmpeg_path = config.ffmpeg_path if config else ""

                image.compress_image(
                    str(state.target),
                    str(outpath),
                    quality=img_quality,
                    max_width=max_width,
                    max_height=max_height,
                    convert_to_jpeg=False,
                    ffmpeg_path=ffmpeg_path,
                )
            else:
                # Compress to JPG via Pillow. The planned output is .jpg;
                # compress_image_to_jpg may rewrite the extension when it
                # keeps the original instead of the converted JPG.
                img_quality = config.get("document.image_quality", 88) if config else 88
                max_width = config.get("document.max_image_width", None) if config else None
                max_height = config.get("document.max_image_height", None) if config else None
                progressive = config.get("document.jpeg_progressive", True) if config else True
                subsampling = config.get("document.jpeg_subsampling", "4:2:2") if config else "4:2:2"
                flatten_background = config.get("document.jpeg_flatten_background", "#ffffff") if config else "#ffffff"

                outpath = Path(outpath)
                if ext not in _NATIVE_JPG_EXTENSIONS:
                    outpath = outpath.with_suffix(".jpg")

                outpath = image.compress_image_to_jpg(
                    str(state.target),
                    str(outpath),
                    quality=img_quality,
                    progressive=progressive,
                    subsampling=subsampling,
                    max_width=max_width,
                    max_height=max_height,
                    flatten_background=flatten_background,
                )
        else:
            state.error(f"Unsupported document format: {ext}")
            return cleanupFiles
    except Exception as e:
        state.error(f"Error compressing document: {e}")
        return cleanupFiles
    else:
        state.set_target(outpath)

    return cleanupFiles


def pptxToVideo(state: State) -> Handler:
    """
    Converts a pptx file into a video file, then compresses it.
    """
    state.status_convert()

    # Use output directory for intermediate and final files
    output_dir = state.get_output_path()
    if output_dir:
        # Use the original PPTX stem (not the output_path stem) to avoid double "compressed_" prefix
        original_stem = state.origin.stem  # Use state.origin instead of state.target
        outfile = (output_dir / (original_stem + ".mp4")).as_posix()
    else:
        # Fallback to input directory if no output path configured
        original_stem = state.origin.stem
        outfile = (state.target.parent / (original_stem + ".mp4")).as_posix()

    # Mark this as an intermediate file for cleanup purposes
    state.metadata["intermediate_powerpoint_file"] = outfile

    try:
        pptx.to_mp4(str(state.target), outfile)
    except Exception:
        state.error("Error converting PPTX file")
        # Clean up intermediate MP4 file on failure
        try:
            Path(outfile).unlink(missing_ok=True)
        except Exception:
            pass
        return cleanupFiles
    else:
        state.set_target(outfile)
        # Pass to video compression pipeline (analyzeVideo → compressVideo)
        return analyzeVideo
    return cleanupFiles


def compressVideo(state: State) -> Handler:
    """
    Compresses a video file.
    """
    state.status_compress()

    # Determine output path
    output_path = state.get_output_path()
    if output_path:
        outfile = output_path
    else:
        outfile = state.target.parent.joinpath("compressed_" + state.target.name)

    try:
        video.compress(
            str(state.target),
            str(outfile),
            config=state.config if hasattr(state, "config") else None,
            downscale=(True if state.metadata.get("height", 0) > 720 else False),
        )
    except Exception:
        # Clean up output file on failure
        try:
            Path(outfile).unlink(missing_ok=True)
        except Exception:
            pass
        # Clean up intermediate PowerPoint file if exists
        intermediate_file = state.metadata.get("intermediate_powerpoint_file")
        if intermediate_file:
            try:
                Path(intermediate_file).unlink(missing_ok=True)
            except Exception:
                pass
        state.error("Error compressing MP4 video")
        return cleanupFiles  # Still go to cleanup, but status is ERROR
    else:
        state.set_target(outfile)
        # Clean up intermediate PowerPoint file on successful compression
        intermediate_file = state.metadata.get("intermediate_powerpoint_file")
        if intermediate_file:
            try:
                Path(intermediate_file).unlink(missing_ok=True)
            except Exception:
                pass

    return cleanupFiles


def selectAnalyzer(
    state: State,
    handler: dict[type[Enum] | EnumValue, Handler] | None = None,
) -> Handler:
    """
    First transition of state machine.
    Detects origin format and returns an appropriate handler for analysis.
    """
    if handler is None:
        handler = {
            Video: analyzeVideo,
            Slideshow: analyzeSlideshow,
            Document: analyzeDocument,
        }

    # Map format enums to their handlers
    suffix = state.target.suffix.lstrip(".").upper()  # Enums store file extension in uppercase
    for format_enum in Format:
        # format_enum is now the Video/Slideshow/Document class
        if suffix in format_enum.__dict__:
            # Store the format string value directly
            state.set_format_value(format_enum.__dict__[suffix])
            return handler[format_enum]

    # No matching target format found
    state.error("File type cannot be handled")
    return cleanupFiles
