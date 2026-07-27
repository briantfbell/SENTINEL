"""SQLite has no timezone type; everything stored is UTC by convention
(AGENTS.md section 12), so every repository needs to reattach tzinfo
dropped on the round trip. One helper, so this doesn't get re-solved (or
re-forgotten) per repository.
"""

from datetime import UTC, datetime


def ensure_utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)
