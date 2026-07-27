"""Fixed domain vocabulary. Values here are specified in AGENTS.md and are
not to be extended casually — see section 13, "changing the state set or
event taxonomy" requires stopping to ask.
"""

from enum import StrEnum


class SystemState(StrEnum):
    """AGENTS.md section 7.1. The state machine is the only writer of this."""

    DISARMED = "disarmed"
    ARMED = "armed"
    ALERT = "alert"
    WARNING = "warning"
    ESCALATED = "escalated"
    COOLDOWN = "cooldown"


class Severity(StrEnum):
    """Event severity, used for filtering the event log (section 8.2)."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class EventType(StrEnum):
    """The event taxonomy from AGENTS.md section 7.3."""

    PERSON_DETECTED = "person_detected"
    PERSON_GONE = "person_gone"
    SYSTEM_ARMED = "system_armed"
    SYSTEM_DISARMED = "system_disarmed"
    CAMERA_ONLINE = "camera_online"
    CAMERA_OFFLINE = "camera_offline"
    RECORDING_STARTED = "recording_started"
    RECORDING_STOPPED = "recording_stopped"
    ANNOUNCEMENT_STARTED = "announcement_started"
    ANNOUNCEMENT_FINISHED = "announcement_finished"
    GRACE_EXPIRED = "grace_expired"
    WARNING_EXPIRED = "warning_expired"
    COOLDOWN_EXPIRED = "cooldown_expired"
    PIN_ACCEPTED = "pin_accepted"
    PIN_REJECTED = "pin_rejected"
    LOCKOUT_STARTED = "lockout_started"
    DISK_SPACE_LOW = "disk_space_low"
    DETECTOR_LAGGING = "detector_lagging"


class TimerName(StrEnum):
    """The three named timers in the escalation ladder (section 7.1)."""

    GRACE = "grace"
    WARNING = "warning"
    COOLDOWN = "cooldown"


class AnnouncementLevel(StrEnum):
    """Which announcement/volume a PlayAnnouncement action fires (section 7.2)."""

    WARNING = "warning"
    ESCALATED = "escalated"
