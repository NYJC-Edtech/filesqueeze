"""filesqueeze.fsm

Implements a state machine for the conversion pipeline.
"""
from os import PathLike
from typing import Generic, Callable, TypeVar

from .default import State
from .enums import Format

# Generic type for state object
S = TypeVar("S")

# A state machine transition function that takes a state and returns another handler
Handler = Callable[[S], "Handler"]
# An external callback, called after each state transition
StateCallback = Callable[[S], None]
# A customisable factory function that creates a state object
StateFactory = Callable[[PathLike], S]

def default_state_factory(filepath, **kwargs):
    """Default state factory that forwards kwargs to State constructor."""
    return State(filepath, **kwargs)


class StateMachine(Generic[S]):
    """A simple state machine for the conversion pipeline.

    The state machine is implemented as a series of functions that take in a State object
    and return another function, which is the next transition for the state machine.
    """

    def __init__(self, start: Handler, *,
                 onupdate: StateCallback = lambda s: None,
                 state_factory: StateFactory = default_state_factory):
        self.state_factory = state_factory
        # External callback, called after each state transition
        self.onupdate = onupdate
        # First transition of state machine
        self.start = start

    def transition(self, state: S, handler: Handler) -> tuple[S, Handler]:
        """Execute the next transition for the state machine."""
        # Call the handler with the current state
        next_handler = handler(state)
        self.onupdate(state)
        # Return the new state and the next handler
        return state, next_handler

    def run(self, *args, **kwargs) -> S:
        """Run the state machine until completion.
        Returns the final state.
        """
        state, handler = self.state_factory(*args, **kwargs), self.start
        while handler:
            state, handler = self.transition(state, handler)
        return state
