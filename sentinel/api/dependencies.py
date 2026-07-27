"""Shared FastAPI dependencies. Never instantiates a provider directly —
everything comes from the Container on app.state (AGENTS.md section 6).
"""

from fastapi import Cookie, Depends, HTTPException, Request, status

from sentinel.services import Container

SESSION_COOKIE_NAME = "sentinel_session"


def get_container(request: Request) -> Container:
    return request.app.state.container  # type: ignore[no-any-return]


def get_client_ip(request: Request) -> str:
    return request.client.host if request.client is not None else "unknown"


def require_session(
    container: Container = Depends(get_container),
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
) -> None:
    """Every state-changing endpoint depends on this (AGENTS.md section 4.6)."""
    if session_token is None or not container.auth_service.validate_session(
        session_token
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )
