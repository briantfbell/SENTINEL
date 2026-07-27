"""Async pub/sub. No knowledge of state or persistence — that belongs to
whatever subscribes (AGENTS.md section 6 layering).
"""

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

from sentinel.events.notification import Notification
from sentinel.models import EventType, Severity

Handler = Callable[[Notification], Awaitable[None]]


class EventBus:
    """Fan-out publish/subscribe. Subscribers run in registration order."""

    def __init__(
        self, clock: Callable[[], datetime] = lambda: datetime.now(UTC)
    ) -> None:
        self._subscribers: list[Handler] = []
        self._clock = clock

    def subscribe(self, handler: Handler) -> None:
        self._subscribers.append(handler)

    def unsubscribe(self, handler: Handler) -> None:
        self._subscribers.remove(handler)

    async def publish(
        self,
        event_type: EventType,
        *,
        source: str,
        severity: Severity = Severity.INFO,
        metadata: dict[str, Any] | None = None,
    ) -> Notification:
        """Timestamp, wrap, and deliver to every subscriber in order.

        Returns the Notification so callers (and tests) can inspect what
        was actually published, including the assigned timestamp.
        """
        notification = Notification(
            type=event_type,
            timestamp=self._clock(),
            source=source,
            severity=severity,
            metadata=metadata or {},
        )
        for handler in self._subscribers:
            await handler(notification)
        return notification
