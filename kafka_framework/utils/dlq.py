"""
Dead Letter Queue (DLQ) utilities.
"""
from typing import Any, Dict, Optional
import json
import logging
from datetime import datetime

from ..models import KafkaMessage
from ..kafka.producer import KafkaProducerManager

logger = logging.getLogger(__name__)

class DLQHandler:
    """Handles Dead Letter Queue operations."""
    def __init__(
        self,
        producer: KafkaProducerManager,
        dlq_topic_prefix: str = "dlq",
    ):
        self.producer = producer
        self.dlq_topic_prefix = dlq_topic_prefix
        
    def get_dlq_topic(self, original_topic: str) -> str:
        """Get the DLQ topic name for an original topic."""
        return f"{self.dlq_topic_prefix}.{original_topic}"
        
    async def send_to_dlq(
        self,
        message: KafkaMessage,
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Send a failed message to the DLQ.
        
        Args:
            message: Original Kafka message
            error: Exception that caused the failure
            context: Additional context about the failure
        """
        dlq_topic = self.get_dlq_topic(message.topic)
        
        # Create DLQ message headers
        dlq_headers = {
            "original_topic": message.topic,
            "original_partition": str(message.partition),
            "original_offset": str(message.offset),
            "error_type": error.__class__.__name__,
            "error_message": str(error),
            "failed_at": datetime.now().isoformat(),
        }
        
        if context:
            dlq_headers["context"] = json.dumps(context)
            
        if message.headers.retry:
            dlq_headers["retry_count"] = str(message.headers.retry.retry_count)
            dlq_headers["last_retry"] = message.headers.retry.last_retried_timestamp.isoformat()
            
        # Send to DLQ topic
        try:
            await self.producer.send(
                topic=dlq_topic,
                value=message.value,
                key=message.key,
                headers=dlq_headers,
            )
            logger.info(
                f"Message sent to DLQ topic {dlq_topic}. "
                f"Original topic: {message.topic}, "
                f"Partition: {message.partition}, "
                f"Offset: {message.offset}"
            )
            
        except Exception as e:
            logger.error(f"Failed to send message to DLQ {dlq_topic}: {e}")
            raise
