## The conversion pipeline is implemented as a state machine.
## State information is encapsulated in the State class.
## Transitions are handled by handlers, which are functions that take in a State object
## and return another handler, which is the next transition for the state machine.

from typing import Callable, Optional

# Export system modules
from . import (
    handlers,
    logger,  # Logger.setup, setup_logging
)
from .config import Config
from .fsm import StateMachine

# Export ops modules
from .ops import document, image, video
from .ops import presentation as pptx

# Re-export commonly used items for convenience
from .system import (
    binaries,
    platform,
    register_binary_finder,
    register_logger,
    trace_context,
    trace_handler,
)

start = handlers.selectAnalyzer

StateMachine(start=handlers.selectAnalyzer)


def _make_file(
    filepath: str, callback: Callable | None = None, config: Config | None = None, output_path: str | None = None
) -> str:
    """Generic entry point for the file compression pipeline.

    Args:
        filepath: Path to the file to compress.
        callback: Optional callback function for state updates.
        config: Optional Config object for compression settings.
        output_path: Optional output path for compressed file.

    Returns:
        Path to the final compressed file.
    """
    sm = StateMachine(start=handlers.selectAnalyzer)
    if callback:
        sm.onupdate = callback
    final = sm.run(filepath, config=config, output_path=output_path)
    return final.target


def make_video(
    filepath: str, callback: Callable | None = None, config: Config | None = None, output_path: str | None = None
) -> str:
    """Entry point to the compression pipeline for video files.

    Args:
        filepath: Path to the video file to compress.
        callback: Optional callback function for state updates.
        config: Optional Config object for compression settings.
        output_path: Optional output path for compressed file.

    Returns:
        Path to the final compressed file.
    """
    return _make_file(filepath, callback, config, output_path)


def make_pdf(
    filepath: str, callback: Callable | None = None, config: Config | None = None, output_path: str | None = None
) -> str:
    """Entry point to the compression pipeline for PDF files.

    Args:
        filepath: Path to the PDF file to compress.
        callback: Optional callback function for state updates.
        config: Optional Config object for compression settings.
        output_path: Optional output path for compressed file.

    Returns:
        Path to the final compressed file.
    """
    return _make_file(filepath, callback, config, output_path)


def make_image(
    filepath: str, callback: Callable | None = None, config: Config | None = None, output_path: str | None = None
) -> str:
    """Entry point to the compression pipeline for image files.

    Args:
        filepath: Path to the image file to compress.
        callback: Optional callback function for state updates.
        config: Optional Config object for compression settings.
        output_path: Optional output path for compressed file.

    Returns:
        Path to the final compressed file.
    """
    return _make_file(filepath, callback, config, output_path)


def make_presentation(
    filepath: str, callback: Callable | None = None, config: Config | None = None, output_path: str | None = None
) -> str:
    """Entry point to the compression pipeline for PowerPoint files.

    Args:
        filepath: Path to the PowerPoint file to compress.
        callback: Optional callback function for state updates.
        config: Optional Config object for compression settings.
        output_path: Optional output path for compressed file.

    Returns:
        Path to the final compressed file.
    """
    return _make_file(filepath, callback, config, output_path)


__all__ = [
    "video",
    "document",
    "image",
    "pptx",  # Alias for presentation
    "logger",
    "platform",
    "binaries",
    "make_video",
    "make_pdf",
    "make_image",
    "make_presentation",
    "register_logger",
    "register_binary_finder",
    "trace_context",
    "trace_handler",
]
