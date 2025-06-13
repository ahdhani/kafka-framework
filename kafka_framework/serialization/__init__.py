"""
Serialization module for the Kafka framework.
"""

from .avro import AvroSerializer
from .base import BaseSerializer
from .json import JSONSerializer
from .protobuf import ProtobufSerializer

__all__ = ["BaseSerializer", "JSONSerializer", "AvroSerializer", "ProtobufSerializer"]
