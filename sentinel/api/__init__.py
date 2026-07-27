"""FastAPI routers, dependencies, schemas. Never instantiates a provider
directly — everything comes from `services` (AGENTS.md section 6).
"""

from sentinel.api.app import create_app

__all__ = ["create_app"]
