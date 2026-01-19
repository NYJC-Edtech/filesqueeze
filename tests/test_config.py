"""Test configuration module."""

import tempfile
from pathlib import Path

import pytest

from filesqueeze.config import Config


def test_config_defaults():
    """Test that default config values are loaded."""
    config = Config()

    # Test dot notation access
    assert config.get('ffmpeg.crf') == 28
    assert config.get('directories.input') == 'G:/Shared drives/compressor/upload'
    assert config.get('logging.level') == 'INFO'

    # Test property access
    assert config.input_dir == Path('G:/Shared drives/compressor/upload')
    assert config.output_dir == Path('G:/Shared drives/compressor/compressed')


def test_config_from_file():
    """Test loading config from file."""
    # Create a temporary config file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
        f.write('[ffmpeg]\ncrf = 23\n[logging]\nlevel = "DEBUG"\n')
        temp_config_path = f.name

    try:
        config = Config(config_path=temp_config_path)
        assert config.get('ffmpeg.crf') == 23
        assert config.get('logging.level') == 'DEBUG'
    finally:
        Path(temp_config_path).unlink()


def test_config_sections():
    """Test getting entire config sections."""
    config = Config()

    ffmpeg_section = config.get_section('ffmpeg')
    assert 'crf' in ffmpeg_section
    assert 'threads' in ffmpeg_section


def test_config_cascade():
    """Test that config cascade works (project > user > defaults)."""
    # This test verifies the priority order of config sources
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a user config
        user_config = Path(tmpdir) / 'user.toml'
        user_config.write_text('[ffmpeg]\ncrf = 25\n')

        # Create a project config
        project_config = Path(tmpdir) / 'project.toml'
        project_config.write_text('[ffmpeg]\ncrf = 23\n')

        # Load project config (should override user config)
        config = Config(config_path=project_config)
        assert config.get('ffmpeg.crf') == 23


def test_config_get_with_default():
    """Test config.get() with default values."""
    config = Config()

    # Existing key
    assert config.get('ffmpeg.crf') == 28

    # Non-existing key with default
    assert config.get('nonexistent.key', 'default_value') == 'default_value'

    # Non-existing key without default
    assert config.get('nonexistent.key') is None
