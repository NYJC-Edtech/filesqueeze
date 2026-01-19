"""Test logging module."""

import tempfile
from pathlib import Path

import pytest

from filesqueeze.config import Config
from filesqueeze.logger import Logger, get_logger


def test_logging_setup():
    """Test logging setup with console and file handlers."""
    tmpdir = Path(tempfile.mkdtemp())
    try:
        log_file = tmpdir / 'test.log'

        # Setup logger
        logger = Logger.setup(
            log_file=log_file,
            level='DEBUG',
            format_type='detailed'
        )

        # Test logging
        logger.debug("This is a debug message")
        logger.info("This is an info message")
        logger.warning("This is a warning")
        logger.error("This is an error")

        # Close all handlers to release file lock
        for handler in logger.handlers[:]:
            handler.close()
            logger.removeHandler(handler)

        # Check that log file was created
        assert log_file.exists(), "Log file was not created"

        # Check log file content
        log_content = log_file.read_text()
        assert "debug message" in log_content
        assert "info message" in log_content
        assert "warning" in log_content
        assert "error" in log_content
    finally:
        # Clean up temp directory
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_logging_with_config():
    """Test logging setup using Config object."""
    tmpdir = Path(tempfile.mkdtemp())
    try:
        # Create config with custom settings
        config_file = tmpdir / 'config.toml'
        config_file.write_text('[logging]\nlevel = "WARNING"\nfile = "test2.log"\n')

        log_file = tmpdir / 'test2.log'
        config = Config(config_path=config_file)

        # Setup logger with config
        logger = Logger.setup(config=config, log_file=log_file, level='WARNING')

        # Test that WARNING level is respected
        assert logger.level == 30  # WARNING = 30

        logger.info("This info message should not appear in file")
        logger.warning("This warning should appear")

        # Close handlers before reading
        for handler in logger.handlers[:]:
            handler.close()
            logger.removeHandler(handler)

        log_content = log_file.read_text()
        assert "info message" not in log_content
        assert "warning should appear" in log_content
    finally:
        # Clean up temp directory
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_get_logger():
    """Test get_logger convenience function."""
    # get_logger with no name returns 'filesqueeze'
    logger1 = get_logger()
    assert logger1.name == 'filesqueeze'

    # get_logger with a custom name uses that name
    logger2 = get_logger('test')
    assert logger2.name == 'test'

    # get_logger with None returns 'filesqueeze'
    logger3 = get_logger(None)
    assert logger3.name == 'filesqueeze'


def test_logging_formats():
    """Test different log formats."""
    tmpdir = Path(tempfile.mkdtemp())
    try:
        log_file = tmpdir / 'test.log'

        # Test simple format
        logger = Logger.setup(
            log_file=log_file,
            level='INFO',
            format_type='simple'
        )
        logger.info("test message")

        for handler in logger.handlers[:]:
            handler.close()
            logger.removeHandler(handler)

        log_content = log_file.read_text()
        # Simple format should not have timestamps
        assert 'INFO:' in log_content
        assert 'test message' in log_content
    finally:
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)
