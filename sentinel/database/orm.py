"""Declarative ORM models. Column shape must stay in sync with the DDL in
`database/migrations/` by hand — there is no autogeneration (AGENTS.md
section 8.2 prohibits Alembic for the MVP).
"""

from datetime import datetime

from sqlalchemy import JSON, DateTime, Index
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class EventRecord(Base):
    """Maps to the `events` table (AGENTS.md section 8.2)."""

    __tablename__ = "events"
    __table_args__ = (
        Index("ix_events_timestamp", "timestamp"),
        Index("ix_events_type", "type"),
        Index("ix_events_severity", "severity"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    type: Mapped[str]
    source: Mapped[str]
    severity: Mapped[str]
    state_at_time: Mapped[str]
    # Named metadata_json in Python: `metadata` is reserved on Base for the
    # table's own MetaData. Still stored as the "metadata" column in SQLite.
    metadata_json: Mapped[dict[str, object]] = mapped_column("metadata", JSON)


class SessionRecord(Base):
    """Maps to the `sessions` table (AGENTS.md section 8.2)."""

    __tablename__ = "sessions"

    token_hash: Mapped[str] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    client_ip: Mapped[str]
