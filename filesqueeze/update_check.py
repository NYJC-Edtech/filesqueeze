"""filesqueeze.update_check

Check GitHub for newer FileSqueeze releases.

The check is deliberately conservative: it only ever reports, never downloads
or installs (see the auto-update issue for the planned v0.9.3 work). Every
failure mode — no network, GitHub unreachable, unexpected payload, unparsable
version — resolves to ``None`` so callers can fire-and-forget it in a
background thread at startup.
"""

import json
import logging
import tomllib
import urllib.error
import urllib.request
from dataclasses import dataclass
from importlib import metadata
from pathlib import Path

from .config import Config

logger = logging.getLogger(__name__)

GITHUB_REPO = "NYJC-Edtech/filesqueeze"
LATEST_RELEASE_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
# GitHub redirects this to the latest release's page; stable permalink for "get the new version"
RELEASES_PAGE_URL = f"https://github.com/{GITHUB_REPO}/releases/latest"

DEFAULT_TIMEOUT_SECONDS = 5.0

_USER_AGENT = "filesqueeze-update-check"


@dataclass(frozen=True)
class UpdateInfo:
    """A newer release found on GitHub."""

    current_version: str
    latest_version: str
    download_url: str


def get_current_version() -> str | None:
    """Return the running FileSqueeze version, or None when it cannot be determined.

    A dev checkout is preferred over installed package metadata: the checkout
    may carry a freshly bumped version while the editable-install metadata is
    stale. Production installs (pip install from a wheel) have no pyproject.toml
    next to the package and fall through to importlib.metadata.
    """
    pyproject = Path(__file__).resolve().parent.parent / "pyproject.toml"
    try:
        with open(pyproject, "rb") as f:
            version = tomllib.load(f)["project"]["version"]
        return str(version)
    except (OSError, KeyError, tomllib.TOMLDecodeError, TypeError):
        pass

    try:
        return metadata.version("filesqueeze")
    except Exception:
        logger.debug("Could not determine the running FileSqueeze version", exc_info=True)
        return None


def parse_version(version: str) -> tuple[int, ...] | None:
    """Parse a version string into a comparable tuple of integers.

    Accepts an optional ``v`` prefix and drops any pre-release (``-``) or
    build (``+``) suffix, so ``v0.9.2`` and ``0.9.2-beta.1`` both parse to
    ``(0, 9, 2)``. Returns None for unparsable input.

    Note: pre-release versions compare as equal to their final release; the
    project does not publish pre-releases, so this is acceptable here.
    """
    if not isinstance(version, str):
        return None
    core = version.strip().lower().removeprefix("v").split("-", 1)[0].split("+", 1)[0]
    parts = core.split(".")
    if not parts or not all(part.isdigit() for part in parts):
        return None
    return tuple(int(part) for part in parts)


def is_newer(latest: str, current: str) -> bool:
    """Return True when ``latest`` is a strictly newer release than ``current``.

    Numeric comparison with zero-padding, so ``0.9`` and ``0.9.0`` are equal.
    Unparsable versions are never reported as updates.
    """
    latest_parsed = parse_version(latest)
    current_parsed = parse_version(current)
    if latest_parsed is None or current_parsed is None:
        return False
    width = max(len(latest_parsed), len(current_parsed))
    latest_padded = latest_parsed + (0,) * (width - len(latest_parsed))
    current_padded = current_parsed + (0,) * (width - len(current_parsed))
    return latest_padded > current_padded


def fetch_latest_release(timeout: float = DEFAULT_TIMEOUT_SECONDS) -> str | None:
    """Return the latest published release version from GitHub, or None on failure.

    Uses the unauthenticated GitHub releases API (no dependencies added);
    failures — network down, HTTP errors, rate limits, unexpected payloads —
    are logged at debug level and returned as None.
    """
    try:
        request = urllib.request.Request(
            LATEST_RELEASE_API_URL,
            headers={"Accept": "application/vnd.github+json", "User-Agent": _USER_AGENT},
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.load(response)
    except (urllib.error.URLError, OSError, ValueError) as e:
        logger.debug("Release check against %s failed: %s", LATEST_RELEASE_API_URL, e)
        return None

    tag = payload.get("tag_name") if isinstance(payload, dict) else None
    if not isinstance(tag, str) or not tag.strip():
        logger.debug("Release check response had no usable tag_name: %r", payload)
        return None
    return tag.strip()


def check_for_updates(config: Config | None = None, timeout: float = DEFAULT_TIMEOUT_SECONDS) -> UpdateInfo | None:
    """Check GitHub for a release newer than the running version.

    Args:
        config: Optional Config; when it disables ``updates.check_on_startup``,
            no request is made.
        timeout: Network timeout for the GitHub request.

    Returns:
        UpdateInfo when a newer release is available, otherwise None
        (disabled, offline, up to date, or anything failed).
    """
    if config is not None and not config.get("updates.check_on_startup", True):
        logger.debug("Update check disabled by configuration")
        return None

    current = get_current_version()
    if current is None:
        return None

    latest = fetch_latest_release(timeout=timeout)
    if latest is None or not is_newer(latest, current):
        return None

    return UpdateInfo(current_version=current, latest_version=latest, download_url=RELEASES_PAGE_URL)
