"""The rule table: AGENTS.md section 7.2's Actions column, transposed
directly. Reads state, never writes it (section 4.5).
"""

from dataclasses import dataclass

from sentinel.models import (
    Action,
    AnnouncementLevel,
    CancelTimers,
    EventType,
    FinalizeClip,
    LogEvent,
    PlayAnnouncement,
    RefreshDashboard,
    RefreshPresence,
    SetHealthDegraded,
    StartRecording,
    StartTimer,
    StopAudio,
    StopRecording,
    SystemState,
    TimerName,
)


@dataclass(frozen=True)
class TableRule:
    """One row of the transition table's Actions column.

    `state=None` models a "_any_" wildcard row: it matches from every
    state. Specific-state rows must be listed before wildcard rows in
    RULES so they take precedence (AGENTS.md section 7.2 has both an
    ARMED-specific CameraOffline row and a wildcard one, with different
    actions).
    """

    event: EventType
    action_list: tuple[Action, ...]
    state: SystemState | None = None

    def matches(self, event_type: EventType, state: SystemState) -> bool:
        return self.event == event_type and (self.state is None or self.state == state)

    def actions(self, event_type: EventType, state: SystemState) -> list[Action]:
        return list(self.action_list)


# AGENTS.md section 7.2, in table order. Specific-state rows come before
# the two "_any_" wildcard rows at the end.
RULES: tuple[TableRule, ...] = (
    TableRule(
        state=SystemState.DISARMED,
        event=EventType.SYSTEM_ARMED,
        action_list=(LogEvent(), RefreshDashboard()),
    ),
    TableRule(
        state=SystemState.DISARMED,
        event=EventType.PERSON_DETECTED,
        action_list=(LogEvent(),),
    ),
    TableRule(
        state=SystemState.ARMED,
        event=EventType.PERSON_DETECTED,
        action_list=(StartRecording(), StartTimer(TimerName.GRACE)),
    ),
    TableRule(
        state=SystemState.ARMED,
        event=EventType.CAMERA_OFFLINE,
        action_list=(LogEvent(),),
    ),
    TableRule(
        state=SystemState.ALERT,
        event=EventType.GRACE_EXPIRED,
        action_list=(
            PlayAnnouncement(AnnouncementLevel.WARNING),
            StartTimer(TimerName.WARNING),
        ),
    ),
    TableRule(
        state=SystemState.ALERT,
        event=EventType.PERSON_GONE,
        action_list=(StartTimer(TimerName.COOLDOWN),),
    ),
    TableRule(
        state=SystemState.ALERT,
        event=EventType.PERSON_DETECTED,
        action_list=(RefreshPresence(),),
    ),
    TableRule(
        state=SystemState.WARNING,
        event=EventType.WARNING_EXPIRED,
        action_list=(PlayAnnouncement(AnnouncementLevel.ESCALATED),),
    ),
    TableRule(
        state=SystemState.WARNING,
        event=EventType.PERSON_GONE,
        action_list=(StopAudio(), StartTimer(TimerName.COOLDOWN)),
    ),
    TableRule(
        state=SystemState.WARNING,
        event=EventType.PERSON_DETECTED,
        action_list=(RefreshPresence(),),
    ),
    TableRule(
        state=SystemState.ESCALATED,
        event=EventType.PERSON_GONE,
        action_list=(StopAudio(), StartTimer(TimerName.COOLDOWN)),
    ),
    TableRule(
        state=SystemState.ESCALATED,
        event=EventType.PERSON_DETECTED,
        action_list=(RefreshPresence(),),
    ),
    TableRule(
        state=SystemState.COOLDOWN,
        event=EventType.PERSON_DETECTED,
        action_list=(StartTimer(TimerName.GRACE),),
    ),
    TableRule(
        state=SystemState.COOLDOWN,
        event=EventType.COOLDOWN_EXPIRED,
        action_list=(StopRecording(), FinalizeClip()),
    ),
    TableRule(
        state=None,
        event=EventType.SYSTEM_DISARMED,
        action_list=(StopAudio(), StopRecording(), CancelTimers()),
    ),
    TableRule(
        state=None,
        event=EventType.CAMERA_OFFLINE,
        action_list=(LogEvent(), SetHealthDegraded()),
    ),
)


class RuleEngine:
    """Looks up the action list for (event, state). Never mutates state."""

    def __init__(self, rules: tuple[TableRule, ...] = RULES) -> None:
        self._rules = rules

    def actions_for(self, event_type: EventType, state: SystemState) -> list[Action]:
        """Return the actions for the first matching rule, or [] if none match.

        An empty result is not an error: most event types (health, auth,
        camera-online, recording/announcement lifecycle) have no rule yet
        and simply produce no actions until a later slice adds one.
        """
        for rule in self._rules:
            if rule.matches(event_type, state):
                return rule.actions(event_type, state)
        return []
