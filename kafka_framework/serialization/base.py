"""
Base serializer interface for the Kafka framework.
"""

from abc import ABC, abstractmethod
from typing import Any


class BaseSerializer(ABC):
    """
    Base class for all serializers.
    """

    @abstractmethod
    async def serialize(
        self,
        value: Any,
    ) -> bytes:
        """Serialize a value to bytes."""
        pass

    @abstractmethod
    async def deserialize(
        self,
        value: bytes,
    ) -> Any:
        """Deserialize bytes to a value."""
        pass
