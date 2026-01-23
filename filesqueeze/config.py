"""filesqueeze.config

Configuration management for FileSqueeze.
Supports config cascade: CLI args → project config → user config → defaults.
"""

import logging
import os
from pathlib import Path
from typing import Any, Optional

try:
    import tomllib  # Python 3.11+
except ImportError:
    import tomli as tomllib  # Python < 3.11


class Config:
    """Configuration manager with dot-notation access and default values."""

    # Default configuration values
    DEFAULTS = {
        'directories': {
            'input': '~/FileSqueeze/upload',
            'output': '~/FileSqueeze/compressed',
        },
        'file_detection': {
            'extensions': ['mp4', 'avi', 'wmv', 'pptx', 'pdf', 'jpg', 'jpeg', 'png'],
            'min_age_seconds': 60,
            'min_size_bytes': 1024,  # 1KB
        },
        'ffmpeg': {
            'path': '',  # empty = use PATH
            'crf': 28,
            'threads': 8,
            'preset': 'veryfast',
            'max_height': 720,
            'audio_bitrate': '96k',
        },
        'document': {
            'ghostscript_path': '',  # empty = use PATH
            'pdf_quality': 'printer',  # screen, ebook, printer, prepress, default
            'pdf_compression_level': 2,
            'image_quality': 90,
            'max_image_width': 1920,
            'max_image_height': 1080,
            'convert_to_jpeg': False,
        },
        'processing': {
            'timeout_seconds': 1800,
            'lock_timeout_seconds': 300,
            'max_retries': 2,
        },
        'logging': {
            'level': 'INFO',
            'file': '~/.config/filesqueeze/filesqueeze.log',
            'max_bytes': 10485760,  # 10MB
            'backup_count': 5,
            'format': 'detailed',  # simple, detailed, json
        },
        'output': {
            'structure': 'flat',  # flat, by_type, by_date, mirror
            'preserve_timestamps': True,
            'save_metadata': False,
        },
    }

    def __init__(self, config_path: Optional[str | Path | dict] = None):
        """Initialize configuration.

        Args:
            config_path: Optional path to a specific config file, or a dict with config values.
                        If not provided, will search for config files.
        """
        self._config = {}
        self._load_configs(config_path)

    def _load_configs(self, config_path: Optional[str | Path | dict]) -> None:
        """Load configurations from all sources in priority order.

        Priority (highest to lowest):
        1. Environment variables (FILESQUEEZE_*)
        2. Config file (if provided)
        3. User config (~/.config/filesqueeze/config.toml)
        4. Project config (./filesqueeze.toml)
        5. DEFAULTS
        """
        # Start with defaults
        self._config = self._deep_copy(self.DEFAULTS)

        # If config_path is a dict, merge it directly (for testing)
        if isinstance(config_path, dict):
            self._merge_dict(config_path)
            self._apply_env_overrides()
            return

        # Load user config
        user_config_path = Path.home() / '.config' / 'filesqueeze' / 'config.toml'
        if user_config_path.exists():
            self._merge_toml(user_config_path)

        # Load project config
        if config_path:
            project_config = Path(config_path)
        else:
            project_config = Path.cwd() / 'filesqueeze.toml'

        if project_config.exists():
            self._merge_toml(project_config)

        # Apply environment variable overrides (highest priority)
        self._apply_env_overrides()

    def _merge_toml(self, path: Path) -> None:
        """Merge TOML config file into current config."""
        try:
            with open(path, 'rb') as f:
                data = tomllib.load(f)
            self._deep_merge(self._config, data)
        except Exception as e:
            logging.getLogger('filesqueeze').warning(f"Failed to load config from {path}: {e}")

    def _merge_dict(self, data: dict) -> None:
        """Merge dict directly into current config (for testing)."""
        self._deep_merge(self._config, data)

    def _deep_merge(self, base: dict, update: dict) -> None:
        """Deep merge update dict into base dict."""
        for key, value in update.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value

    def _deep_copy(self, data: dict) -> dict:
        """Create a deep copy of a dictionary."""
        import copy
        return copy.deepcopy(data)

    def _apply_env_overrides(self) -> None:
        """Apply environment variable overrides to configuration.

        Supported environment variables:
        - FILESQUEEZE_INPUT_DIR: Override input directory
        - FILESQUEEZE_OUTPUT_DIR: Override output directory
        - FILESQUEEZE_LOG_FILE: Override log file path

        Environment variables take precedence over all other config sources.
        """
        env_overrides = {
            'FILESQUEEZE_INPUT_DIR': ('directories', 'input'),
            'FILESQUEEZE_OUTPUT_DIR': ('directories', 'output'),
            'FILESQUEEZE_LOG_FILE': ('logging', 'file'),
        }

        for env_var, (section, key) in env_overrides.items():
            value = os.getenv(env_var)
            if value:
                # Ensure section exists
                if section not in self._config:
                    self._config[section] = {}
                self._config[section][key] = value
                logging.getLogger('filesqueeze').info(
                    f"Config override from {env_var}: {value}"
                )

    def get(self, key: str, default: Any = None) -> Any:
        """Get config value using dot notation.

        Examples:
            config.get('ffmpeg.crf')
            config.get('directories.input')
        """
        keys = key.split('.')
        value = self._config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def get_section(self, section: str) -> dict:
        """Get entire config section."""
        return self._config.get(section, {})

    @property
    def input_dir(self) -> Path:
        """Get input directory path."""
        return Path(self.get('directories.input'))

    @property
    def output_dir(self) -> Path:
        """Get output directory path."""
        return Path(self.get('directories.output'))

    @property
    def ffmpeg_path(self) -> str:
        """Get FFmpeg path (empty if using PATH)."""
        return self.get('ffmpeg.path', '')

    @property
    def ghostscript_path(self) -> str:
        """Get Ghostscript path (empty if using PATH)."""
        return self.get('document.ghostscript_path', '')

    def as_dict(self) -> dict:
        """Return entire config as dictionary."""
        return self._deep_copy(self._config)

    def __repr__(self) -> str:
        return f"Config({self._config!r})"
