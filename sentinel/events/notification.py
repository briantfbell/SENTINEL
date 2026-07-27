"""What travels on the event bus, before the state machine has seen it."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from sentinel.models import EventType, Severity


@dataclass(frozen=True)
class Notification:
    """A message published on the bus.

    Deliberately lighter than the persisted `Event`: it has no
    `state_at_time`, because the publisher doesn't know the system state
    and shouldn't have to — that's filled in by whatever subscriber runs
    the event through the state machine (AGENTS.md section 4.5).
    """

    type: EventType
    timestamp: datetime
    source: str
    severity: Severity = Severity.INFO
    metadata: dict[str, Any] = field(default_factory=dict)
