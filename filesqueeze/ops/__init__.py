"""filesqueeze.ops

Business logic operations for file compression.

This package contains all file processing operations (video, document, image, presentation).
These modules depend on the system package for utilities (logger, binaries, platform).

Architecture:
    system ← ops (ops depends on system)
    ops → handlers, service (handlers/service depend on ops)

Usage:
    from filesqueeze.ops import video, document, image, presentation
"""

# Public API exports
from filesqueeze.ops import document, image, presentation, video

__all__ = [
    "document",
    "image",
    "presentation",
    "video",
]
