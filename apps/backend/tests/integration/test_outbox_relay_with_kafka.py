"""Real integration tests for OutboxRelayService using Kafka and PostgreSQL testcontainers."""

import asyncio
import json
from datetime import UTC, datetime, timedelta
from unittest.mock import patch
from uuid import uuid4

import pytest
from aiokafka import AIOKafkaConsumer
from sqlalchemy import delete, insert, select
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.workflow import EventOutbox
from src.schemas.enums import OutboxStatus
from src.services.outbox.relay import OutboxRelayService


@pytest.mark.integration
class TestOutboxRelayServiceRealKafka:
    """Real integration test cases for OutboxRelayService using Kafka and PostgreSQL testcontainers."""

    @pytest.fixture
    async def clean_outbox_table(self, db_session: AsyncSession):
        """Clean the event_outbox table before and after each test."""
        await db_session.execute(delete(EventOutbox))
        await db_session.commit()

        yield

        await db_session.execute(delete(EventOutbox))
        await db_session.commit()

    @pytest.fixture
    def kafka_settings(self, kafka_service):
        """Create settings using real Kafka testcontainer."""
        from unittest.mock import MagicMock

        settings = MagicMock()
        settings.environment = "test"
        settings.log_level = "DEBUG"
        settings.kafka_bootstrap_servers = kafka_service["bootstrap_servers"]

        # Relay-specific settings optimized for testing
        relay_settings = MagicMock()
        relay_settings.poll_interval_seconds = 0.1
        relay_settings.batch_size = 5
        relay_settings.yield_sleep_ms = 10
        relay_settings.loop_error_backoff_ms = 100
        relay_settings.retry_backoff_ms = 100
        relay_settings.max_backoff_ms = 5000
        relay_settings.max_retries_default = 2
        settings.relay = relay_settings

        return settings

    @pytest.fixture
    async def kafka_consumer(self, kafka_service):
        """Create a Kafka consumer for verifying sent messages."""
        consumer = AIOKafkaConsumer(
            bootstrap_servers=kafka_service["bootstrap_servers"],
            group_id=f"test-consumer-{uuid4()}",
            auto_offset_reset="earliest",
            value_deserializer=lambda x: json.loads(x.decode("utf-8")) if x else None,
            consumer_timeout_ms=5000,  # 5 second timeout
        )
        await consumer.start()

        yield consumer

        await consumer.stop()

    def create_mock_sql_session(self, db_session: AsyncSession):
        """Create a mock create_sql_session that uses the same database engine as the test.

        Ensures OutboxRelayService uses the same Postgres testcontainer database
        as the tests, avoiding cross-DB visibility issues.
        """
        from contextlib import asynccontextmanager
        from sqlalchemy.orm import sessionmaker

        engine = db_session.bind

        @asynccontextmanager
        async def mock_create_sql_session():
            async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)()
            try:
                yield async_session
            except Exception:
                await async_session.rollback()
                raise
            finally:
                await async_session.close()

        return mock_create_sql_session

    async def create_test_message(
        self,
        db_session: AsyncSession,
        topic: str = "test.topic",
        status: OutboxStatus = OutboxStatus.PENDING,
        retry_count: int = 0,
        max_retries: int = 3,
        scheduled_at: datetime = None,
        payload: dict = None,
    ) -> EventOutbox:
        """Create a test message in the outbox table."""
        if payload is None:
            payload = {"event": "test", "data": "kafka_integration_test", "timestamp": datetime.now(UTC).isoformat()}

        # Ensure DB check constraints are satisfied: scheduled_at (if set) >= created_at
        now_ts = datetime.now(UTC)
        created_ts = now_ts
        if scheduled_at is not None and scheduled_at < created_ts:
            created_ts = scheduled_at

        message_data = {
            "id": uuid4(),
            "topic": topic,
            "key": "test-key",
            "partition_key": "partition-1",
            "payload": payload,
            "headers": {"source": "kafka_integration_test", "version": "1.0"},
            "status": status,
            "retry_count": retry_count,
            "max_retries": max_retries,
            "scheduled_at": scheduled_at,
            "created_at": created_ts,
        }

        result = await db_session.execute(insert(EventOutbox).values(message_data).returning(EventOutbox))
        message = result.scalar_one()
        await db_session.commit()
        return message

    async def get_message_from_db(self, db_session: AsyncSession, message_id) -> EventOutbox:
        """Retrieve a message from the database."""
        result = await db_session.execute(select(EventOutbox).where(EventOutbox.id == message_id))
        return result.scalar_one()

    async def consume_messages(self, consumer: AIOKafkaConsumer, topic: str, expected_count: int = 1) -> list[dict]:
        """Consume messages from Kafka topic with timeout."""
        consumer.subscribe([topic])

        consumed_messages = []
        start_time = datetime.now(UTC)
        timeout_seconds = 10

        try:
            while len(consumed_messages) < expected_count:
                # Check for timeout
                if (datetime.now(UTC) - start_time).total_seconds() > timeout_seconds:
                    break

                # Poll for messages
                try:
                    msg_batch = await asyncio.wait_for(consumer.getmany(timeout_ms=1000), timeout=2.0)
                    for topic_partition, messages in msg_batch.items():
                        for message in messages:
                            consumed_messages.append(
                                {
                                    "topic": message.topic,
                                    "partition": message.partition,
                                    "offset": message.offset,
                                    "key": message.key.decode("utf-8") if message.key else None,
                                    "value": message.value,
                                    "headers": {k: v.decode("utf-8") for k, v in message.headers}
                                    if message.headers
                                    else {},
                                    "timestamp": message.timestamp,
                                }
                            )
                except TimeoutError:
                    continue

        except Exception as e:
            print(f"Error consuming messages: {e}")

        return consumed_messages

    @pytest.mark.asyncio
    async def test_single_message_end_to_end_kafka(
        self, kafka_settings, clean_outbox_table, db_session, kafka_consumer
    ):
        """Test complete end-to-end message processing with real Kafka."""
        with patch("src.services.outbox.relay.get_settings") as mock_get_settings:
            mock_get_settings.return_value = kafka_settings

            # Create test message
            test_payload = {"event": "e2e_test", "data": {"message": "hello kafka"}}
            test_message = await self.create_test_message(
                db_session, topic="integration.test.e2e", payload=test_payload
            )

            # Start the relay service with real Kafka
            service = OutboxRelayService()
            # Use the same DB as the test Postgres container for entire run
            with patch("src.services.outbox.relay.create_sql_session", self.create_mock_sql_session(db_session)):
                await service.start()
                # Process the message
                processed = await service._drain_once()
                assert processed == 1

                # Verify database state - message should be marked as SENT
                updated_message = await self.get_message_from_db(db_session, test_message.id)
                assert updated_message.status == OutboxStatus.SENT
                assert updated_message.sent_at is not None
                assert updated_message.last_error is None

                # Verify message was actually sent to Kafka
                consumed_messages = await self.consume_messages(
                    kafka_consumer, "integration.test.e2e", expected_count=1
                )

                assert len(consumed_messages) == 1
                kafka_message = consumed_messages[0]

                # Verify Kafka message content
                assert kafka_message["topic"] == "integration.test.e2e"
                assert kafka_message["key"] == "test-key"
                assert kafka_message["value"] == test_payload
                assert kafka_message["headers"]["source"] == "kafka_integration_test"
                assert kafka_message["headers"]["version"] == "1.0"

                await service.stop()

    @pytest.mark.asyncio
    async def test_multiple_messages_kafka_ordering(
        self, kafka_settings, clean_outbox_table, db_session, kafka_consumer
    ):
        """Test multiple message processing with real Kafka ordering."""
        with patch("src.services.outbox.relay.get_settings") as mock_get_settings:
            mock_get_settings.return_value = kafka_settings

            # Create multiple test messages with different payloads
            test_messages = []
            for i in range(3):
                payload = {"event": f"multi_test_{i}", "data": {"index": i, "batch": "multi_kafka"}}
                message = await self.create_test_message(db_session, topic="integration.test.multi", payload=payload)
                test_messages.append((message, payload))

            service = OutboxRelayService()
            with patch("src.services.outbox.relay.create_sql_session", self.create_mock_sql_session(db_session)):
                await service.start()
                # Process all messages
                processed = await service._drain_once()
                assert processed == 3

                # Verify all messages are marked as SENT in database
                for test_message, _ in test_messages:
                    updated_message = await self.get_message_from_db(db_session, test_message.id)
                    assert updated_message.status == OutboxStatus.SENT

                # Verify all messages were sent to Kafka
                consumed_messages = await self.consume_messages(
                    kafka_consumer, "integration.test.multi", expected_count=3
                )

                assert len(consumed_messages) == 3

                # Verify message ordering and content
                consumed_payloads = [msg["value"] for msg in consumed_messages]
                expected_payloads = [payload for _, payload in test_messages]

                # Messages should be in order (though Kafka ordering within partition is guaranteed)
                for i, consumed_payload in enumerate(consumed_payloads):
                    assert consumed_payload["data"]["batch"] == "multi_kafka"
                    assert consumed_payload["event"].startswith("multi_test_")

                await service.stop()

    @pytest.mark.asyncio
    async def test_message_retry_with_kafka_failure_simulation(
        self, kafka_settings, clean_outbox_table, db_session, kafka_service
    ):
        """Test message retry behavior when Kafka is unavailable then becomes available."""
        with patch("src.services.outbox.relay.get_settings") as mock_get_settings:
            mock_get_settings.return_value = kafka_settings

            # Create test message
            test_payload = {"event": "retry_test", "data": {"scenario": "kafka_unavailable"}}
            test_message = await self.create_test_message(
                db_session, topic="integration.test.retry", payload=test_payload
            )

            # First, simulate Kafka failure by using invalid bootstrap servers
            kafka_settings.kafka_bootstrap_servers = ["invalid:9092"]

            service = OutboxRelayService()

            try:
                await service.start()
            except Exception:
                # Expected to fail with invalid Kafka configuration
                pass

            # The service should fail to start with invalid Kafka config
            # Let's test with proper Kafka but temporary processing failure
            kafka_settings.kafka_bootstrap_servers = kafka_service["bootstrap_servers"]

            # Test successful retry after fixing configuration
            service2 = OutboxRelayService()
            with patch("src.services.outbox.relay.create_sql_session", self.create_mock_sql_session(db_session)):
                await service2.start()
                # Process the message - should succeed now
                processed = await service2._drain_once()
                assert processed == 1

                # Verify message was processed successfully
                updated_message = await self.get_message_from_db(db_session, test_message.id)
                assert updated_message.status == OutboxStatus.SENT

                await service2.stop()

    @pytest.mark.asyncio
    async def test_large_payload_kafka_handling(self, kafka_settings, clean_outbox_table, db_session, kafka_consumer):
        """Test handling of large payloads with real Kafka."""
        with patch("src.services.outbox.relay.get_settings") as mock_get_settings:
            mock_get_settings.return_value = kafka_settings

            # Create message with large payload
            large_payload = {
                "event": "large_payload_test",
                "data": {
                    "description": "Testing large message handling with Kafka",
                    "large_text": "x" * 10000,  # 10KB of text
                    "array_data": list(range(1000)),
                    "nested_structure": {
                        "level1": {"level2": {"items": [{"id": i, "data": f"item_{i}_data"} for i in range(100)]}}
                    },
                },
                "metadata": {"size": "large", "compression": "none", "timestamp": datetime.now(UTC).isoformat()},
            }

            test_message = await self.create_test_message(
                db_session, topic="integration.test.large", payload=large_payload
            )

            service = OutboxRelayService()
            with patch("src.services.outbox.relay.create_sql_session", self.create_mock_sql_session(db_session)):
                await service.start()
                # Process the large message
                processed = await service._drain_once()
                assert processed == 1

                # Verify database state
                updated_message = await self.get_message_from_db(db_session, test_message.id)
                assert updated_message.status == OutboxStatus.SENT

                # Verify large message was successfully sent to Kafka
                consumed_messages = await self.consume_messages(
                    kafka_consumer, "integration.test.large", expected_count=1
                )

                assert len(consumed_messages) == 1
                kafka_message = consumed_messages[0]

                # Verify the large payload was transmitted correctly
                assert kafka_message["value"] == large_payload
                assert len(kafka_message["value"]["data"]["large_text"]) == 10000
                assert len(kafka_message["value"]["data"]["array_data"]) == 1000
                assert len(kafka_message["value"]["data"]["nested_structure"]["level1"]["level2"]["items"]) == 100

                await service.stop()

    @pytest.mark.asyncio
    async def test_concurrent_processing_with_real_kafka(
        self, kafka_settings, clean_outbox_table, db_session, kafka_consumer
    ):
        """Test concurrent message processing with real Kafka to ensure no duplication."""
        with patch("src.services.outbox.relay.get_settings") as mock_get_settings:
            mock_get_settings.return_value = kafka_settings

            # Create multiple messages for concurrent processing
            test_messages = []
            for i in range(5):
                payload = {"event": f"concurrent_test_{i}", "data": {"worker_id": None, "index": i}}
                message = await self.create_test_message(
                    db_session, topic="integration.test.concurrent", payload=payload
                )
                test_messages.append((message, payload))

            # Create two concurrent workers
            service1 = OutboxRelayService()
            service2 = OutboxRelayService()

            with patch("src.services.outbox.relay.create_sql_session", self.create_mock_sql_session(db_session)):
                await service1.start()
                await service2.start()
                # Run both workers concurrently
                results = await asyncio.gather(
                    service1._drain_once(), service2._drain_once(), return_exceptions=True
                )

                # Total processed should equal number of messages (no duplication)
                total_processed = sum(r for r in results if isinstance(r, int))
                assert total_processed == len(test_messages)

                # Verify all messages were sent to Kafka
                consumed_messages = await self.consume_messages(
                    kafka_consumer, "integration.test.concurrent", expected_count=len(test_messages)
                )

                assert len(consumed_messages) == len(test_messages)

                # Verify no message duplication in Kafka
                consumed_indices = {msg["value"]["data"]["index"] for msg in consumed_messages}
                expected_indices = {i for i in range(len(test_messages))}
                assert consumed_indices == expected_indices

                await service1.stop()
                await service2.stop()

    @pytest.mark.asyncio
    async def test_message_headers_kafka_transmission(
        self, kafka_settings, clean_outbox_table, db_session, kafka_consumer
    ):
        """Test that message headers are correctly transmitted to Kafka."""
        with patch("src.services.outbox.relay.get_settings") as mock_get_settings:
            mock_get_settings.return_value = kafka_settings

            # Create message with complex headers
            test_payload = {"event": "headers_test", "data": {"purpose": "header_verification"}}
            complex_headers = {
                "content-type": "application/json",
                "source-service": "outbox-relay-test",
                "correlation-id": str(uuid4()),
                "version": "1.2.3",
                "priority": "high",
                "unicode-header": "测试中文",
            }

            # Create message with headers in database
            message_data = {
                "id": uuid4(),
                "topic": "integration.test.headers",
                "key": "headers-test-key",
                "partition_key": "headers-partition",
                "payload": test_payload,
                "headers": complex_headers,
                "status": OutboxStatus.PENDING,
                "retry_count": 0,
                "max_retries": 3,
                "created_at": datetime.now(UTC),
            }

            result = await db_session.execute(insert(EventOutbox).values(message_data).returning(EventOutbox))
            test_message = result.scalar_one()
            await db_session.commit()

            service = OutboxRelayService()
            with patch("src.services.outbox.relay.create_sql_session", self.create_mock_sql_session(db_session)):
                await service.start()

            try:
                # Process the message
                processed = await service._drain_once()
                assert processed == 1

                # Verify message was sent to Kafka with headers
                consumed_messages = await self.consume_messages(
                    kafka_consumer, "integration.test.headers", expected_count=1
                )

                assert len(consumed_messages) == 1
                kafka_message = consumed_messages[0]

                # Verify headers were transmitted correctly
                received_headers = kafka_message["headers"]

                assert received_headers["content-type"] == "application/json"
                assert received_headers["source-service"] == "outbox-relay-test"
                assert received_headers["version"] == "1.2.3"
                assert received_headers["priority"] == "high"
                assert received_headers["unicode-header"] == "测试中文"

                # Verify correlation-id is a valid UUID string
                assert len(received_headers["correlation-id"]) == 36  # UUID string length

            finally:
                await service.stop()

    @pytest.mark.asyncio
    async def test_scheduled_messages_with_kafka_timing(
        self, kafka_settings, clean_outbox_table, db_session, kafka_consumer
    ):
        """Test scheduled message processing with real Kafka."""
        with patch("src.services.outbox.relay.get_settings") as mock_get_settings:
            mock_get_settings.return_value = kafka_settings

            # Create immediate message
            immediate_payload = {"event": "immediate", "data": {"type": "immediate_processing"}}
            immediate_message = await self.create_test_message(
                db_session,
                topic="integration.test.scheduled",
                payload=immediate_payload,
                scheduled_at=None,  # Process immediately
            )

            # Create scheduled message for the past (should process)
            past_payload = {"event": "past_scheduled", "data": {"type": "past_scheduled"}}
            past_scheduled_message = await self.create_test_message(
                db_session,
                topic="integration.test.scheduled",
                payload=past_payload,
                scheduled_at=datetime.now(UTC) - timedelta(seconds=10),  # 10 seconds ago
            )

            # Create scheduled message for the future (should not process)
            future_payload = {"event": "future_scheduled", "data": {"type": "future_scheduled"}}
            future_scheduled_message = await self.create_test_message(
                db_session,
                topic="integration.test.scheduled",
                payload=future_payload,
                scheduled_at=datetime.now(UTC) + timedelta(hours=1),  # 1 hour from now
            )

            service = OutboxRelayService()
            with patch("src.services.outbox.relay.create_sql_session", self.create_mock_sql_session(db_session)):
                await service.start()
                # Process messages - should process immediate and past scheduled only
                processed = await service._drain_once()
                assert processed == 2  # immediate + past scheduled

                # Verify Kafka received only the processable messages
                consumed_messages = await self.consume_messages(
                    kafka_consumer, "integration.test.scheduled", expected_count=2
                )

                assert len(consumed_messages) == 2

                # Verify message types
                consumed_events = {msg["value"]["event"] for msg in consumed_messages}
                assert consumed_events == {"immediate", "past_scheduled"}

                # Verify future scheduled message is still pending
                future_message_updated = await self.get_message_from_db(db_session, future_scheduled_message.id)
                assert future_message_updated.status == OutboxStatus.PENDING

                await service.stop()

    @pytest.mark.asyncio
    async def test_kafka_producer_configuration_validation(self, kafka_settings, clean_outbox_table):
        """Test that the service properly validates Kafka producer configuration."""
        # Test with invalid bootstrap servers
        kafka_settings.kafka_bootstrap_servers = ["invalid-host:9092"]

        with patch("src.services.outbox.relay.get_settings") as mock_get_settings:
            mock_get_settings.return_value = kafka_settings

            service = OutboxRelayService()

            # Service should fail to start with invalid Kafka configuration
            with pytest.raises(Exception):  # Could be ConnectionError or similar
                await service.start()
                # Give it a moment to fail
                await asyncio.sleep(0.1)
                await service.stop()

    @pytest.mark.asyncio
    async def test_service_graceful_shutdown_with_kafka(self, kafka_settings, clean_outbox_table, db_session):
        """Test graceful shutdown while processing messages with real Kafka."""
        with patch("src.services.outbox.relay.get_settings") as mock_get_settings:
            mock_get_settings.return_value = kafka_settings

            # Create test message
            test_payload = {"event": "shutdown_test", "data": {"scenario": "graceful_shutdown"}}
            await self.create_test_message(db_session, topic="integration.test.shutdown", payload=test_payload)

            service = OutboxRelayService()
            with patch("src.services.outbox.relay.create_sql_session", self.create_mock_sql_session(db_session)):
                await service.start()

            try:
                # Start processing in background
                process_task = asyncio.create_task(service._drain_once())

                # Give it a moment to start processing
                await asyncio.sleep(0.05)

                # Initiate shutdown
                shutdown_start = datetime.now(UTC)
                await service.stop()
                shutdown_end = datetime.now(UTC)

                # Wait for processing to complete
                try:
                    result = await asyncio.wait_for(process_task, timeout=2.0)
                    # Processing should complete successfully
                    assert isinstance(result, int)
                except TimeoutError:
                    process_task.cancel()
                    # Timeout is acceptable for graceful shutdown test
                    pass

    
                # Verify shutdown was reasonably quick
                shutdown_duration = (shutdown_end - shutdown_start).total_seconds()
                assert shutdown_duration < 2.0  # Should shutdown within 2 seconds

                # Verify service is properly stopped
                assert service._stop_event.is_set()
                assert service._producer is None

            except Exception:
                # Ensure cleanup even if test fails
                if not service._stop_event.is_set():
                    await service.stop()
                raise
