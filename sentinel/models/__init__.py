"""Domain types: enums, events, DTOs. May import config, nothing else internal."""

from sentinel.models.enums import EventType, Severity, SystemState
from sentinel.models.events import Event

__all__ = ["Event", "EventType", "Severity", "SystemState"]
