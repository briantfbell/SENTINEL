"""Migration 2: sessions table (AGENTS.md section 4.6, 8.2)."""

from sqlalchemy import Connection, text


def upgrade(connection: Connection) -> None:
    connection.execute(
        text(
            """
            CREATE TABLE sessions (
                token_hash VARCHAR PRIMARY KEY,
                created_at DATETIME NOT NULL,
                expires_at DATETIME NOT NULL,
                client_ip VARCHAR NOT NULL
            )
            """
        )
    )
