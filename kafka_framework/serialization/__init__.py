"""
Serialization module for the Kafka framework.
"""
from .base import BaseSerializer
from .json import JSONSerializer
from .avro import AvroSerializer

__all__ = ["BaseSerializer", "JSONSerializer", "AvroSerializer"]
