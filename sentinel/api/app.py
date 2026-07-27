"""FastAPI application factory. Never instantiates providers directly —
everything comes from the already-wired Container (AGENTS.md section 6).
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

import sentinel
from sentinel.api.routers import auth, camera, dashboard, events, recordings, system
from sentinel.services import Container

_STATIC_DIR = Path(sentinel.__file__).resolve().parent / "dashboard" / "static"


def create_app(container: Container) -> FastAPI:
    # docs/redoc disabled: FastAPI's default Swagger UI loads its JS/CSS
    # from a CDN at runtime, which section 2 rule 1 (no network calls
    # leave the LAN) forbids.
    app = FastAPI(title="Sentinel", docs_url=None, redoc_url=None, openapi_url=None)
    app.state.container = container

    app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")

    app.include_router(dashboard.router)
    app.include_router(auth.router)
    app.include_router(system.router)
    app.include_router(events.router)
    app.include_router(camera.router)
    app.include_router(recordings.router)

    return app
