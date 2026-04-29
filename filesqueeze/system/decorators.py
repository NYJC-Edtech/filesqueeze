"""Function tracing decorators.

Provides automatic logging of entry/exit/timing/exceptions
for business logic functions.
"""

import functools
import time
from typing import Callable


def trace_function(func: Callable) -> Callable:
    """Decorator for tracing business logic functions.

    Automatically logs:
    - Entry with function name and parameters
    - Exit with duration and return value
    - Exception with full traceback and duration

    Usage:
        @trace_function
        def compress_video(input_path: str, output_path: str, config: Config) -> bool:
            ...
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Import here to avoid circular dependency
        from .logger import get_logger

        logger = get_logger()
        func_name = func.__name__

        # Log entry
        logger.debug(
            f"Function entry: {func_name}", extra={"function": func_name, "event": "entry", "module": func.__module__}
        )

        start_time = time.time()
        try:
            # Call function
            result = func(*args, **kwargs)
            duration_ms = int((time.time() - start_time) * 1000)

            # Log exit
            logger.debug(
                f"Function exit: {func_name}",
                extra={
                    "function": func_name,
                    "event": "exit",
                    "duration_ms": duration_ms,
                    "result": str(result) if result is not None else None,
                },
            )
            return result

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)

            # Log exception
            logger.error(
                f"Function failed: {func_name}",
                exc_info=True,
                extra={
                    "function": func_name,
                    "event": "exception",
                    "duration_ms": duration_ms,
                    "exception_type": type(e).__name__,
                    "exception_message": str(e),
                },
            )
            raise

    return wrapper


def trace_function_async(func: Callable) -> Callable:
    """Decorator for tracing async business logic functions.

    Automatically logs entry/exit/exceptions for async functions.
    Currently unused but provided for future async support.

    Usage:
        @trace_function_async
        async def compress_video_async(...) -> bool:
            ...
    """

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        # Import here to avoid circular dependency
        from .logger import get_logger

        logger = get_logger()
        func_name = func.__name__

        # Log entry
        logger.debug(
            f"Async function entry: {func_name}", extra={"function": func_name, "event": "entry", "module": func.__module__}
        )

        start_time = time.time()
        try:
            # Call async function
            result = await func(*args, **kwargs)
            duration_ms = int((time.time() - start_time) * 1000)

            # Log exit
            logger.debug(
                f"Async function exit: {func_name}",
                extra={
                    "function": func_name,
                    "event": "exit",
                    "duration_ms": duration_ms,
                    "result": str(result) if result is not None else None,
                },
            )
            return result

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)

            # Log exception
            logger.error(
                f"Async function failed: {func_name}",
                exc_info=True,
                extra={
                    "function": func_name,
                    "event": "exception",
                    "duration_ms": duration_ms,
                    "exception_type": type(e).__name__,
                    "exception_message": str(e),
                },
            )
            raise

    return wrapper
