"""
Kafka consumer implementation with priority queues and retry mechanism.
"""

import asyncio
import logging
import time
from asyncio import PriorityQueue
from datetime import datetime
from typing import Any

from aiokafka import AIOKafkaConsumer
from aiokafka.structs import ConsumerRecord

from ..dependencies import DependencyCache, get_dependant, solve_dependencies
from ..middleware.base import BaseMiddleware
from ..models import KafkaMessage, RetryInfo
from ..routing import EventHandler, TopicRouter
from ..serialization import BaseSerializer
from ..utils.dlq import DLQHandler

logger = logging.getLogger(__name__)


class KafkaConsumerManager:
    """
    Manages Kafka consumer operations with priority queues and routing.
    """

    def __init__(
        self,
        consumer: AIOKafkaConsumer,
        routers: list[TopicRouter],
        serializer: BaseSerializer,
        dlq_handler: DLQHandler,
        max_batch_size: int = 100,
        consumer_timeout_ms: int = 1000,
        shutdown_timeout: float = 30.0,
        middlewares: list[BaseMiddleware] | None = None,
    ):
        self.consumer = consumer
        self.routers = routers
        self.serializer = serializer
        self.dlq_handler = dlq_handler
        self.topics: set[str] = set()
        self.route_handler_map: dict[str, EventHandler] = {}
        self.priority_queue: PriorityQueue = PriorityQueue()
        self.running = False
        self.max_batch_size = max_batch_size
        self.consumer_timeout_ms = consumer_timeout_ms
        self.shutdown_timeout = shutdown_timeout
        self._consumer_task: asyncio.Task | None = None
        self._processor_task: asyncio.Task | None = None
        self._message_counter: int = 0
        self._error_counter: int = 0
        self._last_processed_time: float = time.time()
        self.middlewares = middlewares or []

        # Collect all topics from routers
        for router in self.routers:
            self.topics.update(router.get_topics())
            self.route_handler_map.update(router.get_route_handler_map())

    async def start(self) -> None:
        """Start the consumer and message processor tasks."""
        if self.running:
            return

        self.running = True

        # Subscribe to all topics
        self.consumer.subscribe(list(self.topics))
        await self.consumer.start()

        # Start consumer and processor tasks
        self._consumer_task = asyncio.create_task(self._consume_messages())
        self._processor_task = asyncio.create_task(self._process_priority_queue())

        logger.info(f"Started consumer for topics: {self.topics}")

    async def stop(self) -> None:
        """Gracefully stop the consumer and processor tasks."""
        if not self.running:
            return

        self.running = False
        logger.info("Stopping consumer manager...")

        # Wait for tasks to complete with timeout #TODO: Need to fix something here
        tasks = [t for t in [self._consumer_task, self._processor_task] if t is not None]
        if tasks:
            done, pending = await asyncio.wait(tasks, timeout=self.shutdown_timeout)
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        await self.consumer.stop()
        logger.info("Consumer manager stopped")

    def get_health_metrics(self) -> dict[str, Any]:
        """Return health metrics for monitoring."""
        return {
            "messages_processed": self._message_counter,
            "errors": self._error_counter,
            "queue_size": self.priority_queue.qsize(),
            "last_processed_time": self._last_processed_time,
            "is_running": self.running,
        }

    async def _consume_messages(self) -> None:
        """Consume messages from Kafka and add to priority queue."""
        while self.running:
            try:
                batch = await self.consumer.getmany(
                    timeout_ms=self.consumer_timeout_ms, max_records=self.max_batch_size
                )
                for _tp, messages in batch.items():
                    for message in messages:
                        await self._handle_message(message)

            except Exception as e:
                self._error_counter += 1
                logger.error(f"Error consuming messages: {e}", exc_info=True)
                await asyncio.sleep(1)  # Prevent tight loop on persistent errors

    async def _handle_message(self, message: ConsumerRecord) -> None:
        """Handle a single message and add to priority queue."""
        try:
            # Deserialize message value
            value = await self.serializer.deserialize(message.value)
            # Create KafkaMessage using the factory method
            kafka_message = KafkaMessage.from_aiokafka(message, value)

            # Determine routing key
            route = (
                f"{message.topic}.{kafka_message.headers.event_name}"
                if kafka_message.headers.event_name
                else message.topic
            )

            handler = self.route_handler_map.get(route)
            if not handler:
                logger.warning(f"No handler found for route: {route}")
                return

            # Add to priority queue with current retry count considered
            priority = self._calculate_priority(handler, kafka_message.headers.retry)
            await self.priority_queue.put((priority, (handler, kafka_message)))

        except Exception as e:
            self._error_counter += 1
            logger.error(f"Error handling message: {e}", exc_info=True)

    def _calculate_priority(self, handler: EventHandler, retry_info: RetryInfo | None) -> int:
        """Calculate message priority based on handler priority and retry count."""
        base_priority = handler.priority
        retry_count = retry_info.retry_count if retry_info else 0
        return base_priority + (retry_count * 10)  # Lower priority for retried messages

    async def _process_priority_queue(self) -> None:
        """Process messages from the priority queue."""
        while self.running:
            try:
                # Get message with timeout to allow for graceful shutdown
                try:
                    _, (handler, message) = await asyncio.wait_for(
                        self.priority_queue.get(), timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue

                await self._process_message(handler, message)
                self._last_processed_time = time.time()
                self._message_counter += 1

            except Exception as e:
                self._error_counter += 1
                logger.error(f"Error in priority queue processing: {e}", exc_info=True)
                await asyncio.sleep(1)

    async def _process_message(self, handler: EventHandler, message: KafkaMessage) -> None:
        """Process a single message with its handler."""
        try:
            # Create middleware chain
            async def execute_handler(msg: KafkaMessage) -> Any:
                # Solve dependencies
                cache = DependencyCache()
                dependant = get_dependant(handler.func)
                values = await solve_dependencies(dependant, cache)
                # Execute handler
                return await handler.func(msg, **values)

            # Build middleware chain
            middleware_chain = execute_handler
            for middleware in reversed(self.middlewares):
                next_chain = middleware_chain

                def middleware_chain(msg, m=middleware, n=next_chain):
                    return m(msg, n)

            # Execute middleware chain
            await middleware_chain(message)

        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            await self._handle_failure(handler, message, e)

    async def _handle_failure(
        self,
        handler: EventHandler,
        message: KafkaMessage,
        error: Exception,
    ) -> None:
        """Handle message processing failure with exponential backoff retry."""
        retry_count = message.headers.retry.retry_count if message.headers.retry else 0

        if retry_count < handler.retry_attempts:
            # Calculate backoff delay
            delay = min(2**retry_count, 300)  # Max 5 minutes delay

            # Update retry information
            retry_info = RetryInfo(
                topic=message.topic,
                partition=message.partition,
                offset=message.offset,
                retry_count=retry_count + 1,
                event_name=message.headers.event_name or "",
                last_retried_timestamp=datetime.now(),
            )

            # Update message headers with new retry info
            message.headers.retry = retry_info

            # Wait for backoff period
            await asyncio.sleep(delay)

            # Requeue with updated priority
            priority = self._calculate_priority(handler, message.headers.retry)
            await self.priority_queue.put((priority, (handler, message)))

            logger.info(f"Retrying message (attempt {retry_count + 1}/{handler.retry_attempts})")

        elif handler.dlq_topic:
            # Send to DLQ with context
            context = {
                "handler": handler.__class__.__name__,
                "retry_attempts": handler.retry_attempts,
            }

            try:
                await self.dlq_handler.send_to_dlq(handler.dlq_topic, message, error, context)
            except Exception as dlq_error:
                logger.error(
                    f"Failed to send message to DLQ. Original error: {error}. "
                    f"DLQ error: {dlq_error}",
                    exc_info=True,
                )
