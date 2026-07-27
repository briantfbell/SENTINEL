"""Wires the state machine, rule engine, event log, timers, and audio
together. Not the full composition root (that's `container.py`) — this
is the orchestration layer: publishing a notification must drive a
transition (when the event is state-machine-relevant), persist it,
compute the action list, and execute the actions that don't yet need a
camera or detector.
"""

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path

from sentinel.audio import AudioPlayer
from sentinel.config import AudioSettings, StateSettings
from sentinel.database import EventRepository
from sentinel.events import EventBus, Notification, TimerService
from sentinel.models import (
    Action,
    AnnouncementLevel,
    CancelTimers,
    Event,
    EventType,
    PlayAnnouncement,
    StartTimer,
    StopAudio,
    TimerName,
)
from sentinel.rules import RuleEngine
from sentinel.state import TRANSITIONS, StateMachine, TransitionResult

_TIMER_EVENT: dict[TimerName, EventType] = {
    TimerName.GRACE: EventType.GRACE_EXPIRED,
    TimerName.WARNING: EventType.WARNING_EXPIRED,
    TimerName.COOLDOWN: EventType.COOLDOWN_EXPIRED,
}

# Only these event types ever appear in the transition table (AGENTS.md
# section 7.2) — the rest of the taxonomy (section 7.3) is informational:
# logged, and available to the rule engine, but never routed through the
# state machine. Publishing one of those must not raise.
_STATE_MACHINE_EVENTS: set[EventType] = {t.event for t in TRANSITIONS} | {
    EventType.SYSTEM_DISARMED,
    EventType.CAMERA_OFFLINE,
}

# Runs a blocking call off the event loop. Injectable so tests can run it
# inline instead of through a real thread pool — the same "inject a
# clock" reasoning as TimerService's Sleeper (AGENTS.md section 9).
BlockingRunner = Callable[..., Awaitable[None]]


@dataclass(frozen=True)
class DispatchResult:
    """The outcome of processing one notification."""

    transition: TransitionResult | None
    actions: list[Action]


class EventDispatcher:
    """Subscribes to the bus and processes each notification in order."""

    def __init__(
        self,
        state_machine: StateMachine,
        rule_engine: RuleEngine,
        event_repository: EventRepository,
        timer_service: TimerService,
        state_settings: StateSettings,
        bus: EventBus,
        audio_player: AudioPlayer,
        audio_settings: AudioSettings,
        run_blocking: BlockingRunner = asyncio.to_thread,
    ) -> None:
        self._state_machine = state_machine
        self._rule_engine = rule_engine
        self._event_repository = event_repository
        self._timer_service = timer_service
        self._bus = bus
        self._audio_player = audio_player
        self._run_blocking = run_blocking
        self._timer_seconds: dict[TimerName, float] = {
            TimerName.GRACE: state_settings.grace_seconds,
            TimerName.WARNING: state_settings.warning_seconds,
            TimerName.COOLDOWN: state_settings.cooldown_seconds,
        }
        self._announcements: dict[AnnouncementLevel, tuple[Path, float]] = {
            AnnouncementLevel.WARNING: (
                audio_settings.warning_clip_path,
                audio_settings.warning_volume,
            ),
            AnnouncementLevel.ESCALATED: (
                audio_settings.escalated_clip_path,
                audio_settings.escalated_volume,
            ),
        }

    async def on_notification(self, notification: Notification) -> DispatchResult:
        """Transition (if relevant), persist, compute actions, execute them."""
        if notification.type in _STATE_MACHINE_EVENTS:
            transition = self._state_machine.handle(notification.type)
            state_at_time = transition.from_state
        else:
            transition = None
            state_at_time = self._state_machine.state

        actions = self._rule_engine.actions_for(notification.type, state_at_time)

        self._event_repository.add(
            Event(
                type=notification.type,
                timestamp=notification.timestamp,
                source=notification.source,
                severity=notification.severity,
                state_at_time=state_at_time,
                metadata=notification.metadata,
            )
        )

        if transition is not None and transition.from_state != transition.to_state:
            # A state change invalidates any timer scheduled by the state
            # being left (e.g. the grace timer if PersonGone cuts ALERT
            # short) — left running, it would later fire into a state
            # that doesn't accept it and raise IllegalTransitionError.
            # DECISIONS.md 0013.
            self._timer_service.cancel_all()

        self._execute_actions(actions, source=notification.source)

        return DispatchResult(transition=transition, actions=actions)

    def _execute_actions(self, actions: list[Action], *, source: str) -> None:
        for action in actions:
            if isinstance(action, StartTimer):
                self._timer_service.start(
                    action.name,
                    self._timer_seconds[action.name],
                    _TIMER_EVENT[action.name],
                    source=source,
                )
            elif isinstance(action, CancelTimers):
                self._timer_service.cancel_all()
            elif isinstance(action, PlayAnnouncement):
                self._play_announcement(action.level, source=source)
            elif isinstance(action, StopAudio):
                self._audio_player.stop()

    def _play_announcement(self, level: AnnouncementLevel, *, source: str) -> None:
        clip_path, volume = self._announcements[level]
        asyncio.create_task(self._run_announcement(clip_path, volume, source=source))

    async def _run_announcement(
        self, clip_path: Path, volume: float, *, source: str
    ) -> None:
        await self._bus.publish(EventType.ANNOUNCEMENT_STARTED, source=source)
        await self._run_blocking(self._audio_player.play, clip_path, volume)
        await self._bus.publish(EventType.ANNOUNCEMENT_FINISHED, source=source)
