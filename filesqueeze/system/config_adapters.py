"""Type-safe configuration adapters.

Provides validated, type-safe access to configuration values
for each operation type (video, document, image, presentation).
"""

from typing import Optional
from filesqueeze.config import Config


class ConfigValidationError(ValueError):
    """Raised when config value fails validation."""

    pass


class VideoConfig:
    """Adapter for video operation configuration.

    Provides validated access to video-related config values.
    """

    def __init__(self, config: Config):
        """Initialize video config adapter.

        Args:
            config: FileSqueeze configuration object

        Raises:
            ConfigValidationError: If config values are invalid
        """
        self._config = config
        # Validate on construction
        self._validate()

    def _validate(self) -> None:
        """Validate all video config values.

        Raises:
            ConfigValidationError: If any value is out of range
        """
        crf = self._config.get("ffmpeg.crf", 28)
        if not isinstance(crf, (int, float)) or not (0 <= crf <= 51):
            raise ConfigValidationError(f"Invalid ffmpeg.crf: {crf}. Must be 0-51.")

        preset = self._config.get("ffmpeg.preset", "veryfast")
        valid_presets = ["ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"]
        if preset not in valid_presets:
            raise ConfigValidationError(f"Invalid ffmpeg.preset: {preset}. Must be one of {valid_presets}")

    @property
    def crf(self) -> int:
        """Get CRF value (0-51).

        Lower = better quality, larger file. Recommended: 18-28.
        """
        return int(self._config.get("ffmpeg.crf", 28))

    @property
    def preset(self) -> str:
        """Get ffmpeg preset."""
        return self._config.get("ffmpeg.preset", "veryfast")

    @property
    def threads(self) -> int:
        """Get thread count."""
        return int(self._config.get("ffmpeg.threads", 8))

    @property
    def max_height(self) -> int:
        """Get maximum video height."""
        return int(self._config.get("ffmpeg.max_height", 720))

    @property
    def audio_bitrate(self) -> str:
        """Get audio bitrate."""
        return self._config.get("ffmpeg.audio_bitrate", "96k")

    @property
    def timeout(self) -> int:
        """Get timeout in seconds."""
        return int(self._config.get("processing.timeout_seconds", 1800))

    @property
    def min_output_size_bytes(self) -> int:
        """Get minimum output file size in bytes."""
        return int(self._config.get("processing.min_output_size_bytes", 4096))


class DocumentConfig:
    """Adapter for document operation configuration.

    Provides validated access to document-related config values.
    """

    def __init__(self, config: Config):
        """Initialize document config adapter.

        Args:
            config: FileSqueeze configuration object

        Raises:
            ConfigValidationError: If config values are invalid
        """
        self._config = config
        self._validate()

    def _validate(self) -> None:
        """Validate all document config values.

        Raises:
            ConfigValidationError: If any value is out of range
        """
        quality = self._config.get("document.image_quality", 90)
        if not isinstance(quality, (int, float)) or not (0 <= quality <= 100):
            raise ConfigValidationError(f"Invalid document.image_quality: {quality}. Must be 0-100.")

    @property
    def pdf_quality(self) -> str:
        """Get PDF quality setting."""
        return self._config.get("document.pdf_quality", "printer")

    @property
    def pdf_compression_level(self) -> int:
        """Get PDF compression level (0-4)."""
        return int(self._config.get("document.pdf_compression_level", 2))

    @property
    def quality(self) -> int:
        """Get image quality (0-100)."""
        return int(self._config.get("document.image_quality", 90))

    @property
    def max_image_width(self) -> int:
        """Get maximum image width."""
        return int(self._config.get("document.max_image_width", 1920))

    @property
    def max_image_height(self) -> int:
        """Get maximum image height."""
        return int(self._config.get("document.max_image_height", 1080))

    @property
    def convert_to_jpeg(self) -> bool:
        """Get whether to convert PNG to JPEG."""
        return bool(self._config.get("document.convert_to_jpeg", False))

    @property
    def timeout(self) -> int:
        """Get timeout in seconds."""
        return int(self._config.get("processing.pdf_timeout_seconds", 300))


class ImageConfig:
    """Adapter for image operation configuration.

    Provides validated access to image-related config values.
    """

    def __init__(self, config: Config):
        """Initialize image config adapter.

        Args:
            config: FileSqueeze configuration object

        Raises:
            ConfigValidationError: If config values are invalid
        """
        self._config = config
        # Note: Image config uses document.image_quality in current config
        # This adapter will be used when we split image operations

    @property
    def quality(self) -> int:
        """Get JPEG quality (0-100)."""
        return int(self._config.get("document.image_quality", 90))

    @property
    def max_width(self) -> int:
        """Get maximum image width."""
        return int(self._config.get("document.max_image_width", 1920))

    @property
    def max_height(self) -> int:
        """Get maximum image height."""
        return int(self._config.get("document.max_image_height", 1080))

    @property
    def timeout(self) -> int:
        """Get timeout in seconds."""
        return int(self._config.get("processing.image_timeout_seconds", 60))

    @property
    def min_output_size_bytes(self) -> int:
        """Get minimum output file size in bytes."""
        return int(self._config.get("processing.min_output_size_bytes", 4096))


class PresentationConfig:
    """Adapter for presentation operation configuration.

    Provides validated access to presentation-related config values.
    """

    def __init__(self, config: Config):
        """Initialize presentation config adapter.

        Args:
            config: FileSqueeze configuration object

        Raises:
            ConfigValidationError: If config values are invalid
        """
        self._config = config
        # Note: Presentations use video config values (crf, preset)

    @property
    def crf(self) -> int:
        """Get CRF value for presentation video (0-51)."""
        return int(self._config.get("ffmpeg.crf", 28))

    @property
    def preset(self) -> str:
        """Get ffmpeg preset for presentation."""
        return self._config.get("ffmpeg.preset", "veryfast")

    @property
    def timeout(self) -> int:
        """Get timeout in seconds."""
        return int(self._config.get("processing.timeout_seconds", 1800))
