"""Pulls frames from the camera, runs them through the detector and
debouncer, and publishes PersonDetected/PersonGone.

AGENTS.md section 5 puts real camera capture and inference loops in
threads because they're blocking and CPU-bound. Mocks are neither, so
this is a plain asyncio task for now; a real Detector (slice 10) is the
point where threading actually earns its complexity, not before.
"""

import asyncio
from collections.abc import Awaitable, Callable

from sentinel.camera import CameraProvider
from sentinel.detection import DetectionDebouncer, Detector
from sentinel.events import EventBus

Sleeper = Callable[[float], Awaitable[None]]


class DetectionLoop:
    """Runs only while armed — started/stopped by the dispatcher on
    transitions into and out of DISARMED (AGENTS.md section 7.1:
    "DISARMED: monitoring off, no events processed").
    """

    def __init__(
        self,
        camera_provider: CameraProvider,
        detector: Detector,
        debouncer: DetectionDebouncer,
        bus: EventBus,
        interval_seconds: float,
        sleep: Sleeper = asyncio.sleep,
    ) -> None:
        self._camera_provider = camera_provider
        self._detector = detector
        self._debouncer = debouncer
        self._bus = bus
        self._interval_seconds = interval_seconds
        self._sleep = sleep
        self._task: asyncio.Task[None] | None = None

    def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._run())

    def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            self._task = None

    async def _run(self) -> None:
        while True:
            frame = self._camera_provider.get_snapshot()
            detections = self._detector.detect(frame)
            event_type = self._debouncer.process(detections)
            if event_type is not None:
                await self._bus.publish(event_type, source="detection")
            await self._sleep(self._interval_seconds)
