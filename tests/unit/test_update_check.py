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
            patch("filesqueeze.update_check.fetch_latest_release", return_value="v0.9.2"),
        ):
            from filesqueeze.update_check import RELEASES_PAGE_URL, UpdateInfo, check_for_updates

            info = check_for_updates(Config({"updates": {"check_on_startup": True}}))

        assert info == UpdateInfo(current_version="0.9.1", latest_version="v0.9.2", download_url=RELEASES_PAGE_URL)
        assert "github.com" in info.download_url

    def test_returns_none_when_up_to_date(self):
        from filesqueeze.config import Config
        from filesqueeze.update_check import check_for_updates

        with (
            patch("filesqueeze.update_check.get_current_version", return_value="0.9.2"),
            patch("filesqueeze.update_check.fetch_latest_release", return_value="v0.9.2"),
        ):
            assert check_for_updates(Config({"updates": {"check_on_startup": True}})) is None

    def test_returns_none_when_disabled(self):
        from filesqueeze.config import Config
        from filesqueeze.update_check import check_for_updates

        with patch("filesqueeze.update_check.fetch_latest_release") as mock_fetch:
            assert check_for_updates(Config({"updates": {"check_on_startup": False}})) is None
            mock_fetch.assert_not_called()

    def test_returns_none_when_github_unreachable(self):
        from filesqueeze.config import Config
        from filesqueeze.update_check import check_for_updates

        with (
            patch("filesqueeze.update_check.get_current_version", return_value="0.9.1"),
            patch("filesqueeze.update_check.fetch_latest_release", return_value=None),
        ):
            assert check_for_updates(Config({"updates": {"check_on_startup": True}})) is None
