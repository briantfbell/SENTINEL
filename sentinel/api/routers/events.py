"""Recent events, newest first, for the dashboard's event list."""

from fastapi import APIRouter, Depends

from sentinel.api.dependencies import get_container
from sentinel.api.schemas import EventOut
from sentinel.services import Container

router = APIRouter(prefix="/api/events", tags=["events"])


@router.get("/", response_model=list[EventOut])
def list_recent_events(
    limit: int = 20, container: Container = Depends(get_container)
) -> list[EventOut]:
    return [
        EventOut.from_event(event) for event in container.event_repository.recent(limit)
    ]
