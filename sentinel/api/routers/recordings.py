"""Recent recordings, newest first — read-only, same trust model as
events (AGENTS.md section 8.2, slice 5's public/read-only precedent).
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from sentinel.api.dependencies import get_container
from sentinel.models import Recording
from sentinel.services import Container

router = APIRouter(prefix="/api/recordings", tags=["recordings"])


class RecordingOut(BaseModel):
    started_at: str
    ended_at: str
    path: str
    size_bytes: int
    trigger_event_id: int | None

    @classmethod
    def from_recording(cls, recording: Recording) -> "RecordingOut":
        return cls(
            started_at=recording.started_at.isoformat(),
            ended_at=recording.ended_at.isoformat(),
            path=recording.path,
            size_bytes=recording.size_bytes,
            trigger_event_id=recording.trigger_event_id,
        )


@router.get("/", response_model=list[RecordingOut])
def list_recent_recordings(
    limit: int = 20, container: Container = Depends(get_container)
) -> list[RecordingOut]:
    recordings = container.recording_repository.recent(limit)
    return [RecordingOut.from_recording(r) for r in recordings]
