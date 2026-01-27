"""Test system logger registration pattern.

These tests verify the lazy logger registration pattern used
in the system package.
"""

import pytest
import logging
from unittest.mock import MagicMock, patch


class TestLoggerRegistration:
    """Test logger registration and lazy access."""

    def test_register_and_get_logger(self):
        """Register custom logger and retrieve it."""
        from filesqueeze.system.logger import register_logger, get_logger

        # Reset state
        import filesqueeze.system.logger as logger_module
        logger_module._logger = None

        # Register custom logger
        custom_logger = logging.getLogger('test_custom')
        register_logger(custom_logger)

        # Retrieve
        retrieved = get_logger()
        assert retrieved is custom_logger

    def test_get_logger_before_registration(self):
        """Get default logger before registration."""
        from filesqueeze.system.logger import get_logger

        # Reset state
        import filesqueeze.system.logger as logger_module
        logger_module._logger = None

        # Should return default logger
        logger = get_logger()
        assert logger.name == 'filesqueeze'
        assert isinstance(logger, logging.Logger)

    def test_double_registration_raises(self):
        """Double registration should raise RuntimeError."""
        from filesqueeze.system.logger import register_logger

        # Reset state
        import filesqueeze.system.logger as logger_module
        logger_module._logger = None

        # First registration
        register_logger(logging.getLogger('test1'))

        # Second registration should raise
        with pytest.raises(RuntimeError, match="already registered"):
            register_logger(logging.getLogger('test2'))

    def test_lazy_logger_works_before_registration(self):
        """Lazy logger proxy works before registration."""
        from filesqueeze.system.logger import logger, register_logger

        # Reset state
        import filesqueeze.system.logger as logger_module
        logger_module._logger = None

        # Import logger BEFORE registration
        # This simulates ops modules importing logger at module load time
        assert logger is not None

        # Register AFTER import
        custom_logger = logging.getLogger('lazy_test')
        register_logger(custom_logger)

        # Lazy logger should now delegate to registered logger
        # This test verifies the lazy proxy pattern works
        logger.info("Test message")

        # Verify the custom logger received the call
        # (This requires the custom logger to have handlers, but we just verify no error)

    def test_lazy_logger_after_registration(self):
        """Lazy logger works correctly after registration."""
        from filesqueeze.system.logger import logger, register_logger
        from io import StringIO

        # Reset state
        import filesqueeze.system.logger as logger_module
        logger_module._logger = None

        # Create logger with handler we can inspect
        custom_logger = logging.getLogger('test_after')
        custom_logger.setLevel(logging.INFO)

        # Add string handler to capture logs
        log_stream = StringIO()
        handler = logging.StreamHandler(log_stream)
        handler.setLevel(logging.INFO)
        custom_logger.addHandler(handler)

        # Register
        register_logger(custom_logger)

        # Use lazy logger
        logger.info("Test message via lazy logger")

        # Verify it was logged
        log_output = log_stream.getvalue()
        assert "Test message via lazy logger" in log_output

    def test_get_logger_returns_same_instance(self):
        """get_logger returns same instance on multiple calls."""
        from filesqueeze.system.logger import register_logger, get_logger

        # Reset state
        import filesqueeze.system.logger as logger_module
        logger_module._logger = None

        custom_logger = logging.getLogger('test_same')
        register_logger(custom_logger)

        # Multiple calls should return same instance
        logger1 = get_logger()
        logger2 = get_logger()
        assert logger1 is logger2
        assert logger1 is custom_logger

    def test_logger_module_level_attributes(self):
        """Logger module has expected attributes."""
        from filesqueeze.system import logger

        # Module-level logger should exist
        assert hasattr(logger, 'info')
        assert hasattr(logger, 'debug')
        assert hasattr(logger, 'warning')
        assert hasattr(logger, 'error')
        assert hasattr(logger, 'critical')


class TestLoggerThreadSafety:
    """Test thread safety of logger registration."""

    def test_concurrent_registration(self):
        """Concurrent registrations should be safe."""
        import threading
        from filesqueeze.system.logger import register_logger, get_logger

        # Reset state
        import filesqueeze.system.logger as logger_module
        logger_module._logger = None

        results = []
        errors = []

        def register(logger_num):
            try:
                register_logger(logging.getLogger(f'test_thread_{logger_num}'))
                results.append(f'success_{logger_num}')
            except RuntimeError as e:
                errors.append(str(e))

        # Spawn multiple threads registering simultaneously
        threads = [threading.Thread(target=register, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should have exactly 1 success, 4 errors
        assert len(results) == 1, f"Expected 1 success, got {len(results)}"
        assert len(errors) == 4, f"Expected 4 errors, got {len(errors)}"

        # All errors should mention "already registered"
        for error in errors:
            assert "already registered" in error.lower()


class TestLoggerResetBetweenTests:
    """Test that logger state can be reset between tests."""

    def test_test_isolation(self):
        """Verify tests don't interfere with each other."""
        from filesqueeze.system.logger import register_logger, get_logger

        # Register logger in this test
        register_logger(logging.getLogger('test_isolation'))
        logger = get_logger()

        assert logger.name == 'test_isolation'

        # After test completes, conftest fixture resets state
        # Next test should get fresh state
