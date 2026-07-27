from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import text

from sentinel.database import EventRepository, apply_migrations, open_engine
from sentinel.database.migrations import MIGRATIONS
from sentinel.models import Event, EventType, Severity, SystemState

NOW = datetime(2026, 7, 27, 12, 0, 0, tzinfo=UTC)


def _event(**overrides: object) -> Event:
    defaults: dict[str, object] = {
        "type": EventType.PERSON_DETECTED,
        "timestamp": NOW,
        "source": "detector",
        "severity": Severity.INFO,
        "state_at_time": SystemState.ARMED,
        "metadata": {"confidence": 0.9},
    }
    defaults.update(overrides)
    return Event(**defaults)  # type: ignore[arg-type]


def test_schema_creates_on_first_run(tmp_path: Path) -> None:
    engine = open_engine(tmp_path / "sentinel.db")
    apply_migrations(engine)

    with engine.connect() as conn:
        tables = {
            row[0]
            for row in conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table'")
            )
        }
    assert {"events", "schema_version"} <= tables


def test_migrations_are_idempotent(tmp_path: Path) -> None:
    engine = open_engine(tmp_path / "sentinel.db")
    apply_migrations(engine)
    apply_migrations(engine)  # must not error or duplicate rows

    with engine.connect() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM schema_version")).scalar()
    assert count == len(MIGRATIONS)


def test_wal_mode_is_enabled(tmp_path: Path) -> None:
    engine = open_engine(tmp_path / "sentinel.db")

    with engine.connect() as conn:
        mode = conn.execute(text("PRAGMA journal_mode")).scalar()
    assert mode == "wal"


def test_write_and_read_back_event(tmp_path: Path) -> None:
    engine = open_engine(tmp_path / "sentinel.db")
    apply_migrations(engine)
    repo = EventRepository(engine)

    repo.add(_event())
    results = repo.query()

    assert len(results) == 1
    assert results[0] == _event()


def test_query_filters_by_time_range(tmp_path: Path) -> None:
    engine = open_engine(tmp_path / "sentinel.db")
    apply_migrations(engine)
    repo = EventRepository(engine)
    repo.add(_event(timestamp=NOW))
    repo.add(_event(timestamp=NOW + timedelta(hours=1)))

    results = repo.query(start=NOW + timedelta(minutes=30))

    assert len(results) == 1
    assert results[0].timestamp == NOW + timedelta(hours=1)


def test_query_filters_by_type(tmp_path: Path) -> None:
    engine = open_engine(tmp_path / "sentinel.db")
    apply_migrations(engine)
    repo = EventRepository(engine)
    repo.add(_event(type=EventType.PERSON_DETECTED))
    repo.add(_event(type=EventType.PERSON_GONE))

    results = repo.query(event_type=EventType.PERSON_GONE)

    assert len(results) == 1
    assert results[0].type == EventType.PERSON_GONE


def test_query_filters_by_severity(tmp_path: Path) -> None:
    engine = open_engine(tmp_path / "sentinel.db")
    apply_migrations(engine)
    repo = EventRepository(engine)
    repo.add(_event(severity=Severity.INFO))
    repo.add(_event(severity=Severity.CRITICAL))

    results = repo.query(severity=Severity.CRITICAL)

    assert len(results) == 1
    assert results[0].severity == Severity.CRITICAL


def test_query_orders_oldest_to_newest(tmp_path: Path) -> None:
    engine = open_engine(tmp_path / "sentinel.db")
    apply_migrations(engine)
    repo = EventRepository(engine)
    repo.add(_event(timestamp=NOW + timedelta(hours=1)))
    repo.add(_event(timestamp=NOW))

    results = repo.query()

    assert [r.timestamp for r in results] == [NOW, NOW + timedelta(hours=1)]
