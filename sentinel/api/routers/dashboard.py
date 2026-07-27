"""Renders the dashboard HTML. Templates live in sentinel/dashboard/, but
this module reaches them by filesystem path via the root `sentinel`
package, not by importing `sentinel.dashboard` — that package has no
Python behavior for the API to depend on, only templates and static
assets, and the import contract only governs Python imports between
layers (AGENTS.md section 6).
"""

from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

import sentinel
from sentinel.api.dependencies import get_container
from sentinel.services import Container

_TEMPLATES_DIR = Path(sentinel.__file__).resolve().parent / "dashboard" / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))

router = APIRouter(tags=["dashboard"])


@router.get("/", response_class=HTMLResponse)
def index(
    request: Request, container: Container = Depends(get_container)
) -> HTMLResponse:
    return templates.TemplateResponse(request, "index.html", _context(container))


@router.get("/partials/status", response_class=HTMLResponse)
def status_partial(
    request: Request, container: Container = Depends(get_container)
) -> HTMLResponse:
    return templates.TemplateResponse(
        request, "partials/status.html", _context(container)
    )


@router.get("/partials/events", response_class=HTMLResponse)
def events_partial(
    request: Request, container: Container = Depends(get_container)
) -> HTMLResponse:
    return templates.TemplateResponse(
        request, "partials/events.html", _context(container)
    )


def _context(container: Container) -> dict[str, object]:
    """Shared template context: partials re-render their own hx-trigger
    attributes on every outerHTML swap, so they need this every time too,
    not just on the initial full-page load.
    """
    return {
        "state": container.state_machine.state.value,
        "events": container.event_repository.recent(20),
        "status_poll_interval_ms": container.settings.dashboard.status_poll_interval_ms,
    }
