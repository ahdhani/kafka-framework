"""
Unit tests for message processing in KafkaConsumerManager.
"""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiokafka.structs import ConsumerRecord

from kafka_framework.kafka.consumer import KafkaConsumerManager
from kafka_framework.middleware.base import BaseMiddleware
from kafka_framework.models import KafkaMessage, RetryInfo
from kafka_framework.routing import EventHandler


class MiddlewareTestable(BaseMiddleware):
    def __init__(self):
        self.calls = []

    async def __call__(self, message, call_next):
        self.calls.append(("before", message))
        result = await call_next(message)
        self.calls.append(("after", result))
        return result


@pytest.fixture
def mock_consumer_record():
    """Create a mock ConsumerRecord."""
    return ConsumerRecord(
        topic="test-topic",
        partition=0,
        offset=0,
        timestamp=int(datetime.now().timestamp() * 1000),
        timestamp_type=0,
        key=None,
        value=b'{"test": "data"}',
        checksum=None,
        serialized_key_size=-1,
        serialized_value_size=len(b'{"test": "data"}'),
        headers=[("event_name", b"test_event"), ("data_version", b"1.0")],
    )


@pytest.fixture
def mock_kafka_message(mock_consumer_record):
    """Create a mock KafkaMessage."""
    return KafkaMessage.from_aiokafka(mock_consumer_record, {"test": "data"})


@pytest.fixture
def mock_handler():
    """Create a mock EventHandler."""

    async def handler_func(message):
        return message.value

    return EventHandler(func=handler_func, priority=1, retry_attempts=3, dlq_topic="test-dlq")


@pytest.fixture
async def consumer_manager():
    """Create a KafkaConsumerManager with mocked dependencies."""
    consumer = AsyncMock()
    router = MagicMock()
    serializer = AsyncMock()
    serializer.deserialize = AsyncMock(return_value={"test": "data"})
    dlq_handler = AsyncMock()

    manager = KafkaConsumerManager(
        consumer=consumer,
        routers=[router],
        serializer=serializer,
        dlq_handler=dlq_handler,
    )

    yield manager
    manager.running = False


@pytest.mark.asyncio
async def test_handle_message_success(consumer_manager, mock_consumer_record):
    """Test successful message handling."""
    # Setup
    handler = AsyncMock()
    consumer_manager.route_handler_map = {"test-topic.test_event": handler}

    # Execute
    await consumer_manager._handle_message(mock_consumer_record)

    # Verify
    assert consumer_manager.priority_queue.qsize() == 1
    priority, (stored_handler, stored_message) = await consumer_manager.priority_queue.get()
    assert stored_handler == handler
    assert isinstance(stored_message, KafkaMessage)
    assert stored_message.topic == mock_consumer_record.topic


@pytest.mark.asyncio
async def test_handle_message_no_handler(consumer_manager, mock_consumer_record):
    """Test message handling when no handler is found."""
    # Setup
    consumer_manager.route_handler_map = {}

    # Execute
    await consumer_manager._handle_message(mock_consumer_record)

    # Verify
    assert consumer_manager.priority_queue.qsize() == 0


@pytest.mark.asyncio
async def test_calculate_priority(consumer_manager, mock_handler):
    """Test priority calculation with different retry counts."""
    # No retries
    priority = consumer_manager._calculate_priority(mock_handler, None)
    assert priority == mock_handler.priority

    # With retries
    retry_info = RetryInfo(
        topic="test",
        partition=0,
        offset=0,
        retry_count=2,
        event_name="test",
        last_retried_timestamp=datetime.now(),
    )
    priority = consumer_manager._calculate_priority(mock_handler, retry_info)
    assert priority == mock_handler.priority + (2 * 10)


@pytest.mark.asyncio
async def test_process_message_success(consumer_manager, mock_kafka_message, mock_handler):
    """Test successful message processing."""
    # Setup
    middleware = MiddlewareTestable()
    consumer_manager.middlewares = [middleware]

    # Execute
    await consumer_manager._process_message(mock_handler, mock_kafka_message)

    # Verify middleware was called
    assert len(middleware.calls) == 2
    assert middleware.calls[0][0] == "before"
    assert middleware.calls[1][0] == "after"


@pytest.mark.asyncio
async def test_process_message_failure(consumer_manager, mock_kafka_message, mock_handler):
    """Test message processing with failure and retry."""

    # Setup
    async def failing_handler(message):
        raise ValueError("Test error")

    mock_handler.func = failing_handler

    # Execute
    await consumer_manager._process_message(mock_handler, mock_kafka_message)

    # Verify message was requeued
    assert consumer_manager.priority_queue.qsize() == 1
    priority, (stored_handler, stored_message) = await consumer_manager.priority_queue.get()
    assert stored_handler == mock_handler
    assert stored_message.headers.retry.retry_count == 1


@pytest.mark.asyncio
async def test_handle_failure_with_retries(consumer_manager, mock_kafka_message, mock_handler):
    """Test failure handling with retries."""
    error = ValueError("Test error")

    # Execute with retry count < max attempts
    await consumer_manager._handle_failure(mock_handler, mock_kafka_message, error)

    # Verify message was requeued
    assert consumer_manager.priority_queue.qsize() == 1
    priority, (stored_handler, stored_message) = await consumer_manager.priority_queue.get()
    assert stored_message.headers.retry.retry_count == 1


@pytest.mark.asyncio
async def test_handle_failure_dlq(consumer_manager, mock_kafka_message, mock_handler):
    """Test failure handling when max retries exceeded."""
    # Setup
    error = ValueError("Test error")
    mock_kafka_message.headers.retry = RetryInfo(
        topic="test",
        partition=0,
        offset=0,
        retry_count=3,  # Max retries reached
        event_name="test",
        last_retried_timestamp=datetime.now(),
    )

    # Execute
    await consumer_manager._handle_failure(mock_handler, mock_kafka_message, error)

    # Verify DLQ handler was called
    consumer_manager.dlq_handler.send_to_dlq.assert_called_once()
    call_args = consumer_manager.dlq_handler.send_to_dlq.call_args
    assert call_args[0][0] == mock_handler.dlq_topic  # dlq_topic
    assert call_args[0][1] == mock_kafka_message  # message
    assert isinstance(call_args[0][2], ValueError)  # error
    assert "retry_attempts" in call_args[0][3]  # context


@pytest.mark.asyncio
async def test_process_priority_queue(consumer_manager, mock_kafka_message, mock_handler):
    """Test priority queue processing."""
    # Setup
    consumer_manager.running = True
    await consumer_manager.priority_queue.put((1, (mock_handler, mock_kafka_message)))

    # Start processing in background
    task = asyncio.create_task(consumer_manager._process_priority_queue())

    # Wait a bit for processing
    await asyncio.sleep(0.1)

    # Stop processing
    consumer_manager.running = False
    await task

    # Verify metrics
    assert consumer_manager._message_counter == 1
    assert consumer_manager._last_processed_time is not None
