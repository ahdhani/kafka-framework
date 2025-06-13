"""
TopicRouter implementation for routing Kafka messages to handlers.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from ..dependencies import get_dependant


@dataclass
class EventHandler:
    """Event handler configuration."""

    func: Callable
    priority: int = 1
    retry_attempts: int = 0
    dlq_topic: str | None = None
    dependencies: list[Any] = field(default_factory=list)


class TopicRouter:
    """
    Router for Kafka topics and events.
    Similar to FastAPI's APIRouter.
    """

    def __init__(self):
        self.routes: dict[str, dict[str, EventHandler]] = {}

    def topic_event(
        self,
        topic: str,
        event_name: str,
        *,
        priority: int = 1,
        retry_attempts: int = 0,
        dlq_topic: str | None = None,
    ) -> Callable:
        """Decorator for registering topic event handlers."""

        def decorator(func: Callable) -> Callable:
            if topic not in self.routes:
                self.routes[topic] = {}

            # Get dependencies from function signature
            dependant = get_dependant(func)

            self.routes[topic][event_name] = EventHandler(
                func=func,
                priority=priority,
                retry_attempts=retry_attempts,
                dlq_topic=dlq_topic,
                dependencies=dependant.dependencies,
            )
            return func

        return decorator

    def get_handler(self, topic: str, event_name: str) -> EventHandler | None:
        """Get the handler for a topic and event."""
        return self.routes.get(topic, {}).get(event_name)

    def get_topics(self) -> list[str]:
        """Get all registered topics."""
        return list(self.routes.keys())
