"""
Simplified end-to-end integration test for EventBridge service using testcontainers.

This is a minimal test to verify the basic EventBridge functionality works.
"""

import asyncio
import json
import os
import time
from datetime import datetime
from uuid import uuid4

import pytest
import redis.asyncio as aioredis
from aiokafka import AIOKafkaProducer
from aiokafka.admin import AIOKafkaAdminClient, NewTopic
from src.services.eventbridge.factory import EventBridgeServiceFactory


@pytest.mark.integration
class TestEventBridgeSimpleE2E:
    """Simplified E2E test using real testcontainers."""

    @pytest.fixture(autouse=True)
    async def setup_services(self, kafka_service, redis_service):
        """Setup services with testcontainer configurations."""
        self.kafka_config = kafka_service
        self.redis_config = redis_service

        # Override environment variables for integration testing
        bootstrap_servers = self.kafka_config["bootstrap_servers"]
        if isinstance(bootstrap_servers, list):
            os.environ["KAFKA_BOOTSTRAP_SERVERS"] = ",".join(bootstrap_servers)
        else:
            os.environ["KAFKA_BOOTSTRAP_SERVERS"] = bootstrap_servers

        # Directly update global settings to use testcontainer Redis
        from src.core.config import get_settings

        settings = get_settings()
        settings.database.redis_host = self.redis_config["host"]
        settings.database.redis_port = int(self.redis_config["port"])

        # Also update Kafka settings for EventBridge
        if isinstance(bootstrap_servers, list) and bootstrap_servers:
            host, port = bootstrap_servers[0].split(":")
        elif isinstance(bootstrap_servers, str):
            host, port = bootstrap_servers.split(":")
        else:
            host, port = self.kafka_config["host"], str(self.kafka_config["port"])
        settings.kafka_host = host
        settings.kafka_port = int(port)

        # Test topic for EventBridge
        self.test_topic = "genesis.session.events"
        await self._ensure_topic_exists(self.test_topic)

        # Redis client for verification - use the same Redis as the EventBridge
        redis_url = f"redis://{self.redis_config['host']}:{self.redis_config['port']}/0"
        print(f"Test Redis URL: {redis_url}")
        self.redis_client = aioredis.from_url(redis_url)

        yield

        # Cleanup after test
        await self.cleanup()

    async def _ensure_topic_exists(self, topic_name: str):
        """Ensure the test topic exists in Kafka."""
        bootstrap_servers = self.kafka_config["bootstrap_servers"]
        if isinstance(bootstrap_servers, list):
            bootstrap_servers = ",".join(bootstrap_servers)

        admin_client = AIOKafkaAdminClient(
            bootstrap_servers=bootstrap_servers,
            request_timeout_ms=15000,
        )

        try:
            await admin_client.start()
            try:
                metadata = await admin_client.describe_topics([topic_name])
                if topic_name in metadata:
                    return  # Topic exists
            except Exception:
                pass  # Topic doesn't exist, create it

            # Create topic
            new_topic = NewTopic(name=topic_name, num_partitions=1, replication_factor=1)
            await admin_client.create_topics([new_topic])
            await asyncio.sleep(2)

        finally:
            await admin_client.close()

    async def _produce_kafka_message(self, message_data: dict) -> None:
        """Produce a test message to Kafka."""
        bootstrap_servers = self.kafka_config["bootstrap_servers"]
        if isinstance(bootstrap_servers, list):
            bootstrap_servers = ",".join(bootstrap_servers)

        producer = AIOKafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            acks="all",
        )

        try:
            await producer.start()
            await producer.send_and_wait(self.test_topic, message_data)
        finally:
            await producer.stop()

    def _create_genesis_event(self) -> dict:
        """Create a valid Genesis event for testing."""
        user_id = str(uuid4())
        session_id = str(uuid4())
        novel_id = str(uuid4())

        return {
            "event_id": str(uuid4()),
            "event_type": "Genesis.Session.Started",
            "aggregate_id": session_id,
            "correlation_id": str(uuid4()),
            "trace_id": str(uuid4()),
            "timestamp": datetime.now().isoformat(),
            "payload": {
                "user_id": user_id,
                "session_id": session_id,
                "novel_id": novel_id,
                "timestamp": datetime.now().isoformat(),
                "content": {"action": "session_started", "metadata": {"source": "simple_e2e_test"}},
            },
        }

    async def _wait_for_redis_stream_message(self, user_id: str, timeout: float = 10.0) -> dict:
        """Wait for SSE message to appear in Redis Stream."""
        stream_key = f"events:user:{user_id}"
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                # Read from Redis Stream
                result = await self.redis_client.xread({stream_key: "0"}, count=10, block=1000)

                if result:
                    for _stream_name, messages in result:
                        for _message_id, fields in messages:
                            # Convert Redis hash to dict
                            message_data = {}

                            # fields is already a dictionary from Redis
                            for key_bytes, value_bytes in fields.items():
                                key = key_bytes.decode("utf-8") if isinstance(key_bytes, bytes) else key_bytes
                                value = value_bytes.decode("utf-8") if isinstance(value_bytes, bytes) else value_bytes
                                if key == "data":
                                    # Parse JSON data
                                    message_data[key] = json.loads(value)
                                else:
                                    message_data[key] = value

                            return message_data

            except Exception as e:
                # Continue waiting if no message yet
                error_msg = str(e).lower()
                if "no data" not in error_msg and "timeout" not in error_msg and str(e) != "0":
                    print(f"Redis stream read error: {e}")

            await asyncio.sleep(0.1)

        raise TimeoutError(f"No message received in Redis stream {stream_key} within {timeout}s")

    @pytest.mark.asyncio
    async def test_eventbridge_basic_functionality(self):
        """Test basic EventBridge functionality with direct service usage."""
        # Create Genesis event
        event_data = self._create_genesis_event()
        user_id = event_data["payload"]["user_id"]

        # Create EventBridge service directly
        factory = EventBridgeServiceFactory()
        bridge_service = factory.create_event_bridge_service()

        # Create mock Kafka message
        from unittest.mock import Mock

        mock_message = Mock()
        mock_message.value = event_data
        mock_message.topic = self.test_topic
        mock_message.partition = 0
        mock_message.offset = 123

        try:
            # Initialize Redis SSE service
            redis_sse_service = factory.get_redis_sse_service()
            await redis_sse_service.init_pubsub_client()

            # Process the message directly
            result = await bridge_service.process_event(mock_message)
            assert result is True, "Event should be processed successfully"

            # Debug: Check what keys exist in Redis
            keys = await self.redis_client.keys("*")
            print(f"All keys in Redis: {keys}")

            # Debug: Check specifically for SSE stream keys
            sse_keys = await self.redis_client.keys("events:user:*")
            print(f"SSE stream keys: {sse_keys}")

            # Verify message appears in Redis Stream
            stream_message = await self._wait_for_redis_stream_message(user_id, timeout=10.0)

            # Basic verification
            assert "data" in stream_message, "SSE message should have 'data' field"
            assert "event" in stream_message, "SSE message should have 'event' field"
            assert stream_message["event"] == "Genesis.Session.Started"

            sse_data = stream_message["data"]
            assert sse_data["event_type"] == "Genesis.Session.Started"
            assert sse_data["event_id"] == event_data["event_id"]
            assert sse_data["session_id"] == event_data["payload"]["session_id"]
            assert sse_data["novel_id"] == event_data["payload"]["novel_id"]

            print("✓ Basic EventBridge functionality verified")
            print(f"✓ Event {event_data['event_id']} processed successfully")

        finally:
            # Cleanup service
            await bridge_service.shutdown()
            await factory.cleanup()

    async def cleanup(self):
        """Cleanup resources after tests."""
        try:
            if hasattr(self, "redis_client") and self.redis_client:
                await self.redis_client.close()

            # Clean up environment variables
            env_vars_to_clean = [
                "KAFKA_BOOTSTRAP_SERVERS",
                "DATABASE__REDIS_HOST",
                "DATABASE__REDIS_PORT",
            ]

            for env_var in env_vars_to_clean:
                if env_var in os.environ:
                    del os.environ[env_var]

        except Exception as e:
            print(f"Cleanup warning: {e}")
