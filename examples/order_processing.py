"""
Example of using the Kafka framework for order processing.
"""

import asyncio
from datetime import datetime

from kafka_framework import Depends, KafkaApp, TopicRouter
from kafka_framework.exceptions import RetryableError
from kafka_framework.serialization import JSONSerializer

# Create the app instance
app = KafkaApp(
    bootstrap_servers=["localhost:9092"],
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
    print(f"Processing order {order['id']} at {datetime.now()}")
    print(f"Using payment gateway: {config['payment_gateway']}")

    # Simulate order processing
    await asyncio.sleep(1)
    print(f"Order {order['id']} processed successfully")


@router.topic_event(
    "orders", "order_cancelled", priority=2, retry_attempts=3, dlq_topic="orders_dlq"
)
async def handle_order_cancelled(message):
    """Handle order cancellation events."""
    order = message.value
    print(f"Cancelling order {order['id']} at {datetime.now()}")

    # Simulate failure for demonstration
    if order.get("simulate_failure"):
        raise RetryableError("Temporary failure in order cancellation")

    # Simulate cancellation
    await asyncio.sleep(1)
    print(f"Order {order['id']} cancelled successfully")


# Include router in app
app.include_router(router)


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
                topic="orders",
                value={"event": "order_created", "data": order},
                headers={"data_version": "1.0"},
            )
        else:
            await app._producer.send(
                topic="orders",
                value={"event": "order_cancelled", "data": order},
                headers={"data_version": "1.0"},
            )

        print(f"Produced message for order {order['id']}")


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
            print("\nShutting down...")


if __name__ == "__main__":
    asyncio.run(main())
