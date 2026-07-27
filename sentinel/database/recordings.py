"""Read/write access to the recordings table (AGENTS.md sections 4.8, 8.2)."""

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from sentinel.database.orm import RecordingRecord
from sentinel.database.timezones import ensure_utc
from sentinel.models import Recording


class RecordingRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def add(self, recording: Recording) -> int:
        record = RecordingRecord(
            started_at=recording.started_at,
            ended_at=recording.ended_at,
            path=recording.path,
            trigger_event_id=recording.trigger_event_id,
            size_bytes=recording.size_bytes,
        )
        with Session(self._engine) as session:
            session.add(record)
            session.commit()
            return record.id

    def recent(self, limit: int) -> list[Recording]:
        """Return the most recent recordings, newest first."""
        statement = (
            select(RecordingRecord)
            .order_by(RecordingRecord.started_at.desc())
            .limit(limit)
        )
        with Session(self._engine) as session:
            records = session.execute(statement).scalars().all()
            return [
                Recording(
                    started_at=ensure_utc(r.started_at),
                    ended_at=ensure_utc(r.ended_at),
                    path=r.path,
                    size_bytes=r.size_bytes,
                    trigger_event_id=r.trigger_event_id,
                )
                for r in records
            ]
