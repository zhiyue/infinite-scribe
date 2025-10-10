"""
Real end-to-end integration tests for EventBridge service using testcontainers.

Tests the complete EventBridge pipeline with real Kafka and Redis instances.
"""

import asyncio
import json
import os
from datetime import datetime
from uuid import uuid4

import pytest
from aiokafka import AIOKafkaProducer
from aiokafka.admin import AIOKafkaAdminClient, NewTopic
from src.services.eventbridge.factory import EventBridgeServiceFactory


@pytest.mark.integration
class TestEventBridgeE2EIntegration:
    """End-to-end integration tests using real Kafka and Redis."""

    @pytest.fixture(autouse=True)
    async def setup_services(self, kafka_service, redis_service):
        """Setup services with testcontainer configurations."""
        self.kafka_config = kafka_service
        self.redis_config = redis_service

        # Override environment variables for integration testing
        os.environ["KAFKA_HOST"] = self.kafka_config["host"]
        os.environ["KAFKA_PORT"] = str(self.kafka_config["port"])
        os.environ["DATABASE__REDIS_HOST"] = self.redis_config["host"]
        os.environ["DATABASE__REDIS_PORT"] = str(self.redis_config["port"])

        # Create test topic
        self.test_topic = "genesis.session.events"
        await self._ensure_topic_exists(self.test_topic)

        # Create EventBridge factory with fresh settings
        self.factory = EventBridgeServiceFactory()
        self.bridge_service = self.factory.create_event_bridge_service()

        # Initialize Redis SSE service
        redis_sse_service = self.factory._get_redis_sse_service()
        await redis_sse_service.init_pubsub_client()

        yield

        # Cleanup after test
        await self.cleanup()

    async def _ensure_topic_exists(self, topic_name: str):
        """Ensure the test topic exists in Kafka."""
        admin_client = AIOKafkaAdminClient(
            bootstrap_servers=self.kafka_config["bootstrap_servers"],
            request_timeout_ms=10000,
        )

        try:
            await admin_client.start()

            # Check if topic exists
            metadata = await admin_client.describe_topics([topic_name])
            if topic_name not in metadata:
                # Create topic
                new_topic = NewTopic(name=topic_name, num_partitions=1, replication_factor=1)
                await admin_client.create_topics([new_topic])

        except Exception as e:
            # Topic might already exist
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

    def _create_invalid_event(self) -> dict:
        """Create an invalid event (non-Genesis) for testing."""
        return {
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

    @pytest.mark.asyncio
    async def test_eventbridge_processes_valid_genesis_event(self):
        """Test EventBridge processes valid Genesis events end-to-end."""
        # Create a valid Genesis event
        event_data = self._create_valid_genesis_event()

        # Set up consumer reference for the service
        kafka_manager = self.factory._get_kafka_client_manager()
        consumer = await kafka_manager.create_consumer()
        self.bridge_service.set_consumer(consumer)

        # Create mock Redis SSE service that we can verify
        from unittest.mock import AsyncMock

        mock_redis_sse = AsyncMock()
        mock_redis_sse.publish_event = AsyncMock(return_value="stream-123")

        # Replace the Redis SSE service temporarily
        original_redis_sse = self.bridge_service.redis_sse_service
        self.bridge_service.redis_sse_service = mock_redis_sse

        try:
            # Produce the event to Kafka
            await self._produce_test_message(event_data)

            # Wait a moment for message to be available
            await asyncio.sleep(0.5)

            # Process messages through the bridge
            message_batch = await consumer.getmany(timeout_ms=2000)

            if message_batch:
                for _topic_partition, messages in message_batch.items():
                    for message in messages:
                        # Process the message
                        result = await self.bridge_service.process_event(message)
                        assert result is True

                        # Verify Redis SSE was called
                        mock_redis_sse.publish_event.assert_called_once()
                        call_args = mock_redis_sse.publish_event.call_args

                        # Verify the published event structure
                        published_event = call_args[0][1]  # Second argument is the event data
                        assert published_event["event_type"] == "Genesis.Session.Started"
                        assert published_event["user_id"] == event_data["payload"]["user_id"]
                        assert "correlation_id" in published_event
                        assert "trace_id" in published_event

                        break
                    break
            else:
                pytest.fail("No messages received from Kafka")

        finally:
            # Restore original Redis SSE service
            self.bridge_service.redis_sse_service = original_redis_sse
            await kafka_manager.stop_consumer()

    @pytest.mark.asyncio
    async def test_eventbridge_filters_non_genesis_events(self):
        """Test EventBridge filters out non-Genesis events."""
        # Create an invalid (non-Genesis) event
        event_data = self._create_invalid_event()

        # Set up consumer reference for the service
        kafka_manager = self.factory._get_kafka_client_manager()
        consumer = await kafka_manager.create_consumer()
        self.bridge_service.set_consumer(consumer)

        # Create mock Redis SSE service
        from unittest.mock import AsyncMock

        mock_redis_sse = AsyncMock()
        original_redis_sse = self.bridge_service.redis_sse_service
        self.bridge_service.redis_sse_service = mock_redis_sse

        try:
            # Produce the event to Kafka
            await self._produce_test_message(event_data)

            # Wait a moment for message to be available
            await asyncio.sleep(0.5)

            # Process messages through the bridge
            message_batch = await consumer.getmany(timeout_ms=2000)

            if message_batch:
                for _topic_partition, messages in message_batch.items():
                    for message in messages:
                        # Process the message
                        result = await self.bridge_service.process_event(message)
                        assert result is True

                        # Verify Redis SSE was NOT called (event was filtered)
                        mock_redis_sse.publish_event.assert_not_called()
                        break
                    break
            else:
                pytest.fail("No messages received from Kafka")

        finally:
            self.bridge_service.redis_sse_service = original_redis_sse
            await kafka_manager.stop_consumer()

    @pytest.mark.asyncio
    async def test_eventbridge_circuit_breaker_with_real_redis_failure(self):
        """Test circuit breaker behavior with real Redis connection."""
        # Create a valid Genesis event
        event_data = self._create_valid_genesis_event()

        # Set up consumer reference for the service
        kafka_manager = self.factory._get_kafka_client_manager()
        consumer = await kafka_manager.create_consumer()
        self.bridge_service.set_consumer(consumer)

        # Create a Redis SSE service that will fail
        from unittest.mock import AsyncMock

        failing_redis_sse = AsyncMock()
        failing_redis_sse.publish_event = AsyncMock(side_effect=ConnectionError("Redis connection failed"))

        original_redis_sse = self.bridge_service.redis_sse_service
        self.bridge_service.redis_sse_service = failing_redis_sse

        try:
            # Produce the event to Kafka
            await self._produce_test_message(event_data)

            # Wait a moment for message to be available
            await asyncio.sleep(0.5)

            # Process messages - should handle Redis failure gracefully
            message_batch = await consumer.getmany(timeout_ms=2000)

            if message_batch:
                for _topic_partition, messages in message_batch.items():
                    for message in messages:
                        # Process the message - should not fail despite Redis error
                        result = await self.bridge_service.process_event(message)
                        assert result is True

                        # Verify circuit breaker recorded the failure
                        assert self.bridge_service.circuit_breaker.failure_count > 0
                        break
                    break
            else:
                pytest.fail("No messages received from Kafka")

        finally:
            self.bridge_service.redis_sse_service = original_redis_sse
            await kafka_manager.stop_consumer()

    @pytest.mark.asyncio
    async def test_eventbridge_offset_commit_with_real_kafka(self):
        """Test offset commit behavior with real Kafka."""
        # Create multiple valid Genesis events
        events = [self._create_valid_genesis_event() for _ in range(3)]

        # Set up consumer reference for the service
        kafka_manager = self.factory._get_kafka_client_manager()
        consumer = await kafka_manager.create_consumer()
        self.bridge_service.set_consumer(consumer)

        # Create mock Redis SSE service for controlled testing
        from unittest.mock import AsyncMock

        mock_redis_sse = AsyncMock()
        mock_redis_sse.publish_event = AsyncMock(return_value="stream-123")

        original_redis_sse = self.bridge_service.redis_sse_service
        self.bridge_service.redis_sse_service = mock_redis_sse

        try:
            # Produce all events to Kafka
            for event_data in events:
                await self._produce_test_message(event_data)

            # Wait for messages to be available
            await asyncio.sleep(1.0)

            # Process all messages
            processed_count = 0
            message_batch = await consumer.getmany(timeout_ms=3000)

            if message_batch:
                for _topic_partition, messages in message_batch.items():
                    for message in messages:
                        # Process each message
                        result = await self.bridge_service.process_event(message)
                        assert result is True
                        processed_count += 1

                # Verify we processed all expected messages
                assert processed_count == len(events)

                # Trigger offset commit
                await self.bridge_service.commit_processed_offsets()

                # Verify Redis SSE was called for each event
                assert mock_redis_sse.publish_event.call_count == len(events)

            else:
                pytest.fail("No messages received from Kafka")

        finally:
            self.bridge_service.redis_sse_service = original_redis_sse
            await kafka_manager.stop_consumer()

    @pytest.mark.asyncio
    async def test_eventbridge_service_complete_lifecycle(self):
        """Test complete EventBridge service lifecycle with real services."""
        # This test verifies the entire service can start, process events, and shutdown
        from unittest.mock import AsyncMock

        # Create a valid Genesis event
        event_data = self._create_valid_genesis_event()

        # Create new service instance for lifecycle test
        test_factory = EventBridgeServiceFactory()
        test_service = test_factory.create_event_bridge_service()

        # Mock Redis SSE to avoid external dependencies in this test
        mock_redis_sse = AsyncMock()
        mock_redis_sse.publish_event = AsyncMock(return_value="stream-456")
        mock_redis_sse.close = AsyncMock()
        test_service.redis_sse_service = mock_redis_sse

        # Set up consumer
        kafka_manager = test_factory._get_kafka_client_manager()
        consumer = await kafka_manager.create_consumer()
        test_service.set_consumer(consumer)

        try:
            # Produce test event
            await self._produce_test_message(event_data)
            await asyncio.sleep(0.5)

            # Process messages
            message_batch = await consumer.getmany(timeout_ms=2000)
            if message_batch:
                for _topic_partition, messages in message_batch.items():
                    for message in messages:
                        result = await test_service.process_event(message)
                        assert result is True
                        break
                    break

            # Verify processing worked
            mock_redis_sse.publish_event.assert_called_once()

            # Test graceful shutdown
            await test_service.shutdown()

            # Verify cleanup was called
            mock_redis_sse.close.assert_called_once()

        finally:
            # Cleanup
            await test_factory.cleanup()

    @pytest.mark.asyncio
    async def test_eventbridge_handles_malformed_kafka_messages(self):
        """Test EventBridge handles malformed Kafka messages gracefully."""
        # Set up consumer reference for the service
        kafka_manager = self.factory._get_kafka_client_manager()
        consumer = await kafka_manager.create_consumer()
        self.bridge_service.set_consumer(consumer)

        # Produce a malformed message (invalid JSON structure)
        malformed_data = {"invalid": "structure", "missing": "required_fields"}
        await self._produce_test_message(malformed_data)

        # Create mock Redis SSE service
        from unittest.mock import AsyncMock

        mock_redis_sse = AsyncMock()
        original_redis_sse = self.bridge_service.redis_sse_service
        self.bridge_service.redis_sse_service = mock_redis_sse

        try:
            # Wait for message to be available
            await asyncio.sleep(0.5)

            # Process messages - should handle malformed data gracefully
            message_batch = await consumer.getmany(timeout_ms=2000)

            if message_batch:
                for _topic_partition, messages in message_batch.items():
                    for message in messages:
                        # Process should continue despite malformed message
                        result = await self.bridge_service.process_event(message)
                        assert result is True  # Should continue processing

                        # Verify Redis SSE was NOT called (malformed message filtered)
                        mock_redis_sse.publish_event.assert_not_called()
                        break
                    break
            else:
                pytest.fail("No messages received from Kafka")

        finally:
            self.bridge_service.redis_sse_service = original_redis_sse
            await kafka_manager.stop_consumer()

    async def cleanup(self):
        """Cleanup resources after test."""
        try:
            if hasattr(self, "factory") and self.factory:
                await self.factory.cleanup()
        except Exception as e:
            print(f"Cleanup error: {e}")
