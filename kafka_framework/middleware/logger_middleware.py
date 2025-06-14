"""
Logger middleware implementation.
"""

import logging
import time
from typing import Any

from ..models import KafkaMessage
from .base import BaseMiddleware, NextMiddleware

logger = logging.getLogger(__name__)


class KafkaLoggerMiddleware(BaseMiddleware):
    """
    Middleware for logging Kafka message processing.
    """

    def __init__(self, log_level: int = logging.INFO):
        self.log_level = log_level

    @staticmethod
    def log_message(level: str, message: str, extra: dict[str, Any] | None = None) -> None:
        """Log a message with the specified level and extra data."""
        log_func = getattr(logger, level.lower(), logger.info)
        log_func(message, extra=extra or {})

    async def __call__(self, message: KafkaMessage, next_middleware: NextMiddleware) -> Any:
        """Process and log the message."""
        start_time = time.time()

        # Log message receipt
        self.log_message(
            "info",
            f"Processing message from topic: {message.topic}",
            {
                "topic": message.topic,
                "partition": message.partition,
                "offset": message.offset,
                "key": message.key,
                "timestamp": message.headers.timestamp,
            },
        )

        try:
            # Process message
            result = await next_middleware(message)

            # Log successful processing
            processing_time = time.time() - start_time
            self.log_message(
                "info",
                f"Successfully processed message from topic {message.topic}",
                {
                    "topic": message.topic,
                    "processing_time": processing_time,
                    "success": True,
                },
            )

            return result

        except Exception as e:
            # Log processing failure
            processing_time = time.time() - start_time
            self.log_message(
                "error",
                f"Failed to process message from topic {message.topic}: {str(e)}",
                {
                    "topic": message.topic,
                    "processing_time": processing_time,
                    "success": False,
                    "error": str(e),
                },
            )
            raise
