import pytest

from sentinel.models import EventType, SystemState
from sentinel.state import TRANSITIONS, IllegalTransitionError, StateMachine, Transition

ALL_STATES = list(SystemState)
ALL_EVENTS = list(EventType)

# Legal (state, event) pairs: every explicit table row plus the two
# wildcards, which are legal from every state.
_LEGAL_PAIRS: set[tuple[SystemState, EventType]] = (
    {(t.from_state, t.event) for t in TRANSITIONS}
    | {(state, EventType.SYSTEM_DISARMED) for state in ALL_STATES}
    | {(state, EventType.CAMERA_OFFLINE) for state in ALL_STATES}
)


@pytest.mark.parametrize(
    "transition", TRANSITIONS, ids=lambda t: f"{t.from_state}+{t.event}"
)
def test_every_transition_table_row(transition: Transition) -> None:
    machine = StateMachine(initial_state=transition.from_state)

    result = machine.handle(transition.event)

    assert result.to_state == transition.to_state
    assert machine.state == transition.to_state


@pytest.mark.parametrize("state", ALL_STATES)
def test_system_disarmed_wins_from_every_state(state: SystemState) -> None:
    machine = StateMachine(initial_state=state)

    result = machine.handle(EventType.SYSTEM_DISARMED)

    assert result.to_state == SystemState.DISARMED
    assert machine.state == SystemState.DISARMED


@pytest.mark.parametrize("state", ALL_STATES)
def test_camera_offline_never_changes_state(state: SystemState) -> None:
    machine = StateMachine(initial_state=state)

    result = machine.handle(EventType.CAMERA_OFFLINE)

    assert result.to_state == state
    assert machine.state == state


@pytest.mark.parametrize(
    ("state", "event"),
    [(state, event) for state in ALL_STATES for event in ALL_EVENTS],
)
def test_illegal_pairs_raise(state: SystemState, event: EventType) -> None:
    machine = StateMachine(initial_state=state)

    if (state, event) in _LEGAL_PAIRS:
        machine.handle(event)  # must not raise
        return

    with pytest.raises(IllegalTransitionError):
        machine.handle(event)


def test_illegal_event_does_not_change_state() -> None:
    machine = StateMachine(initial_state=SystemState.ARMED)

    with pytest.raises(IllegalTransitionError):
        machine.handle(EventType.WARNING_EXPIRED)

    assert machine.state == SystemState.ARMED
