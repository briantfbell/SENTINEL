"""Wires the state machine, rule engine, event log, and timers together.

This is not the full composition root (that's `container.py`, added once
the API and providers exist) — it's the minimal orchestration slice 4
needs: publishing a notification must drive a transition, persist it,
compute the action list, and — for the two actions a TimerService can
already execute without any hardware — actually run them.
"""

from dataclasses import dataclass

from sentinel.config import StateSettings
from sentinel.database import EventRepository
from sentinel.events import Notification, TimerService
from sentinel.models import (
    Action,
    CancelTimers,
    Event,
    EventType,
    StartTimer,
    TimerName,
)
from sentinel.rules import RuleEngine
from sentinel.state import StateMachine, TransitionResult

_TIMER_EVENT: dict[TimerName, EventType] = {
    TimerName.GRACE: EventType.GRACE_EXPIRED,
    TimerName.WARNING: EventType.WARNING_EXPIRED,
    TimerName.COOLDOWN: EventType.COOLDOWN_EXPIRED,
}


@dataclass(frozen=True)
class DispatchResult:
    """The outcome of processing one notification."""

    transition: TransitionResult
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
    ) -> None:
        self._state_machine = state_machine
        self._rule_engine = rule_engine
        self._event_repository = event_repository
        self._timer_service = timer_service
        self._timer_seconds: dict[TimerName, float] = {
            TimerName.GRACE: state_settings.grace_seconds,
            TimerName.WARNING: state_settings.warning_seconds,
            TimerName.COOLDOWN: state_settings.cooldown_seconds,
        }

    async def on_notification(self, notification: Notification) -> DispatchResult:
        """Transition, persist, compute actions, and execute any timer actions."""
        transition = self._state_machine.handle(notification.type)
        actions = self._rule_engine.actions_for(
            notification.type, transition.from_state
        )

        self._event_repository.add(
            Event(
                type=notification.type,
                timestamp=notification.timestamp,
                source=notification.source,
                severity=notification.severity,
                state_at_time=transition.from_state,
                metadata=notification.metadata,
            )
        )

        self._execute_timer_actions(actions, source=notification.source)

        return DispatchResult(transition=transition, actions=actions)

    def _execute_timer_actions(self, actions: list[Action], *, source: str) -> None:
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
