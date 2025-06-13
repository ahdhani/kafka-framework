"""
Decorator functions for topic event routing.
"""

from collections.abc import Callable
from functools import wraps
from typing import Any


def topic_event(
    topic: str,
    event_name: str,
    *,
    priority: int = 1,
    retry_attempts: int = 0,
    dlq_topic: str | None = None,
) -> Callable:
    """
    Decorator for topic event handlers.
    This is a convenience wrapper around TopicRouter.topic_event.
    """

    def decorator(func: Callable) -> Callable:
        # Store metadata on the function for later use by the router
        func._topic = topic
        func._event_name = event_name
        func._priority = priority
        func._retry_attempts = retry_attempts
        func._dlq_topic = dlq_topic

        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            return await func(*args, **kwargs)

        return wrapper

    return decorator
