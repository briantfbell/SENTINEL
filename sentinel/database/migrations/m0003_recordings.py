"""Migration 3: recordings table (AGENTS.md section 8.2)."""

from sqlalchemy import Connection, text


def upgrade(connection: Connection) -> None:
    connection.execute(
        text(
            """
            CREATE TABLE recordings (
                id INTEGER PRIMARY KEY,
                started_at DATETIME NOT NULL,
                ended_at DATETIME NOT NULL,
                path VARCHAR NOT NULL,
                trigger_event_id INTEGER,
                size_bytes INTEGER NOT NULL
            )
            """
        )
    )
    connection.execute(
        text("CREATE INDEX ix_recordings_started_at ON recordings (started_at)")
    )
