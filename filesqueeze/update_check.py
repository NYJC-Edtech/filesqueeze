"""filesqueeze.update_check

Check GitHub for newer FileSqueeze releases.

The check is deliberately conservative: it only ever reports, never downloads
or installs (see filesqueeze.updater for the download/apply half). Every
failure mode — no network, GitHub unreachable, unexpected payload, unparsable
version — resolves to ``None`` so callers can fire-and-forget it in a
background thread at startup.

Results are cached for a few hours in the config directory so repeated starts
(and the standalone compress dialog's own check) do not hammer the
unauthenticated GitHub API (60 requests/hour per IP).
"""

import json
import logging
import os
import re
import time
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

# A fresh cache result suppresses new API calls within this window; anything
# older is ignored (not served stale — a failed network check stays "no info").
CACHE_MAX_AGE_SECONDS = 6 * 3600

_USER_AGENT = "filesqueeze-update-check"

# Release wheels are published as filesqueeze-<version>-py3-none-any.whl
_WHEEL_ASSET_PATTERN = re.compile(r"filesqueeze-(\d+(?:\.\d+)*)-py3-none-any\.whl", re.IGNORECASE)


@dataclass(frozen=True)
class UpdateInfo:
    """A newer release found on GitHub.

    ``wheel_url`` is the direct download URL of the release's wheel asset;
    None when the release publishes no matching wheel (auto-update then
    degrades to opening the releases page).
    """

    current_version: str
    latest_version: str
    download_url: str
    wheel_url: str | None = None


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


def is_dev_checkout() -> bool:
    """Return True when running from a source checkout rather than an installed wheel.

    Dev checkouts must not self-update: the version comes from pyproject.toml
    in the checkout, which a pip install would never replace, so applying a
    release wheel would leave the checkout reporting the old (and still
    "outdated") version forever. Updates happen via git pull instead.
    """
    return (Path(__file__).resolve().parent.parent / "pyproject.toml").exists()


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


def find_wheel_asset(payload: object, tag: str) -> str | None:
    """Return the wheel asset's download URL for ``tag``, or None.

    Matches ``filesqueeze-<tag version>-py3-none-any.whl`` among the release
    assets; the version must equal the tag so a renamed or stale asset is
    never offered for install.
    """
    if not isinstance(payload, dict) or not isinstance(tag, str):
        return None
    assets = payload.get("assets")
    if not isinstance(assets, list):
        return None
    version = tag.strip().lower().removeprefix("v")
    for asset in assets:
        if not isinstance(asset, dict):
            continue
        name = asset.get("name")
        url = asset.get("browser_download_url")
        if not isinstance(name, str) or not isinstance(url, str):
            continue
        match = _WHEEL_ASSET_PATTERN.fullmatch(name.strip())
        if match and match.group(1) == version:
            return url
    return None


def fetch_release_payload(timeout: float = DEFAULT_TIMEOUT_SECONDS) -> dict | None:
    """Return the latest release's GitHub API payload, or None on failure.

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

    if not isinstance(payload, dict):
        logger.debug("Release check response was not an object: %r", payload)
        return None
    return payload


def fetch_latest_release(timeout: float = DEFAULT_TIMEOUT_SECONDS) -> str | None:
    """Return the latest published release version (tag) from GitHub, or None on failure."""
    payload = fetch_release_payload(timeout=timeout)
    if payload is None:
        return None
    tag = payload.get("tag_name")
    if not isinstance(tag, str) or not tag.strip():
        logger.debug("Release check response had no usable tag_name: %r", payload)
        return None
    return tag.strip()


def _cache_path() -> Path | None:
    """Return the update-check cache file path, or None when caching is off.

    Dev checkouts and test runs never touch user state (mirrors the dev-mode
    mutex split in tray.py); FILEQUEEZE_UPDATE_CACHE overrides the location
    for tests and unusual setups.
    """
    if os.getenv("PYTEST_CURRENT_TEST") is not None or os.getenv("FILEQUEEZE_DEV_MODE") == "1":
        return None
    override = os.getenv("FILEQUEEZE_UPDATE_CACHE")
    if override:
        return Path(override)
    return Path.home() / ".config" / "filesqueeze" / "update_cache.json"


def _read_cache(cache_path: Path | None) -> tuple[str, str | None] | None:
    """Return (latest_tag, wheel_url) from a fresh-enough cache file, or None."""
    if cache_path is None:
        return None
    try:
        raw = json.loads(cache_path.read_text(encoding="utf-8"))
        checked_at = float(raw["checked_at"])
        tag = raw["tag"]
        if not isinstance(tag, str) or not tag.strip():
            return None
        if time.time() - checked_at > CACHE_MAX_AGE_SECONDS:
            logger.debug("Update cache is stale (older than %ss)", CACHE_MAX_AGE_SECONDS)
            return None
        wheel_url = raw.get("wheel_url")
        return tag.strip(), wheel_url if isinstance(wheel_url, str) else None
    except (OSError, ValueError, KeyError, TypeError):
        logger.debug("Ignoring unreadable update cache: %s", cache_path)
        return None


def _write_cache(cache_path: Path | None, tag: str, wheel_url: str | None) -> None:
    """Persist a successful check so later starts can skip the API call."""
    if cache_path is None:
        return
    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"checked_at": time.time(), "tag": tag, "wheel_url": wheel_url}
        cache_path.write_text(json.dumps(payload), encoding="utf-8")
    except OSError:
        logger.debug("Could not write update cache: %s", cache_path, exc_info=True)


def check_for_updates(
    config: Config | None = None,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    use_cache: bool = True,
    cache_path: Path | None = None,
) -> UpdateInfo | None:
    """Check GitHub for a release newer than the running version.

    Args:
        config: Optional Config; when it disables ``updates.check_on_startup``,
            no request is made.
        timeout: Network timeout for the GitHub request.
        use_cache: Reuse a recent check result instead of hitting the API again.
        cache_path: Override the cache location (tests); None means the default.

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

    if cache_path is None:
        cache_path = _cache_path()

    cached = _read_cache(cache_path if use_cache else None)
    if cached is not None:
        latest, wheel_url = cached
        logger.debug("Using cached update check result: %s", latest)
    else:
        payload = fetch_release_payload(timeout=timeout)
        if payload is None:
            return None
        latest = payload.get("tag_name") if isinstance(payload.get("tag_name"), str) else None
        if not latest or not latest.strip():
            logger.debug("Release check response had no usable tag_name: %r", payload)
            return None
        latest = latest.strip()
        wheel_url = find_wheel_asset(payload, latest)
        _write_cache(cache_path, latest, wheel_url)

    if not is_newer(latest, current):
        return None

    return UpdateInfo(current_version=current, latest_version=latest, download_url=RELEASES_PAGE_URL, wheel_url=wheel_url)


# Outcomes of a user-requested check (run_manual_check). Unlike the startup
# check — which is silent on anything but a find — a manual check must tell
# the user WHY nothing was announced: offline, disabled, or up to date.
MANUAL_CHECK_DISABLED = "disabled"
MANUAL_CHECK_ERROR = "error"
MANUAL_CHECK_UP_TO_DATE = "up_to_date"
MANUAL_CHECK_UPDATE_AVAILABLE = "update_available"


def run_manual_check(config: Config | None = None, timeout: float = DEFAULT_TIMEOUT_SECONDS) -> tuple[str, UpdateInfo | None]:
    """Run a fresh, user-requested update check and classify the outcome.

    Never uses the cache (the user asked for a fresh answer) and never
    raises. Returns ``(status, update_info)``; update_info is set only for
    MANUAL_CHECK_UPDATE_AVAILABLE.
    """
    if config is not None and not config.get("updates.check_on_startup", True):
        return MANUAL_CHECK_DISABLED, None

    current = get_current_version()
    if current is None:
        return MANUAL_CHECK_ERROR, None

    payload = fetch_release_payload(timeout=timeout)
    if payload is None:
        return MANUAL_CHECK_ERROR, None

    tag = payload.get("tag_name")
    if not isinstance(tag, str) or not tag.strip():
        logger.debug("Manual check response had no usable tag_name: %r", payload)
        return MANUAL_CHECK_ERROR, None
    tag = tag.strip()

    if not is_newer(tag, current):
        return MANUAL_CHECK_UP_TO_DATE, None

    return MANUAL_CHECK_UPDATE_AVAILABLE, UpdateInfo(
        current_version=current,
        latest_version=tag,
        download_url=RELEASES_PAGE_URL,
        wheel_url=find_wheel_asset(payload, tag),
    )
