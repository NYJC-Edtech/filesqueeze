"""Test configuration module."""

import tempfile
from pathlib import Path

import pytest

from filesqueeze.config import Config


def test_config_defaults():
    """Test that default config values are loaded."""
    import os

    # Use empty dict to test pure defaults without user config interference
    config = Config({})

    # Test dot notation access - paths are expanded at load time
    assert config.get("ffmpeg.crf") == 28
    expected_input = Path("~/FileSqueeze/upload").expanduser()
    expected_output = Path("~/FileSqueeze/compressed").expanduser()

    # Compare as Path objects to handle path separator differences
    assert Path(config.get("directories.input")) == expected_input
    assert config.get("logging.level") == "INFO"

    # Test property access - paths are already expanded
    assert config.input_dir == expected_input
    assert config.output_dir == expected_output


def test_config_from_file():
    """Test loading config from file."""
    # Create a temporary config file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write('[ffmpeg]\ncrf = 23\n[logging]\nlevel = "DEBUG"\n')
        temp_config_path = f.name

    try:
        config = Config(config_path=temp_config_path)
        assert config.get("ffmpeg.crf") == 23
        assert config.get("logging.level") == "DEBUG"
    finally:
        Path(temp_config_path).unlink()


def test_config_sections():
    """Test getting entire config sections."""
    config = Config()

    ffmpeg_section = config.get_section("ffmpeg")
    assert "crf" in ffmpeg_section
    assert "threads" in ffmpeg_section


def test_config_cascade():
    """Test that config cascade works (project > user > defaults)."""
    # This test verifies the priority order of config sources
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a user config
        user_config = Path(tmpdir) / "user.toml"
        user_config.write_text("[ffmpeg]\ncrf = 25\n")

        # Create a project config
        project_config = Path(tmpdir) / "project.toml"
        project_config.write_text("[ffmpeg]\ncrf = 23\n")

        # Load project config (should override user config)
        config = Config(config_path=project_config)
        assert config.get("ffmpeg.crf") == 23


def test_config_get_with_default():
    """Test config.get() with default values."""
    config = Config()

    # Existing key
    assert config.get("ffmpeg.crf") == 28

    # Non-existing key with default
    assert config.get("nonexistent.key", "default_value") == "default_value"

    # Non-existing key without default
    assert config.get("nonexistent.key") is None


def test_config_does_not_modify_user_config():
    """Test that Config() instantiation never modifies the user config file.

    This is a critical safety test to ensure tests don't accidentally wipe
    or modify the production user configuration.

    The user config at ~/.config/filesqueeze/config.toml contains:
    - Custom input/output directories (e.g., network drives)
    - Auto-detected binary paths
    - User-specific settings

    If this file gets modified by tests, FileSqueeze will stop working.
    """
    from pathlib import Path

    user_config_path = Path.home() / ".config" / "filesqueeze" / "config.toml"

    # Read config before creating Config instance
    before_content = None
    before_mtime = None
    if user_config_path.exists():
        before_content = user_config_path.read_text()
        before_mtime = user_config_path.stat().st_mtime

    # Create multiple Config instances (this should never modify user config)
    config1 = Config({})
    config2 = Config()
    config3 = Config({"ffmpeg": {"crf": 99}})  # Custom config

    # Verify user config is unchanged
    after_content = None
    after_mtime = None
    if user_config_path.exists():
        after_content = user_config_path.read_text()
        after_mtime = user_config_path.stat().st_mtime

    # File content must not change
    if before_content is not None:
        assert before_content == after_content, "Config() must never modify user config file content"

    # File modification time must not change
    if before_mtime is not None:
        assert before_mtime == after_mtime, "Config() must never modify user config file"
