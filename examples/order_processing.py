"""
Example order processing application using the Kafka framework.
"""

import logging
from datetime import datetime

from kafka_framework import Depends, KafkaApp, TopicRouter
from kafka_framework.exceptions import RetryableError
from kafka_framework.middleware import KafkaLoggerMiddleware
from kafka_framework.serialization import JSONSerializer
from kafka_framework.utils.logging import setup_logging

# Setup logging with debug level and file output
setup_logging(
    level=logging.INFO,
    # log_file="order_processing.log"
)

logger = logging.getLogger(__name__)

# Create the app instance
app = KafkaApp(
    bootstrap_servers=["localhost:9094"],
    group_id="order-processor",
    serializer=JSONSerializer(),
    config={
        "consumer_config": {
            "auto_offset_reset": "earliest",
            "enable_auto_commit": True,
        }
    },
)

# Create a router
router = TopicRouter()


# Define dependencies
async def get_db():
    """Simulate database connection."""
    await asyncio.sleep(0.1)  # Simulate connection time
    return {"connection": "db"}


def get_config():
    """Get configuration."""
    return {"payment_gateway": "stripe", "environment": "development"}


# Define event handlers
@router.topic_event("orders", "order_created", priority=1)
async def handle_order_created(message, db=Depends(get_db), config=Depends(get_config)):
    """Handle order creation events."""
    order = message.value
    logger.info("Test dependency %s", db)

    # Simulate failure for demonstration
    logger.info("Processing order %s at %s", order["id"], datetime.now())
    logger.info("Using payment gateway: %s", config["payment_gateway"])

    # Simulate order processing
    await asyncio.sleep(1)
    logger.info("Order %s processed successfully", order["id"])


@router.topic_event("orders", "order_cancelled", priority=2, retry_attempts=3)
async def handle_order_cancelled(message):
    """Handle order cancellation events."""
    order = message.value
    logger.info("Cancelling order %s at %s", order["id"], datetime.now())

    # Simulate failure for demonstration
    if order.get("simulate_failure"):
        raise RetryableError("Temporary failure in order cancellation")

    # Simulate cancellation
    await asyncio.sleep(1)
    logger.info("Order %s cancelled successfully", order["id"])


# Include router in app
app.include_router(router)

app.add_middleware(KafkaLoggerMiddleware())


async def produce_test_messages():
    """Produce some test messages."""
    test_orders = [
        {"id": "order-001", "customer": "John Doe", "amount": 99.99, "status": "created"},
        {
            "id": "order-002",
            "customer": "Jane Smith",
            "amount": 149.99,
            "status": "cancelled",
            "simulate_failure": True,
        },
    ]

    # Produce messages
    for order in test_orders:
        if order["status"] == "created":
            await app._producer.send(
                key=order["id"].encode(),
                topic="orders",
                value=order,
                headers={"data_version": "1.0", "event_name": "order_created"},
            )
        else:
            await app._producer.send(
                key=order["id"].encode(),
                topic="orders",
                value=order,
                headers={"event_name": "order_cancelled", "data_version": "1.0"},
            )

        logger.info("Produced message for order %s", order["id"])


async def main():
    """Run the example."""
    async with app.lifespan():
        # Start producing test messages
        await produce_test_messages()

        # Keep the consumer running
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Shutting down...")


if __name__ == "__main__":
    import asyncio

    logger.info("Starting order processing service...")

    asyncio.run(main())
