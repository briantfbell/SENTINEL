"""Declarative action descriptions the rule engine produces (AGENTS.md
section 7.4). Pure data — no I/O, no provider calls. An executor in
`services` is responsible for dispatching each one to the right
provider; that executor grows slice by slice as providers are added.
"""

from dataclasses import dataclass

from sentinel.models.enums import AnnouncementLevel, TimerName


@dataclass(frozen=True)
class LogEvent:
    """Write the triggering event to the log. No side effect beyond that."""


@dataclass(frozen=True)
class RefreshDashboard:
    pass


@dataclass(frozen=True)
class RefreshPresence:
    """Continued presence while already alerting: no new escalation."""


@dataclass(frozen=True)
class StartRecording:
    pass


@dataclass(frozen=True)
class StopRecording:
    pass


@dataclass(frozen=True)
class FinalizeClip:
    pass


@dataclass(frozen=True)
class PlayAnnouncement:
    level: AnnouncementLevel


@dataclass(frozen=True)
class StopAudio:
    pass


@dataclass(frozen=True)
class StartTimer:
    name: TimerName


@dataclass(frozen=True)
class CancelTimers:
    pass


@dataclass(frozen=True)
class SetHealthDegraded:
    degraded: bool = True


Action = (
    LogEvent
    | RefreshDashboard
    | RefreshPresence
    | StartRecording
    | StopRecording
    | FinalizeClip
    | PlayAnnouncement
    | StopAudio
    | StartTimer
    | CancelTimers
    | SetHealthDegraded
)
