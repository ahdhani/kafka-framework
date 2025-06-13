"""
Avro serializer implementation.
"""
from typing import Any, Dict, Optional
import json

try:
    import fastavro
except ImportError:
    fastavro = None

from .base import BaseSerializer

class AvroSerializer(BaseSerializer):
    """
    Avro serializer with schema registry support.
    Requires the [avro] extra to be installed.
    """
    def __init__(
        self,
        schema_registry_url: str,
        schema_str: Optional[str] = None,
        schema_dict: Optional[Dict] = None,
    ):
        if fastavro is None:
            raise ImportError(
                "fastavro is not installed. Install kafka-framework[avro] to use AvroSerializer."
            )
            
        if not schema_str and not schema_dict:
            raise ValueError("Either schema_str or schema_dict must be provided")
            
        self.schema_registry_url = schema_registry_url
        self.schema = schema_dict or json.loads(schema_str)
        self.parsed_schema = fastavro.parse_schema(self.schema)
        
    async def serialize(
        self,
        value: Any,
        topic: str,
        headers: Optional[Dict[str, Any]] = None,
    ) -> bytes:
        """Serialize a value to Avro bytes."""
        return fastavro.schemaless_writer(value, self.parsed_schema)
        
    async def deserialize(
        self,
        value: bytes,
        topic: str,
        headers: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Deserialize Avro bytes to a value."""
        return fastavro.schemaless_reader(value, self.parsed_schema)
