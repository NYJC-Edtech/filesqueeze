"""filesqueeze.logger

Logging configuration for FileSqueeze.
Dual handlers: StreamHandler (stdout) + RotatingFileHandler.
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

from .config import Config


class Logger:
    """Logger manager with dual output (console + file)."""

    # Log format templates
    FORMATS = {
        'simple': '%(levelname)s: %(message)s',
        'detailed': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        'json': '%(asctime)s %(name)s %(levelname)s %(message)s',
    }

    @staticmethod
    def setup(
        config: Optional[Config] = None,
        log_file: Optional[str | Path] = None,
        level: str = 'INFO',
        format_type: str = 'detailed',
        max_bytes: int = 10485760,
        backup_count: int = 5,
    ) -> logging.Logger:
        """Set up logging with console and file handlers.

        Args:
            config: Config object (will override other parameters if provided)
            log_file: Path to log file
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            format_type: Format type (simple, detailed, json)
            max_bytes: Max size of each log file before rotation
            backup_count: Number of backup files to keep

        Returns:
            Configured logger instance
        """
        # Get settings from config if provided
        if config:
            log_file = log_file or config.get('logging.file')
            level = level or config.get('logging.level', 'INFO')
            format_type = format_type or config.get('logging.format', 'detailed')
            max_bytes = max_bytes or config.get('logging.max_bytes', 10485760)
            backup_count = backup_count or config.get('logging.backup_count', 5)

        # Create logger
        logger = logging.getLogger('filesqueeze')
        logger.setLevel(getattr(logging, level.upper(), logging.INFO))

        # Remove existing handlers to avoid duplicates
        logger.handlers.clear()

        # Create formatter
        formatter = logging.Formatter(
            Logger.FORMATS.get(format_type, Logger.FORMATS['detailed']),
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)  # Always INFO for console
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # File handler (if log file specified)
        if log_file:
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)

            file_handler = RotatingFileHandler(
                log_path,
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding='utf-8'
            )
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
        return logging.getLogger(name or 'filesqueeze')


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Convenience function to get a logger instance.

    Args:
        name: Logger name

    Returns:
            Logger instance
    """
    return Logger.get_logger(name)
