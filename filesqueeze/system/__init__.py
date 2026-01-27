"""FileSqueeze System Package

System-level infrastructure services (logger, binaries, platform, config).

CRITICAL RULE: Never import from 'filesqueeze.ops' package.
Dependency direction: ops → system (OK), system → ops (FORBIDDEN)
"""

from .logger import (
    logger,
    register_logger,
    get_logger,
    TraceContext,
    trace_context,
    get_trace_context,
    trace_handler,
    log_transition,
    StructuredFormatter,
)
from .binaries import register_binary_finder, get_binary_finder
from .platform import is_windows, is_linux, is_mac, get_platform
from .config_adapters import (
    VideoConfig,
    DocumentConfig,
    ImageConfig,
    PresentationConfig,
)
from .decorators import trace_function

__all__ = [
    'logger',
    'register_logger',
    'get_logger',
    'TraceContext',
    'trace_context',
    'get_trace_context',
    'trace_handler',
    'log_transition',
    'StructuredFormatter',
    'register_binary_finder',
    'get_binary_finder',
    'is_windows',
    'is_linux',
    'is_mac',
    'get_platform',
    'VideoConfig',
    'DocumentConfig',
    'ImageConfig',
    'PresentationConfig',
    'trace_function',
]
