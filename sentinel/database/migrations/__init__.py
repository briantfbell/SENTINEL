"""Hand-written schema migrations, applied in order and tracked in a
schema_version table. No Alembic (AGENTS.md section 8.2) — each migration
is a small, explicit `upgrade(connection)` function reviewed like any
other change, not generated from ORM model diffs.
"""

from collections.abc import Callable
from typing import NamedTuple

from sqlalchemy import Connection, Engine, text

from sentinel.database.migrations.m0001_initial import upgrade as _m0001_upgrade
from sentinel.database.migrations.m0002_sessions import upgrade as _m0002_upgrade


class Migration(NamedTuple):
    version: int
    description: str
    upgrade: Callable[[Connection], None]


MIGRATIONS: list[Migration] = [
    Migration(1, "schema_version and events tables", _m0001_upgrade),
    Migration(2, "sessions table", _m0002_upgrade),
]


def apply_migrations(engine: Engine) -> None:
    """Bring the database up to the newest known schema version.

    Safe to call on every startup: migrations already recorded in
    schema_version are skipped.
    """
    with engine.begin() as connection:
        connection.execute(
            text("CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL)")
        )
        current_version = _current_version(connection)
        for migration in MIGRATIONS:
            if migration.version > current_version:
                migration.upgrade(connection)
                connection.execute(
                    text("INSERT INTO schema_version (version) VALUES (:version)"),
                    {"version": migration.version},
                )


def _current_version(connection: Connection) -> int:
    result = connection.execute(
        text("SELECT MAX(version) FROM schema_version")
    ).scalar()
    return int(result) if result is not None else 0
