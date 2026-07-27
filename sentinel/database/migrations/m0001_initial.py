"""Migration 1: schema_version and events tables."""

from sqlalchemy import Connection, text


def upgrade(connection: Connection) -> None:
    connection.execute(
        text(
            """
            CREATE TABLE events (
                id INTEGER PRIMARY KEY,
                timestamp DATETIME NOT NULL,
                type VARCHAR NOT NULL,
                source VARCHAR NOT NULL,
                severity VARCHAR NOT NULL,
                state_at_time VARCHAR NOT NULL,
                metadata JSON NOT NULL
            )
            """
        )
    )
    connection.execute(text("CREATE INDEX ix_events_timestamp ON events (timestamp)"))
    connection.execute(text("CREATE INDEX ix_events_type ON events (type)"))
    connection.execute(text("CREATE INDEX ix_events_severity ON events (severity)"))
