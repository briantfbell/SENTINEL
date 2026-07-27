"""SQLite engine construction. Nothing outside this package imports sqlalchemy."""

from pathlib import Path

from sqlalchemy import Engine, event
from sqlalchemy import create_engine as _create_engine
from sqlalchemy.engine.interfaces import DBAPIConnection
from sqlalchemy.pool import ConnectionPoolEntry


def open_engine(database_path: Path) -> Engine:
    """Open (creating the parent directory if needed) a WAL-mode SQLite engine.

    WAL mode lets the API read the event log while a writer holds a
    transaction open, which matters once the dashboard is polling the
    same file the recorder is writing to (AGENTS.md section 8.2).
    """
    database_path.parent.mkdir(parents=True, exist_ok=True)
    engine = _create_engine(f"sqlite:///{database_path}")

    @event.listens_for(engine, "connect")
    def _enable_wal(
        dbapi_connection: DBAPIConnection, _connection_record: ConnectionPoolEntry
    ) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine
