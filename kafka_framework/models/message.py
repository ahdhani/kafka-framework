"""
Message models for Kafka messages and headers.
"""

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from aiokafka import ConsumerRecord


@dataclass
class RetryInfo:
    """Retry information for a message."""

    topic: str
    partition: int
    offset: int
    retry_count: int
    event_name: str
    last_retried_timestamp: datetime


@dataclass
class MessageHeaders:
    """Headers for a Kafka message."""

    timestamp: datetime
    data_version: str
    retry: RetryInfo | None = None
    custom_headers: dict[str, Any] = None
    event_name: str | None = None


@dataclass
class KafkaMessage:
    """
    Rich Kafka message model with comprehensive headers.
    """

    value: Any
    headers: MessageHeaders
    topic: str
    partition: int
    offset: int
    key: bytes | None = None

    @classmethod
    def from_aiokafka(cls, message: ConsumerRecord, deserialized_value: Any) -> "KafkaMessage":
        """Create a KafkaMessage from an aiokafka message."""
        headers_dict = {x[0]: x[1].decode() for x in message.headers} if message.headers else {}
        retry_info = None
        if "retry" in headers_dict:
            retry_data = json.loads(headers_dict["retry"])
            retry_info = RetryInfo(
                topic=retry_data["topic"],
                partition=retry_data["partition"],
                offset=retry_data["offset"],
                retry_count=retry_data["retry_count"],
                event_name=retry_data["event_name"],
                last_retried_timestamp=datetime.fromtimestamp(retry_data["last_retried_timestamp"]),
            )

        headers = MessageHeaders(
            timestamp=datetime.fromtimestamp(message.timestamp / 1000),
            data_version=headers_dict.get("data_version", "1.0"),
            retry=retry_info,
            event_name=headers_dict.get("event_name"),
            custom_headers={
                k: v.decode()
                for k, v in headers_dict.items()
                if k not in ["data_version", "retry", "timestamp", "event_name"]
            },
        )

        return cls(
            value=deserialized_value,
            headers=headers,
            topic=message.topic,
            partition=message.partition,
            offset=message.offset,
            key=message.key,
        )

    def __lt__(self, other):  # TODO : Fix properly
        return self.partition < other.partition
