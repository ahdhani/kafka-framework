"""
JSON serializer implementation.
"""
import json
from typing import Any, Dict, Optional
from datetime import datetime

from .base import BaseSerializer

class JSONSerializer(BaseSerializer):
    """
    JSON serializer with datetime support.
    """
    def __init__(self, encoding: str = "utf-8"):
        self.encoding = encoding
        
    async def serialize(
        self,
        value: Any,
        topic: str,
        headers: Optional[Dict[str, Any]] = None,
    ) -> bytes:
        """Serialize a value to JSON bytes."""
        def _json_serial(obj: Any) -> str:
            """JSON serializer for objects not serializable by default json code."""
            if isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError(f"Type {type(obj)} not serializable")
            
        return json.dumps(value, default=_json_serial).encode(self.encoding)
        
    async def deserialize(
        self,
        value: bytes,
        topic: str,
        headers: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Deserialize JSON bytes to a value."""
        return json.loads(value.decode(self.encoding))
