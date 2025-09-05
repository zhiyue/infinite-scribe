"""Integration tests for OutboxRelayService using testcontainers."""

import asyncio
import json
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy import delete, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.sql.session import create_sql_session
from src.models.workflow import EventOutbox
from src.schemas.enums import OutboxStatus
from src.services.outbox.relay import OutboxRelayService


@pytest.mark.integration
class TestOutboxRelayServiceIntegration:
    """Integration test cases for OutboxRelayService using testcontainers."""

    def create_mock_sql_session(self, db_session: AsyncSession):
        """Create a mock create_sql_session that uses the same database engine as the test.

        This ensures OutboxRelayService uses the same testcontainer database
        as the integration tests, but with a separate session to avoid conflicts.
        """
        from sqlalchemy.orm import sessionmaker

        # Get the same engine as the test
        engine = db_session.bind

        @asynccontextmanager
        async def mock_create_sql_session():
            # Create session with same engine as test
            async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)()
            try:
                yield async_session
                # Let service handle its own commits - don't auto-commit here
            except Exception:
                await async_session.rollback()
                raise
            finally:
                await async_session.close()

        return mock_create_sql_session

    @pytest.fixture
    async def clean_outbox_table(self, db_session: AsyncSession):
        """Clean the event_outbox table before and after each test."""
        await db_session.execute(delete(EventOutbox))
        await db_session.commit()

        yield

        await db_session.execute(delete(EventOutbox))
        await db_session.commit()

    @pytest.fixture
    def mock_kafka_settings(self):
        """Create mock settings with test Kafka configuration."""
        settings = MagicMock()
        settings.environment = "test"
        settings.log_level = "DEBUG"
        settings.kafka_bootstrap_servers = ["localhost:9092"]

        # Relay-specific settings with fast intervals for testing
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
            payload = {"event": "test", "data": "integration_test"}

        # Ensure DB check constraints are satisfied:
        # - scheduled_at (if provided) must be >= created_at
        now_ts = datetime.now(UTC)
        created_ts = now_ts
        if scheduled_at is not None and scheduled_at < created_ts:
            # Align created_at to scheduled_at to satisfy constraint
            created_ts = scheduled_at

        message_data = {
            "id": uuid4(),
            "topic": topic,
            "key": "test-key",
            "partition_key": "partition-1",
            "payload": payload,
            "headers": {"source": "integration_test", "version": "1.0"},
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
        # Create a fresh session to bypass any transaction isolation issues
        from sqlalchemy.orm import sessionmaker

        engine = db_session.bind
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)()
        try:
            result = await async_session.execute(select(EventOutbox).where(EventOutbox.id == message_id))
            return result.scalar_one()
        finally:
            await async_session.close()

    @pytest.mark.asyncio
    async def test_service_initialization_and_cleanup(self, mock_kafka_settings, clean_outbox_table):
        """Test service can be initialized and cleaned up properly."""
        with patch("src.services.outbox.relay.get_settings") as mock_get_settings:
            mock_get_settings.return_value = mock_kafka_settings

            service = OutboxRelayService()

            # Test start
            await service.start()
            assert service._producer is not None

            # Test stop
            await service.stop()
            assert service._producer is None
            assert service._stop_event.is_set()

    @pytest.mark.asyncio
    async def test_single_message_processing_success(self, mock_kafka_settings, clean_outbox_table, db_session):
        """Test processing a single message successfully using testcontainers."""
        with patch("src.services.outbox.relay.get_settings") as mock_get_settings:
            mock_get_settings.return_value = mock_kafka_settings

            # Create test message using testcontainer database
            test_message = await self.create_test_message(db_session)

            # Mock successful Kafka producer
            with patch("src.services.outbox.relay.AIOKafkaProducer") as mock_producer_class:
                mock_producer = AsyncMock()
                mock_producer.start = AsyncMock()
                mock_producer.stop = AsyncMock()
                mock_producer.send_and_wait = AsyncMock()
                mock_producer_class.return_value = mock_producer

                # Patch the database session creation to use testcontainer database
                with patch("src.services.outbox.relay.create_sql_session", self.create_mock_sql_session(db_session)):
                    service = OutboxRelayService()
                    await service.start()

                    # Process messages
                    processed = await service._drain_once()

                    await service.stop()

                    # Verify processing result
                    assert processed == 1

                    # Verify message status in testcontainer database
                    updated_message = await self.get_message_from_db(db_session, test_message.id)
                    assert updated_message.status == OutboxStatus.SENT
                    assert updated_message.sent_at is not None
                    assert updated_message.last_error is None

    @pytest.mark.asyncio
    async def test_multiple_message_processing(self, mock_kafka_settings, clean_outbox_table, db_session):
        """Test processing multiple messages in a batch."""
        with patch("src.services.outbox.relay.get_settings") as mock_get_settings:
            mock_get_settings.return_value = mock_kafka_settings

            # Create multiple test messages
            test_messages = []
            for i in range(3):
                message = await self.create_test_message(
                    db_session, topic=f"test.topic.{i}", payload={"event": f"test_{i}", "data": f"message_{i}"}
                )
                test_messages.append(message)

            # Mock successful Kafka producer
            with patch("src.services.outbox.relay.AIOKafkaProducer") as mock_producer_class:
                mock_producer = AsyncMock()
                mock_producer_class.return_value = mock_producer
                mock_producer.send_and_wait = AsyncMock()

                # Patch the database session creation to use testcontainer database
                with patch("src.services.outbox.relay.create_sql_session", self.create_mock_sql_session(db_session)):
                    service = OutboxRelayService()
                    await service.start()

                    # Process messages
                    processed = await service._drain_once()

                    await service.stop()

                    # Verify processing result
                    assert processed == 3

                    # Verify all messages are sent
                    for test_message in test_messages:
                        updated_message = await self.get_message_from_db(db_session, test_message.id)
                        assert updated_message.status == OutboxStatus.SENT
                        assert updated_message.sent_at is not None

    @pytest.mark.asyncio
    async def test_message_retry_on_failure(self, mock_kafka_settings, clean_outbox_table, db_session):
        """Test message retry logic on Kafka failure."""
        with patch("src.services.outbox.relay.get_settings") as mock_get_settings:
            mock_get_settings.return_value = mock_kafka_settings

            # Create test message
            test_message = await self.create_test_message(db_session)

            # Mock failing Kafka producer
            with patch("src.services.outbox.relay.AIOKafkaProducer") as mock_producer_class:
                mock_producer = AsyncMock()
                mock_producer.start = AsyncMock()
                mock_producer.stop = AsyncMock()
                mock_producer_class.return_value = mock_producer

                async def mock_send_and_wait(*args, **kwargs):
                    raise Exception("Kafka send failed")

                mock_producer.send_and_wait = mock_send_and_wait

                # Patch the database session creation to use testcontainer database
                with patch("src.services.outbox.relay.create_sql_session", self.create_mock_sql_session(db_session)):
                    service = OutboxRelayService()
                    await service.start()

                    # Process messages (should fail)
                    processed = await service._drain_once()

                    await service.stop()

                # Verify processing result
                assert processed == 0

                # Verify message is still pending with retry count increased
                updated_message = await self.get_message_from_db(db_session, test_message.id)
                assert updated_message.status == OutboxStatus.PENDING
                assert updated_message.retry_count == 1
                assert updated_message.last_error == "Kafka send failed"
                assert updated_message.scheduled_at is not None

    @pytest.mark.asyncio
    async def test_message_marked_failed_after_max_retries(self, mock_kafka_settings, clean_outbox_table, db_session):
        """Test message is marked as failed after exceeding max retries."""
        with patch("src.services.outbox.relay.get_settings") as mock_get_settings:
            mock_get_settings.return_value = mock_kafka_settings

            # Create test message with high retry count
            test_message = await self.create_test_message(
                db_session,
                retry_count=1,  # One more retry will reach max_retries (2)
                max_retries=2,
            )

            # Mock failing Kafka producer
            with patch("src.services.outbox.relay.AIOKafkaProducer") as mock_producer_class:
                mock_producer = AsyncMock()
                mock_producer.start = AsyncMock()
                mock_producer.stop = AsyncMock()
                mock_producer_class.return_value = mock_producer

                async def mock_send_and_wait(*args, **kwargs):
                    raise Exception("Kafka send failed")

                mock_producer.send_and_wait = mock_send_and_wait

                # Patch the database session creation to use testcontainer database
                with patch("src.services.outbox.relay.create_sql_session", self.create_mock_sql_session(db_session)):
                    service = OutboxRelayService()
                    await service.start()

                    # Process messages (should fail permanently)
                    processed = await service._drain_once()

                    await service.stop()

                    # Verify processing result
                    assert processed == 0

                    # Verify message is marked as failed
                    updated_message = await self.get_message_from_db(db_session, test_message.id)
                    assert updated_message.status == OutboxStatus.FAILED
                    assert updated_message.retry_count == 2
                    assert updated_message.last_error == "Kafka send failed"
                    assert updated_message.scheduled_at is None

    @pytest.mark.asyncio
    async def test_scheduled_message_not_processed_early(self, mock_kafka_settings, clean_outbox_table, db_session):
        """Test that scheduled messages are not processed before their time."""
        with patch("src.services.outbox.relay.get_settings") as mock_get_settings:
            mock_get_settings.return_value = mock_kafka_settings

            # Create message scheduled for future
            future_time = datetime.now(UTC) + timedelta(hours=1)
            test_message = await self.create_test_message(db_session, scheduled_at=future_time)

            # Mock successful Kafka producer
            with patch("src.services.outbox.relay.AIOKafkaProducer") as mock_producer_class:
                mock_producer = AsyncMock()
                mock_producer.start = AsyncMock()
                mock_producer.stop = AsyncMock()
                mock_producer.send_and_wait = AsyncMock()
                mock_producer_class.return_value = mock_producer

                # Patch the database session creation to use testcontainer database
                with patch("src.services.outbox.relay.create_sql_session", self.create_mock_sql_session(db_session)):
                    service = OutboxRelayService()
                    await service.start()

                    # Process messages (should find no eligible messages)
                    processed = await service._drain_once()

                    await service.stop()

                # Verify no messages were processed
                assert processed == 0

                # Verify message is still pending
                updated_message = await self.get_message_from_db(db_session, test_message.id)
                assert updated_message.status == OutboxStatus.PENDING
                assert updated_message.sent_at is None

    @pytest.mark.asyncio
    async def test_scheduled_message_processed_when_due(self, mock_kafka_settings, clean_outbox_table, db_session):
        """Test that scheduled messages are processed when their time arrives."""
        with patch("src.services.outbox.relay.get_settings") as mock_get_settings:
            mock_get_settings.return_value = mock_kafka_settings

            # Create message scheduled for past
            past_time = datetime.now(UTC) - timedelta(minutes=1)
            test_message = await self.create_test_message(db_session, scheduled_at=past_time)

            # Mock successful Kafka producer
            with patch("src.services.outbox.relay.AIOKafkaProducer") as mock_producer_class:
                mock_producer = AsyncMock()
                mock_producer_class.return_value = mock_producer
                mock_producer.send_and_wait = AsyncMock()

                # Patch the database session creation to use testcontainer database
                with patch("src.services.outbox.relay.create_sql_session", self.create_mock_sql_session(db_session)):
                    service = OutboxRelayService()
                    await service.start()

                    # Process messages (should process the scheduled message)
                    processed = await service._drain_once()

                    await service.stop()

                    # Verify message was processed
                    assert processed == 1

                    # Verify message is sent
                    updated_message = await self.get_message_from_db(db_session, test_message.id)
                    assert updated_message.status == OutboxStatus.SENT
                    assert updated_message.sent_at is not None

    @pytest.mark.asyncio
    async def test_concurrent_workers_skip_locked_rows(self, mock_kafka_settings, clean_outbox_table, db_session):
        """Test that concurrent workers don't process the same message."""
        with patch("src.services.outbox.relay.get_settings") as mock_get_settings:
            mock_get_settings.return_value = mock_kafka_settings

            # Create test message
            test_message = await self.create_test_message(db_session)

            # Mock Kafka producer that delays processing
            with patch("src.services.outbox.relay.AIOKafkaProducer") as mock_producer_class:
                mock_producer = AsyncMock()
                mock_producer_class.return_value = mock_producer

                async def slow_send_and_wait(*args, **kwargs):
                    await asyncio.sleep(0.1)  # Simulate slow processing

                mock_producer.send_and_wait = slow_send_and_wait

                # Patch the database session creation to use testcontainer database
                with patch("src.services.outbox.relay.create_sql_session", self.create_mock_sql_session(db_session)):
                    # Create two services (simulating concurrent workers)
                    service1 = OutboxRelayService()
                    service2 = OutboxRelayService()

                    await service1.start()
                    await service2.start()

                    # Start both services concurrently
                    results = await asyncio.gather(
                        service1._drain_once(), service2._drain_once(), return_exceptions=True
                    )

                    await service1.stop()
                    await service2.stop()

                    # Only one worker should have processed the message
                    total_processed = sum(r for r in results if isinstance(r, int))
                    assert total_processed == 1

                    # Verify message was processed once
                    updated_message = await self.get_message_from_db(db_session, test_message.id)
                    assert updated_message.status == OutboxStatus.SENT

    @pytest.mark.asyncio
    async def test_race_condition_prevention_with_revalidation(
        self, mock_kafka_settings, clean_outbox_table, db_session
    ):
        """Test that race condition between phases is prevented by revalidation."""
        with patch("src.services.outbox.relay.get_settings") as mock_get_settings:
            mock_get_settings.return_value = mock_kafka_settings

            # Create test message
            test_message = await self.create_test_message(db_session)

            # Mock successful Kafka producer
            with patch("src.services.outbox.relay.AIOKafkaProducer") as mock_producer_class:
                mock_producer = AsyncMock()
                mock_producer_class.return_value = mock_producer
                mock_producer.send_and_wait = AsyncMock()

                service = OutboxRelayService()
                await service.start()

                # Simulate race condition: change message status between phases
                original_lock_row = service._lock_row

                async def race_condition_lock_row(session, oid):
                    # Before locking, another process changes the message status
                    if oid == test_message.id:
                        async with create_sql_session() as update_session:
                            await update_session.execute(
                                update(EventOutbox)
                                .where(EventOutbox.id == test_message.id)
                                .values(status=OutboxStatus.SENT)
                            )
                            await update_session.commit()

                    # Now try to lock (should return None due to status change)
                    return await original_lock_row(session, oid)

                service._lock_row = race_condition_lock_row

                # Process messages (should handle race condition gracefully)
                processed = await service._drain_once()

                await service.stop()

                # No messages should be processed due to race condition
                assert processed == 0

    @pytest.mark.asyncio
    async def test_json_serialization_handles_complex_payloads(
        self, mock_kafka_settings, clean_outbox_table, db_session
    ):
        """Test that complex JSON payloads are handled correctly."""
        with patch("src.services.outbox.relay.get_settings") as mock_get_settings:
            mock_get_settings.return_value = mock_kafka_settings

            # Create message with complex payload
            complex_payload = {
                "event": "complex_event",
                "data": {
                    "nested": {"deeply": {"nested": "value"}},
                    "array": [1, 2, {"key": "value"}],
                    "unicode": "测试中文",
                    "special_chars": "!@#$%^&*()",
                    "numbers": [1, 2.5, -10],
                    "booleans": [True, False],
                    "null_value": None,
                },
                "timestamp": datetime.now(UTC).isoformat(),
                "metadata": {"version": "1.0", "source": "integration_test"},
            }

            test_message = await self.create_test_message(db_session, payload=complex_payload)

            # Mock successful Kafka producer and capture sent data
            sent_data = []

            with patch("src.services.outbox.relay.AIOKafkaProducer") as mock_producer_class:
                mock_producer = AsyncMock()
                mock_producer_class.return_value = mock_producer

                async def capture_send_and_wait(*args, **kwargs):
                    sent_data.append(kwargs.get("value", args[1] if len(args) > 1 else None))

                mock_producer.send_and_wait = capture_send_and_wait

                # Patch the database session creation to use testcontainer database
                with patch("src.services.outbox.relay.create_sql_session", self.create_mock_sql_session(db_session)):
                    service = OutboxRelayService()
                    await service.start()

                    # Process messages
                    processed = await service._drain_once()

                    await service.stop()

                # Verify processing
                assert processed == 1

                # Verify JSON serialization
                assert len(sent_data) == 1
                sent_bytes = sent_data[0]
                assert isinstance(sent_bytes, bytes)

                # Deserialize and verify content
                deserialized = json.loads(sent_bytes.decode("utf-8"))
                assert deserialized == complex_payload

    @pytest.mark.asyncio
    async def test_header_encoding_with_various_types(self, mock_kafka_settings, clean_outbox_table, db_session):
        """Test header encoding with various data types."""
        with patch("src.services.outbox.relay.get_settings") as mock_get_settings:
            mock_get_settings.return_value = mock_kafka_settings

            # Create message with complex headers
            complex_headers = {
                "string_header": "test_value",
                "numeric_header": 123,
                "boolean_header": True,
                "unicode_header": "测试",
                "special_chars": "!@#$%",
            }

            # Update test message with complex headers
            message_data = {
                "id": uuid4(),
                "topic": "test.topic",
                "payload": {"event": "header_test"},
                "headers": complex_headers,
                "status": OutboxStatus.PENDING,
                "retry_count": 0,
                "max_retries": 3,
                "created_at": datetime.now(UTC),
            }

            async with create_sql_session() as session:
                result = await session.execute(insert(EventOutbox).values(message_data).returning(EventOutbox))
                test_message = result.scalar_one()
                await session.commit()

            # Mock successful Kafka producer and capture headers
            sent_headers = []

            with patch("src.services.outbox.relay.AIOKafkaProducer") as mock_producer_class:
                mock_producer = AsyncMock()
                mock_producer_class.return_value = mock_producer

                async def capture_send_and_wait(*args, **kwargs):
                    sent_headers.append(kwargs.get("headers"))

                mock_producer.send_and_wait = capture_send_and_wait

                service = OutboxRelayService()
                await service.start()

                # Process messages
                processed = await service._drain_once()

                await service.stop()

                # Verify processing
                assert processed == 1

                # Verify headers were encoded correctly
                assert len(sent_headers) == 1
                headers = sent_headers[0]
                assert isinstance(headers, list)

                # Convert back to dict for verification
                header_dict = {k: v.decode("utf-8") for k, v in headers}
                expected = {
                    "string_header": "test_value",
                    "numeric_header": "123",
                    "boolean_header": "True",
                    "unicode_header": "测试",
                    "special_chars": "!@#$%",
                }
                assert header_dict == expected

    @pytest.mark.asyncio
    async def test_service_stops_gracefully_during_processing(
        self, mock_kafka_settings, clean_outbox_table, db_session
    ):
        """Test that service stops gracefully even during message processing."""
        with patch("src.services.outbox.relay.get_settings") as mock_get_settings:
            mock_get_settings.return_value = mock_kafka_settings

            # Create test message
            test_message = await self.create_test_message(db_session)

            # Mock Kafka producer with delay to simulate processing time
            with patch("src.services.outbox.relay.AIOKafkaProducer") as mock_producer_class:
                mock_producer = AsyncMock()
                mock_producer_class.return_value = mock_producer

                async def delayed_send_and_wait(*args, **kwargs):
                    await asyncio.sleep(0.2)  # Simulate processing delay

                mock_producer.send_and_wait = delayed_send_and_wait

                service = OutboxRelayService()
                await service.start()

                # Start processing in background
                process_task = asyncio.create_task(service._drain_once())

                # Stop service after short delay (during processing)
                await asyncio.sleep(0.1)
                await service.stop()

                # Wait for processing to complete (should handle stop gracefully)
                try:
                    result = await asyncio.wait_for(process_task, timeout=1.0)
                    # Processing may complete or be interrupted
                    assert isinstance(result, int)
                except TimeoutError:
                    process_task.cancel()
                    # Timeout is acceptable for graceful shutdown test
                    pass

    @pytest.mark.asyncio
    async def test_batch_size_limiting(self, mock_kafka_settings, clean_outbox_table, db_session):
        """Test that batch size is respected."""
        # Set small batch size
        mock_kafka_settings.relay.batch_size = 2

        with patch("src.services.outbox.relay.get_settings") as mock_get_settings:
            mock_get_settings.return_value = mock_kafka_settings

            # Create more messages than batch size
            test_messages = []
            for i in range(5):
                message = await self.create_test_message(
                    db_session, topic=f"test.topic.{i}", payload={"event": f"batch_test_{i}"}
                )
                test_messages.append(message)

            # Ensure all changes are flushed to the database
            await db_session.flush()

            # Mock successful Kafka producer
            with patch("src.services.outbox.relay.AIOKafkaProducer") as mock_producer_class:
                mock_producer = AsyncMock()
                mock_producer_class.return_value = mock_producer
                mock_producer.send_and_wait = AsyncMock()

                # Patch the database session creation to use testcontainer database
                with patch("src.services.outbox.relay.create_sql_session", self.create_mock_sql_session(db_session)):
                    service = OutboxRelayService()
                    await service.start()

                    # First drain should process only batch_size messages
                    processed_first = await service._drain_once()
                    assert processed_first == 2

                    # Second drain should process next batch_size messages
                    processed_second = await service._drain_once()
                    assert processed_second == 2

                    # Third drain should process the final remaining message
                    processed_third = await service._drain_once()
                    assert processed_third == 1

                    # Fourth drain should find no more messages
                    processed_fourth = await service._drain_once()
                    assert processed_fourth == 0

                    await service.stop()

    @pytest.mark.asyncio
    async def test_database_connection_error_handling(self, mock_kafka_settings, clean_outbox_table, db_session):
        """Test handling of database connection errors."""
        with patch("src.services.outbox.relay.get_settings") as mock_get_settings:
            mock_get_settings.return_value = mock_kafka_settings

            service = OutboxRelayService()

            # Mock database session to raise connection error
            with patch("src.services.outbox.relay.create_sql_session") as mock_create_session:
                mock_create_session.side_effect = Exception("Database connection failed")

                await service.start()

                # Database error should propagate from _drain_once()
                with pytest.raises(Exception, match="Database connection failed"):
                    await service._drain_once()

                await service.stop()

    @pytest.mark.asyncio
    async def test_exponential_backoff_timing_integration(self, mock_kafka_settings, clean_outbox_table, db_session):
        """Integration test for exponential backoff timing."""
        with patch("src.services.outbox.relay.get_settings") as mock_get_settings:
            mock_get_settings.return_value = mock_kafka_settings

            # Create test message
            test_message = await self.create_test_message(db_session, max_retries=2)

            # Mock failing Kafka producer
            with patch("src.services.outbox.relay.AIOKafkaProducer") as mock_producer_class:
                mock_producer = AsyncMock()
                mock_producer_class.return_value = mock_producer

                async def mock_send_and_wait(*args, **kwargs):
                    raise Exception("Simulated failure")

                mock_producer.send_and_wait = mock_send_and_wait

                # Patch the database session creation to use testcontainer database
                with patch("src.services.outbox.relay.create_sql_session", self.create_mock_sql_session(db_session)):
                    service = OutboxRelayService()
                    await service.start()

                    # First failure - should schedule retry
                    start_time = datetime.now(UTC)
                    processed = await service._drain_once()
                    assert processed == 0

                    # Check message state after first failure
                    updated_message = await self.get_message_from_db(db_session, test_message.id)
                    assert updated_message.retry_count == 1
                    assert updated_message.scheduled_at is not None

                    # Calculate expected delay (base_ms * 2^0 = 100ms)
                    expected_delay = timedelta(milliseconds=100)
                    actual_delay = updated_message.scheduled_at - start_time

                    # Allow some tolerance for execution time
                    assert abs((actual_delay - expected_delay).total_seconds()) < 0.1

                    await service.stop()
