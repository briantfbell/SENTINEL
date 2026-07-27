"""The state machine: a pure function of (current state, event).

AGENTS.md section 4.5: the state machine is the only component permitted
to change system state and performs no I/O. AGENTS.md section 7.2's
transition table is the specification, implemented here as data rather
than nested `if` statements so it stays trivially auditable against the
table in the doc.

What actions to fire in response to a transition is the rule engine's
job (section 7.4, built in slice 4), not this module's — this module
answers exactly one question: what state comes next, or is the event
illegal here.
"""

from dataclasses import dataclass

from sentinel.models import EventType, SystemState
from sentinel.state.errors import IllegalTransitionError


@dataclass(frozen=True)
class Transition:
    from_state: SystemState
    event: EventType
    to_state: SystemState


@dataclass(frozen=True)
class TransitionResult:
    """The outcome of handling one event."""

    from_state: SystemState
    event: EventType
    to_state: SystemState


# AGENTS.md section 7.2, transposed directly from the table. The two
# "_any_" rows (SystemDisarmed, CameraOffline) are wildcards handled
# separately in StateMachine.handle, not encoded here.
TRANSITIONS: tuple[Transition, ...] = (
    Transition(SystemState.DISARMED, EventType.SYSTEM_ARMED, SystemState.ARMED),
    Transition(SystemState.DISARMED, EventType.PERSON_DETECTED, SystemState.DISARMED),
    Transition(SystemState.ARMED, EventType.PERSON_DETECTED, SystemState.ALERT),
    Transition(SystemState.ARMED, EventType.CAMERA_OFFLINE, SystemState.ARMED),
    Transition(SystemState.ALERT, EventType.GRACE_EXPIRED, SystemState.WARNING),
    Transition(SystemState.ALERT, EventType.PERSON_GONE, SystemState.COOLDOWN),
    Transition(SystemState.ALERT, EventType.PERSON_DETECTED, SystemState.ALERT),
    Transition(SystemState.WARNING, EventType.WARNING_EXPIRED, SystemState.ESCALATED),
    Transition(SystemState.WARNING, EventType.PERSON_GONE, SystemState.COOLDOWN),
    Transition(SystemState.WARNING, EventType.PERSON_DETECTED, SystemState.WARNING),
    Transition(SystemState.ESCALATED, EventType.PERSON_GONE, SystemState.COOLDOWN),
    Transition(SystemState.ESCALATED, EventType.PERSON_DETECTED, SystemState.ESCALATED),
    Transition(SystemState.COOLDOWN, EventType.PERSON_DETECTED, SystemState.ALERT),
    Transition(SystemState.COOLDOWN, EventType.COOLDOWN_EXPIRED, SystemState.ARMED),
)


class StateMachine:
    """Owns `SystemState`. Exposes no public setter, only `handle`."""

    def __init__(self, initial_state: SystemState = SystemState.DISARMED) -> None:
        self._state = initial_state

    @property
    def state(self) -> SystemState:
        return self._state

    def handle(self, event_type: EventType) -> TransitionResult:
        """Apply an event and return the resulting transition.

        Raises IllegalTransitionError for any (state, event) pair absent
        from the transition table, per AGENTS.md section 7.2: "any pair
        not in this table is an illegal transition and must raise, never
        silently pass."
        """
        from_state = self._state

        if event_type == EventType.SYSTEM_DISARMED:
            to_state = SystemState.DISARMED
        elif event_type == EventType.CAMERA_OFFLINE:
            to_state = from_state
        else:
            to_state = self._lookup(from_state, event_type)

        self._state = to_state
        return TransitionResult(
            from_state=from_state, event=event_type, to_state=to_state
        )

    @staticmethod
    def _lookup(from_state: SystemState, event_type: EventType) -> SystemState:
        for transition in TRANSITIONS:
            if transition.from_state is from_state and transition.event is event_type:
                return transition.to_state
        raise IllegalTransitionError(
            f"No legal transition for event '{event_type}' in state '{from_state}'"
        )
