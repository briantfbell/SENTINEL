"""Read/write access to the event log. The only place that translates
between the domain `Event` model and the `EventRecord` ORM row.
"""

from datetime import datetime

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from sentinel.database.orm import EventRecord
from sentinel.database.timezones import ensure_utc
from sentinel.models import Event, EventType, Severity, SystemState


class EventRepository:
    """Persists and queries events (AGENTS.md section 8.2)."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def add(self, event: Event) -> int:
        """Append an event to the log. Events are immutable once written.

        Returns the assigned row id, so callers (the dispatcher) can
        record which event triggered a recording.
        """
        record = EventRecord(
            timestamp=event.timestamp,
            type=event.type.value,
            source=event.source,
            severity=event.severity.value,
            state_at_time=event.state_at_time.value,
            metadata_json=event.metadata,
        )
        with Session(self._engine) as session:
            session.add(record)
            session.commit()
            return record.id

    def query(
        self,
        *,
        start: datetime | None = None,
        end: datetime | None = None,
        event_type: EventType | None = None,
        severity: Severity | None = None,
    ) -> list[Event]:
        """Return matching events ordered oldest to newest.

        Every filter is optional and combines with AND, matching the
        "searchable by time range, type, and severity" requirement in
        AGENTS.md section 8.2.
        """
        statement = select(EventRecord)
        if start is not None:
            statement = statement.where(EventRecord.timestamp >= start)
        if end is not None:
            statement = statement.where(EventRecord.timestamp <= end)
        if event_type is not None:
            statement = statement.where(EventRecord.type == event_type.value)
        if severity is not None:
            statement = statement.where(EventRecord.severity == severity.value)
        statement = statement.order_by(EventRecord.timestamp)

        with Session(self._engine) as session:
            records = session.execute(statement).scalars().all()
            return [_to_domain(record) for record in records]

    def recent(self, limit: int) -> list[Event]:
        """Return the most recent events, newest first, for dashboard display."""
        statement = (
            select(EventRecord).order_by(EventRecord.timestamp.desc()).limit(limit)
        )
        with Session(self._engine) as session:
            records = session.execute(statement).scalars().all()
            return [_to_domain(record) for record in records]


def _to_domain(record: EventRecord) -> Event:
    return Event(
        type=EventType(record.type),
        timestamp=ensure_utc(record.timestamp),
        source=record.source,
        severity=Severity(record.severity),
        state_at_time=SystemState(record.state_at_time),
        metadata=record.metadata_json,
    )
