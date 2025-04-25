## The conversion pipeline is implemented as a state machine.
## State information is encapsulated in the State class.
## Transitions are handled by handlers, which are functions that take in a State object
## and return another handler, which is the next transition for the state machine.

from . import handlers
from .state import State
from .enums import Status



state_factory = State
start = handlers.selectAnalyzer



def make_video(filepath: str, on_update=lambda data: None) -> str:
    """
    Entry point to the compression pipeline.
    Begins compression on the given filepath.
    Returns the path to the final file.
    """
    state = state_factory(filepath)
    handler = start  # first state machine transition
    while handler:
        handler = handler(state)
        on_update(state.as_dict())
    return state.target