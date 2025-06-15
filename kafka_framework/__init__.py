"""
FastAPI-style Kafka framework for building event-driven applications.
"""

from .app import KafkaApp
from .dependencies import Depends
from .models import KafkaMessage
from .routing import TopicRouter
from .serialization import AvroSerializer, JSONSerializer

__version__ = "0.1.0"
__all__ = [
    "KafkaApp",
    "TopicRouter",
    "Depends",
    "KafkaMessage",
    "JSONSerializer",
    "AvroSerializer",
]
