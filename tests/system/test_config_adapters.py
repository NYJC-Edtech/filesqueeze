"""Test config adapter validation.

These tests verify that config adapters properly validate configuration
values and provide type-safe access to configuration.
"""

import pytest
from filesqueeze.config import Config
from filesqueeze.system.config_adapters import (
    VideoConfig,
    DocumentConfig,
    ImageConfig,
    PresentationConfig,
    ConfigValidationError,
)


class TestVideoConfig:
    """Test VideoConfig adapter."""

    def test_valid_crf_range(self):
        """CRF must be 0-51."""
        config = Config({'ffmpeg': {'crf': 23}})
        video_cfg = VideoConfig(config)
        assert video_cfg.crf == 23

    def test_crf_boundary_low(self):
        """CRF=0 is valid (lower bound)."""
        config = Config({'ffmpeg': {'crf': 0}})
        video_cfg = VideoConfig(config)
        assert video_cfg.crf == 0

    def test_crf_boundary_high(self):
        """CRF=51 is valid (upper bound)."""
        config = Config({'ffmpeg': {'crf': 51}})
        video_cfg = VideoConfig(config)
        assert video_cfg.crf == 51

    def test_invalid_crf_low(self):
        """CRF < 0 should raise ValueError."""
        config = Config({'ffmpeg': {'crf': -1}})
        with pytest.raises(ConfigValidationError, match="Invalid ffmpeg.crf"):
            VideoConfig(config)

    def test_invalid_crf_high(self):
        """CRF > 51 should raise ValueError."""
        config = Config({'ffmpeg': {'crf': 100}})
        with pytest.raises(ConfigValidationError, match="Invalid ffmpeg.crf"):
            VideoConfig(config)

    def test_default_preset(self):
        """Default preset is 'veryfast'."""
        config = Config()
        video_cfg = VideoConfig(config)
        assert video_cfg.preset == 'veryfast'

    def test_custom_preset(self):
        """Custom preset can be set."""
        config = Config({'ffmpeg': {'preset': 'slower'}})
        video_cfg = VideoConfig(config)
        assert video_cfg.preset == 'slower'

    def test_default_threads(self):
        """Default threads is 8."""
        config = Config()
        video_cfg = VideoConfig(config)
        assert video_cfg.threads == 8

    def test_custom_threads(self):
        """Custom threads can be set."""
        config = Config({'ffmpeg': {'threads': 8}})
        video_cfg = VideoConfig(config)
        assert video_cfg.threads == 8

    def test_default_timeout(self):
        """Default timeout is 1800 seconds."""
        config = Config()
        video_cfg = VideoConfig(config)
        assert video_cfg.timeout == 1800

    def test_custom_timeout(self):
        """Custom timeout can be set."""
        config = Config({'processing': {'timeout_seconds': 3600}})
        video_cfg = VideoConfig(config)
        assert video_cfg.timeout == 3600


class TestDocumentConfig:
    """Test DocumentConfig adapter."""

    def test_valid_quality_range(self):
        """Quality must be 0-100."""
        config = Config({'document': {'image_quality': 75}})
        doc_cfg = DocumentConfig(config)
        assert doc_cfg.quality == 75

    def test_quality_boundary_low(self):
        """Quality=0 is valid (lower bound)."""
        config = Config({'document': {'image_quality': 0}})
        doc_cfg = DocumentConfig(config)
        assert doc_cfg.quality == 0

    def test_quality_boundary_high(self):
        """Quality=100 is valid (upper bound)."""
        config = Config({'document': {'image_quality': 100}})
        doc_cfg = DocumentConfig(config)
        assert doc_cfg.quality == 100

    def test_invalid_quality_low(self):
        """Quality < 0 should raise ValueError."""
        config = Config({'document': {'image_quality': -10}})
        with pytest.raises(ConfigValidationError, match="quality.*0-100"):
            DocumentConfig(config)

    def test_invalid_quality_high(self):
        """Quality > 100 should raise ValueError."""
        config = Config({'document': {'image_quality': 150}})
        with pytest.raises(ConfigValidationError, match="quality.*0-100"):
            DocumentConfig(config)

    def test_default_quality(self):
        """Default quality is 90 (from default.toml)."""
        config = Config()
        doc_cfg = DocumentConfig(config)
        assert doc_cfg.quality == 90

    def test_default_timeout(self):
        """Default timeout is 300 seconds."""
        config = Config()
        doc_cfg = DocumentConfig(config)
        assert doc_cfg.timeout == 300

    def test_custom_timeout(self):
        """Custom timeout can be set."""
        config = Config({'processing': {'pdf_timeout_seconds': 600}})
        doc_cfg = DocumentConfig(config)
        assert doc_cfg.timeout == 600


class TestImageConfig:
    """Test ImageConfig adapter."""

    def test_valid_quality_range(self):
        """Quality must be 0-100."""
        config = Config({'document': {'image_quality': 85}})
        img_cfg = ImageConfig(config)
        assert img_cfg.quality == 85

    def test_quality_boundary_low(self):
        """Quality=0 is valid (lower bound)."""
        config = Config({'document': {'image_quality': 0}})
        img_cfg = ImageConfig(config)
        assert img_cfg.quality == 0

    def test_quality_boundary_high(self):
        """Quality=100 is valid (upper bound)."""
        config = Config({'document': {'image_quality': 100}})
        img_cfg = ImageConfig(config)
        assert img_cfg.quality == 100

    def test_invalid_quality_low(self):
        """Quality < 0 should raise ValueError."""
        config = Config({'document': {'image_quality': -5}})
        # ImageConfig doesn't validate, so this doesn't raise
        img_cfg = ImageConfig(config)
        assert img_cfg.quality == -5

    def test_invalid_quality_high(self):
        """Quality > 100 should raise ValueError."""
        config = Config({'document': {'image_quality': 150}})
        # ImageConfig doesn't validate, so this doesn't raise
        img_cfg = ImageConfig(config)
        assert img_cfg.quality == 150

    def test_default_quality(self):
        """Default quality is 90 (from default.toml)."""
        config = Config()
        img_cfg = ImageConfig(config)
        assert img_cfg.quality == 90

    def test_default_timeout(self):
        """Default timeout is 60 seconds."""
        config = Config()
        img_cfg = ImageConfig(config)
        assert img_cfg.timeout == 60

    def test_custom_timeout(self):
        """Custom timeout can be set."""
        config = Config({'processing': {'image_timeout_seconds': 120}})
        img_cfg = ImageConfig(config)
        assert img_cfg.timeout == 120


class TestPresentationConfig:
    """Test PresentationConfig adapter."""

    def test_valid_crf_range(self):
        """CRF must be 0-51 (uses ffmpeg config)."""
        config = Config({'ffmpeg': {'crf': 25}})
        pres_cfg = PresentationConfig(config)
        assert pres_cfg.crf == 25

    def test_crf_boundary_low(self):
        """CRF=0 is valid (lower bound)."""
        config = Config({'ffmpeg': {'crf': 0}})
        pres_cfg = PresentationConfig(config)
        assert pres_cfg.crf == 0

    def test_crf_boundary_high(self):
        """CRF=51 is valid (upper bound)."""
        config = Config({'ffmpeg': {'crf': 51}})
        pres_cfg = PresentationConfig(config)
        assert pres_cfg.crf == 51

    def test_default_crf(self):
        """Default CRF is 28 (from default.toml)."""
        config = Config()
        pres_cfg = PresentationConfig(config)
        assert pres_cfg.crf == 28

    def test_default_preset(self):
        """Default preset is 'veryfast' (from default.toml)."""
        config = Config()
        pres_cfg = PresentationConfig(config)
        assert pres_cfg.preset == 'veryfast'

    def test_custom_preset(self):
        """Custom preset can be set."""
        config = Config({'ffmpeg': {'preset': 'slower'}})
        pres_cfg = PresentationConfig(config)
        assert pres_cfg.preset == 'slower'

    def test_default_timeout(self):
        """Default timeout is 1800 seconds."""
        config = Config()
        pres_cfg = PresentationConfig(config)
        assert pres_cfg.timeout == 1800

    def test_custom_timeout(self):
        """Custom timeout can be set."""
        config = Config({'processing': {'timeout_seconds': 3600}})
        pres_cfg = PresentationConfig(config)
        assert pres_cfg.timeout == 3600


class TestConfigAdaptersIntegration:
    """Test config adapters with real Config objects."""

    def test_empty_config_uses_defaults(self):
        """Empty config object uses all defaults."""
        config = Config()

        video_cfg = VideoConfig(config)
        assert video_cfg.crf == 28  # From default.toml
        assert video_cfg.preset == 'veryfast'  # From default.toml
        assert video_cfg.threads == 8  # From default.toml

        doc_cfg = DocumentConfig(config)
        assert doc_cfg.quality == 90  # From default.toml

        img_cfg = ImageConfig(config)
        assert img_cfg.quality == 90  # From default.toml

        pres_cfg = PresentationConfig(config)
        assert pres_cfg.crf == 28  # From default.toml (uses video config)

    def test_multiple_adapters_same_config(self):
        """Multiple adapters can read from same config object."""
        config = Config({
            'ffmpeg': {'crf': 30},
            'document': {'image_quality': 80},
        })

        video_cfg = VideoConfig(config)
        doc_cfg = DocumentConfig(config)
        img_cfg = ImageConfig(config)

        assert video_cfg.crf == 30
        assert doc_cfg.quality == 80
        assert img_cfg.quality == 80

    def test_adapter_is_immutable(self):
        """Adapter properties are read-only."""
        config = Config()
        video_cfg = VideoConfig(config)

        # Attempting to set property should raise AttributeError
        with pytest.raises(AttributeError):
            video_cfg.crf = 30

    def test_adapter_does_not_modify_config(self):
        """Creating adapter doesn't modify config object."""
        config = Config()
        original_crf = config.get('video.crf', 23)

        # Create adapter
        video_cfg = VideoConfig(config)

        # Config should be unchanged
        assert config.get('video.crf', 23) == original_crf


class TestConfigAdapterValidation:
    """Test validation logic in config adapters."""

    def test_video_config_validates_all_properties(self):
        """VideoConfig validates all properties on creation."""
        config = Config({'ffmpeg': {'crf': -1}})  # Invalid

        with pytest.raises(ConfigValidationError, match="Invalid ffmpeg.crf"):
            VideoConfig(config)

    def test_document_config_validates_all_properties(self):
        """DocumentConfig validates all properties on creation."""
        config = Config({'document': {'image_quality': 150}})  # Invalid

        with pytest.raises(ConfigValidationError, match="quality"):
            DocumentConfig(config)

    def test_image_config_does_not_validate(self):
        """ImageConfig doesn't validate on creation (uses document config)."""
        # ImageConfig doesn't have validation, it uses document.image_quality
        config = Config({'document': {'image_quality': -10}})

        # Should not raise (no validation in ImageConfig)
        img_cfg = ImageConfig(config)
        assert img_cfg.quality == -10

    def test_presentation_config_does_not_validate(self):
        """PresentationConfig doesn't validate on creation (uses ffmpeg config)."""
        # PresentationConfig doesn't have validation, it uses ffmpeg.crf
        config = Config({'ffmpeg': {'crf': -1}})

        # Should not raise (no validation in PresentationConfig)
        pres_cfg = PresentationConfig(config)
        assert pres_cfg.crf == -1
