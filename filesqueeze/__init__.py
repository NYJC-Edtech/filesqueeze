## The conversion pipeline is implemented as a state machine.
## State information is encapsulated in the State class.
## Transitions are handled by handlers, which are functions that take in a State object
## and return another handler, which is the next transition for the state machine.

from typing import Callable, Optional

from . import handlers
from .fsm import StateMachine
from .config import Config


start = handlers.selectAnalyzer

StateMachine(start=handlers.selectAnalyzer)

def make_video(filepath: str, callback: Optional[Callable] = None, config: Optional[Config] = None, output_path: Optional[str] = None) -> str:
    """Entry point to the compression pipeline for video files.

    Args:
        filepath: Path to the video file to compress.
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

def make_pdf(filepath: str, callback: Optional[Callable] = None, config: Optional[Config] = None, output_path: Optional[str] = None) -> str:
    """Entry point to the compression pipeline for PDF files.

    Args:
        filepath: Path to the PDF file to compress.
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

def make_image(filepath: str, callback: Optional[Callable] = None, config: Optional[Config] = None, output_path: Optional[str] = None) -> str:
    """Entry point to the compression pipeline for image files.

    Args:
        filepath: Path to the image file to compress.
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