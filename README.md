# Kafka Framework

A FastAPI-inspired framework for building Kafka applications in Python with a focus on developer experience and robust features.

## Features

- FastAPI-style routing with decorators
- Dependency injection system
- Pluggable serialization (JSON, Protobuf, Avro)
- Priority-based message processing
- Configurable retry mechanism with exception filtering
- Dead Letter Queue (DLQ) support
- Async/await patterns using aiokafka
- Type hints throughout

## Installation

Basic installation:
```bash
pip install kafka-framework
```

With Avro support:
```bash
pip install kafka-framework[avro]
```

With all extras:
```bash
pip install kafka-framework[all]
```

## Quick Start

```python
from kafka_framework import KafkaApp, TopicRouter, Depends
from kafka_framework.serialization import JSONSerializer

# Create the app instance
app = KafkaApp(
    bootstrap_servers=["localhost:9092"],
    group_id="my-consumer-group",
    serializer=JSONSerializer()
)

# Create a router
router = TopicRouter()

# Define dependencies
async def get_db():
    # Return database connection
    return {"connection": "db"}

def get_config():
    return {"env": "production"}

# Define event handlers
@router.topic_event("orders", "order_created", priority=1)
async def handle_order_created(message, db=Depends(get_db), config=Depends(get_config)):
    order = message.value
    print(f"Processing order {order['id']} with config {config}")
    # Process order...

@router.topic_event(
    "orders",
    "order_cancelled",
    priority=2,
    retry_attempts=3,
    dlq_topic="orders_dlq"
)
async def handle_order_cancelled(message):
    order = message.value
    print(f"Cancelling order {order['id']}")
    # Cancel order...

# Include router in app
app.include_router(router)

# Run the app
async def main():
    async with app.lifespan():
        await app.start()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

## Advanced Features

### Priority-based Processing

Messages are processed based on handler priority (higher numbers first):

```python
@router.topic_event("notifications", "high_priority", priority=10)
async def handle_high_priority(message):
    # Processed first
    pass

@router.topic_event("notifications", "low_priority", priority=1)
async def handle_low_priority(message):
    # Processed after high priority
    pass
```

### Retry Mechanism

Configure retries with exponential backoff:

```python
from kafka_framework.kafka import RetryConfig
from kafka_framework.exceptions import RetryableError

retry_config = RetryConfig(
    max_attempts=3,
    initial_delay=1.0,
    max_delay=60.0,
    exponential_base=2.0,
    exceptions=[RetryableError]
)

@router.topic_event(
    "payments",
    "payment_processed",
    retry_attempts=3,
    retry_config=retry_config
)
async def handle_payment(message):
    # Will retry up to 3 times with exponential backoff
    pass
```

### Dead Letter Queue (DLQ)

Handle failed messages with DLQ:

```python
@router.topic_event(
    "orders",
    "order_created",
    dlq_topic="orders_dlq"
)
async def handle_order(message):
    # Failed messages will be sent to orders_dlq topic
    pass
```

### Custom Serialization

Use Avro serialization (requires kafka-framework[avro]):

```python
from kafka_framework.serialization import AvroSerializer

schema = {
    "type": "record",
    "name": "Order",
    "fields": [
        {"name": "id", "type": "string"},
        {"name": "amount", "type": "double"}
    ]
}

app = KafkaApp(
    bootstrap_servers=["localhost:9092"],
    serializer=AvroSerializer(
        schema_registry_url="http://localhost:8081",
        schema_str=json.dumps(schema)
    )
)
```

### Message Headers

Access message headers and metadata:

```python
@router.topic_event("orders", "order_created")
async def handle_order(message):
    # Access message data
    order_data = message.value

    # Access message headers
    print(f"Data version: {message.headers.data_version}")
    print(f"Timestamp: {message.headers.timestamp}")

    # Access retry information (if being retried)
    if message.headers.retry:
        print(f"Retry count: {message.headers.retry.retry_count}")
        print(f"Last retry: {message.headers.retry.last_retried_timestamp}")
```

## Configuration

### Consumer Configuration

```python
app = KafkaApp(
    bootstrap_servers=["localhost:9092"],
    group_id="my-group",
    config={
        "consumer_config": {
            "auto_offset_reset": "earliest",
            "enable_auto_commit": True,
            "max_poll_records": 500
        }
    }
)
```

### Producer Configuration

```python
app = KafkaApp(
    bootstrap_servers=["localhost:9092"],
    config={
        "producer_config": {
            "acks": "all",
            "compression_type": "gzip",
            "max_request_size": 1048576
        }
    }
)
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
