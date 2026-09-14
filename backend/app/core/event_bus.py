import asyncio
from typing import Any, Callable, Dict, List, Set
from app.core.logging import logger


class EventBus:
    """Asynchronous in-memory event bus for decoupling internal pub/sub and WebSocket broadcast."""

    def __init__(self):
        self._subscribers: Dict[str, Set[Callable]] = {}

    def subscribe(self, topic: str, callback: Callable) -> None:
        """Subscribe a callable (sync or async) to a given topic."""
        if topic not in self._subscribers:
            self._subscribers[topic] = set()
        self._subscribers[topic].add(callback)

    def unsubscribe(self, topic: str, callback: Callable) -> None:
        """Unsubscribe a callable from a topic."""
        if topic in self._subscribers:
            self._subscribers[topic].discard(callback)
            if not self._subscribers[topic]:
                del self._subscribers[topic]

    async def publish(self, topic: str, data: Any) -> None:
        """Publish an event to all subscribers of topic (and wildcard topic '*')."""
        targets = list(self._subscribers.get(topic, [])) + list(self._subscribers.get("*", []))
        for cb in targets:
            try:
                if asyncio.iscoroutinefunction(cb):
                    asyncio.create_task(cb(topic, data))
                else:
                    cb(topic, data)
            except Exception as e:
                logger.error(f"Error invoking event subscriber for topic '{topic}': {e}", exc_info=True)


# Global singleton instance
event_bus = EventBus()

TOPIC_TELEMETRY = "telemetry"
TOPIC_COMMAND_DISPATCHED = "command_dispatched"
TOPIC_COMMAND_RESULT = "command_result"
TOPIC_STATE_CHANGED = "state_changed"
TOPIC_SAFETY_ALERT = "safety_alert"
TOPIC_AI_UPDATE = "ai_update"
