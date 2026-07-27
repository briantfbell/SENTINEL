"""The Recording domain DTO (AGENTS.md section 8.2)."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Recording:
    started_at: datetime
    ended_at: datetime
    path: str
    size_bytes: int
    trigger_event_id: int | None = None
