# Kafka Framework

[![PyPI version](https://img.shields.io/pypi/v/kafka-framework?color=blue)](https://pypi.org/project/kafka-framework/)
[![CI](https://github.com/ahdhani/kafka-framework/actions/workflows/ci.yml/badge.svg)](https://github.com/hani0x/kafka-framework/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code Style: ruff](https://img.shields.io/badge/style-ruff-blue)](https://github.com/astral-sh/ruff)

> A **FastAPI-inspired framework** to build production-grade Kafka applications effortlessly, with support for routing, DI, retries, DLQ, and custom serialization.

---

## ✨ Why Kafka Framework?

✅ **FastAPI-like routing** using decorators

✅ **Built-in dependency injection** system

✅ **Priority-based message processing**

✅ **Retry and DLQ** support

✅ **Plug-and-play serialization** (JSON, Avro, Protobuf)

✅ **Built for async** using [`aiokafka`](https://github.com/aio-libs/aiokafka)

---

## 📦 Installation

### Basic

```bash
pip install kafka-framework
```

### With Avro support

```bash
pip install kafka-framework[avro]
```

### All extras

```bash
pip install kafka-framework[all]
```

---

## ⚡ Quick Start

```python
from kafka_framework import KafkaApp, TopicRouter, Depends
from kafka_framework.serialization import JSONSerializer

app = KafkaApp(
    bootstrap_servers=["localhost:9092"],
    group_id="my-consumer-group",
    serializer=JSONSerializer()
)

router = TopicRouter()

# Dependencies
async def get_db():
    return {"connection": "db"}

def get_config():
    return {"env": "production"}

@router.topic_event(topic="orders", event_name="order_created", priority=1)
async def handle_order_created(message, db=Depends(get_db), config=Depends(get_config)):
    print(f"Processing order {message.value['id']}")

@router.topic_event(
    topic="orders",
    event_name="order_cancelled",
    priority=2,
    retry_attempts=3,
    dlq_postfix="cancelled"
)
async def handle_order_cancelled(message):
    print(f"Cancelling order {message.value['id']}")

app.include_router(router)

# Entry point
if __name__ == "__main__":
    import asyncio
    asyncio.run(app.start())
```

---

## 🧹 Core Concepts

### 🔁 Priority-Based Processing

Handlers with higher priority run first:

```python
@router.topic_event("notifications", "vip", priority=10)
async def handle_vip(message): ...

@router.topic_event("notifications", "normal", priority=1)
async def handle_normal(message): ...
```

---

### 💀 Dead Letter Queue (DLQ)

Unprocessed or failed messages are pushed to DLQ.

```python
@router.topic_event("orders", "order_created", dlq_postfix="created")
async def handle_order(message): ...
```

---

### 🧪 Retry Logic

Retries failed handlers before DLQ fallback:

```python
@router.topic_event("orders", "fail", retry_attempts=5)
async def flaky_handler(message): ...
```

---

### 🧬 Custom Serialization

Supports JSON, Protobuf, and Avro.

```python
from kafka_framework.serialization import AvroSerializer
import json

schema = {
    "type": "record",
    "name": "Order",
    "fields": [{"name": "id", "type": "string"}, {"name": "amount", "type": "double"}]
}

app = KafkaApp(
    bootstrap_servers=["localhost:9092"],
    serializer=AvroSerializer(
        schema_registry_url="http://localhost:8081",
        schema_str=json.dumps(schema)
    )
)
```

---

## ⚙️ Configuration

```python
KafkaApp(
    bootstrap_servers=["localhost:9092"],
    group_id="your-group",
    config={
        "consumer_config": {
            "auto_offset_reset": "earliest",
            "enable_auto_commit": True,
            "max_poll_records": 500
        },
        "producer_config": {
            "acks": "all",
            "compression_type": "gzip",
            "max_request_size": 1048576
        }
    }
)
```

---

## 🤝 Contributing

We welcome contributions! Here’s how you can help:

* 🤛 Open issues
* ✍️ Submit PRs
* 🗨️ Discuss improvements
* 📚 Improve docs and examples

See [CONTRIBUTING.md](./CONTRIBUTING.md) to get started.

---

## 🧭 Roadmap

* [ ] Documentation
* [ ] Admin/monitoring interface
* [ ] Kafka Streams integration
* [ ] Auto-schema registry
* [ ] CLI tooling

---

## 📄 License

This project is licensed under the MIT License. See [LICENSE](./LICENSE) for details.

---

## 🌎 Links

* 📘 [Documentation (coming soon)](https://github.com/ahdhani/kafka-framework/wiki)
* 🐍 [PyPI package](https://pypi.org/project/kafka-framework/)
* 🔧 [GitHub Actions CI](https://github.com/ahdhani/kafka-framework/actions)
* 💬 [Discussions](https://github.com/ahdhani/kafka-framework/discussions) (coming soon)

---

**Build Kafka consumers like web APIs — clean, testable, async-ready.**
