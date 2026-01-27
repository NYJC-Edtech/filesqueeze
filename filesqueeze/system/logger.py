"""System logger with trace context support and lazy registration.

This module provides:
1. Logger registration pattern for dependency injection
2. Lazy logger proxy for late registration
3. Trace context support for distributed tracing
4. Structured logging with automatic context enrichment

Usage:
    # At startup (cli.py, service.py, tray.py)
    from filesqueeze.logger import setup_logging
    logger = setup_logging(config)
    from filesqueeze.system import register_logger
    register_logger(logger)

    # In ops modules
    from filesqueeze.system import logger
    logger.info("Processing file")  # Works even if not registered yet

    # With trace context
    from filesqueeze.system.logger import trace_context
    with trace_context(file_path="test.pdf", workflow="compress"):
        logger.info("Starting")  # Auto-includes trace_id, file, workflow
"""

import logging
import threading
import uuid
import time
import json
import functools
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, Callable


# ============================================================================
# Trace Context Support
# ============================================================================

class TraceContext:
    """Holds trace context for a single file processing workflow.

    Each file gets a unique trace ID that follows it through the entire
    state machine. This allows reconstructing the full execution path.

    Attributes:
        trace_id: Unique identifier for this processing workflow
        file_path: Path to file being processed
        workflow: Workflow type (watch, cli, gui)
        start_time: When workflow started
        metadata: Additional context (file size, format, etc.)
    """

    def __init__(
        self,
        trace_id: Optional[str] = None,
        file_path: Optional[Path] = None,
        workflow: str = "unknown",
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.trace_id = trace_id or str(uuid.uuid4())[:8]
        self.file_path = file_path
        self.workflow = workflow
        self.start_time = time.time()
        self.metadata = metadata or {}
        self._current_handler: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary for logging."""
        return {
            "trace_id": self.trace_id,
            "file": str(self.file_path) if self.file_path else None,
            "workflow": self.workflow,
            "handler": self._current_handler,
            "elapsed_ms": int((time.time() - self.start_time) * 1000),
            **self.metadata
        }


# Global trace context (thread-local for thread safety)
_trace_context = threading.local()


@contextmanager
def trace_context(file_path: Optional[Path] = None, workflow: str = "unknown", **kwargs):
    """Context manager for automatic trace context.

    Automatically enriches all log entries within the context with:
    - trace_id: Unique ID for this workflow
    - file_path: File being processed
    - workflow: Type of workflow (watch, cli, gui)
    - Timing metadata

    Args:
        file_path: Path to file being processed
        workflow: Type of workflow (watch, cli, gui)
        **kwargs: Additional context (custom fields)

    Example:
        with trace_context(file_path="test.pdf", workflow="compress"):
            logger.info("Starting")  # Auto-includes trace_id, file
            process_file()
            logger.info("Finished")  # Auto-includes elapsed_ms
    """
    # Build context
    context = TraceContext(
        file_path=file_path,
        workflow=workflow,
        metadata=kwargs
    )

    # Set context in thread-local storage
    old_context = getattr(_trace_context, 'context', None)
    _trace_context.context = context

    try:
        yield context
    finally:
        # Restore previous context
        _trace_context.context = old_context


def get_trace_context() -> Optional[TraceContext]:
    """Get the current trace context."""
    return getattr(_trace_context, 'context', None)


# ============================================================================
# Structured Formatter
# ============================================================================

class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logging.

    Outputs log records as JSON for machine parsing while maintaining
    human-readability in development.
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        # Create base log entry
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add structured context if present
        if hasattr(record, 'context'):
            log_entry.update(record.context)

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
            }

        return json.dumps(log_entry, default=str)


# ============================================================================
# Logger Registration
# ============================================================================

# Global logger instance (None until registered)
_logger: Optional[logging.Logger] = None
# Lock for thread-safe registration
_logger_lock = threading.Lock()


def register_logger(logger: logging.Logger) -> None:
    """Register the logger for all FileSqueeze modules.

    Called once at startup to inject logger dependency.

    Args:
        logger: Configured logger instance

    Note:
        If the same logger instance is already registered, this is a no-op.
        This allows multiple calls to setup_logging() in tests without errors.
    """
    global _logger

    with _logger_lock:
        # Allow re-registration if it's the same logger instance (helpful for tests)
        if _logger is not None and _logger is not logger:
            raise RuntimeError(
                f"Logger already registered as '{_logger.name}'. "
                "Check import order - logger should only be registered once at startup."
            )
        if _logger is None:
            _logger = logger


def get_logger() -> logging.Logger:
    """Get the registered logger.

    Returns:
        Logger instance (or default Python logger if not registered)

    Note:
        If called before registration, returns a default logger named 'filesqueeze'.
    """
    global _logger

    # Return registered logger if available
    if _logger is not None:
        return _logger

    # Return default logger if not yet registered
    return logging.getLogger('filesqueeze')


class _LazyLogger:
    """Lazy logger proxy with automatic trace context enrichment.

    Delegates to get_logger() to handle late registration.
    Automatically adds trace context to log entries when available.

    Example:
        from filesqueeze.system.logger import logger

        # This works even if logger hasn't been registered yet
        logger.info("Processing file")

        # With trace context
        with trace_context(file_path="test.pdf"):
            logger.info("Compressing")  # Auto-includes trace_id, file
    """

    def _add_context(self, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Add current trace context to log extra fields."""
        if extra is None:
            extra = {}

        context = get_trace_context()
        if context:
            extra['context'] = context.to_dict()
        return extra

    def _log(self, level_method, msg: str, *args, **kwargs):
        """Log a message with automatic context enrichment."""
        actual_logger = get_logger()
        extra = self._add_context(kwargs.pop('extra', None))
        level_method(msg, *args, extra=extra, **kwargs)

    def debug(self, msg: str, *args, **kwargs):
        """Log debug message with automatic context."""
        self._log(get_logger().debug, msg, *args, **kwargs)

    def info(self, msg: str, *args, **kwargs):
        """Log info message with automatic context."""
        self._log(get_logger().info, msg, *args, **kwargs)

    def warning(self, msg: str, *args, **kwargs):
        """Log warning message with automatic context."""
        self._log(get_logger().warning, msg, *args, **kwargs)

    def error(self, msg: str, *args, **kwargs):
        """Log error message with automatic context."""
        self._log(get_logger().error, msg, *args, **kwargs)

    def critical(self, msg: str, *args, **kwargs):
        """Log critical message with automatic context."""
        self._log(get_logger().critical, msg, *args, **kwargs)

    def exception(self, msg: str, *args, **kwargs):
        """Log exception message with automatic context."""
        actual_logger = get_logger()
        extra = self._add_context(kwargs.pop('extra', None))
        actual_logger.exception(msg, *args, extra=extra, exc_info=True, **kwargs)

    def __getattr__(self, name):
        """Delegate any other attributes to the actual logger."""
        actual_logger = get_logger()
        return getattr(actual_logger, name)

    def __repr__(self):
        """String representation of the lazy logger."""
        return f"<LazyLogger delegating to {get_logger().name}>"


# Create lazy logger instance for module-level usage
logger = _LazyLogger()


# ============================================================================
# Handler Tracing Decorator
# ============================================================================

def trace_handler(func: Callable) -> Callable:
    """Decorator for automatic handler entry/exit logging.

    Automatically logs:
    - Entry: When handler is called with file path, handler name
    - Exit: When handler returns with duration, result
    - Exception: If handler raises with full traceback

    This makes logging non-brittle - you can't forget to log,
    and you get consistent, structured output.

    Args:
        func: Handler function to decorate

    Example:
        @trace_handler
        def compressVideo(state: State) -> Handler:
            ...  # Entry/exit automatically logged
    """
    @functools.wraps(func)
    def wrapper(state, *args, **kwargs):
        # Get or create trace context
        context = get_trace_context()
        if not context and state:
            context = TraceContext(file_path=getattr(state, 'origin', None))
            _trace_context.context = context

        # Set current handler name
        if context:
            context._current_handler = func.__name__

        # Log entry
        logger.info(
            f"Handler entry: {func.__name__}",
            operation=func.__name__,
            event="entry"
        )

        # Track timing
        start_time = time.time()
        result = None
        exception_occurred = False

        try:
            # Call the actual handler
            result = func(state, *args, **kwargs)
            return result

        except Exception as e:
            exception_occurred = True
            duration_ms = int((time.time() - start_time) * 1000)

            # Log exception with full context
            logger.error(
                f"Handler failed: {func.__name__}",
                exc_info=True,
                operation=func.__name__,
                event="exception",
                exception_type=type(e).__name__,
                exception_message=str(e),
                duration_ms=duration_ms
            )

            # Re-raise to maintain existing error handling
            raise

        finally:
            # Log exit (only if no exception, to avoid duplicate logs)
            if not exception_occurred:
                duration_ms = int((time.time() - start_time) * 1000)
                next_handler = result.__name__ if hasattr(result, '__name__') else None

                logger.info(
                    f"Handler exit: {func.__name__}",
                    operation=func.__name__,
                    event="exit",
                    duration_ms=duration_ms,
                    next_handler=next_handler
                )

            # Clear current handler
            if context:
                context._current_handler = None

    return wrapper


def log_transition(from_handler: str, to_handler: str, state):
    """Log a state machine transition.

    Called automatically by StateMachine.

    Args:
        from_handler: Current handler name
        to_handler: Next handler name
        state: State object
    """
    logger.info(
        f"State transition: {from_handler} → {to_handler}",
        event="transition",
        from_handler=from_handler,
        to_handler=to_handler,
        status=str(state.status) if hasattr(state, 'status') else None
    )
