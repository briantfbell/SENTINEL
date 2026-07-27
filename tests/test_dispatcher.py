import asyncio
from collections.abc import Callable
from pathlib import Path

import pytest

from sentinel.audio import MockAudioPlayer
from sentinel.camera import MockCamera
from sentinel.config import AudioSettings, DetectionSettings, StateSettings
from sentinel.database import (
    EventRepository,
    RecordingRepository,
    apply_migrations,
    open_engine,
)
from sentinel.detection import Detection, DetectionDebouncer, MockDetector
from sentinel.events import EventBus, Notification, TimerService
from sentinel.models import EventType, StartTimer, SystemState, TimerName
from sentinel.rules import RuleEngine
from sentinel.services import DetectionLoop, DispatchResult, EventDispatcher, Recorder
from sentinel.state import StateMachine


async def _no_wait(_seconds: float) -> None:
    pass


async def _yielding_sleep(_seconds: float) -> None:
    """A fast sleeper that still cooperatively yields once, unlike a true
    no-op — DetectionLoop's `while True` would otherwise never give the
    test's own coroutine a turn to run (AGENTS.md section 9: inject a
    clock, not a way to skip yielding entirely).
    """
    await asyncio.sleep(0)


async def _run_inline(func: Callable[..., None], *args: object) -> None:
    """Runs a "blocking" call in place instead of a real thread pool, so
    tests stay deterministic (AGENTS.md section 9: inject a clock)."""
    func(*args)


def _build_dispatcher(
    tmp_path: Path, *, detector_script: list[list[Detection]] | None = None
) -> tuple[
    EventDispatcher, EventBus, EventRepository, RecordingRepository, MockAudioPlayer
]:
    engine = open_engine(tmp_path / "sentinel.db")
    apply_migrations(engine)
    event_repository = EventRepository(engine)
    recording_repository = RecordingRepository(engine)
    bus = EventBus()
    timers = TimerService(bus, sleep=_no_wait)
    audio_player = MockAudioPlayer()
    camera_provider = MockCamera()
    recorder = Recorder(
        camera_provider=camera_provider,
        recording_repository=recording_repository,
        recordings_path=tmp_path / "recordings",
    )
    detection_loop = DetectionLoop(
        camera_provider=camera_provider,
        detector=MockDetector(detector_script),
        debouncer=DetectionDebouncer(DetectionSettings()),
        bus=bus,
        interval_seconds=0.0,
        sleep=_yielding_sleep,
    )
    dispatcher = EventDispatcher(
        state_machine=StateMachine(),
        rule_engine=RuleEngine(),
        event_repository=event_repository,
        timer_service=timers,
        state_settings=StateSettings(),
        bus=bus,
        audio_player=audio_player,
        audio_settings=AudioSettings(),
        recorder=recorder,
        detection_loop=detection_loop,
        run_blocking=_run_inline,
    )
    bus.subscribe(dispatcher.on_notification)
    return dispatcher, bus, event_repository, recording_repository, audio_player


@pytest.mark.asyncio
async def test_publishing_drives_a_transition_and_persists_it(tmp_path: Path) -> None:
    _dispatcher, bus, event_repository, _recordings, _audio = _build_dispatcher(
        tmp_path
    )

    await bus.publish(EventType.SYSTEM_ARMED, source="api")

    logged = event_repository.query()
    assert len(logged) == 1
    assert logged[0].type == EventType.SYSTEM_ARMED
    assert logged[0].state_at_time == SystemState.DISARMED


@pytest.mark.asyncio
async def test_dispatch_result_returns_expected_actions(tmp_path: Path) -> None:
    dispatcher, bus, _events, _recordings, _audio = _build_dispatcher(tmp_path)
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
    dispatcher, bus, event_repository, _recordings, _audio = _build_dispatcher(tmp_path)

    await bus.publish(EventType.DISK_SPACE_LOW, source="retention")

    assert dispatcher._state_machine.state == SystemState.DISARMED
    logged = event_repository.query()
    assert len(logged) == 1
    assert logged[0].type == EventType.DISK_SPACE_LOW
    assert logged[0].state_at_time == SystemState.DISARMED


@pytest.mark.asyncio
async def test_grace_expired_plays_announcement_and_logs_it(tmp_path: Path) -> None:
    _dispatcher, bus, event_repository, _recordings, audio = _build_dispatcher(tmp_path)
    await bus.publish(EventType.SYSTEM_ARMED, source="api")
    await bus.publish(EventType.PERSON_DETECTED, source="detector")

    await asyncio.sleep(0)  # let the grace timer fire -> WARNING
    await asyncio.sleep(0)  # let the announcement task it scheduled run

    assert len(audio.calls) == 1
    assert audio.calls[0].clip_path == AudioSettings().warning_clip_path
    assert audio.calls[0].volume == AudioSettings().warning_volume

    event_types = [event.type for event in event_repository.query()]
    assert EventType.ANNOUNCEMENT_STARTED in event_types
    assert EventType.ANNOUNCEMENT_FINISHED in event_types


@pytest.mark.asyncio
async def test_stop_audio_action_calls_player_stop(tmp_path: Path) -> None:
    _dispatcher, bus, _events, _recordings, audio = _build_dispatcher(tmp_path)
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
    dispatcher, bus, _events, _recordings, _audio = _build_dispatcher(tmp_path)
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
async def test_arming_starts_detection_loop_and_disarming_stops_it(
    tmp_path: Path,
) -> None:
    dispatcher, bus, _events, _recordings, _audio = _build_dispatcher(tmp_path)

    await bus.publish(EventType.SYSTEM_ARMED, source="api")
    assert dispatcher._detection_loop._task is not None

    await bus.publish(EventType.SYSTEM_DISARMED, source="api")
    assert dispatcher._detection_loop._task is None


@pytest.mark.asyncio
async def test_detection_loop_drives_person_detected_through_the_bus(
    tmp_path: Path,
) -> None:
    """The mock detector, not a manual publish call, is what produces
    PersonDetected here — proving the whole vertical slice (camera ->
    detector -> debouncer -> bus -> dispatcher -> state machine) works,
    not just the dispatcher in isolation.
    """
    hit = [Detection(confidence=0.9, box_area_ratio=0.5)]
    script = [[], [], hit, hit, hit]  # consecutive_frames defaults to 3
    dispatcher, bus, event_repository, _recordings, _audio = _build_dispatcher(
        tmp_path, detector_script=script
    )

    await bus.publish(EventType.SYSTEM_ARMED, source="api")
    for _ in range(20):  # generous margin over len(script) scheduling ticks
        await asyncio.sleep(0)

    # With instant mock timers, the ladder keeps advancing past ALERT once
    # detection fires — the point here is that detection (not a manual
    # publish call) is what started it at all.
    assert dispatcher._state_machine.state != SystemState.ARMED
    event_types = [event.type for event in event_repository.query()]
    assert EventType.PERSON_DETECTED in event_types

    await bus.publish(
        EventType.SYSTEM_DISARMED, source="api"
    )  # stop the detection loop


@pytest.mark.asyncio
async def test_full_escalation_ladder_via_mock_timers(tmp_path: Path) -> None:
    """ARMED -> ALERT -> WARNING -> ESCALATED -> COOLDOWN -> ARMED, driven
    entirely by mock detection events and instantly-firing timers — the
    same loop slice 8's end-to-end MVP demo exercises, minus the
    dashboard and real providers.
    """
    dispatcher, bus, event_repository, recording_repository, audio = _build_dispatcher(
        tmp_path
    )

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

    event_types = [event.type for event in event_repository.query()]
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

    recordings = recording_repository.recent(10)
    assert len(recordings) == 1
    assert recordings[0].ended_at > recordings[0].started_at
    assert recordings[0].size_bytes > 0

    await bus.publish(
        EventType.SYSTEM_DISARMED, source="api"
    )  # stop the detection loop
