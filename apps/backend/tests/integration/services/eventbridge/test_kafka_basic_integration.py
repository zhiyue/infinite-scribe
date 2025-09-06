"""
Basic Kafka integration tests using testcontainers.

Tests basic Kafka producer/consumer functionality.
"""

import asyncio
import json
from uuid import uuid4

import pytest
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from aiokafka.admin import AIOKafkaAdminClient, NewTopic


@pytest.mark.integration
class TestKafkaBasicIntegration:
    """Basic Kafka integration tests."""

    @pytest.fixture(autouse=True)
    async def setup_services(self, kafka_service):
        """Setup Kafka service."""
        self.kafka_config = kafka_service
        self.test_topic = "test.basic.integration"

        # Ensure topic exists
        await self._create_topic(self.test_topic)

    async def _create_topic(self, topic_name: str):
        """Create a topic and wait for it to be ready."""
        admin_client = AIOKafkaAdminClient(
            bootstrap_servers=self.kafka_config["bootstrap_servers"],
            request_timeout_ms=30000,
        )

        try:
            await admin_client.start()

            # Create topic
            new_topic = NewTopic(name=topic_name, num_partitions=1, replication_factor=1)

            try:
                await admin_client.create_topics([new_topic])
                print(f"Created topic: {topic_name}")
            except Exception as e:
                if "already exists" not in str(e).lower():
                    print(f"Topic creation error: {e}")
                else:
                    print(f"Topic {topic_name} already exists")

            # Wait for topic metadata to propagate
            await asyncio.sleep(2.0)

        finally:
            await admin_client.close()

    @pytest.mark.asyncio
    async def test_basic_kafka_produce_consume(self):
        """Test basic Kafka producer and consumer functionality."""
        test_message = {
            "id": str(uuid4()),
            "message": "Hello from integration test",
            "timestamp": "2025-01-01T00:00:00Z",
        }

        # Step 1: Produce message
        producer = AIOKafkaProducer(
            bootstrap_servers=self.kafka_config["bootstrap_servers"],
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )

        try:
            await producer.start()
            await producer.send_and_wait(self.test_topic, test_message)
            print("Message produced successfully")
        finally:
            await producer.stop()

        # Step 2: Consume message
        consumer = AIOKafkaConsumer(
            self.test_topic,
            bootstrap_servers=self.kafka_config["bootstrap_servers"],
            auto_offset_reset="earliest",
            group_id=f"test-group-{uuid4()}",
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        )

        try:
            await consumer.start()

            # Wait for partition assignment
            await asyncio.sleep(2.0)

            # Try to consume message
            consumed_message = None
            for attempt in range(5):
                msg_pack = await consumer.getmany(timeout_ms=5000)
                if msg_pack:
                    for _topic_partition, messages in msg_pack.items():
                        if messages:
                            consumed_message = messages[0]
                            break
                    if consumed_message:
                        break
                print(f"No messages in attempt {attempt + 1}/5")
                await asyncio.sleep(1.0)

            # Verify we got the message
            assert consumed_message is not None, "Failed to consume message from Kafka"
            assert consumed_message.value["id"] == test_message["id"]
            assert consumed_message.value["message"] == test_message["message"]
            print("Message consumed successfully")

        finally:
            await consumer.stop()

    @pytest.mark.asyncio
    async def test_multiple_messages_produce_consume(self):
        """Test producing and consuming multiple messages."""
        test_messages = [{"id": str(uuid4()), "seq": i, "data": f"message-{i}"} for i in range(3)]

        # Produce all messages
        producer = AIOKafkaProducer(
            bootstrap_servers=self.kafka_config["bootstrap_servers"],
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )

        try:
            await producer.start()
            for msg in test_messages:
                await producer.send_and_wait(self.test_topic, msg)
            print(f"Produced {len(test_messages)} messages")
        finally:
            await producer.stop()

        # Consume all messages
        consumer = AIOKafkaConsumer(
            self.test_topic,
            bootstrap_servers=self.kafka_config["bootstrap_servers"],
            auto_offset_reset="earliest",
            group_id=f"test-group-multi-{uuid4()}",
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        )

        consumed_messages = []
        try:
            await consumer.start()

            # Wait for partition assignment
            await asyncio.sleep(2.0)

            # Try to consume all messages
            for _attempt in range(10):  # More attempts for multiple messages
                msg_pack = await consumer.getmany(timeout_ms=3000)
                if msg_pack:
                    for _topic_partition, messages in msg_pack.items():
                        consumed_messages.extend(messages)

                if len(consumed_messages) >= len(test_messages):
                    break

                print(f"Consumed {len(consumed_messages)}/{len(test_messages)} messages so far")
                await asyncio.sleep(0.5)

            # Verify all messages were consumed
            assert len(consumed_messages) >= len(
                test_messages
            ), f"Expected {len(test_messages)} messages, got {len(consumed_messages)}"

            # Verify message content
            consumed_ids = {msg.value["id"] for msg in consumed_messages[: len(test_messages)]}
            expected_ids = {msg["id"] for msg in test_messages}
            assert consumed_ids == expected_ids, "Message IDs don't match"

            print(f"Successfully consumed {len(consumed_messages)} messages")

        finally:
            await consumer.stop()
