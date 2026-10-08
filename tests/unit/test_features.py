"""Test feature flags (issue #4): selectively enable/disable platform-dependent features.

PPTX-to-video conversion requires Windows (PowerShell COM automation via
PowerShell), so it must be skipped cleanly elsewhere or when disabled in
config.

All filesqueeze imports happen inside the tests, not at module level: the
circular-import tests in tests/system delete filesqueeze modules from
sys.modules, so classes imported at collection time can be different
objects than the ones production code imports lazily at call time.
"""

from pathlib import Path

import pytest


@pytest.fixture
def features():
    """Import filesqueeze.features at call time (see module docstring)."""
    import filesqueeze.features as features_module

    return features_module


@pytest.fixture
def config_factory():
    """Factory for Config objects (imported at call time)."""

    def make(overrides=None):
        from filesqueeze.config import Config

        return Config(overrides or {})

    return make


class TestFeatureValidation:
    """Test feature name validation."""

    def test_known_features_accepted(self, features):
        from filesqueeze.constants import Features

        for feature in Features.ALL:
            features.validate_feature(feature)

    def test_unknown_feature_rejected(self, features):
        with pytest.raises(features.UnknownFeatureError):
            features.validate_feature("nonexistent_feature")


class TestPlatformSupport:
    """Test platform requirement checks."""

    def test_pptx_to_video_requires_windows(self, features):
        from filesqueeze.constants import Features

        assert features.is_platform_supported(Features.PPTX_TO_VIDEO, current_platform="windows")
        assert not features.is_platform_supported(Features.PPTX_TO_VIDEO, current_platform="linux")
        assert not features.is_platform_supported(Features.PPTX_TO_VIDEO, current_platform="macos")

    def test_unknown_feature_raises(self, features):
        with pytest.raises(features.UnknownFeatureError):
            features.is_platform_supported("nonexistent_feature")


class TestIsEnabled:
    """Test the combined platform + config feature resolution."""

    def test_enabled_on_windows_without_config(self, features):
        from filesqueeze.constants import Features

        assert features.is_enabled(Features.PPTX_TO_VIDEO, config=None, current_platform="windows")

    def test_disabled_on_non_windows_without_config(self, features):
        from filesqueeze.constants import Features

        assert not features.is_enabled(Features.PPTX_TO_VIDEO, config=None, current_platform="linux")

    def test_disabled_on_non_windows_even_when_config_enables(self, features, config_factory):
        # Platform capability cannot be overridden by config
        from filesqueeze.constants import Features

        config = config_factory({"features": {"pptx_to_video": True}})
        assert not features.is_enabled(Features.PPTX_TO_VIDEO, config=config, current_platform="linux")

    def test_disabled_by_config_on_supported_platform(self, features, config_factory):
        from filesqueeze.constants import Features

        config = config_factory({"features": {"pptx_to_video": False}})
        assert not features.is_enabled(Features.PPTX_TO_VIDEO, config=config, current_platform="windows")

    def test_default_toml_enables_pptx_to_video(self, features, config_factory):
        # The bundled default.toml enables the feature (platform still applies)
        from filesqueeze.constants import Features

        config = config_factory()
        assert config.get("features.pptx_to_video") is True
        assert features.is_enabled(Features.PPTX_TO_VIDEO, config=config, current_platform="windows")


class TestDisabledReason:
    """Test human-readable disabled reasons."""

    def test_no_reason_when_enabled(self, features):
        from filesqueeze.constants import Features

        assert features.disabled_reason(Features.PPTX_TO_VIDEO, current_platform="windows") is None

    def test_platform_reason_names_requirement(self, features):
        from filesqueeze.constants import Features

        reason = features.disabled_reason(Features.PPTX_TO_VIDEO, current_platform="linux")
        assert reason is not None
        assert "windows" in reason

    def test_config_reason_mentions_key(self, features, config_factory):
        from filesqueeze.constants import Features

        config = config_factory({"features": {"pptx_to_video": False}})
        reason = features.disabled_reason(Features.PPTX_TO_VIDEO, config=config, current_platform="windows")
        assert reason is not None
        assert "features.pptx_to_video" in reason


class TestScannerGating:
    """Test that the scanner skips files belonging to disabled features."""

    def test_pptx_accepted_when_feature_available(self, monkeypatch):
        import filesqueeze.features as features_module
        from filesqueeze.scanner import FileScanner

        monkeypatch.setattr(features_module, "get_platform", lambda: "windows")
        scanner = FileScanner()
        assert scanner.is_valid_extension(Path("deck.pptx"))

    def test_pptx_rejected_when_disabled_by_config(self, config_factory):
        from filesqueeze.scanner import FileScanner

        config = config_factory({"features": {"pptx_to_video": False}})
        scanner = FileScanner(config)
        assert not scanner.is_valid_extension(Path("deck.pptx"))
        assert not scanner.is_valid_extension(Path("deck.ppt"))

    def test_other_extensions_unaffected_by_disabled_feature(self, config_factory):
        from filesqueeze.scanner import FileScanner

        config = config_factory({"features": {"pptx_to_video": False}})
        scanner = FileScanner(config)
        assert scanner.is_valid_extension(Path("clip.mp4"))
        assert scanner.is_valid_extension(Path("doc.pdf"))
        assert scanner.is_valid_extension(Path("photo.jpg"))


class TestHandlerGating:
    """Test that the FSM skips slideshows cleanly when the feature is off."""

    def test_analyze_slideshow_errors_cleanly_when_disabled(self, tmp_path, config_factory):
        from filesqueeze import handlers
        from filesqueeze.fsm import State
        from filesqueeze.fsm.enums import Status

        pptx_file = tmp_path / "deck.pptx"
        pptx_file.write_text("fake pptx content")

        config = config_factory({"features": {"pptx_to_video": False}})
        state = State(pptx_file, config=config)

        result = handlers.analyzeSlideshow(state)

        assert result is handlers.cleanupFiles
        assert state.status == Status.ERROR


class TestToMp4Gate:
    """Test the direct-API gate in ops.presentation.to_mp4."""

    def test_to_mp4_raises_when_disabled_by_config(self, tmp_path, config_factory):
        import filesqueeze.features
        from filesqueeze.ops import presentation

        pptx_file = tmp_path / "deck.pptx"
        pptx_file.write_text("fake pptx content")

        config = config_factory({"features": {"pptx_to_video": False}})
        with pytest.raises(filesqueeze.features.FeatureDisabledError):
            presentation.to_mp4(str(pptx_file), str(tmp_path / "out.mp4"), config=config)
