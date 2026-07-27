from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from sentinel.database import SessionRepository, apply_migrations, open_engine
from sentinel.services import AuthService, InvalidPinError, LockedOutError, hash_pin

PIN = "1234"
NOW = datetime(2026, 7, 27, 12, 0, 0, tzinfo=UTC)


def _build_service(
    tmp_path: Path,
    *,
    max_attempts: int = 5,
    lockout_seconds: int = 300,
    clock=lambda: NOW,
) -> AuthService:
    engine = open_engine(tmp_path / "sentinel.db")
    apply_migrations(engine)
    return AuthService(
        session_repository=SessionRepository(engine),
        pin_hash=hash_pin(PIN),
        session_ttl_seconds=900,
        max_attempts=max_attempts,
        lockout_seconds=lockout_seconds,
        clock=clock,
    )


def test_correct_pin_issues_a_valid_session(tmp_path: Path) -> None:
    service = _build_service(tmp_path)

    token = service.login(PIN, "192.168.1.10")

    assert service.validate_session(token) is True


def test_wrong_pin_raises_and_grants_no_session(tmp_path: Path) -> None:
    service = _build_service(tmp_path)

    with pytest.raises(InvalidPinError):
        service.login("0000", "192.168.1.10")


def test_lockout_after_max_attempts(tmp_path: Path) -> None:
    service = _build_service(tmp_path, max_attempts=3)

    for _ in range(3):
        with pytest.raises(InvalidPinError):
            service.login("0000", "192.168.1.10")

    with pytest.raises(LockedOutError):
        service.login(PIN, "192.168.1.10")  # even the correct PIN is rejected


def test_lockout_is_scoped_to_client_ip(tmp_path: Path) -> None:
    service = _build_service(tmp_path, max_attempts=3)

    for _ in range(3):
        with pytest.raises(InvalidPinError):
            service.login("0000", "192.168.1.10")

    token = service.login(PIN, "192.168.1.99")
    assert service.validate_session(token) is True


def test_lockout_expires(tmp_path: Path) -> None:
    current = {"now": NOW}
    service = _build_service(
        tmp_path, max_attempts=1, lockout_seconds=60, clock=lambda: current["now"]
    )

    with pytest.raises(InvalidPinError):
        service.login("0000", "192.168.1.10")
    with pytest.raises(LockedOutError):
        service.login(PIN, "192.168.1.10")

    current["now"] = NOW + timedelta(seconds=61)
    token = service.login(PIN, "192.168.1.10")
    assert service.validate_session(token) is True


def test_expired_session_is_invalid(tmp_path: Path) -> None:
    current = {"now": NOW}
    service = _build_service(tmp_path, clock=lambda: current["now"])
    service._session_ttl = timedelta(seconds=1)

    token = service.login(PIN, "192.168.1.10")
    current["now"] = NOW + timedelta(seconds=2)

    assert service.validate_session(token) is False


def test_logout_invalidates_the_session(tmp_path: Path) -> None:
    service = _build_service(tmp_path)
    token = service.login(PIN, "192.168.1.10")

    service.logout(token)

    assert service.validate_session(token) is False


def test_unknown_token_is_invalid(tmp_path: Path) -> None:
    service = _build_service(tmp_path)

    assert service.validate_session("not-a-real-token") is False
