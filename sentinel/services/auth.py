"""Server-side PIN verification and session management (AGENTS.md 4.6).

The PIN keypad is a UI affordance, not a security control — anyone on the
Wi-Fi can reach the API directly, so every check here happens server-side:
the PIN hash never leaves config, session tokens are stored as hashes,
and failed attempts are counted per client IP with a real lockout.
"""

import hashlib
import secrets
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from sentinel.database import SessionRepository, StoredSession
from sentinel.services.errors import InvalidPinError, LockedOutError

_hasher = PasswordHasher()


class AuthService:
    """Instance-held state only (AGENTS.md section 2 rule 5: no globals).

    Failed-attempt counters and lockouts live on this object, constructed
    once in the composition root and injected everywhere it's needed.
    """

    def __init__(
        self,
        session_repository: SessionRepository,
        pin_hash: str,
        session_ttl_seconds: int,
        max_attempts: int,
        lockout_seconds: int,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._sessions = session_repository
        self._pin_hash = pin_hash
        self._session_ttl = timedelta(seconds=session_ttl_seconds)
        self._max_attempts = max_attempts
        self._lockout_seconds = lockout_seconds
        self._clock = clock
        self._failure_counts: dict[str, int] = {}
        self._locked_until: dict[str, datetime] = {}

    def login(self, pin: str, client_ip: str) -> str:
        """Verify a PIN and, on success, create a session.

        Returns the raw opaque token (only its hash is persisted). Raises
        LockedOutError if this client IP is locked out, or InvalidPinError
        if the PIN is wrong (which may itself trigger a new lockout).
        """
        now = self._clock()
        self._reject_if_locked_out(client_ip, now)

        try:
            _hasher.verify(self._pin_hash, pin)
        except VerifyMismatchError as exc:
            self._record_failure(client_ip, now)
            raise InvalidPinError("Incorrect PIN") from exc

        self._failure_counts.pop(client_ip, None)
        token = secrets.token_urlsafe(32)
        self._sessions.create(
            StoredSession(
                token_hash=_hash_token(token),
                created_at=now,
                expires_at=now + self._session_ttl,
                client_ip=client_ip,
            )
        )
        return token

    def logout(self, token: str) -> None:
        self._sessions.delete(_hash_token(token))

    def validate_session(self, token: str) -> bool:
        session = self._sessions.get(_hash_token(token))
        if session is None:
            return False
        return self._clock() < session.expires_at

    def _reject_if_locked_out(self, client_ip: str, now: datetime) -> None:
        locked_until = self._locked_until.get(client_ip)
        if locked_until is not None and now < locked_until:
            raise LockedOutError((locked_until - now).total_seconds())
        if locked_until is not None:
            del self._locked_until[client_ip]

    def _record_failure(self, client_ip: str, now: datetime) -> None:
        count = self._failure_counts.get(client_ip, 0) + 1
        self._failure_counts[client_ip] = count
        if count >= self._max_attempts:
            self._locked_until[client_ip] = now + timedelta(
                seconds=self._lockout_seconds
            )
            self._failure_counts.pop(client_ip, None)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def hash_pin(pin: str) -> str:
    """Used by `sentinel-admin set-pin` to generate the config value."""
    return _hasher.hash(pin)
