"""
FastAPI-style Kafka framework for building event-driven applications.
"""

from .app import KafkaApp
from .routing import TopicRouter, topic_event
from .dependencies import Depends
from .models import KafkaMessage
from .serialization import JSONSerializer, AvroSerializer

__version__ = "0.1.0"
__all__ = [
    "KafkaApp",
    "TopicRouter",
    "topic_event",
    "Depends",
    "KafkaMessage",
    "JSONSerializer",
    "AvroSerializer",
]
