from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from sentinel.models import Event, EventType, Severity, SystemState


def _make_event(**overrides: object) -> Event:
    defaults: dict[str, object] = {
        "type": EventType.PERSON_DETECTED,
        "timestamp": datetime(2026, 7, 27, 12, 0, 0, tzinfo=UTC),
        "source": "detector",
        "severity": Severity.INFO,
        "state_at_time": SystemState.ARMED,
    }
    defaults.update(overrides)
    return Event(**defaults)  # type: ignore[arg-type]


def test_event_is_frozen() -> None:
    event = _make_event()
    with pytest.raises(ValidationError):
        event.severity = Severity.CRITICAL  # type: ignore[misc]


def test_event_defaults_to_empty_metadata() -> None:
    assert _make_event().metadata == {}


def test_naive_timestamp_is_rejected() -> None:
    with pytest.raises(ValidationError, match="timezone-aware"):
        _make_event(timestamp=datetime(2026, 7, 27, 12, 0, 0))
