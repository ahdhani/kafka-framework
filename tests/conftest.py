"""
Common test fixtures and utilities.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from kafka_framework.app import KafkaApp  # Adjust import based on your layout


@pytest.fixture
def mock_serializer():
    serializer = MagicMock()
    serializer.serialize.return_value = b"mocked-bytes"
    serializer.deserialize.return_value = {"mocked": "data"}
    return serializer


@pytest.fixture
def kafka_config():
    return {
        "bootstrap_servers": "localhost:9092",
        "group_id": "test-group",
        "client_id": "test-client",
    }


@pytest.fixture
def mock_kafka_app(mock_serializer, kafka_config):
    app = KafkaApp(
        bootstrap_servers=kafka_config["bootstrap_servers"],
        group_id=kafka_config["group_id"],
        client_id=kafka_config["client_id"],
        serializer=mock_serializer,
    )

    with (
        patch("kafka_framework.app.AIOKafkaProducer", new_callable=AsyncMock),
        patch("kafka_framework.app.AIOKafkaConsumer", new_callable=AsyncMock),
        patch("kafka_framework.app.KafkaProducerManager"),
        patch("kafka_framework.app.KafkaConsumerManager"),
        patch("kafka_framework.app.DLQHandler"),
    ):
        # Stub producer manager and consumer manager
        app._producer = MagicMock()
        app._producer.start = AsyncMock()
        app._producer.stop = AsyncMock()

        app._consumer = MagicMock()
        app._consumer.start = AsyncMock()
        app._consumer.stop = AsyncMock()

        app._dlq_handler = MagicMock()

        # Mark startup done to bypass internal checks
        app._startup_done = True

        yield app
