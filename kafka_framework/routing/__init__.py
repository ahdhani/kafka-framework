"""
Routing module for the Kafka framework.
"""

from .decorators import topic_event
from .router import EventHandler, TopicRouter

__all__ = ["TopicRouter", "EventHandler", "topic_event"]
