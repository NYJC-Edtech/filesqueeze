"""filesqueeze.config

Configuration management for FileSqueeze.
Supports config cascade: CLI args → project config → user config → defaults.

Path Expansion Policy:
All path values containing ~ (tilde) or environment variables are expanded
once during config initialization. This ensures that config.get() always
returns expanded, ready-to-use paths, eliminating the need for expanduser()
calls throughout the codebase.
"""

import os
from pathlib import Path
from typing import Any, Optional

try:
    import tomllib  # Python 3.11+
except ImportError:
    import tomli as tomllib  # Python < 3.11

from .system import logger


class Config:
    """Configuration manager with dot-notation access and default values.

    Configuration loading cascade (priority low to high):
    1. default.toml (bundled with package) - Base defaults
    2. ~/.config/filesqueeze/config.toml - User config
    3. ./filesqueeze.toml - Project config
    4. FILESQUEEZE_* environment variables - Runtime overrides
    """

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
        5. default.toml (bundled with package)
        """
        # Load default.toml as base configuration
        self._config = self._load_default_config()

        # If config_path is a dict, merge it directly (for testing)
        if isinstance(config_path, dict):
            self._merge_dict(config_path)
            self._apply_env_overrides()
            self._expand_paths()
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

        # Expand all paths (tilde and environment variables)
        self._expand_paths()

    def _load_default_config(self) -> dict:
        """Load default.toml from installed package.

        This is the single source of truth for default configuration values.
        If default.toml cannot be found, it indicates a broken installation.

        Returns:
            Dictionary containing default configuration.

        Raises:
            RuntimeError: If default.toml is missing from installation.
        """

        # Strategy 1: Try importlib.resources (Python 3.7+)
        # This works for installed packages and is the recommended approach
        try:
            import importlib.resources
            import importlib

            package = importlib.import_module('filesqueeze')
            with importlib.resources.files(package).joinpath('default.toml').open('rb') as f:
                return tomllib.load(f)
        except Exception:
            # Strategy 2: Fallback to __file__ for development/edge cases
            # Catch any exception from importlib.resources (OSError, TypeError, etc.)
            default_path = Path(__file__).parent / 'default.toml'
            if default_path.exists():
                with open(default_path, 'rb') as f:
                    return tomllib.load(f)

        # If we get here, default.toml is missing - this is an installation error
        logger.error(
            "CRITICAL: default.toml not found in FileSqueeze installation.\n"
            "This indicates a broken or incomplete installation.\n\n"
            "Searched in:\n"
            f"  - Package resources (importlib.resources)\n"
            f"  - {Path(__file__).parent / 'default.toml'}\n\n"
            "To fix this issue:\n"
            "  1. Reinstall FileSqueeze: pip install --force-reinstall filesqueeze\n"
            "  2. Or if using the development version, ensure default.toml exists in the filesqueeze package directory\n"
        )

        raise RuntimeError(
            "FileSqueeze installation error: default.toml not found.\n"
            "Please reinstall: pip install --force-reinstall filesqueeze"
        )

    def _merge_toml(self, path: Path) -> None:
        """Merge TOML config file into current config."""
        try:
            with open(path, 'rb') as f:
                data = tomllib.load(f)
            self._deep_merge(self._config, data)
        except Exception as e:
            logger.warning(f"Failed to load config from {path}: {e}")

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
                logger.info(
                    f"Config override from {env_var}: {value}"
                )

    def _expand_paths(self) -> None:
        """Expand ~ and environment variables in all path config values.

        This is called once during config initialization to ensure all paths
        are expanded and ready to use. Callers can use config.get() directly
        without needing to call Path.expanduser() or os.path.expanduser().

        Path keys that are expanded:
        - directories.input, directories.output
        - logging.file
        - ffmpeg.path
        - document.ghostscript_path
        - ocr.tesseract_path

        Design rationale:
        Expanding at load time (rather than on each access) provides:
        1. Single source of truth - config.get() always returns expanded paths
        2. No need to remember to call expanduser() throughout the codebase
        3. Avoids bugs where unexpanded tildes create directories literally named '~'
        """
        path_keys = [
            ('directories', 'input'),
            ('directories', 'output'),
            ('logging', 'file'),
            ('ffmpeg', 'path'),
            ('document', 'ghostscript_path'),
            ('ocr', 'tesseract_path'),
        ]

        for section, key in path_keys:
            path_str = self.get(f'{section}.{key}')
            if path_str and isinstance(path_str, str):
                # Expand both ~ (home directory) and %VAR% or $VAR environment vars
                expanded = os.path.expanduser(os.path.expandvars(path_str))
                if section not in self._config:
                    self._config[section] = {}
                self._config[section][key] = expanded

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
        """Get input directory path.

        Note: Paths are expanded at config load time, so this returns
        an expanded Path ready for use.
        """
        path_str = self.get('directories.input')
        return Path(path_str)

    @property
    def output_dir(self) -> Path:
        """Get output directory path.

        Note: Paths are expanded at config load time, so this returns
        an expanded Path ready for use.
        """
        path_str = self.get('directories.output')
        return Path(path_str)

    @property
    def archive_dir(self) -> Optional[Path]:
        """Get archive directory path for original files after compression.

        Returns None if archive is disabled (empty string in config).
        Otherwise returns Path object (expanded).

        Note: Paths are expanded at config load time, so this returns
        an expanded Path ready for use.
        """
        path_str = self.get('directories.archive', 'archive')
        if not path_str or path_str.strip() == '':
            return None
        return Path(path_str)

    @property
    def ffmpeg_path(self) -> str:
        """Get FFmpeg path (empty if using PATH)."""
        return self.get('ffmpeg.path', '')

    @property
    def ghostscript_path(self) -> str:
        """Get Ghostscript path (empty if using PATH)."""
        return self.get('document.ghostscript_path', '')

    @property
    def log_file(self) -> Path:
        """Get log file path as Path object.

        Note: Paths are expanded at config load time, so this returns
        an expanded Path ready for use.
        """
        path_str = self.get('logging.file')
        return Path(path_str)

    @property
    def tesseract_path(self) -> Path:
        """Get Tesseract OCR path as Path object.

        Returns Path object for Tesseract executable, or Path('tesseract')
        if using system PATH.

        Note: This property should be used when Tesseract path is needed
        for Path operations. For subprocess calls, convert to str().
        """
        path_str = self.get('ocr.tesseract_path', '')
        return Path(path_str) if path_str else Path('tesseract')

    def as_dict(self) -> dict:
        """Return entire config as dictionary."""
        return self._deep_copy(self._config)

    def __repr__(self) -> str:
        return f"Config({self._config!r})"
