from sentinel.models import (
    CancelTimers,
    EventType,
    LogEvent,
    RefreshPresence,
    SetHealthDegraded,
    StartTimer,
    StopAudio,
    SystemState,
    TimerName,
)
from sentinel.rules import RuleEngine


def test_start_recording_and_grace_timer_on_first_detection() -> None:
    engine = RuleEngine()

    actions = engine.actions_for(EventType.PERSON_DETECTED, SystemState.ARMED)

    assert StartTimer(TimerName.GRACE) in actions


def test_continued_presence_only_refreshes() -> None:
    engine = RuleEngine()

    actions = engine.actions_for(EventType.PERSON_DETECTED, SystemState.WARNING)

    assert actions == [RefreshPresence()]


def test_disarmed_wildcard_applies_from_any_state() -> None:
    engine = RuleEngine()

    for state in SystemState:
        actions = engine.actions_for(EventType.SYSTEM_DISARMED, state)
        assert StopAudio() in actions
        assert CancelTimers() in actions


def test_armed_specific_camera_offline_overrides_wildcard() -> None:
    engine = RuleEngine()

    armed_actions = engine.actions_for(EventType.CAMERA_OFFLINE, SystemState.ARMED)
    other_actions = engine.actions_for(EventType.CAMERA_OFFLINE, SystemState.ALERT)

    assert armed_actions == [LogEvent()]
    assert other_actions == [LogEvent(), SetHealthDegraded()]


def test_unmapped_event_returns_no_actions() -> None:
    engine = RuleEngine()

    actions = engine.actions_for(EventType.PIN_ACCEPTED, SystemState.DISARMED)

    assert actions == []
