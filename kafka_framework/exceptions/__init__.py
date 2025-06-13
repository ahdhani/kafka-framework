"""
Exceptions module for the Kafka framework.
"""

from .handlers import (
    ConsumerError,
    KafkaFrameworkError,
    NonRetryableError,
    ProducerError,
    RetryableError,
    SerializationError,
    handle_exceptions,
    is_retryable,
)

__all__ = [
    "KafkaFrameworkError",
    "SerializationError",
    "ConsumerError",
    "ProducerError",
    "RetryableError",
    "NonRetryableError",
    "handle_exceptions",
    "is_retryable",
]
