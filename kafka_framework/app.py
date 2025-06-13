"""
Main KafkaApp class implementation.
"""

from contextlib import asynccontextmanager
from typing import Any

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

from .kafka.consumer import KafkaConsumerManager
from .kafka.producer import KafkaProducerManager
from .models import KafkaConfig
from .routing import TopicRouter
from .serialization import BaseSerializer, JSONSerializer


class KafkaApp:
    """
    Main application class for the Kafka framework.
    Similar to FastAPI's FastAPI class.
    """

    def __init__(
        self,
        *,
        bootstrap_servers: str | list[str],
        group_id: str | None = None,
        client_id: str | None = None,
        serializer: BaseSerializer | None = None,
        config: dict[str, Any] | None = None,
    ):
        if isinstance(bootstrap_servers, str):
            bootstrap_servers = [bootstrap_servers]

        self.bootstrap_servers = bootstrap_servers
        self.group_id = group_id or "kafka_framework_consumer_group"
        self.client_id = client_id
        self.serializer = serializer or JSONSerializer()
        self.config = KafkaConfig(**(config or {}))

        self.routers: list[TopicRouter] = []
        self._consumer: KafkaConsumerManager | None = None
        self._producer: KafkaProducerManager | None = None
        self._startup_done = False

    def include_router(self, router: TopicRouter) -> None:
        """Add a TopicRouter to the application."""
        self.routers.append(router)

    async def _setup_consumer(self) -> None:
        """Initialize the Kafka consumer."""
        consumer = AIOKafkaConsumer(
            bootstrap_servers=self.bootstrap_servers,
            group_id=self.group_id,
            client_id=self.client_id,
            **self.config.consumer_config,
        )
        self._consumer = KafkaConsumerManager(
            consumer=consumer,
            routers=self.routers,
            serializer=self.serializer,
        )

    async def _setup_producer(self) -> None:
        """Initialize the Kafka producer."""
        producer = AIOKafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            client_id=self.client_id,
            **self.config.producer_config,
        )
        self._producer = KafkaProducerManager(
            producer=producer,
            serializer=self.serializer,
        )

    async def start(self) -> None:
        """Start the Kafka application."""
        if self._startup_done:
            return

        await self._setup_consumer()
        await self._setup_producer()

        if self._consumer:
            await self._consumer.start()
        if self._producer:
            await self._producer.start()

        self._startup_done = True

    async def stop(self) -> None:
        """Stop the Kafka application."""
        if self._consumer:
            await self._consumer.stop()
        if self._producer:
            await self._producer.stop()

        self._startup_done = False

    @asynccontextmanager
    async def lifespan(self):
        """Lifespan context manager for the application."""
        await self.start()
        try:
            yield self
        finally:
            await self.stop()

    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop()
