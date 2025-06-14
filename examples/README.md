# Kafka Framework Examples

This directory contains examples of using the Kafka framework along with a Docker Compose setup for running Kafka.

## Running Kafka

The `docker-compose.yml` file provides a single-node Kafka setup using KRaft (no ZooKeeper required) and includes Kafka UI for easy monitoring.

### Start Kafka

```bash
docker-compose up -d
```

### Stop Kafka

```bash
docker-compose down
```

### View Kafka Logs

```bash
docker-compose logs -f kafka
```

### Connection Details

- Bootstrap servers: `localhost:9092` (internal), `localhost:9094` (external)
- Default partitions per topic: 3
- Auto topic creation: enabled
- Kafka UI: http://localhost:8080

### Kafka UI

The setup includes Kafka UI (by Provectus) which provides a web interface to:
- Monitor topics, partitions, and messages
- Create and delete topics
- View consumer groups and their lag
- Browse messages with advanced filters
- Monitor broker metrics

Access it at http://localhost:8080

### Testing Kafka Connection

```bash
# List topics
docker-compose exec kafka kafka-topics.sh --bootstrap-server localhost:9092 --list

# Create a topic
docker-compose exec kafka kafka-topics.sh --bootstrap-server localhost:9092 --create --topic test --partitions 3 --replication-factor 1

# Describe a topic
docker-compose exec kafka kafka-topics.sh --bootstrap-server localhost:9092 --describe --topic test
```

## Running the Examples

1. Start Kafka using docker-compose
2. Install the framework and dependencies
3. Run the example:
   ```bash
   python order_processing.py
   ```
