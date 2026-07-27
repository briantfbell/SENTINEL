import asyncio
from collections.abc import Callable
from pathlib import Path

import pytest

from sentinel.audio import MockAudioPlayer
from sentinel.config import AudioSettings, StateSettings
from sentinel.database import EventRepository, apply_migrations, open_engine
from sentinel.events import EventBus, Notification, TimerService
from sentinel.models import EventType, StartTimer, SystemState, TimerName
from sentinel.rules import RuleEngine
from sentinel.services import DispatchResult, EventDispatcher
from sentinel.state import StateMachine


async def _no_wait(_seconds: float) -> None:
    pass


async def _run_inline(func: Callable[..., None], *args: object) -> None:
    """Runs a "blocking" call in place instead of a real thread pool, so
    tests stay deterministic (AGENTS.md section 9: inject a clock)."""
    func(*args)


def _build_dispatcher(
    tmp_path: Path,
) -> tuple[EventDispatcher, EventBus, EventRepository, MockAudioPlayer]:
    engine = open_engine(tmp_path / "sentinel.db")
    apply_migrations(engine)
    repository = EventRepository(engine)
    bus = EventBus()
    timers = TimerService(bus, sleep=_no_wait)
    audio_player = MockAudioPlayer()
    dispatcher = EventDispatcher(
        state_machine=StateMachine(),
        rule_engine=RuleEngine(),
        event_repository=repository,
        timer_service=timers,
        state_settings=StateSettings(),
        bus=bus,
        audio_player=audio_player,
        audio_settings=AudioSettings(),
        run_blocking=_run_inline,
    )
    bus.subscribe(dispatcher.on_notification)
    return dispatcher, bus, repository, audio_player


@pytest.mark.asyncio
async def test_publishing_drives_a_transition_and_persists_it(tmp_path: Path) -> None:
    _dispatcher, bus, repository, _audio = _build_dispatcher(tmp_path)

    await bus.publish(EventType.SYSTEM_ARMED, source="api")

    logged = repository.query()
    assert len(logged) == 1
    assert logged[0].type == EventType.SYSTEM_ARMED
    assert logged[0].state_at_time == SystemState.DISARMED


@pytest.mark.asyncio
async def test_dispatch_result_returns_expected_actions(tmp_path: Path) -> None:
    dispatcher, bus, _repository, _audio = _build_dispatcher(tmp_path)
    results: list[DispatchResult] = []

    async def capture(notification: Notification) -> None:
        results.append(await dispatcher.on_notification(notification))

    # Replace the default subscription so we can capture DispatchResult too.
    bus.unsubscribe(dispatcher.on_notification)
    bus.subscribe(capture)

    await bus.publish(EventType.SYSTEM_ARMED, source="api")
    await bus.publish(EventType.PERSON_DETECTED, source="detector")

    assert results[0].transition is not None
    assert results[0].transition.to_state == SystemState.ARMED
    assert results[1].transition is not None
    assert results[1].transition.to_state == SystemState.ALERT
    assert StartTimer(TimerName.GRACE) in results[1].actions


@pytest.mark.asyncio
async def test_informational_events_do_not_crash_or_change_state(
    tmp_path: Path,
) -> None:
    """AnnouncementStarted/Finished, PinAccepted, DiskSpaceLow, etc. are in
    the section 7.3 taxonomy but never appear in the section 7.2 transition
    table — publishing one must log it, not raise IllegalTransitionError.
    """
    dispatcher, bus, repository, _audio = _build_dispatcher(tmp_path)

    await bus.publish(EventType.DISK_SPACE_LOW, source="retention")

    assert dispatcher._state_machine.state == SystemState.DISARMED
    logged = repository.query()
    assert len(logged) == 1
    assert logged[0].type == EventType.DISK_SPACE_LOW
    assert logged[0].state_at_time == SystemState.DISARMED


@pytest.mark.asyncio
async def test_grace_expired_plays_announcement_and_logs_it(tmp_path: Path) -> None:
    _dispatcher, bus, repository, audio = _build_dispatcher(tmp_path)
    await bus.publish(EventType.SYSTEM_ARMED, source="api")
    await bus.publish(EventType.PERSON_DETECTED, source="detector")

    await asyncio.sleep(0)  # let the grace timer fire -> WARNING
    await asyncio.sleep(0)  # let the announcement task it scheduled run

    assert len(audio.calls) == 1
    assert audio.calls[0].clip_path == AudioSettings().warning_clip_path
    assert audio.calls[0].volume == AudioSettings().warning_volume

    event_types = [event.type for event in repository.query()]
    assert EventType.ANNOUNCEMENT_STARTED in event_types
    assert EventType.ANNOUNCEMENT_FINISHED in event_types


@pytest.mark.asyncio
async def test_stop_audio_action_calls_player_stop(tmp_path: Path) -> None:
    _dispatcher, bus, _repository, audio = _build_dispatcher(tmp_path)
    await bus.publish(EventType.SYSTEM_ARMED, source="api")
    await bus.publish(EventType.PERSON_DETECTED, source="detector")
    await asyncio.sleep(0)  # let the grace timer fire -> WARNING

    await bus.publish(EventType.PERSON_GONE, source="detector")  # -> COOLDOWN

    assert audio.stop_count == 1


@pytest.mark.asyncio
async def test_leaving_warning_early_cancels_its_timer(tmp_path: Path) -> None:
    """Regression test for DECISIONS.md 0013: the still-pending warning
    timer must not survive into COOLDOWN and fire WarningExpired there.
    """
    dispatcher, bus, _repository, _audio = _build_dispatcher(tmp_path)
    await bus.publish(EventType.SYSTEM_ARMED, source="api")
    await bus.publish(EventType.PERSON_DETECTED, source="detector")
    await asyncio.sleep(0)  # grace timer fires -> WARNING (also starts warning timer)
    await asyncio.sleep(0)  # let the announcement task settle

    await bus.publish(EventType.PERSON_GONE, source="detector")  # -> COOLDOWN
    assert dispatcher._state_machine.state == SystemState.COOLDOWN

    # If the warning timer weren't cancelled, this would fire WarningExpired
    # into COOLDOWN and raise IllegalTransitionError inside the timer task
    # — which -W error::pytest.PytestUnraisableExceptionWarning turns into
    # a test failure instead of a silently swallowed background exception.
    await asyncio.sleep(0)


@pytest.mark.asyncio
async def test_full_escalation_ladder_via_mock_timers(tmp_path: Path) -> None:
    """ARMED -> ALERT -> WARNING -> ESCALATED -> COOLDOWN -> ARMED, driven
    entirely by mock detection events and instantly-firing timers — the
    same loop slice 8's end-to-end MVP demo will exercise, minus the
    dashboard and real providers.
    """
    dispatcher, bus, repository, audio = _build_dispatcher(tmp_path)

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

    assert len(audio.calls) == 2  # warning announcement, escalated announcement

    event_types = [event.type for event in repository.query()]
    for expected in (
        EventType.SYSTEM_ARMED,
        EventType.PERSON_DETECTED,
        EventType.GRACE_EXPIRED,
        EventType.ANNOUNCEMENT_STARTED,
        EventType.ANNOUNCEMENT_FINISHED,
        EventType.WARNING_EXPIRED,
        EventType.PERSON_GONE,
        EventType.COOLDOWN_EXPIRED,
    ):
        assert expected in event_types
    assert event_types.count(EventType.ANNOUNCEMENT_STARTED) == 2
    assert event_types.count(EventType.ANNOUNCEMENT_FINISHED) == 2
