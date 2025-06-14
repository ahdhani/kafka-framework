"""
Kafka producer implementation.
"""

import logging
from typing import Any

from aiokafka import AIOKafkaProducer

from ..serialization import BaseSerializer

logger = logging.getLogger(__name__)


class KafkaProducerManager:
    """
    Manages Kafka producer operations.
    """

    def __init__(
        self,
        producer: AIOKafkaProducer,
        serializer: BaseSerializer,
    ):
        self.producer = producer
        self.serializer = serializer

    async def start(self) -> None:
        """Start the producer."""
        await self.producer.start()

    async def stop(self) -> None:
        """Stop the producer."""
        await self.producer.stop()

    async def send(
        self,
        topic: str,
        value: Any,
        key: bytes | None = None,
        partition: int | None = None,
        timestamp_ms: int | None = None,
        headers: dict[str, Any] | None = None,
    ) -> None:
        """
        Send a message to Kafka.

        Args:
            topic: Topic to send the message to
            value: Message value
            key: Message key
            partition: Specific partition (optional)
            timestamp_ms: Message timestamp in milliseconds (optional)
            headers: Message headers (optional)
        """
        try:
            # Serialize the value
            serialized_value = await self.serializer.serialize(value)

            # Convert headers to list of tuples if present
            kafka_headers = None
            if headers:
                kafka_headers = [(str(k), str(v).encode()) for k, v in headers.items()]

            # Send the message
            await self.producer.send(
                topic,
                value=serialized_value,
                key=key,
                partition=partition,
                timestamp_ms=timestamp_ms,
                headers=kafka_headers,
            )

        except Exception as e:
            logger.error(f"Error sending message to {topic}: {e}")
            raise
