"""Login/logout. PIN verification happens server-side only (AGENTS.md 4.6)."""

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status

from sentinel.api.dependencies import (
    SESSION_COOKIE_NAME,
    get_client_ip,
    get_container,
    require_session,
)
from sentinel.api.schemas import LoginRequest, MessageResponse
from sentinel.services import Container, InvalidPinError, LockedOutError

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=MessageResponse)
def login(
    payload: LoginRequest,
    response: Response,
    client_ip: str = Depends(get_client_ip),
    container: Container = Depends(get_container),
) -> MessageResponse:
    try:
        token = container.auth_service.login(payload.pin, client_ip)
    except LockedOutError as exc:
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED, detail=str(exc)
        ) from exc
    except InvalidPinError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)
        ) from exc

    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        max_age=container.settings.auth.session_ttl_seconds,
        httponly=True,
        samesite="strict",
    )
    return MessageResponse(message="ok")


@router.post(
    "/logout", response_model=MessageResponse, dependencies=[Depends(require_session)]
)
def logout(
    response: Response,
    container: Container = Depends(get_container),
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
) -> MessageResponse:
    if session_token is not None:
        container.auth_service.logout(session_token)
    response.delete_cookie(SESSION_COOKIE_NAME)
    return MessageResponse(message="ok")
