"""The Event domain model.

AGENTS.md section 7.3: events are frozen, immutable, and serializable.
This is the generic envelope persisted by the event log (section 8.2);
the event bus and rule engine built in slice 4 dispatch on `type`.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from sentinel.models.enums import EventType, Severity, SystemState


class Event(BaseModel):
    """A single occurrence in the system, timestamped and immutable."""

    model_config = ConfigDict(frozen=True)

    type: EventType
    timestamp: datetime
    source: str
    severity: Severity
    state_at_time: SystemState
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("timestamp")
    @classmethod
    def _require_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError(
                "timestamp must be timezone-aware UTC (AGENTS.md section 12)"
            )
        return value
