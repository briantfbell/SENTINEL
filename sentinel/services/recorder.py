"""Captures start/end snapshot evidence and persists a finalized
recording row (AGENTS.md sections 4.8, 8.2).

Scope note (DECISIONS.md 0014): this captures two bookend frames, not
continuous video. Real continuous capture needs a real camera's frame
stream and a video-encoding decision, neither of which exist yet —
both are slice 9+ concerns. A snapshot-based system can honestly do no
more than this, and pretending otherwise would be worse than not
recording at all.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from sentinel.camera import CameraProvider
from sentinel.database import RecordingRepository
from sentinel.models import Recording


@dataclass
class _ActiveRecording:
    started_at: datetime
    clip_dir: Path
    trigger_event_id: int | None


class Recorder:
    def __init__(
        self,
        camera_provider: CameraProvider,
        recording_repository: RecordingRepository,
        recordings_path: Path,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._camera_provider = camera_provider
        self._recording_repository = recording_repository
        self._recordings_path = recordings_path
        self._clock = clock
        self._active: _ActiveRecording | None = None

    def start(self, trigger_event_id: int | None = None) -> None:
        """Begin a recording. A no-op if one is already active — re-entry
        actions (e.g. continued presence in ALERT) must not restart it.
        """
        if self._active is not None:
            return
        started_at = self._clock()
        clip_dir = self._recordings_path / started_at.strftime("%Y%m%dT%H%M%S%f")
        clip_dir.mkdir(parents=True, exist_ok=True)
        (clip_dir / "start.jpg").write_bytes(self._camera_provider.get_snapshot())
        self._active = _ActiveRecording(started_at, clip_dir, trigger_event_id)

    def stop(self) -> int | None:
        """End the active recording and persist it. Returns the new row's
        id, or None if nothing was recording.
        """
        if self._active is None:
            return None
        active = self._active
        self._active = None

        (active.clip_dir / "end.jpg").write_bytes(self._camera_provider.get_snapshot())
        ended_at = self._clock()
        size_bytes = sum(f.stat().st_size for f in active.clip_dir.glob("*.jpg"))

        return self._recording_repository.add(
            Recording(
                started_at=active.started_at,
                ended_at=ended_at,
                path=str(active.clip_dir),
                size_bytes=size_bytes,
                trigger_event_id=active.trigger_event_id,
            )
        )
