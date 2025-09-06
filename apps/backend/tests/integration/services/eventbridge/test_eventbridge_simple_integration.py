"""
Simple integration tests for EventBridge service using testcontainers.

Tests basic EventBridge functionality with real Kafka and Redis.
"""

import asyncio
import json
import os
from datetime import datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from aiokafka import AIOKafkaProducer
from aiokafka.admin import AIOKafkaAdminClient, NewTopic
from src.services.eventbridge.factory import EventBridgeServiceFactory


@pytest.mark.integration
class TestEventBridgeSimpleIntegration:
    """Simple integration tests using real Kafka and mocked Redis."""

    @pytest.fixture(autouse=True)
    async def setup_services(self, kafka_service, redis_service):
        """Setup services with testcontainer configurations."""
        self.kafka_config = kafka_service
        self.redis_config = redis_service

        # Override environment variables for integration testing
        os.environ["KAFKA_HOST"] = self.kafka_config["host"]
        os.environ["KAFKA_PORT"] = str(self.kafka_config["port"])

        # Create test topic
        self.test_topic = "genesis.session.events"
        await self._ensure_topic_exists(self.test_topic)

        yield

        # Cleanup environment
        os.environ.pop("KAFKA_HOST", None)
        os.environ.pop("KAFKA_PORT", None)

    async def _ensure_topic_exists(self, topic_name: str):
        """Ensure the test topic exists in Kafka and wait for metadata propagation."""
        admin_client = AIOKafkaAdminClient(
            bootstrap_servers=self.kafka_config["bootstrap_servers"],
            request_timeout_ms=30000,  # Increased timeout
        )

        try:
            await admin_client.start()

            # Check if topic already exists
            try:
                metadata = await admin_client.describe_topics([topic_name])
                if topic_name in metadata:
                    print(f"Topic {topic_name} already exists")
                    return
            except Exception:
                pass  # Topic probably doesn't exist

            # Create topic
            new_topic = NewTopic(name=topic_name, num_partitions=1, replication_factor=1)
            try:
                await admin_client.create_topics([new_topic])
                print(f"Created topic {topic_name}")

                # Wait for topic metadata to propagate
                await asyncio.sleep(3.0)

                # Verify topic was created
                for attempt in range(5):
                    try:
                        metadata = await admin_client.describe_topics([topic_name])
                        if topic_name in metadata:
                            print(f"Topic {topic_name} verified in metadata")
                            break
                    except Exception as e:
                        print(f"Topic verification attempt {attempt + 1}/5 failed: {e}")
                        await asyncio.sleep(1.0)
                else:
                    print(f"Warning: Could not verify topic {topic_name} in metadata")

            except Exception as e:
                if "already exists" not in str(e).lower():
                    print(f"Warning: Topic creation error: {e}")
        finally:
            await admin_client.close()

    async def _produce_test_message(self, message_data: dict) -> None:
        """Produce a test message to Kafka."""
        producer = AIOKafkaProducer(
            bootstrap_servers=self.kafka_config["bootstrap_servers"],
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )

        try:
            await producer.start()
            await producer.send_and_wait(self.test_topic, message_data)
        finally:
            await producer.stop()

    def _create_valid_genesis_event(self) -> dict:
        """Create a valid Genesis event for testing."""
        return {
            "event_id": str(uuid4()),
            "event_type": "Genesis.Session.Started",
            "aggregate_id": str(uuid4()),
            "correlation_id": str(uuid4()),
            "trace_id": str(uuid4()),
            "timestamp": datetime.now().isoformat(),
            "payload": {
                "user_id": str(uuid4()),
                "session_id": str(uuid4()),
                "timestamp": datetime.now().isoformat(),
                "novel_id": str(uuid4()),
                "content": {"action": "session_started", "metadata": {"source": "integration_test"}},
            },
        }

    @pytest.mark.asyncio
    async def test_kafka_connection_and_message_flow(self):
        """Test that we can connect to Kafka and process messages."""
        # Create factory and service
        factory = EventBridgeServiceFactory()

        # Create mock Redis SSE to avoid Redis dependency complexity
        mock_redis_sse = AsyncMock()
        mock_redis_sse.publish_event = AsyncMock(return_value="stream-123")

        try:
            # Create service and replace Redis SSE with mock
            bridge_service = factory.create_event_bridge_service()
            bridge_service.redis_sse_service = mock_redis_sse

            # Set up consumer
            kafka_manager = factory._get_kafka_client_manager()
            consumer = await kafka_manager.create_consumer()
            bridge_service.set_consumer(consumer)

            # Wait for consumer group coordination
            print("Waiting for consumer group coordination...")
            await asyncio.sleep(2.0)

            # Create and produce a valid Genesis event
            event_data = self._create_valid_genesis_event()
            await self._produce_test_message(event_data)
            print("Test message produced")

            # Wait for message to be available and consumer to be ready
            await asyncio.sleep(3.0)

            # Try to consume messages multiple times
            message_batch = None
            for attempt in range(3):
                print(f"Attempting to consume messages (attempt {attempt + 1}/3)...")
                message_batch = await consumer.getmany(timeout_ms=10000)
                if message_batch:
                    print(f"Received message batch with {sum(len(msgs) for msgs in message_batch.values())} messages")
                    break
                await asyncio.sleep(1.0)

            processed = False
            if message_batch:
                for topic_partition, messages in message_batch.items():
                    for message in messages:
                        # Process the message through EventBridge
                        result = await bridge_service._process_event(message)
                        assert result is True
                        processed = True
                        break
                    if processed:
                        break

            # Verify the message was processed
            assert processed, "No messages were processed"

            # Verify Redis SSE was called (event was published)
            mock_redis_sse.publish_event.assert_called_once()

            # Verify the published event structure
            call_args = mock_redis_sse.publish_event.call_args
            published_event = call_args[0][1]  # Second argument is the event data
            assert published_event["event_type"] == "Genesis.Session.Started"
            assert published_event["user_id"] == event_data["payload"]["user_id"]
            assert "correlation_id" in published_event
            assert "trace_id" in published_event

        finally:
            # Cleanup
            if "consumer" in locals():
                await kafka_manager.stop_consumer()
            await factory.cleanup()

    @pytest.mark.asyncio
    async def test_event_filtering_with_real_kafka(self):
        """Test that non-Genesis events are filtered out."""
        # Create factory and service
        factory = EventBridgeServiceFactory()

        # Create mock Redis SSE
        mock_redis_sse = AsyncMock()
        mock_redis_sse.publish_event = AsyncMock()

        try:
            # Create service and replace Redis SSE with mock
            bridge_service = factory.create_event_bridge_service()
            bridge_service.redis_sse_service = mock_redis_sse

            # Set up consumer
            kafka_manager = factory._get_kafka_client_manager()
            consumer = await kafka_manager.create_consumer()
            bridge_service.set_consumer(consumer)

            # Create and produce an invalid (non-Genesis) event
            invalid_event = {
                "event_id": str(uuid4()),
                "event_type": "Chapter.Session.Started",  # Not Genesis
                "aggregate_id": str(uuid4()),
                "correlation_id": str(uuid4()),
                "payload": {
                    "user_id": str(uuid4()),
                    "session_id": str(uuid4()),
                    "timestamp": datetime.now().isoformat(),
                },
            }
            await self._produce_test_message(invalid_event)

            # Wait for message to be available
            await asyncio.sleep(1.0)

            # Consume and process the message
            message_batch = await consumer.getmany(timeout_ms=5000)

            processed = False
            if message_batch:
                for topic_partition, messages in message_batch.items():
                    for message in messages:
                        # Process the message through EventBridge
                        result = await bridge_service._process_event(message)
                        assert result is True  # Processing continues
                        processed = True
                        break
                    if processed:
                        break

            # Verify the message was processed but filtered
            assert processed, "No messages were processed"

            # Verify Redis SSE was NOT called (event was filtered)
            mock_redis_sse.publish_event.assert_not_called()

        finally:
            # Cleanup
            if "consumer" in locals():
                await kafka_manager.stop_consumer()
            await factory.cleanup()

    @pytest.mark.asyncio
    async def test_circuit_breaker_with_kafka_integration(self):
        """Test circuit breaker behavior with real Kafka messages."""
        # Create factory and service
        factory = EventBridgeServiceFactory()

        # Create failing Redis SSE mock
        failing_redis_sse = AsyncMock()
        failing_redis_sse.publish_event = AsyncMock(side_effect=ConnectionError("Redis connection failed"))

        try:
            # Create service and replace Redis SSE with failing mock
            bridge_service = factory.create_event_bridge_service()
            bridge_service.redis_sse_service = failing_redis_sse

            # Set up consumer
            kafka_manager = factory._get_kafka_client_manager()
            consumer = await kafka_manager.create_consumer()
            bridge_service.set_consumer(consumer)

            # Create and produce a valid Genesis event
            event_data = self._create_valid_genesis_event()
            await self._produce_test_message(event_data)

            # Wait for message to be available
            await asyncio.sleep(1.0)

            # Process the message - should handle Redis failure gracefully
            message_batch = await consumer.getmany(timeout_ms=5000)

            processed = False
            if message_batch:
                for topic_partition, messages in message_batch.items():
                    for message in messages:
                        # Process should not fail despite Redis error
                        result = await bridge_service._process_event(message)
                        assert result is True
                        processed = True
                        break
                    if processed:
                        break

            # Verify the message was processed
            assert processed, "No messages were processed"

            # Verify circuit breaker recorded the failure
            assert bridge_service.circuit_breaker.failure_count > 0

            # Verify Redis SSE was attempted
            failing_redis_sse.publish_event.assert_called_once()

        finally:
            # Cleanup
            if "consumer" in locals():
                await kafka_manager.stop_consumer()
            await factory.cleanup()
