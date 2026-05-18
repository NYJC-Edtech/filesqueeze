import tempfile
from pathlib import Path

from . import ocr
from .fsm import Handler, State
from .fsm.enums import Document, Enum, EnumValue, Format, Slideshow, Video
from .ops import document, image, video
from .ops import presentation as pptx
from .system import logger


def cleanupFiles(state: State) -> Handler | None:
    """
    Final transition of state machine.
    Removes origin file.
    """
    # state.origin.unlink()
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
    TODO: Detect PPTX files that contain a single video.
    For now, does nothing and returns a converter handler.
    """
    state.status_analyze()
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
        elif ext in [".jpg", ".jpeg", ".png"]:
            # Get image dimensions
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

        elif ext in [".jpg", ".jpeg", ".png"]:
            # Compress image
            img_quality = config.get("document.image_quality", 85) if config else 85
            max_width = config.get("document.max_image_width", None) if config else None
            max_height = config.get("document.max_image_height", None) if config else None
            convert_to_jpeg = config.get("document.convert_to_jpeg", False) if config else False
            ffmpeg_path = config.ffmpeg_path if config else ""

            image.compress_image(
                str(state.target),
                str(outpath),
                quality=img_quality,
                max_width=max_width,
                max_height=max_height,
                convert_to_jpeg=convert_to_jpeg,
                ffmpeg_path=ffmpeg_path,
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
    Converts a pptx file into a video file.
    """
    state.status_convert()
    outfile = (state.target.parent / (state.target.stem + ".mp4")).as_posix()
    try:
        pptx.to_mp4(str(state.target), outfile)
    except Exception:
        state.error("Error converting PPTX file")
        # TODO: clean up outfile
    else:
        state.set_target(outfile)
        return selectAnalyzer
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
        # TODO: clean up outfile
        state.error("Error compressing MP4 video")
    else:
        state.set_target(outfile)

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
