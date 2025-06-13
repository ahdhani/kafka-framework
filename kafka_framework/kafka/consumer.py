"""
Kafka consumer implementation with priority queues and retry mechanism.
"""
from typing import Any, Dict, List, Optional, Set
import asyncio
from datetime import datetime
import logging
from queue import PriorityQueue

from aiokafka import AIOKafkaConsumer, ConsumerRecord
from aiokafka.errors import KafkaError

from ..routing import TopicRouter, EventHandler
from ..serialization import BaseSerializer
from ..models import KafkaMessage
from ..dependencies import solve_dependencies, DependencyCache

logger = logging.getLogger(__name__)

class KafkaConsumerManager:
    """
    Manages Kafka consumer operations with priority queues and retries.
    """
    def __init__(
        self,
        consumer: AIOKafkaConsumer,
        routers: List[TopicRouter],
        serializer: BaseSerializer,
    ):
        self.consumer = consumer
        self.routers = routers
        self.serializer = serializer
        self.topics: Set[str] = set()
        self.priority_queue: PriorityQueue = PriorityQueue()
        self.running = False
        
        # Collect all topics from routers
        for router in self.routers:
            self.topics.update(router.get_topics())
            
    async def start(self) -> None:
        """Start the consumer."""
        if self.running:
            return
            
        # Subscribe to all topics
        self.consumer.subscribe(list(self.topics))
        await self.consumer.start()
        self.running = True
        
        # Start message processing
        asyncio.create_task(self._process_messages())
        
    async def stop(self) -> None:
        """Stop the consumer."""
        self.running = False
        await self.consumer.stop()
        
    async def _process_messages(self) -> None:
        """Process messages from Kafka."""
        while self.running:
            try:
                batch = await self.consumer.getmany(timeout_ms=1000)
                for tp, messages in batch.items():
                    for message in messages:
                        await self._handle_message(message)
            except Exception as e:
                logger.error(f"Error processing messages: {e}")
                
    async def _handle_message(self, message: ConsumerRecord) -> None:
        """Handle a single message."""
        try:
            # Deserialize the message
            value = await self.serializer.deserialize(
                message.value,
                message.topic,
                dict(message.headers) if message.headers else None,
            )
            
            # Create KafkaMessage instance
            kafka_message = KafkaMessage.from_aiokafka(message, value)
            
            # Find the appropriate handler
            handler = None
            event_name = None
            for router in self.routers:
                for event, event_handler in router.routes.get(message.topic, {}).items():
                    if event in str(value):  # Simple event matching
                        handler = event_handler
                        event_name = event
                        break
                if handler:
                    break
                    
            if not handler:
                logger.warning(f"No handler found for message: {message}")
                return
                
            # Add to priority queue
            priority = handler.priority
            if kafka_message.headers.retry:
                # Lower priority for retried messages
                priority += kafka_message.headers.retry.retry_count
                
            self.priority_queue.put((priority, (handler, kafka_message)))
            await self._process_priority_queue()
            
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            
    async def _process_priority_queue(self) -> None:
        """Process messages in the priority queue."""
        while not self.priority_queue.empty():
            _, (handler, message) = self.priority_queue.get()
            try:
                # Solve dependencies
                cache = DependencyCache()
                values = await solve_dependencies(handler, cache)
                
                # Call the handler
                await handler.func(message, **values)
                
            except Exception as e:
                logger.error(f"Error in handler: {e}")
                await self._handle_failure(handler, message, e)
                
    async def _handle_failure(
        self,
        handler: EventHandler,
        message: KafkaMessage,
        error: Exception,
    ) -> None:
        """Handle message processing failure."""
        retry_count = message.headers.retry.retry_count if message.headers.retry else 0
        
        if retry_count < handler.retry_attempts:
            # Retry the message
            retry_info = {
                "topic": message.topic,
                "partition": message.partition,
                "offset": message.offset,
                "retry_count": retry_count + 1,
                "event_name": message.headers.retry.event_name if message.headers.retry else "unknown",
                "last_retried_timestamp": datetime.now().timestamp(),
            }
            
            # Add to priority queue with lower priority
            self.priority_queue.put(
                (handler.priority + retry_count + 1, (handler, message))
            )
            
        elif handler.dlq_topic:
            # Send to DLQ
            logger.warning(f"Sending message to DLQ: {handler.dlq_topic}")
            # DLQ implementation would go here
            pass
