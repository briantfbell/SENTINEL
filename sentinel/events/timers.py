"""Schedules future events onto the bus.

AGENTS.md section 7.3: timers are first-class. Never sleep inside a
handler and never bury a duration in a rule — durations are injected by
the caller (the services-layer dispatcher, reading config), not baked in
here or in the rule engine.
"""

import asyncio
from collections.abc import Awaitable, Callable

from sentinel.events.bus import EventBus
from sentinel.models import EventType, TimerName

Sleeper = Callable[[float], Awaitable[None]]


class TimerService:
    """Named, cancellable delays that publish an event on expiry.

    `sleep` is injectable so tests can fire a timer without waiting in
    real time (AGENTS.md section 9: "fake time, inject a clock").
    """

    def __init__(self, bus: EventBus, sleep: Sleeper = asyncio.sleep) -> None:
        self._bus = bus
        self._sleep = sleep
        self._tasks: dict[TimerName, asyncio.Task[None]] = {}

    def start(
        self,
        name: TimerName,
        delay_seconds: float,
        event_type: EventType,
        *,
        source: str,
    ) -> None:
        """Start a timer, replacing any existing timer of the same name."""
        self.cancel(name)
        self._tasks[name] = asyncio.create_task(
            self._fire_after(delay_seconds, event_type, source)
        )

    def cancel(self, name: TimerName) -> None:
        task = self._tasks.pop(name, None)
        if task is not None and not task.done():
            task.cancel()

    def cancel_all(self) -> None:
        for name in list(self._tasks):
            self.cancel(name)

    async def _fire_after(
        self, delay_seconds: float, event_type: EventType, source: str
    ) -> None:
        await self._sleep(delay_seconds)
        await self._bus.publish(event_type, source=source)
