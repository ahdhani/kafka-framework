"""
Unit tests for base middleware chain execution.
"""

from datetime import datetime

import pytest

from kafka_framework.middleware.base import BaseMiddleware
from kafka_framework.models import KafkaMessage, MessageHeaders


class MiddlewareTest(BaseMiddleware):
    def __init__(self, should_fail=False):
        self.called = False
        self.should_fail = should_fail

    async def __call__(self, message, next_middleware):
        self.called = True
        if self.should_fail:
            raise ValueError("Test error")
        return await next_middleware(message)


@pytest.mark.asyncio
async def test_middleware_chain_execution():
    """Test basic middleware chain execution."""
    middleware = MiddlewareTest()
    message = KafkaMessage(
        topic="test",
        partition=0,
        offset=0,
        key=None,
        value={"test": "data"},
        headers=MessageHeaders(
            timestamp=datetime.now(),
            data_version="1.0",
            retry=None,
            custom_headers={},
            event_name="test_event",
        ),
    )

    async def handler(msg):
        return msg.value

    # Create middleware chain
    async def next_middleware(msg):
        return await handler(msg)

    # Execute middleware
    result = await middleware(message, next_middleware)

    assert middleware.called
    assert result == {"test": "data"}


@pytest.mark.asyncio
async def test_middleware_chain_error():
    """Test middleware chain error handling."""
    middleware = MiddlewareTest(should_fail=True)
    message = KafkaMessage(
        topic="test",
        partition=0,
        offset=0,
        key=None,
        value={"test": "data"},
        headers=MessageHeaders(
            timestamp=datetime.now(),
            data_version="1.0",
            retry=None,
            custom_headers={},
            event_name="test_event",
        ),
    )

    async def handler(msg):
        return msg.value

    async def next_middleware(msg):
        return await handler(msg)

    with pytest.raises(ValueError, match="Test error"):
        await middleware(message, next_middleware)

    assert middleware.called
