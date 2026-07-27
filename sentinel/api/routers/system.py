"""Arm/disarm and status. Arm and disarm are the only state-changing
endpoints in this slice, so they're the only ones requiring a session.
"""

from fastapi import APIRouter, Depends, HTTPException, status

from sentinel.api.dependencies import get_client_ip, get_container, require_session
from sentinel.api.schemas import MessageResponse, StatusResponse
from sentinel.models import EventType
from sentinel.services import Container
from sentinel.state import IllegalTransitionError

router = APIRouter(prefix="/api/system", tags=["system"])


@router.get("/status", response_model=StatusResponse)
def get_status(container: Container = Depends(get_container)) -> StatusResponse:
    return StatusResponse(state=container.state_machine.state.value)


@router.post(
    "/arm", response_model=MessageResponse, dependencies=[Depends(require_session)]
)
async def arm(
    client_ip: str = Depends(get_client_ip),
    container: Container = Depends(get_container),
) -> MessageResponse:
    return await _publish_or_409(container, EventType.SYSTEM_ARMED, client_ip)


@router.post(
    "/disarm", response_model=MessageResponse, dependencies=[Depends(require_session)]
)
async def disarm(
    client_ip: str = Depends(get_client_ip),
    container: Container = Depends(get_container),
) -> MessageResponse:
    return await _publish_or_409(container, EventType.SYSTEM_DISARMED, client_ip)


async def _publish_or_409(
    container: Container, event_type: EventType, client_ip: str
) -> MessageResponse:
    try:
        await container.bus.publish(event_type, source=f"dashboard:{client_ip}")
    except IllegalTransitionError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc
    return MessageResponse(message=container.state_machine.state.value)
