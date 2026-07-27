"""Converts raw per-frame detections into PersonDetected/PersonGone
events. AGENTS.md section 4.4 and DECISIONS.md 0005: without this
hysteresis the event stream flaps and the state machine thrashes.
Testable with no model and no camera — it only ever sees `Detection`
values a test hands it directly.
"""

from collections.abc import Callable
from datetime import UTC, datetime

from sentinel.config import DetectionSettings
from sentinel.detection.provider import Detection
from sentinel.models import EventType


class DetectionDebouncer:
    def __init__(
        self,
        settings: DetectionSettings,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._settings = settings
        self._clock = clock
        self._consecutive_hits = 0
        self._present = False
        self._last_hit_at: datetime | None = None

    def process(self, detections: list[Detection]) -> EventType | None:
        """Feed one frame's raw detections in. Returns the domain event to
        publish, if this frame is the one that crosses a threshold —
        PERSON_DETECTED, PERSON_GONE, or None most of the time.
        """
        now = self._clock()
        if self._qualifies(detections):
            self._last_hit_at = now
            self._consecutive_hits += 1
            if (
                not self._present
                and self._consecutive_hits >= self._settings.consecutive_frames
            ):
                self._present = True
                return EventType.PERSON_DETECTED
            return None

        self._consecutive_hits = 0
        if self._present and self._last_hit_at is not None:
            absent_for = (now - self._last_hit_at).total_seconds()
            if absent_for >= self._settings.absence_seconds:
                self._present = False
                return EventType.PERSON_GONE
        return None

    def _qualifies(self, detections: list[Detection]) -> bool:
        return any(
            d.confidence >= self._settings.confidence_threshold
            and d.box_area_ratio >= self._settings.min_box_area_ratio
            for d in detections
        )
