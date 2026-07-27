"""Read/write access to the sessions table (AGENTS.md sections 4.6, 8.2)."""

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import Engine, delete
from sqlalchemy.orm import Session

from sentinel.database.orm import SessionRecord
from sentinel.database.timezones import ensure_utc


@dataclass(frozen=True)
class StoredSession:
    token_hash: str
    created_at: datetime
    expires_at: datetime
    client_ip: str


class SessionRepository:
    """Persists opaque session tokens. Never stores a raw PIN or token,
    only the hash (AGENTS.md section 4.6)."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def create(self, session: StoredSession) -> None:
        with Session(self._engine) as db_session:
            db_session.add(
                SessionRecord(
                    token_hash=session.token_hash,
                    created_at=session.created_at,
                    expires_at=session.expires_at,
                    client_ip=session.client_ip,
                )
            )
            db_session.commit()

    def get(self, token_hash: str) -> StoredSession | None:
        with Session(self._engine) as db_session:
            record = db_session.get(SessionRecord, token_hash)
            if record is None:
                return None
            return StoredSession(
                token_hash=record.token_hash,
                created_at=ensure_utc(record.created_at),
                expires_at=ensure_utc(record.expires_at),
                client_ip=record.client_ip,
            )

    def delete(self, token_hash: str) -> None:
        with Session(self._engine) as db_session:
            db_session.execute(
                delete(SessionRecord).where(SessionRecord.token_hash == token_hash)
            )
            db_session.commit()

    def delete_expired(self, now: datetime) -> None:
        with Session(self._engine) as db_session:
            db_session.execute(
                delete(SessionRecord).where(SessionRecord.expires_at <= now)
            )
            db_session.commit()
