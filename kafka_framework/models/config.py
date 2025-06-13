"""
Configuration models for the Kafka framework.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class KafkaConfig:
    """Configuration for Kafka consumer and producer."""

    consumer_config: dict[str, Any] = field(default_factory=dict)
    producer_config: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        # Set default consumer config
        self.consumer_config.setdefault("auto_offset_reset", "earliest")
        self.consumer_config.setdefault("enable_auto_commit", True)
        self.consumer_config.setdefault("max_poll_records", 500)

        # Set default producer config
        self.producer_config.setdefault("acks", "all")
        self.producer_config.setdefault("compression_type", "gzip")
        self.producer_config.setdefault("max_request_size", 1048576)  # 1MB
        self.producer_config.setdefault("request_timeout_ms", 30000)  # 30s
