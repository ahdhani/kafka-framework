"""
Main KafkaApp class implementation.
"""

import logging
from contextlib import asynccontextmanager
from typing import Any

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

from .kafka.consumer import KafkaConsumerManager
from .kafka.producer import KafkaProducerManager
from .middleware.base import BaseMiddleware
from .models import KafkaConfig
from .routing import TopicRouter
from .serialization import BaseSerializer, JSONSerializer
from .utils.dlq import DLQHandler

logger = logging.getLogger(__name__)


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
        self.middlewares: list[BaseMiddleware] = []
        self._consumer: KafkaConsumerManager | None = None
        self._producer: KafkaProducerManager | None = None
        self._dlq_handler: DLQHandler | None = None
        self._startup_done = False

        logger.info(
            "Initialized KafkaApp with bootstrap_servers=%s, group_id=%s, client_id=%s",
            bootstrap_servers,
            self.group_id,
            self.client_id,
        )

    def include_router(self, router: TopicRouter) -> None:
        """Add a TopicRouter to the application."""
        self.routers.append(router)
        topics = router.get_topics()
        logger.info(
            "Added router with %d topics: %s",
            len(topics),
            ", ".join(sorted(topics)),
        )

    def add_middleware(self, middleware: BaseMiddleware) -> None:
        """Add a middleware to the application.

        Args:
            middleware: An instance of BaseMiddleware to be added to the processing pipeline.
        """
        self.middlewares.append(middleware)
        logger.info(f"Added middleware: {middleware.__class__.__name__}")

    async def _setup_producer(self) -> None:
        """Initialize the Kafka producer."""
        logger.info("Setting up Kafka producer...")
        try:
            producer = AIOKafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                client_id=self.client_id,
                **self.config.producer_config,
            )
            self._producer = KafkaProducerManager(
                producer=producer,
                serializer=self.serializer,
            )
            logger.info("Kafka producer setup complete")
        except Exception as e:
            logger.error("Failed to setup Kafka producer: %s", e, exc_info=True)
            raise

    async def _setup_consumer(self) -> None:
        """Initialize the Kafka consumer."""
        logger.info("Setting up Kafka consumer...")
        try:
            # First ensure producer is setup for DLQ
            if not self._producer:
                logger.info("Setting up producer for DLQ support...")
                await self._setup_producer()

            # Setup DLQ handler
            self._dlq_handler = DLQHandler(
                producer=self._producer,
                dlq_topic_prefix=self.dlq_topic_prefix,
            )
            logger.info("DLQ handler initialized with prefix: %s", self.dlq_topic_prefix)

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
                middlewares=self.middlewares,
            )
            logger.info(
                "Consumer setup complete. Batch size: %d, Timeout: %dms",
                self.consumer_batch_size,
                self.consumer_timeout_ms,
            )
        except Exception as e:
            logger.error("Failed to setup Kafka consumer: %s", e, exc_info=True)
            raise

    async def start(self) -> None:
        """Start the Kafka application."""
        if self._startup_done:
            logger.warning("Application already started")
            return

        logger.info("Starting Kafka application...")
        try:
            # Setup components in correct order
            await self._setup_producer()
            await self._setup_consumer()

            # Start components
            if self._producer:
                await self._producer.start()
                logger.info("Producer started successfully")

            if self._consumer:
                await self._consumer.start()
                logger.info("Consumer started successfully")

            self._startup_done = True
            logger.info("Kafka application startup complete")

        except Exception as e:
            logger.error("Failed to start Kafka application: %s", e, exc_info=True)
            # Attempt cleanup
            await self.stop()
            raise

    async def stop(self) -> None:
        """Stop the Kafka application."""
        logger.info("Stopping Kafka application...")
        try:
            if self._consumer:
                await self._consumer.stop()
                logger.info("Consumer stopped successfully")

            if self._producer:
                await self._producer.stop()
                logger.info("Producer stopped successfully")

            self._startup_done = False
            logger.info("Kafka application shutdown complete")

        except Exception as e:
            logger.error("Error during application shutdown: %s", e, exc_info=True)
            raise

    @asynccontextmanager
    async def lifespan(self):
        """Lifespan context manager for the application."""
        logger.info("Entering application lifespan")
        try:
            await self.start()
            yield
        finally:
            logger.info("Exiting application lifespan")
            await self.stop()
