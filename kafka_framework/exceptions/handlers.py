"""
Exception handling for the Kafka framework.
"""

import logging
from collections.abc import Callable
from functools import wraps
from typing import Any

logger = logging.getLogger(__name__)


class KafkaFrameworkError(Exception):
    """Base exception for all Kafka framework errors."""

    pass


class SerializationError(KafkaFrameworkError):
    """Raised when serialization or deserialization fails."""

    pass


class ConsumerError(KafkaFrameworkError):
    """Raised when there's an error in the consumer."""

    pass


class ProducerError(KafkaFrameworkError):
    """Raised when there's an error in the producer."""

    pass


class RetryableError(KafkaFrameworkError):
    """Base class for errors that should trigger a retry."""

    pass


class NonRetryableError(KafkaFrameworkError):
    """Base class for errors that should not trigger a retry."""

    pass


def handle_exceptions(
    *exceptions: type[Exception],
    handler: Callable | None = None,
    reraise: bool = True,
) -> Callable:
    """
    Decorator for handling exceptions in event handlers.

    Args:
        *exceptions: Exception types to catch
        handler: Optional custom handler function
        reraise: Whether to reraise the exception after handling

    Returns:
        Decorated function
    """
    if not exceptions:
        exceptions = (Exception,)

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return await func(*args, **kwargs)

            except exceptions as e:
                logger.error(f"Error in {func.__name__}: {e}")

                if handler:
                    await handler(e, *args, **kwargs)

                if reraise:
                    raise

        return wrapper

    return decorator


def is_retryable(exception: Exception) -> bool:
    """
    Check if an exception should trigger a retry.

    Args:
        exception: Exception to check

    Returns:
        True if the exception should trigger a retry
    """
    # Explicitly non-retryable errors
    if isinstance(exception, NonRetryableError):
        return False

    # Default retry behavior for other exceptions
    return True
