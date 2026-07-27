"""State machine and transition table. No I/O in this layer."""

from sentinel.state.errors import IllegalTransitionError
from sentinel.state.machine import (
    TRANSITIONS,
    StateMachine,
    Transition,
    TransitionResult,
)

__all__ = [
    "TRANSITIONS",
    "IllegalTransitionError",
    "StateMachine",
    "Transition",
    "TransitionResult",
]
