"""Engine, ORM models, migrations, and repositories. Nothing outside this
package imports sqlalchemy (AGENTS.md section 6).
"""

from sentinel.database.engine import open_engine
from sentinel.database.migrations import apply_migrations
from sentinel.database.repository import EventRepository

__all__ = ["EventRepository", "apply_migrations", "open_engine"]
