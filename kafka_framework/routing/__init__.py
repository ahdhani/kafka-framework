"""
Routing module for the Kafka framework.
"""

from .router import EventHandler, TopicRouter

__all__ = ["TopicRouter", "EventHandler"]
