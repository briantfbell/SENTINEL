from datetime import UTC, datetime

import pytest

from sentinel.events import EventBus, Notification
from sentinel.models import EventType, Severity

FIXED_TIME = datetime(2026, 7, 27, 12, 0, 0, tzinfo=UTC)


@pytest.mark.asyncio
async def test_publish_delivers_to_subscriber() -> None:
    bus = EventBus(clock=lambda: FIXED_TIME)
    received: list[Notification] = []

    async def handler(notification: Notification) -> None:
        received.append(notification)

    bus.subscribe(handler)
    await bus.publish(EventType.PERSON_DETECTED, source="detector")

    assert len(received) == 1
    assert received[0].type == EventType.PERSON_DETECTED
    assert received[0].source == "detector"
    assert received[0].timestamp == FIXED_TIME
    assert received[0].severity == Severity.INFO


@pytest.mark.asyncio
async def test_publish_delivers_to_multiple_subscribers_in_order() -> None:
    bus = EventBus(clock=lambda: FIXED_TIME)
    order: list[str] = []

    async def first(_notification: Notification) -> None:
        order.append("first")

    async def second(_notification: Notification) -> None:
        order.append("second")

    bus.subscribe(first)
    bus.subscribe(second)
    await bus.publish(EventType.SYSTEM_ARMED, source="api")

    assert order == ["first", "second"]


@pytest.mark.asyncio
async def test_unsubscribe_stops_delivery() -> None:
    bus = EventBus(clock=lambda: FIXED_TIME)
    received: list[Notification] = []

    async def handler(notification: Notification) -> None:
        received.append(notification)

    bus.subscribe(handler)
    bus.unsubscribe(handler)
    await bus.publish(EventType.SYSTEM_ARMED, source="api")

    assert received == []


@pytest.mark.asyncio
async def test_publish_returns_the_notification() -> None:
    bus = EventBus(clock=lambda: FIXED_TIME)

    notification = await bus.publish(
        EventType.DISK_SPACE_LOW, source="retention", severity=Severity.WARNING
    )

    assert notification.type == EventType.DISK_SPACE_LOW
    assert notification.severity == Severity.WARNING
