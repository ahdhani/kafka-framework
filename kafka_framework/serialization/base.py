"""
Base serializer interface for the Kafka framework.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

class BaseSerializer(ABC):
    """
    Base class for all serializers.
    """
    @abstractmethod
    async def serialize(
        self,
        value: Any,
        topic: str,
        headers: Optional[Dict[str, Any]] = None,
    ) -> bytes:
        """Serialize a value to bytes."""
        pass
        
    @abstractmethod
    async def deserialize(
        self,
        value: bytes,
        topic: str,
        headers: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Deserialize bytes to a value."""
        pass
