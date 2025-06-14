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
    Router for handling Kafka topic events.
    """

    def __init__(self):
        self.route_handler_map: dict[str, EventHandler] = {}
        self.topics: set[str] = set()

    def topic_event(
        self,
        topic: str,
        event_name: str | None = None,
        *,
        priority: int = 1,
        retry_attempts: int = 0,
        dlq_support: bool = True,
        dlq_postfix: str | None = None,
    ) -> Callable:
        """Decorator for registering topic event handlers."""

        def decorator(func: Callable) -> Callable:
            # Get dependencies from function
            dependant = get_dependant(func)

            route = self.get_route(topic, event_name)
            dlq_topic = topic if dlq_support else None
            if dlq_postfix is not None:
                dlq_topic = f"{topic}.{dlq_postfix}"
            self.route_handler_map[route] = EventHandler(
                func=func,
                priority=priority,
                retry_attempts=retry_attempts,
                dlq_topic=dlq_topic,
                dependencies=dependant.dependencies,
            )
            self.topics.add(topic)

            return func

        return decorator

    @staticmethod
    def get_route(topic: str, event_name: str | None = None) -> str:
        if event_name is not None:
            return f"{topic}.{event_name}"
        return topic

    def get_handler(self, topic: str, event_name: str | None = None) -> EventHandler | None:
        """Get the handler for a topic and event."""
        return self.route_handler_map.get(self.get_route(topic, event_name))

    def get_route_handler_map(self) -> dict[str, EventHandler]:
        """Get all registered route_handler_map."""
        return self.route_handler_map

    def get_topics(self) -> set[str]:
        """Get all registered topics."""
        return self.topics
