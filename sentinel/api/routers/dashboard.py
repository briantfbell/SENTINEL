"""Renders the dashboard HTML. Templates live in sentinel/dashboard/, but
this module reaches them by filesystem path via the root `sentinel`
package, not by importing `sentinel.dashboard` — that package has no
Python behavior for the API to depend on, only templates and static
assets, and the import contract only governs Python imports between
layers (AGENTS.md section 6).

Two screens: the kiosk lock screen ("/"), meant to be the only thing a
visitor at the front door sees, and the console ("/console"), reached
from a PIN-gated popup inside the lock screen's site-data panel. The
console page itself checks for a valid session (the same one arm/disarm
uses) and redirects back to the lock screen without one, so visiting
the URL directly doesn't bypass the gate — the partials it polls stay
public/read-only, same as the rest of the status/events API.
"""

from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

import sentinel
from sentinel.api.dependencies import SESSION_COOKIE_NAME, get_container
from sentinel.services import Container

_TEMPLATES_DIR = Path(sentinel.__file__).resolve().parent / "dashboard" / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))

router = APIRouter(tags=["dashboard"])

_SUBSTATE_LABEL: dict[str, str] = {
    "armed": "Monitoring",
    "alert": "Alert — presence detected",
    "warning": "Warning — announcement active",
    "escalated": "Escalated — full volume alert",
    "cooldown": "Cooldown — re-arming",
}

_STATE_DETAIL: dict[str, str] = {
    "disarmed": "Monitoring is off. No events are being processed.",
    "armed": "Monitoring active. No presence detected.",
    "alert": "Presence detected. Grace period running before the first announcement.",
    "warning": "First announcement has played. Presence still detected.",
    "escalated": "Second announcement playing at full volume.",
    "cooldown": "Presence cleared. Settling before the system re-arms.",
}


@router.get("/", response_class=HTMLResponse)
def lock_screen(
    request: Request, container: Container = Depends(get_container)
) -> HTMLResponse:
    return templates.TemplateResponse(request, "lock.html", _lock_context(container))


@router.get("/partials/lock-status", response_class=HTMLResponse)
def lock_status_partial(
    request: Request, container: Container = Depends(get_container)
) -> HTMLResponse:
    return templates.TemplateResponse(
        request, "partials/lock_status.html", _lock_context(container)
    )


@router.get("/console", response_model=None)
def console(
    request: Request, container: Container = Depends(get_container)
) -> HTMLResponse | RedirectResponse:
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if token is None or not container.auth_service.validate_session(token):
        return RedirectResponse(url="/", status_code=303)
    return templates.TemplateResponse(request, "console.html", _context(container))


@router.get("/partials/status", response_class=HTMLResponse)
def status_partial(
    request: Request, container: Container = Depends(get_container)
) -> HTMLResponse:
    return templates.TemplateResponse(
        request, "partials/status.html", _context(container)
    )


@router.get("/partials/state-detail", response_class=HTMLResponse)
def state_detail_partial(
    request: Request, container: Container = Depends(get_container)
) -> HTMLResponse:
    return templates.TemplateResponse(
        request, "partials/state_detail.html", _context(container)
    )


@router.get("/partials/events", response_class=HTMLResponse)
def events_partial(
    request: Request, container: Container = Depends(get_container)
) -> HTMLResponse:
    return templates.TemplateResponse(
        request, "partials/events.html", _context(container)
    )


def _lock_context(container: Container) -> dict[str, object]:
    state = container.state_machine.state.value
    armed = state != "disarmed"
    return {
        "state": state,
        "armed": armed,
        "primary_label": "ARMED" if armed else "DISARMED",
        "substate_label": _SUBSTATE_LABEL.get(state),
        "status_poll_interval_ms": container.settings.dashboard.status_poll_interval_ms,
        "property_address": container.settings.dashboard.property_address,
        "response_units": container.settings.dashboard.response_units,
    }


def _context(container: Container) -> dict[str, object]:
    """Shared context for the console and its partials: partials re-render
    their own hx-trigger attributes on every outerHTML swap, so they need
    this every time too, not just on the initial full-page load.
    """
    state = container.state_machine.state.value
    return {
        "state": state,
        "state_detail": _STATE_DETAIL.get(state, ""),
        "events": container.event_repository.recent(20),
        "status_poll_interval_ms": container.settings.dashboard.status_poll_interval_ms,
    }
