"""filesqueeze.logger

Logging configuration for FileSqueeze.
Dual handlers: StreamHandler (stdout) + RotatingFileHandler or TimedRotatingFileHandler.

This module now re-exports the system logger for backward compatibility.
"""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from pathlib import Path
from typing import Optional

from .config import Config

# Re-export system logger for backward compatibility
from .system.logger import register_logger, get_logger as system_get_logger
from .system import logger as system_logger_module


# Create a module-level logger proxy object
# This allows the logger module to behave like the old logger module
class _ModuleLoggerProxy:
    """Proxy that mimics the old logger module interface."""

    def __init__(self):
        self._cached_logger = None

    def _get_logger(self):
        """Get the actual logger, caching for performance."""
        if self._cached_logger is None:
            self._cached_logger = system_logger_module.get_logger()
        return self._cached_logger

    def info(self, msg, *args, **kwargs):
        """Log info message."""
        return self._get_logger().info(msg, *args, **kwargs)

    def debug(self, msg, *args, **kwargs):
        """Log debug message."""
        return self._get_logger().debug(msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        """Log warning message."""
        return self._get_logger().warning(msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        """Log error message."""
        return self._get_logger().error(msg, *args, **kwargs)

    def critical(self, msg, *args, **kwargs):
        """Log critical message."""
        return self._get_logger().critical(msg, *args, **kwargs)

    def exception(self, msg, *args, **kwargs):
        """Log exception message."""
        return self._get_logger().exception(msg, *args, **kwargs)

    def __getattr__(self, name):
        """Delegate any other attributes to the actual logger."""
        return getattr(self._get_logger(), name)

    def __repr__(self):
        """String representation."""
        return f"<ModuleLoggerProxy delegating to {self._get_logger().name}>"


# Create the proxy instance
_logger_proxy = _ModuleLoggerProxy()

# Export common logging methods at module level for backward compatibility
info = _logger_proxy.info
debug = _logger_proxy.debug
warning = _logger_proxy.warning
error = _logger_proxy.error
critical = _logger_proxy.critical
exception = _logger_proxy.exception


class Logger:
    """Logger manager with dual output (console + file)."""

    # Log format templates
    FORMATS = {
        "simple": "%(levelname)s: %(message)s",
        "detailed": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        "json": "%(asctime)s %(name)s %(levelname)s %(message)s",
    }

    @staticmethod
    def setup(
        config: Optional[Config] = None,
        log_file: Optional[str | Path] = None,
        level: str = "INFO",
        format_type: str = "detailed",
        max_bytes: int = 10485760,
        backup_count: int = 5,
        rotation_type: str = "size",
        when: str = "midnight",
        interval: int = 1,
    ) -> logging.Logger:
        """Set up logging with console and file handlers.

        Args:
            config: Config object (will override other parameters if provided)
            log_file: Path to log file
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            format_type: Format type (simple, detailed, json)
            max_bytes: Max size of each log file before rotation (for size-based rotation)
            backup_count: Number of backup files to keep
            rotation_type: Type of rotation - 'size' or 'time'
            when: When to rotate for time-based ('S'=Seconds, 'M'=Minutes, 'H'=Hours, 'D'=Days, 'midnight'=Daily)
            interval: Interval for rotation (e.g., 1 = every day, 7 = every week)

        Returns:
            Configured logger instance
        """
        # Get settings from config if provided
        if config:
            log_file = log_file or config.get("logging.file")
            level = level or config.get("logging.level", "INFO")
            format_type = format_type or config.get("logging.format", "detailed")
            max_bytes = max_bytes or config.get("logging.max_bytes", 10485760)
            backup_count = backup_count or config.get("logging.backup_count", 5)
            rotation_type = rotation_type or config.get("logging.rotation_type", "size")
            when = when or config.get("logging.when", "midnight")
            interval = interval or config.get("logging.interval", 1)

        # Create logger
        logger = logging.getLogger("filesqueeze")
        logger.setLevel(getattr(logging, level.upper(), logging.INFO))

        # Remove existing handlers to avoid duplicates
        logger.handlers.clear()

        # Create formatter
        formatter = logging.Formatter(Logger.FORMATS.get(format_type, Logger.FORMATS["detailed"]), datefmt="%Y-%m-%d %H:%M:%S")

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)  # Always INFO for console
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # File handler (if log file specified)
        if log_file:
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)

            # Choose handler based on rotation type
            if rotation_type == "time":
                file_handler = TimedRotatingFileHandler(
                    log_path, when=when, interval=interval, backupCount=backup_count, encoding="utf-8"
                )
                # Set naming convention for time-based rotation: filesqueeze.log.2026-01-22
                file_handler.namer = lambda name: name.replace(".log.", ".log_") + ".log" if ".log." in name else name
                file_handler.suffix = "%Y-%m-%d"
            else:
                # Default to size-based rotation
                file_handler = RotatingFileHandler(log_path, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8")

            file_handler.setLevel(getattr(logging, level.upper(), logging.INFO))
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

        return logger

    @staticmethod
    def get_logger(name: Optional[str] = None) -> logging.Logger:
        """Get a logger instance.

        Args:
            name: Logger name (defaults to 'filesqueeze')

        Returns:
            Logger instance
        """
        return logging.getLogger(name or "filesqueeze")


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Convenience function to get a logger instance.

    Args:
        name: Logger name

    Returns:
            Logger instance
    """
    return Logger.get_logger(name)


def setup_logging(config: Optional[Config] = None, log_file: Optional[str | Path] = None) -> logging.Logger:
    """Convenience function to set up logging.

    Args:
        config: Config object with logging settings
        log_file: Optional path to log file (overrides config)

    Returns:
        Configured logger instance

    Note:
        This function both configures the logger AND registers it with the system logger.
    """
    configured_logger = Logger.setup(config=config, log_file=log_file)
    # Register with system logger for dependency injection
    system_get_logger()  # This will be replaced by the registered logger
    register_logger(configured_logger)
    return configured_logger
