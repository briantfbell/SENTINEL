import asyncio

import pytest

from sentinel.events import EventBus, Notification, TimerService
from sentinel.models import EventType, TimerName


async def _no_wait(_seconds: float) -> None:
    """Stand-in for asyncio.sleep so timer tests don't wait in real time."""


@pytest.mark.asyncio
async def test_timer_fires_event_on_expiry() -> None:
    bus = EventBus()
    received: list[Notification] = []

    async def handler(notification: Notification) -> None:
        received.append(notification)

    bus.subscribe(handler)
    timers = TimerService(bus, sleep=_no_wait)

    timers.start(TimerName.GRACE, 10.0, EventType.GRACE_EXPIRED, source="timer")
    await asyncio.gather(*timers._tasks.values())

    assert len(received) == 1
    assert received[0].type == EventType.GRACE_EXPIRED


@pytest.mark.asyncio
async def test_starting_a_timer_replaces_the_previous_one() -> None:
    bus = EventBus()
    received: list[Notification] = []

    async def handler(notification: Notification) -> None:
        received.append(notification)

    bus.subscribe(handler)

    async def slow_wait(_seconds: float) -> None:
        await asyncio.sleep(10)

    timers = TimerService(bus, sleep=slow_wait)
    timers.start(TimerName.GRACE, 10.0, EventType.GRACE_EXPIRED, source="timer")
    first_task = timers._tasks[TimerName.GRACE]

    timers.start(TimerName.GRACE, 10.0, EventType.GRACE_EXPIRED, source="timer")

    assert first_task.cancelled() or first_task.cancelling() > 0
    timers.cancel_all()


@pytest.mark.asyncio
async def test_cancel_prevents_the_event_from_firing() -> None:
    bus = EventBus()
    received: list[Notification] = []

    async def handler(notification: Notification) -> None:
        received.append(notification)

    bus.subscribe(handler)

    async def slow_wait(_seconds: float) -> None:
        await asyncio.sleep(10)

    timers = TimerService(bus, sleep=slow_wait)
    timers.start(TimerName.GRACE, 10.0, EventType.GRACE_EXPIRED, source="timer")
    timers.cancel(TimerName.GRACE)

    await asyncio.sleep(0)  # let the cancellation propagate

    assert received == []


@pytest.mark.asyncio
async def test_cancel_all_cancels_every_timer() -> None:
    bus = EventBus()

    async def slow_wait(_seconds: float) -> None:
        await asyncio.sleep(10)

    timers = TimerService(bus, sleep=slow_wait)
    timers.start(TimerName.GRACE, 10.0, EventType.GRACE_EXPIRED, source="timer")
    timers.start(TimerName.WARNING, 30.0, EventType.WARNING_EXPIRED, source="timer")

    timers.cancel_all()

    assert timers._tasks == {}
