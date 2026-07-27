"""The snapshot endpoint the dashboard polls (AGENTS.md section 4.2).
Read-only, public — same trust model as /api/system/status and
/api/events (slice 5): the PIN gates state-changing actions, not
viewing.
"""

from fastapi import APIRouter, Depends, Response

from sentinel.api.dependencies import get_container
from sentinel.services import Container

router = APIRouter(prefix="/api/camera", tags=["camera"])


@router.get("/snapshot")
def snapshot(container: Container = Depends(get_container)) -> Response:
    jpeg_bytes = container.camera_provider.get_snapshot()
    return Response(content=jpeg_bytes, media_type="image/jpeg")
