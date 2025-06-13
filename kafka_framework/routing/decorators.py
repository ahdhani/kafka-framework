"""
Decorator functions for topic event routing.
"""
from typing import Any, Callable, Optional
from functools import wraps

def topic_event(
    topic: str,
    event_name: str,
    *,
    priority: int = 1,
    retry_attempts: int = 0,
    dlq_topic: Optional[str] = None,
) -> Callable:
    """
    Decorator for topic event handlers.
    This is a convenience wrapper around TopicRouter.topic_event.
    """
    def decorator(func: Callable) -> Callable:
        # Store metadata on the function for later use by the router
        setattr(func, "_topic", topic)
        setattr(func, "_event_name", event_name)
        setattr(func, "_priority", priority)
        setattr(func, "_retry_attempts", retry_attempts)
        setattr(func, "_dlq_topic", dlq_topic)
        
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            return await func(*args, **kwargs)
        return wrapper
    return decorator
