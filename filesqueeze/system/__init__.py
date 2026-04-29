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
    "logger",
    "register_logger",
    "get_logger",
    "TraceContext",
    "trace_context",
    "get_trace_context",
    "trace_handler",
    "log_transition",
    "StructuredFormatter",
    "register_binary_finder",
    "get_binary_finder",
    "is_windows",
    "is_linux",
    "is_mac",
    "get_platform",
    "VideoConfig",
    "DocumentConfig",
    "ImageConfig",
    "PresentationConfig",
    "trace_function",
]
