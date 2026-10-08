"""filesqueeze.features

Feature flags for selectively enabling platform-dependent features.

Some capabilities rely on platform-specific tooling - e.g. PPTX-to-video
conversion drives Microsoft PowerPoint through COM automation via
PowerShell, which only exists on Windows. Feature flags let FileSqueeze
disable such features cleanly (files are skipped, not failed) instead of
crashing mid-processing.

A feature is enabled when BOTH of these hold:

1. The current platform satisfies the feature's platform requirement.
   This check cannot be overridden by config - a feature that cannot run
   on the current OS is always off.
2. The config does not turn it off via ``features.<name> = false``.

See ``[features]`` in ``default.toml`` for the user-facing switches.
"""

from typing import TYPE_CHECKING

from .constants import Features
from .system.platform import get_platform

if TYPE_CHECKING:
    from .config import Config


class FeatureError(RuntimeError):
    """Base class for feature flag errors."""


class UnknownFeatureError(FeatureError):
    """Raised when referencing a feature name that is not registered."""


class FeatureDisabledError(FeatureError):
    """Raised when an operation requires a feature that is not enabled."""


# Feature name -> required platform (as returned by system.platform.get_platform()).
# Features absent from this map run on every platform.
PLATFORM_REQUIREMENTS: dict[str, str] = {
    Features.PPTX_TO_VIDEO: "windows",
}


def validate_feature(feature: str) -> None:
    """Check that a feature name is registered.

    Args:
        feature: Feature name (see ``constants.Features``).

    Raises:
        UnknownFeatureError: If the feature name is not registered.
    """
    if feature not in Features.ALL:
        known = ", ".join(sorted(Features.ALL))
        raise UnknownFeatureError(f"Unknown feature: {feature!r} (known features: {known})")


def is_platform_supported(feature: str, current_platform: str | None = None) -> bool:
    """Check whether the current platform can run a feature.

    Args:
        feature: Feature name (see ``constants.Features``).
        current_platform: Override for the detected platform (for tests);
            defaults to ``system.platform.get_platform()``.

    Returns:
        True if the platform satisfies the feature's requirement.

    Raises:
        UnknownFeatureError: If the feature name is not registered.
    """
    validate_feature(feature)
    required = PLATFORM_REQUIREMENTS.get(feature)
    if required is None:
        return True
    return (current_platform or get_platform()) == required


def is_enabled(feature: str, config: "Config | None" = None, current_platform: str | None = None) -> bool:
    """Check whether a feature is enabled.

    A feature is enabled when the platform supports it and the config has
    not disabled it. With no config, the platform check alone decides.

    Args:
        feature: Feature name (see ``constants.Features``).
        config: Optional Config object; ``features.<name>`` is consulted.
        current_platform: Override for the detected platform (for tests).

    Returns:
        True if the feature is enabled, False otherwise.

    Raises:
        UnknownFeatureError: If the feature name is not registered.
    """
    if not is_platform_supported(feature, current_platform):
        return False
    if config is not None:
        return bool(config.get(f"features.{feature}", True))
    return True


def disabled_reason(feature: str, config: "Config | None" = None, current_platform: str | None = None) -> str | None:
    """Explain why a feature is disabled, or None if it is enabled.

    Args:
        feature: Feature name (see ``constants.Features``).
        config: Optional Config object; ``features.<name>`` is consulted.
        current_platform: Override for the detected platform (for tests).

    Returns:
        Human-readable reason string, or None if the feature is enabled.

    Raises:
        UnknownFeatureError: If the feature name is not registered.
    """
    validate_feature(feature)
    if not is_platform_supported(feature, current_platform):
        required = PLATFORM_REQUIREMENTS[feature]
        return f"{feature} requires {required} (current platform: {current_platform or get_platform()})"
    if config is not None and not bool(config.get(f"features.{feature}", True)):
        return f"{feature} is disabled in config (features.{feature} = false)"
    return None
