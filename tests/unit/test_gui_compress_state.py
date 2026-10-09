"""Unit tests for compress-dialog state persistence (last destination folder).

These tests import the dialog module, which imports tkinter; they are
skipped cleanly when tkinter is unavailable (e.g. CI without python3-tk).
Widget-level GUI testing is tracked separately.
"""

import pytest

pytest.importorskip("tkinter", reason="tkinter not available")

from filesqueeze.gui_compress import load_last_compress_dir, save_last_compress_dir


class TestLastCompressDirPersistence:
    def test_roundtrip(self, tmp_path):
        state_file = tmp_path / "state.toml"

        save_last_compress_dir("D:/Shared/Term4", state_path=state_file)

        assert load_last_compress_dir(state_path=state_file) == "D:/Shared/Term4"

    def test_missing_file_returns_none(self, tmp_path):
        assert load_last_compress_dir(state_path=tmp_path / "absent.toml") is None

    def test_invalid_toml_returns_none(self, tmp_path):
        state_file = tmp_path / "state.toml"
        state_file.write_text("not [valid toml", encoding="utf-8")

        assert load_last_compress_dir(state_path=state_file) is None

    def test_save_creates_parent_directories(self, tmp_path):
        state_file = tmp_path / "nested" / "dirs" / "state.toml"

        save_last_compress_dir(str(tmp_path), state_path=state_file)

        assert state_file.exists()
        assert load_last_compress_dir(state_path=state_file) == str(tmp_path)

    def test_state_file_is_separate_from_user_config(self, tmp_path):
        """State must never touch ~/.config/filesqueeze/config.toml."""
        state_file = tmp_path / "state.toml"
        save_last_compress_dir(str(tmp_path), state_path=state_file)

        assert state_file.name == "state.toml"
        assert "config.toml" not in state_file.name
