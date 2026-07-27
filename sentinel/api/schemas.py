"""Request/response bodies. Never the ORM or domain models directly."""

from datetime import datetime

from pydantic import BaseModel

from sentinel.models import Event


class LoginRequest(BaseModel):
    pin: str


class MessageResponse(BaseModel):
    message: str


class StatusResponse(BaseModel):
    state: str


class EventOut(BaseModel):
    type: str
    timestamp: datetime
    source: str
    severity: str
    state_at_time: str

    @classmethod
    def from_event(cls, event: Event) -> "EventOut":
        return cls(
            type=event.type.value,
            timestamp=event.timestamp,
            source=event.source,
            severity=event.severity.value,
            state_at_time=event.state_at_time.value,
        )
