"""Centralized constants for FileSqueeze configuration keys.

This module provides a single source of truth for all configuration key strings,
eliminating magic strings scattered throughout the codebase and making refactoring
easier and less error-prone.
"""


class ConfigKeys:
    """Centralized configuration key constants.

    These constants provide type-safe access to configuration key paths,
    eliminating typos and making it easier to refactor configuration structure.
    """

    # FFmpeg configuration
    FFMPEG_PATH = "ffmpeg.path"
    FFMPEG_CRF = "ffmpeg.crf"
    FFMPEG_PRESET = "ffmpeg.preset"
    FFMPEG_THREADS = "ffmpeg.threads"

    # Document/PDF configuration
    DOCUMENT_GHOSTSCRIPT_PATH = "document.ghostscript_path"

    # Image configuration
    IMAGE_QUALITY = "image.quality"
    IMAGE_MAX_WIDTH = "image.max_width"
    IMAGE_MAX_HEIGHT = "image.max_height"
    IMAGE_MIN_OUTPUT_SIZE = "image.min_output_size_bytes"

    # OCR/Tesseract configuration
    OCR_TESSERACT_PATH = "ocr.tesseract_path"

    # Presentation configuration
    PRESENTATION_POWERSHELL_PATH = "presentation.powershell_path"

    # Processing configuration
    PROCESSING_TIMEOUT_SECONDS = "processing.timeout_seconds"
    PROCESSING_PRESENTATION_TIMEOUT_SECONDS = "processing.presentation_timeout_seconds"

    # Archive configuration
    ARCHIVE_ENABLED = "archive.enabled"
    ARCHIVE_RETENTION_DAYS = "archive.retention_days"
    ARCHIVE_PATH = "archive.path"


class FileExtensions:
    """File extension constants for type checking and validation."""

    # Video extensions
    VIDEO = ["mp4", "wmv", "avi", "mkv", "mov", "flv"]

    # Document extensions
    DOCUMENT = ["pdf"]

    # Image extensions
    IMAGE = ["jpg", "jpeg", "png"]

    # Presentation extensions
    PRESENTATION = ["ppt", "pptx"]

    # All supported extensions
    ALL_SUPPORTED = VIDEO + DOCUMENT + IMAGE + PRESENTATION


class ErrorMessages:
    """Common error message templates."""

    BINARY_NOT_FOUND = "{binary} not found: {reason}"
    FILE_NOT_FOUND = "File not found: {filepath}"
    CONFIGValidationError = "Invalid configuration value for {config_key}: {value}"
    PROCESSING_TIMEOUT = "Processing timeout for {file_type}: {filepath}"
    OUTPUT_NOT_CREATED = "Output file not created: {filepath}"


class Timeouts:
    """Default timeout values for different operations."""

    BINARY_DETECTION = 5  # seconds
    DEFAULT_PROCESSING = 300  # 5 minutes
    PRESENTATION_CONVERSION = 1800  # 30 minutes
    VIDEO_COMPRESSION = 3600  # 1 hour
    PDF_COMPRESSION = 300  # 5 minutes
    IMAGE_COMPRESSION = 300  # 5 minutes


class FileSizes:
    """File size constants for validation."""

    MIN_OUTPUT_SIZE = 1000  # bytes (1 KB)
    MIN_PDF_SIZE = 100  # bytes
    MIN_IMAGE_SIZE = 1024  # bytes (1 KB)
    MIN_VIDEO_SIZE = 1000  # bytes (1 KB)
