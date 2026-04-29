"""filesqueeze.fsm

Implements a state machine for the conversion pipeline.
"""

from os import PathLike
from typing import Generic, Callable, TypeVar

from .default import State
from .enums import Format
from ..system import logger

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

    Uses the registered system logger for automatic transition logging.
    """

    def __init__(
        self, start: Handler, *, onupdate: StateCallback = lambda s: None, state_factory: StateFactory = default_state_factory
    ):
        self.state_factory = state_factory
        # External callback, called after each state transition
        self.onupdate = onupdate
        # First transition of state machine
        self.start = start

    def transition(self, state: S, handler: Handler) -> tuple[S, Handler]:
        """Execute the next transition for the state machine."""
        # Get handler names for logging
        current_name = handler.__name__ if hasattr(handler, "__name__") else str(handler)

        # Call the handler with the current state
        next_handler = handler(state)
        next_name = next_handler.__name__ if hasattr(next_handler, "__name__") else str(next_handler)

        # Log transition using system logger
        try:
            logger.debug(
                f"State transition: {current_name} -> {next_name}",
                extra={"transition_from": current_name, "transition_to": next_name, "state": str(state)},
            )
        except Exception:
            # Silently fail if logging breaks (state machine continues)
            pass

        # Call external update callback
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
