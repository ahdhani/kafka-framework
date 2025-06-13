"""
Routing module for the Kafka framework.
"""
from .router import TopicRouter, EventHandler
from .decorators import topic_event

__all__ = ["TopicRouter", "EventHandler", "topic_event"]
