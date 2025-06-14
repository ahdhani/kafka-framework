"""
Base classes for Kafka middleware system.
"""

from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from typing import Any

from ..models import KafkaMessage

# Type for the next middleware in chain
NextMiddleware = Callable[[KafkaMessage], Awaitable[Any]]


class BaseMiddleware(ABC):
    """Base class for all middleware."""

    @abstractmethod
    async def __call__(self, message: KafkaMessage, next_middleware: NextMiddleware) -> Any:
        """
        Process the message and call the next middleware.

        Args:
            message: The Kafka message being processed
            next_middleware: The next middleware in the chain

        Returns:
            The result of the middleware chain
        """
        pass


class ExceptionMiddleware(BaseMiddleware):
    """Base class for exception handling middleware."""

    @abstractmethod
    async def handle_exception(self, message: KafkaMessage, exc: Exception) -> None:
        """
        Handle an exception that occurred during message processing.

        Args:
            message: The message that caused the exception
            exc: The exception that occurred
        """
        pass

    async def __call__(self, message: KafkaMessage, next_middleware: NextMiddleware) -> Any:
        try:
            return await next_middleware(message)
        except Exception as e:
            await self.handle_exception(message, e)
            raise
