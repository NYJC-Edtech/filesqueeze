"""FileSqueeze System Package

System-level infrastructure services (logger, binaries, platform, config).

CRITICAL RULE: Never import from 'filesqueeze.ops' package.
Dependency direction: ops → system (OK), system → ops (FORBIDDEN)
"""

from .binaries import get_binary_finder, register_binary_finder
from .config_adapters import (
    DocumentConfig,
    ImageConfig,
    PresentationConfig,
    VideoConfig,
)
from .decorators import trace_function
from .logger import (
    StructuredFormatter,
    TraceContext,
    get_logger,
    get_trace_context,
    log_transition,
    logger,
    register_logger,
    trace_context,
    trace_handler,
)
from .platform import get_platform, is_linux, is_mac, is_windows

__all__ = [
    "DocumentConfig",
    "ImageConfig",
    "PresentationConfig",
    "StructuredFormatter",
    "TraceContext",
    "VideoConfig",
    "get_binary_finder",
    "get_logger",
    "get_platform",
    "get_trace_context",
    "is_linux",
    "is_mac",
    "is_windows",
    "log_transition",
    "logger",
    "register_binary_finder",
    "register_logger",
    "trace_context",
    "trace_function",
    "trace_handler",
]
