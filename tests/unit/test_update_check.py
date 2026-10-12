"""Unit tests for filesqueeze.update_check (release check, v0.9.2).

Imports of ``filesqueeze`` happen INSIDE the test functions: the circular-import
system tests delete sys.modules entries, and a module-level import would bind a
stale module object while unittest.mock's patch() re-imports a fresh one.
"""

import io
import json
import urllib.error
from unittest.mock import patch


def _api_response(payload) -> io.BytesIO:
    """Build a fake urlopen() context-manager return value."""
    return io.BytesIO(json.dumps(payload).encode("utf-8"))


def _release_payload(tag: str = "v0.9.2", wheel_version: str | None = None) -> dict:
    """Build a GitHub latest-release payload with one wheel asset."""
    version = wheel_version or tag.lower().removeprefix("v")
    return {
        "tag_name": tag,
        "assets": [
            {
                "name": f"filesqueeze-{version}-py3-none-any.whl",
                "browser_download_url": f"https://example.com/filesqueeze-{version}-py3-none-any.whl",
            }
        ],
    }


class TestParseVersion:
    def test_parses_plain_version(self):
        from filesqueeze.update_check import parse_version

        assert parse_version("0.9.1") == (0, 9, 1)

    def test_parses_v_prefix(self):
        from filesqueeze.update_check import parse_version

        assert parse_version("v0.9.2") == (0, 9, 2)

    def test_drops_prerelease_and_build_suffixes(self):
        from filesqueeze.update_check import parse_version

        assert parse_version("0.9.3-beta.1") == (0, 9, 3)
        assert parse_version("v1.0.0+build.42") == (1, 0, 0)

    def test_rejects_non_numeric_and_empty(self):
        from filesqueeze.update_check import parse_version

        assert parse_version("abc") is None
        assert parse_version("0.9.x") is None
        assert parse_version("") is None
        assert parse_version(None) is None


class TestIsNewer:
    def test_newer_patch_minor_major(self):
        from filesqueeze.update_check import is_newer

        assert is_newer("0.9.2", "0.9.1")
        assert is_newer("0.10.0", "0.9.9")
        assert is_newer("1.0.0", "0.99.99")

    def test_same_version_is_not_newer(self):
        from filesqueeze.update_check import is_newer

        assert not is_newer("0.9.1", "0.9.1")
        assert not is_newer("v0.9.1", "0.9.1")

    def test_older_is_not_newer(self):
        from filesqueeze.update_check import is_newer

        assert not is_newer("0.9.0", "0.9.1")

    def test_zero_padded_component_comparison(self):
        from filesqueeze.update_check import is_newer

        assert is_newer("0.9.1", "0.9")  # "0.9" == "0.9.0"
        assert not is_newer("0.9", "0.9.0")

    def test_unparsable_versions_never_newer(self):
        from filesqueeze.update_check import is_newer

        assert not is_newer("oops", "0.9.1")
        assert not is_newer("0.9.2", "oops")


class TestFetchLatestRelease:
    def test_returns_tag_name(self):
        with patch("filesqueeze.update_check.urllib.request.urlopen") as mock_open:
            mock_open.return_value.__enter__.return_value = _api_response({"tag_name": "v0.9.2"})

            from filesqueeze.update_check import fetch_latest_release

            assert fetch_latest_release() == "v0.9.2"

    def test_returns_none_on_http_error(self):
        with patch(
            "filesqueeze.update_check.urllib.request.urlopen",
            side_effect=urllib.error.HTTPError("url", 403, "rate limited", None, None),
        ):
            from filesqueeze.update_check import fetch_latest_release

            assert fetch_latest_release() is None

    def test_returns_none_on_network_error(self):
        with patch(
            "filesqueeze.update_check.urllib.request.urlopen",
            side_effect=urllib.error.URLError("no route to host"),
        ):
            from filesqueeze.update_check import fetch_latest_release

            assert fetch_latest_release() is None

    def test_returns_none_on_unexpected_payload(self):
        for payload in [{}, {"tag_name": ""}, "not a dict", None]:
            with patch("filesqueeze.update_check.urllib.request.urlopen") as mock_open:
                mock_open.return_value.__enter__.return_value = _api_response(payload)

                from filesqueeze.update_check import fetch_latest_release

                assert fetch_latest_release() is None, f"payload {payload!r} should yield None"


class TestGetCurrentVersion:
    def test_reads_pyproject_in_dev_checkout(self):
        from filesqueeze.update_check import get_current_version, parse_version

        # The test run happens in the repo, so pyproject.toml is the live version
        version = get_current_version()
        assert version is not None
        assert parse_version(version) is not None

    def test_falls_back_to_package_metadata(self):
        with patch("filesqueeze.update_check.open", side_effect=OSError("not a checkout")):
            with patch("filesqueeze.update_check.metadata.version", return_value="9.9.9"):
                from filesqueeze.update_check import get_current_version

                assert get_current_version() == "9.9.9"

    def test_returns_none_when_undeterminable(self):
        with patch("filesqueeze.update_check.open", side_effect=OSError("not a checkout")):
            with patch("filesqueeze.update_check.metadata.version", side_effect=Exception("no metadata")):
                from filesqueeze.update_check import get_current_version

                assert get_current_version() is None


class TestCheckForUpdates:
    def test_returns_update_info_when_newer_release_exists(self):
        from filesqueeze.config import Config

        with (
            patch("filesqueeze.update_check.get_current_version", return_value="0.9.1"),
            patch("filesqueeze.update_check.fetch_release_payload", return_value=_release_payload("v0.9.2")),
        ):
            from filesqueeze.update_check import RELEASES_PAGE_URL, UpdateInfo, check_for_updates

            info = check_for_updates(Config({"updates": {"check_on_startup": True}}))

        assert info == UpdateInfo(
            current_version="0.9.1",
            latest_version="v0.9.2",
            download_url=RELEASES_PAGE_URL,
            wheel_url="https://example.com/filesqueeze-0.9.2-py3-none-any.whl",
        )
        assert "github.com" in info.download_url

    def test_wheel_url_is_none_when_release_has_no_wheel(self):
        from filesqueeze.config import Config
        from filesqueeze.update_check import check_for_updates

        payload = {
            "tag_name": "v0.9.2",
            "assets": [{"name": "notes.txt", "browser_download_url": "https://example.com/notes.txt"}],
        }
        with (
            patch("filesqueeze.update_check.get_current_version", return_value="0.9.1"),
            patch("filesqueeze.update_check.fetch_release_payload", return_value=payload),
        ):
            info = check_for_updates(Config({"updates": {"check_on_startup": True}}))

        assert info is not None
        assert info.wheel_url is None

    def test_returns_none_when_up_to_date(self):
        from filesqueeze.config import Config
        from filesqueeze.update_check import check_for_updates

        with (
            patch("filesqueeze.update_check.get_current_version", return_value="0.9.2"),
            patch("filesqueeze.update_check.fetch_release_payload", return_value=_release_payload("v0.9.2")),
        ):
            assert check_for_updates(Config({"updates": {"check_on_startup": True}})) is None

    def test_returns_none_when_disabled(self):
        from filesqueeze.config import Config
        from filesqueeze.update_check import check_for_updates

        with patch("filesqueeze.update_check.fetch_release_payload") as mock_fetch:
            assert check_for_updates(Config({"updates": {"check_on_startup": False}})) is None
            mock_fetch.assert_not_called()

    def test_returns_none_when_github_unreachable(self):
        from filesqueeze.config import Config
        from filesqueeze.update_check import check_for_updates

        with (
            patch("filesqueeze.update_check.get_current_version", return_value="0.9.1"),
            patch("filesqueeze.update_check.fetch_release_payload", return_value=None),
        ):
            assert check_for_updates(Config({"updates": {"check_on_startup": True}})) is None


class TestFindWheelAsset:
    def test_finds_matching_wheel(self):
        from filesqueeze.update_check import find_wheel_asset

        assert (
            find_wheel_asset(_release_payload("v0.9.2"), "v0.9.2") == "https://example.com/filesqueeze-0.9.2-py3-none-any.whl"
        )

    def test_ignores_asset_with_wrong_version(self):
        from filesqueeze.update_check import find_wheel_asset

        assert find_wheel_asset(_release_payload("v0.9.2", wheel_version="0.9.1"), "v0.9.2") is None

    def test_ignores_non_wheel_assets(self):
        from filesqueeze.update_check import find_wheel_asset

        payload = {
            "tag_name": "v0.9.2",
            "assets": [{"name": "filesqueeze-0.9.2.zip", "browser_download_url": "https://example.com/x.zip"}],
        }
        assert find_wheel_asset(payload, "v0.9.2") is None

    def test_handles_missing_or_malformed_assets(self):
        from filesqueeze.update_check import find_wheel_asset

        assert find_wheel_asset({}, "v0.9.2") is None
        assert find_wheel_asset({"assets": "nope"}, "v0.9.2") is None
        assert find_wheel_asset({"assets": [{"name": "filesqueeze-0.9.2-py3-none-any.whl"}]}, "v0.9.2") is None
        assert find_wheel_asset(None, "v0.9.2") is None


class TestCheckResultCache:
    def test_successful_check_writes_cache_and_reuse_skips_the_api(self, tmp_path):
        from filesqueeze.update_check import RELEASES_PAGE_URL, UpdateInfo, check_for_updates

        cache_file = tmp_path / "update_cache.json"
        with (
            patch("filesqueeze.update_check.get_current_version", return_value="0.9.1"),
            patch("filesqueeze.update_check.fetch_release_payload", return_value=_release_payload("v0.9.2")) as mock_fetch,
        ):
            first = check_for_updates(cache_path=cache_file)
            second = check_for_updates(cache_path=cache_file)

        assert mock_fetch.call_count == 1  # second check was served from the cache
        assert first == second
        assert first == UpdateInfo(
            current_version="0.9.1",
            latest_version="v0.9.2",
            download_url=RELEASES_PAGE_URL,
            wheel_url="https://example.com/filesqueeze-0.9.2-py3-none-any.whl",
        )

    def test_stale_cache_is_refetched(self, tmp_path):
        import time

        from filesqueeze.update_check import CACHE_MAX_AGE_SECONDS, check_for_updates

        cache_file = tmp_path / "update_cache.json"
        stale = {"checked_at": time.time() - CACHE_MAX_AGE_SECONDS - 60, "tag": "v0.9.2", "wheel_url": None}
        cache_file.write_text(json.dumps(stale), encoding="utf-8")

        with (
            patch("filesqueeze.update_check.get_current_version", return_value="0.9.1"),
            patch("filesqueeze.update_check.fetch_release_payload", return_value=_release_payload("v0.9.3")) as mock_fetch,
        ):
            info = check_for_updates(cache_path=cache_file)

        mock_fetch.assert_called_once()
        assert info is not None and info.latest_version == "v0.9.3"

    def test_corrupt_cache_is_ignored(self, tmp_path):
        from filesqueeze.update_check import check_for_updates

        cache_file = tmp_path / "update_cache.json"
        cache_file.write_text("not json", encoding="utf-8")

        with (
            patch("filesqueeze.update_check.get_current_version", return_value="0.9.1"),
            patch("filesqueeze.update_check.fetch_release_payload", return_value=_release_payload("v0.9.2")) as mock_fetch,
        ):
            info = check_for_updates(cache_path=cache_file)

        mock_fetch.assert_called_once()
        assert info is not None

    def test_use_cache_false_bypasses_a_fresh_cache(self, tmp_path):
        from filesqueeze.update_check import check_for_updates

        cache_file = tmp_path / "update_cache.json"
        with patch("filesqueeze.update_check.fetch_release_payload", return_value=_release_payload("v0.9.2")) as mock_fetch:
            check_for_updates(cache_path=cache_file)
            check_for_updates(cache_path=cache_file, use_cache=False)

        assert mock_fetch.call_count == 2

    def test_no_cache_path_means_no_caching_between_calls(self):
        # Under pytest the default cache location resolves to None (never touch
        # user state from tests), so repeated checks each hit the (mocked) API.
        from filesqueeze.update_check import _cache_path, check_for_updates

        assert _cache_path() is None

        with (
            patch("filesqueeze.update_check.get_current_version", return_value="0.9.1"),
            patch("filesqueeze.update_check.fetch_release_payload", return_value=_release_payload("v0.9.2")) as mock_fetch,
        ):
            check_for_updates()
            check_for_updates()

        assert mock_fetch.call_count == 2


class TestIsDevCheckout:
    def test_true_when_pyproject_sits_next_to_the_package(self):
        from filesqueeze.update_check import is_dev_checkout

        # Test runs execute from the repo checkout
        assert is_dev_checkout() is True

    def test_false_for_installed_layout(self):
        from unittest.mock import MagicMock

        from filesqueeze.update_check import is_dev_checkout

        fake_root = MagicMock()
        fake_root.resolve.return_value.parent.parent.__truediv__.return_value.exists.return_value = False
        with patch("filesqueeze.update_check.Path", return_value=fake_root):
            assert is_dev_checkout() is False


class TestRunManualCheck:
    """The user-requested check classifies every outcome instead of staying silent."""

    def test_returns_update_info_when_newer_release_exists(self):
        with (
            patch("filesqueeze.update_check.get_current_version", return_value="0.9.2"),
            patch("filesqueeze.update_check.fetch_release_payload", return_value=_release_payload("v0.9.3")),
            patch("filesqueeze.update_check._read_cache", return_value=None) as mock_read,
            patch("filesqueeze.update_check._write_cache") as mock_write,
        ):
            from filesqueeze.update_check import (
                MANUAL_CHECK_UPDATE_AVAILABLE,
                RELEASES_PAGE_URL,
                run_manual_check,
            )

            status, info = run_manual_check()

        assert status == MANUAL_CHECK_UPDATE_AVAILABLE
        assert info is not None
        assert info.latest_version == "v0.9.3"
        assert info.current_version == "0.9.2"
        assert info.download_url == RELEASES_PAGE_URL
        assert info.wheel_url is not None and info.wheel_url.endswith("filesqueeze-0.9.3-py3-none-any.whl")
        # A manual check is always fresh: the cache is neither read nor written
        mock_read.assert_not_called()
        mock_write.assert_not_called()

    def test_returns_up_to_date_when_latest_matches_installed(self):
        with (
            patch("filesqueeze.update_check.get_current_version", return_value="0.9.2"),
            patch("filesqueeze.update_check.fetch_release_payload", return_value=_release_payload("v0.9.2")),
        ):
            from filesqueeze.update_check import MANUAL_CHECK_UP_TO_DATE, run_manual_check

            status, info = run_manual_check()

        assert status == MANUAL_CHECK_UP_TO_DATE
        assert info is None

    def test_returns_error_when_github_is_unreachable(self):
        with (
            patch("filesqueeze.update_check.get_current_version", return_value="0.9.2"),
            patch("filesqueeze.update_check.fetch_release_payload", return_value=None),
        ):
            from filesqueeze.update_check import MANUAL_CHECK_ERROR, run_manual_check

            status, info = run_manual_check()

        assert status == MANUAL_CHECK_ERROR
        assert info is None

    def test_returns_error_when_running_version_is_unknown(self):
        with patch("filesqueeze.update_check.get_current_version", return_value=None):
            from filesqueeze.update_check import MANUAL_CHECK_ERROR, run_manual_check

            status, info = run_manual_check()

        assert status == MANUAL_CHECK_ERROR
        assert info is None

    def test_returns_disabled_without_touching_the_network(self):
        from filesqueeze.config import Config

        with patch("filesqueeze.update_check.fetch_release_payload") as mock_fetch:
            from filesqueeze.update_check import MANUAL_CHECK_DISABLED, run_manual_check

            status, info = run_manual_check(Config({"updates": {"check_on_startup": False}}))

        assert status == MANUAL_CHECK_DISABLED
        assert info is None
        mock_fetch.assert_not_called()
