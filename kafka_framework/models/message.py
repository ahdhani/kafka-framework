"""
Message models for Kafka messages and headers.
"""
from typing import Any, Dict, Optional
from dataclasses import dataclass
from datetime import datetime

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
    retry: Optional[RetryInfo] = None
    custom_headers: Dict[str, Any] = None

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
    timestamp: datetime
    key: Optional[bytes] = None
    
    @classmethod
    def from_aiokafka(cls, message: Any, deserialized_value: Any) -> "KafkaMessage":
        """Create a KafkaMessage from an aiokafka message."""
        headers_dict = dict(message.headers) if message.headers else {}
        
        retry_info = None
        if "retry" in headers_dict:
            retry_data = headers_dict["retry"]
            retry_info = RetryInfo(
                topic=retry_data["topic"],
                partition=retry_data["partition"],
                offset=retry_data["offset"],
                retry_count=retry_data["retry_count"],
                event_name=retry_data["event_name"],
                last_retried_timestamp=datetime.fromtimestamp(
                    retry_data["last_retried_timestamp"]
                ),
            )
            
        headers = MessageHeaders(
            timestamp=datetime.fromtimestamp(message.timestamp/1000),
            data_version=headers_dict.get("data_version", "1.0"),
            retry=retry_info,
            custom_headers={
                k: v for k, v in headers_dict.items()
                if k not in ["data_version", "retry"]
            },
        )
        
        return cls(
            value=deserialized_value,
            headers=headers,
            topic=message.topic,
            partition=message.partition,
            offset=message.offset,
            timestamp=datetime.fromtimestamp(message.timestamp/1000),
            key=message.key,
        )
