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
from .utils.dlq import DLQHandler


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
        consumer_batch_size: int = 100,
        consumer_timeout_ms: int = 1000,
        shutdown_timeout: float = 30.0,
        dlq_topic_prefix: str = "dlq",
    ):
        if isinstance(bootstrap_servers, str):
            bootstrap_servers = [bootstrap_servers]

        self.bootstrap_servers = bootstrap_servers
        self.group_id = group_id or "kafka_framework_consumer_group"
        self.client_id = client_id
        self.serializer = serializer or JSONSerializer()
        self.config = KafkaConfig(**(config or {}))

        # Consumer settings
        self.consumer_batch_size = consumer_batch_size
        self.consumer_timeout_ms = consumer_timeout_ms
        self.shutdown_timeout = shutdown_timeout
        self.dlq_topic_prefix = dlq_topic_prefix

        self.routers: list[TopicRouter] = []
        self._consumer: KafkaConsumerManager | None = None
        self._producer: KafkaProducerManager | None = None
        self._dlq_handler: DLQHandler | None = None
        self._startup_done = False

    def include_router(self, router: TopicRouter) -> None:
        """Add a TopicRouter to the application."""
        self.routers.append(router)

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

    async def _setup_consumer(self) -> None:
        """Initialize the Kafka consumer."""
        # First ensure producer is setup for DLQ
        if not self._producer:
            await self._setup_producer()

        # Setup DLQ handler
        self._dlq_handler = DLQHandler(
            producer=self._producer,
            dlq_topic_prefix=self.dlq_topic_prefix,
        )

        # Setup consumer
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
            dlq_handler=self._dlq_handler,
            max_batch_size=self.consumer_batch_size,
            consumer_timeout_ms=self.consumer_timeout_ms,
            shutdown_timeout=self.shutdown_timeout,
        )

    async def start(self) -> None:
        """Start the Kafka application."""
        if self._startup_done:
            return

        # Setup components in correct order
        await self._setup_producer()
        await self._setup_consumer()

        # Start components
        if self._producer:
            await self._producer.start()
        if self._consumer:
            await self._consumer.start()

        self._startup_done = True

    async def stop(self) -> None:
        """Stop the Kafka application."""
        if self._consumer:
            await self._consumer.stop()
        if self._producer:
            await self._producer.stop()

        self._startup_done = False

    def get_all_topics_for_migration(self):
        """Both topics and its dlq's."""
        topics = set()
        for router in self.routers:
            route_handlers = router.get_route_handler_map()
            topics.update(router.get_topics())
            for handler in route_handlers.values():
                topics.add(handler.dlq_topic)
        return topics

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
