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
from filesqueeze.ops import video
from filesqueeze.ops import document
from filesqueeze.ops import image
from filesqueeze.ops import presentation

__all__ = [
    'video',
    'document',
    'image',
    'presentation',
]
