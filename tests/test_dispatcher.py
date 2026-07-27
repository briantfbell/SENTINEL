import asyncio
from pathlib import Path

import pytest

from sentinel.config import StateSettings
from sentinel.database import EventRepository, apply_migrations, open_engine
from sentinel.events import EventBus, Notification, TimerService
from sentinel.models import EventType, StartTimer, SystemState, TimerName
from sentinel.rules import RuleEngine
from sentinel.services import DispatchResult, EventDispatcher
from sentinel.state import StateMachine


async def _no_wait(_seconds: float) -> None:
    pass


def _build_dispatcher(
    tmp_path: Path,
) -> tuple[EventDispatcher, EventBus, EventRepository]:
    engine = open_engine(tmp_path / "sentinel.db")
    apply_migrations(engine)
    repository = EventRepository(engine)
    bus = EventBus()
    timers = TimerService(bus, sleep=_no_wait)
    dispatcher = EventDispatcher(
        state_machine=StateMachine(),
        rule_engine=RuleEngine(),
        event_repository=repository,
        timer_service=timers,
        state_settings=StateSettings(),
    )
    bus.subscribe(dispatcher.on_notification)
    return dispatcher, bus, repository


@pytest.mark.asyncio
async def test_publishing_drives_a_transition_and_persists_it(tmp_path: Path) -> None:
    _dispatcher, bus, repository = _build_dispatcher(tmp_path)

    await bus.publish(EventType.SYSTEM_ARMED, source="api")

    logged = repository.query()
    assert len(logged) == 1
    assert logged[0].type == EventType.SYSTEM_ARMED
    assert logged[0].state_at_time == SystemState.DISARMED


@pytest.mark.asyncio
async def test_dispatch_result_returns_expected_actions(tmp_path: Path) -> None:
    dispatcher, bus, _repository = _build_dispatcher(tmp_path)
    results: list[DispatchResult] = []

    async def capture(notification: Notification) -> None:
        results.append(await dispatcher.on_notification(notification))

    # Replace the default subscription so we can capture DispatchResult too.
    bus.unsubscribe(dispatcher.on_notification)
    bus.subscribe(capture)

    await bus.publish(EventType.SYSTEM_ARMED, source="api")
    await bus.publish(EventType.PERSON_DETECTED, source="detector")

    assert results[0].transition.to_state == SystemState.ARMED
    assert results[1].transition.to_state == SystemState.ALERT
    assert StartTimer(TimerName.GRACE) in results[1].actions


@pytest.mark.asyncio
async def test_full_escalation_ladder_via_mock_timers(tmp_path: Path) -> None:
    """ARMED -> ALERT -> WARNING -> ESCALATED -> COOLDOWN -> ARMED, driven
    entirely by mock detection events and instantly-firing timers — the
    same loop slice 8's end-to-end MVP demo will exercise, minus the
    dashboard and real providers.
    """
    dispatcher, bus, repository = _build_dispatcher(tmp_path)

    await bus.publish(EventType.SYSTEM_ARMED, source="api")
    assert dispatcher._state_machine.state == SystemState.ARMED

    await bus.publish(EventType.PERSON_DETECTED, source="detector")
    assert dispatcher._state_machine.state == SystemState.ALERT
    await asyncio.sleep(0)  # let the grace timer's mock sleep complete
    assert dispatcher._state_machine.state == SystemState.WARNING
    await asyncio.sleep(0)  # warning timer
    assert dispatcher._state_machine.state == SystemState.ESCALATED

    await bus.publish(EventType.PERSON_GONE, source="detector")
    assert dispatcher._state_machine.state == SystemState.COOLDOWN
    await asyncio.sleep(0)  # cooldown timer
    assert dispatcher._state_machine.state == SystemState.ARMED

    event_types = [event.type for event in repository.query()]
    assert event_types == [
        EventType.SYSTEM_ARMED,
        EventType.PERSON_DETECTED,
        EventType.GRACE_EXPIRED,
        EventType.WARNING_EXPIRED,
        EventType.PERSON_GONE,
        EventType.COOLDOWN_EXPIRED,
    ]
