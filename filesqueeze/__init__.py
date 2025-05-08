## The conversion pipeline is implemented as a state machine.
## State information is encapsulated in the State class.
## Transitions are handled by handlers, which are functions that take in a State object
## and return another handler, which is the next transition for the state machine.

from typing import Callable

from . import handlers
from .fsm import StateMachine


start = handlers.selectAnalyzer

StateMachine(start=handlers.selectAnalyzer)

def make_video(filepath: str, callback: Callable) -> str:
    """Entry point to the compression pipeline.
    Begins compression on the given filepath.
    Returns the path to the final file.
    """
    sm = StateMachine(start=handlers.selectAnalyzer)
    if callback:
        sm.onupdate = callback
    final = sm.run(filepath)
    return final.target