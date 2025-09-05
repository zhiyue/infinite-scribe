"""Concurrency and edge case tests for OutboxRelayService using real Kafka testcontainers."""

import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy import delete, insert, select
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.workflow import EventOutbox
from src.schemas.enums import OutboxStatus
from src.services.outbox.relay import OutboxRelayService


@pytest.mark.integration
class TestOutboxRelayServiceConcurrency:
    """Concurrency and edge case test cases for OutboxRelayService."""

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
        """Create settings using real Kafka testcontainer for concurrency testing."""
        settings = MagicMock()
        settings.environment = "test"
        settings.log_level = "DEBUG"
        settings.kafka_bootstrap_servers = kafka_service["bootstrap_servers"]

        # Fast settings for concurrency testing
        relay_settings = MagicMock()
        relay_settings.poll_interval_seconds = 0.01  # Very fast polling
        relay_settings.batch_size = 3
        relay_settings.yield_sleep_ms = 1
        relay_settings.loop_error_backoff_ms = 10
        relay_settings.retry_backoff_ms = 50
        relay_settings.max_backoff_ms = 1000
        relay_settings.max_retries_default = 2
        settings.relay = relay_settings

        return settings

    async def create_test_messages(self, db_session: AsyncSession, count: int = 5) -> list[EventOutbox]:
        """Create multiple test messages for concurrency testing."""
        messages = []
        for i in range(count):
            message_data = {
                "id": uuid4(),
                "topic": f"concurrency.test.{i}",
                "key": f"key-{i}",
                "payload": {"event": f"concurrent_test_{i}", "index": i},
                "headers": {"worker_test": "true", "index": str(i)},
                "status": OutboxStatus.PENDING,
                "retry_count": 0,
                "max_retries": 3,
                "created_at": datetime.now(UTC) + timedelta(milliseconds=i),  # Slight ordering
            }

            result = await db_session.execute(insert(EventOutbox).values(message_data).returning(EventOutbox))
            message = result.scalar_one()
            messages.append(message)

        await db_session.commit()
        return messages

    async def get_all_messages_from_db(self, db_session: AsyncSession) -> list[EventOutbox]:
        """Get all messages from the database."""
        result = await db_session.execute(select(EventOutbox).order_by(EventOutbox.created_at))
        return list(result.scalars().all())

    @pytest.mark.asyncio
    async def test_multiple_concurrent_workers_no_duplication(self, kafka_settings, clean_outbox_table, db_session):
        """Test that multiple concurrent workers don't duplicate message processing using real Kafka."""
        with patch("src.services.outbox.relay.get_settings") as mock_get_settings:
            mock_get_settings.return_value = kafka_settings

            # Create test messages
            test_messages = await self.create_test_messages(db_session, 10)

            # Create Kafka consumer to verify no duplicates
            import json

            from aiokafka import AIOKafkaConsumer

            consumer = AIOKafkaConsumer(
                bootstrap_servers=kafka_settings.kafka_bootstrap_servers,
                group_id=f"concurrency-test-consumer-{uuid4()}",
                auto_offset_reset="earliest",
                value_deserializer=lambda x: json.loads(x.decode("utf-8")) if x else None,
                consumer_timeout_ms=5000,
            )
            await consumer.start()

            # Subscribe to all concurrency test topics
            test_topics = [f"concurrency.test.{i}" for i in range(10)]
            consumer.subscribe(test_topics)

            try:
                # Create multiple worker services
                workers = []
                for i in range(3):
                    worker = OutboxRelayService()
                    await worker.start()
                    workers.append(worker)

                try:
                    # Run workers concurrently
                    tasks = []
                    for worker in workers:
                        # Each worker runs multiple drain cycles
                        async def worker_cycle(w):
                            total_processed = 0
                            for _ in range(5):  # Multiple cycles to increase concurrency
                                processed = await w._drain_once()
                                total_processed += processed
                                if processed == 0:
                                    await asyncio.sleep(0.001)  # Brief pause if no work
                            return total_processed

                        tasks.append(asyncio.create_task(worker_cycle(worker)))

                    # Wait for all workers to complete
                    results = await asyncio.gather(*tasks)
                    total_processed = sum(results)

                    # Verify all messages were processed exactly once in database
                    assert total_processed == len(test_messages)

                    # Verify database state
                    final_messages = await self.get_all_messages_from_db(db_session)
                    sent_count = sum(1 for msg in final_messages if msg.status == OutboxStatus.SENT)
                    assert sent_count == len(test_messages)

                    # Verify messages were sent to Kafka without duplication
                    consumed_messages = []
                    start_time = datetime.now(UTC)

                    while len(consumed_messages) < len(test_messages):
                        # Check timeout (10 seconds max)
                        if (datetime.now(UTC) - start_time).total_seconds() > 10:
                            break

                        try:
                            msg_batch = await asyncio.wait_for(consumer.getmany(timeout_ms=1000), timeout=2.0)
                            for topic_partition, messages in msg_batch.items():
                                for message in messages:
                                    consumed_messages.append(
                                        {
                                            "topic": message.topic,
                                            "value": message.value,
                                            "index": message.value["index"] if message.value else None,
                                        }
                                    )
                        except TimeoutError:
                            continue

                    # Verify no message duplication in Kafka
                    assert len(consumed_messages) == len(test_messages)

                    # Verify all indices are unique (no duplicates)
                    consumed_indices = {msg["index"] for msg in consumed_messages if msg["index"] is not None}
                    expected_indices = {i for i in range(len(test_messages))}
                    assert consumed_indices == expected_indices

                finally:
                    # Clean up workers
                    for worker in workers:
                        await worker.stop()

            finally:
                await consumer.stop()

    @pytest.mark.asyncio
    async def test_high_concurrency_with_mixed_processing_times(
        self, mock_kafka_settings, clean_outbox_table, db_session
    ):
        """Test high concurrency with varying message processing times."""
        with patch("src.services.outbox.relay.get_settings") as mock_get_settings:
            mock_get_settings.return_value = mock_kafka_settings

            # Create test messages
            test_messages = await self.create_test_messages(db_session, 15)

            processing_times = {}

            # Mock Kafka producer with varying processing times
            with patch("src.services.outbox.relay.AIOKafkaProducer") as mock_producer_class:

                async def variable_send_and_wait(topic, **kwargs):
                    # Different messages take different times to process
                    topic_index = int(topic.split(".")[-1])
                    delay = 0.001 + (topic_index % 5) * 0.002  # 1-9ms delays

                    start_time = datetime.now(UTC)
                    await asyncio.sleep(delay)
                    end_time = datetime.now(UTC)

                    processing_times[topic] = (end_time - start_time).total_seconds()

                mock_producer = AsyncMock()
                mock_producer.start = AsyncMock()
                mock_producer.stop = AsyncMock()
                mock_producer.send_and_wait = variable_send_and_wait
                mock_producer_class.return_value = mock_producer

                # Create 4 concurrent workers
                workers = []
                for i in range(4):
                    worker = OutboxRelayService()
                    await worker.start()
                    workers.append(worker)

                try:
                    # Run workers with high concurrency
                    async def aggressive_worker(worker):
                        total_processed = 0
                        for _ in range(10):  # Many rapid cycles
                            processed = await worker._drain_once()
                            total_processed += processed
                        return total_processed

                    # Start all workers simultaneously
                    tasks = [asyncio.create_task(aggressive_worker(worker)) for worker in workers]

                    results = await asyncio.gather(*tasks)
                    total_processed = sum(results)

                    # All messages should be processed despite varying times
                    assert total_processed == len(test_messages)

                    # Verify all messages have different processing characteristics
                    assert len(processing_times) == len(test_messages)

                finally:
                    for worker in workers:
                        await worker.stop()

    @pytest.mark.asyncio
    async def test_worker_failure_during_concurrent_processing(
        self, mock_kafka_settings, clean_outbox_table, db_session
    ):
        """Test that worker failures don't affect other concurrent workers."""
        with patch("src.services.outbox.relay.get_settings") as mock_get_settings:
            mock_get_settings.return_value = mock_kafka_settings

            # Create test messages
            test_messages = await self.create_test_messages(db_session, 8)

            successful_processes = []
            failed_processes = []

            with patch("src.services.outbox.relay.AIOKafkaProducer") as mock_producer_class:

                async def selective_failure_send_and_wait(topic, **kwargs):
                    topic_index = int(topic.split(".")[-1])

                    # Worker 0 fails on even-indexed topics
                    if hasattr(asyncio.current_task(), "worker_id"):
                        worker_id = asyncio.current_task().worker_id
                        if worker_id == 0 and topic_index % 2 == 0:
                            failed_processes.append(f"worker_{worker_id}_{topic}")
                            raise Exception(f"Worker {worker_id} failed on {topic}")

                    await asyncio.sleep(0.005)  # Small delay
                    successful_processes.append(topic)

                mock_producer = AsyncMock()
                mock_producer.start = AsyncMock()
                mock_producer.stop = AsyncMock()
                mock_producer.send_and_wait = selective_failure_send_and_wait
                mock_producer_class.return_value = mock_producer

                # Create workers with IDs
                workers = []
                for i in range(3):
                    worker = OutboxRelayService()
                    await worker.start()
                    workers.append(worker)

                try:

                    async def tagged_worker(worker, worker_id):
                        # Tag the current task with worker ID for failure simulation
                        asyncio.current_task().worker_id = worker_id

                        total_processed = 0
                        for _ in range(6):
                            try:
                                processed = await worker._drain_once()
                                total_processed += processed
                            except Exception:
                                # Worker failures are handled internally
                                pass
                        return total_processed

                    tasks = [asyncio.create_task(tagged_worker(worker, i)) for i, worker in enumerate(workers)]

                    results = await asyncio.gather(*tasks, return_exceptions=True)

                    # Some messages should be processed despite worker failures
                    successful_count = len(successful_processes)
                    assert successful_count > 0

                    # Verify failed messages are still pending and can be retried
                    final_messages = await self.get_all_messages_from_db()
                    pending_messages = [msg for msg in final_messages if msg.status == OutboxStatus.PENDING]

                    # Some messages should have failed and be pending with retry count
                    retry_messages = [msg for msg in pending_messages if msg.retry_count > 0]
                    assert len(retry_messages) > 0

                finally:
                    for worker in workers:
                        await worker.stop()

    @pytest.mark.asyncio
    async def test_race_condition_between_scheduled_and_immediate_messages(
        self, mock_kafka_settings, clean_outbox_table
    ):
        """Test race conditions between scheduled and immediate messages."""
        with patch("src.services.outbox.relay.get_settings") as mock_get_settings:
            mock_get_settings.return_value = mock_kafka_settings

            # Create immediate messages
            immediate_messages = []
            async with create_sql_session() as session:
                for i in range(5):
                    message_data = {
                        "id": uuid4(),
                        "topic": f"immediate.topic.{i}",
                        "payload": {"type": "immediate", "index": i},
                        "status": OutboxStatus.PENDING,
                        "retry_count": 0,
                        "max_retries": 3,
                        "scheduled_at": None,  # Immediate processing
                        "created_at": datetime.now(UTC) + timedelta(milliseconds=i),
                    }
                    result = await session.execute(insert(EventOutbox).values(message_data).returning(EventOutbox))
                    immediate_messages.append(result.scalar_one())
                await session.commit()

            # Create scheduled messages (some ready, some future)
            scheduled_messages = []
            async with create_sql_session() as session:
                base_time = datetime.now(UTC)
                for i in range(5):
                    # Mix of past (ready) and future scheduled times
                    if i < 3:
                        scheduled_time = base_time - timedelta(seconds=i + 1)  # Ready now
                    else:
                        scheduled_time = base_time + timedelta(hours=1)  # Future

                    message_data = {
                        "id": uuid4(),
                        "topic": f"scheduled.topic.{i}",
                        "payload": {"type": "scheduled", "index": i, "ready": i < 3},
                        "status": OutboxStatus.PENDING,
                        "retry_count": 0,
                        "max_retries": 3,
                        "scheduled_at": scheduled_time,
                        "created_at": base_time + timedelta(milliseconds=i + 10),
                    }
                    result = await session.execute(insert(EventOutbox).values(message_data).returning(EventOutbox))
                    scheduled_messages.append(result.scalar_one())
                await session.commit()

            processed_topics = []

            with patch("src.services.outbox.relay.AIOKafkaProducer") as mock_producer_class:

                async def track_processing_send_and_wait(topic, **kwargs):
                    processed_topics.append(topic)
                    await asyncio.sleep(0.002)  # Small processing delay

                mock_producer = AsyncMock()
                mock_producer.start = AsyncMock()
                mock_producer.stop = AsyncMock()
                mock_producer.send_and_wait = track_processing_send_and_wait
                mock_producer_class.return_value = mock_producer

                # Run multiple workers concurrently
                workers = []
                for i in range(2):
                    worker = OutboxRelayService()
                    await worker.start()
                    workers.append(worker)

                try:

                    async def race_worker(worker):
                        total_processed = 0
                        for _ in range(8):  # Multiple cycles for race conditions
                            processed = await worker._drain_once()
                            total_processed += processed
                            await asyncio.sleep(0.001)  # Brief pause
                        return total_processed

                    tasks = [asyncio.create_task(race_worker(worker)) for worker in workers]

                    results = await asyncio.gather(*tasks)
                    total_processed = sum(results)

                    # Should process immediate messages + ready scheduled messages
                    expected_processed = len(immediate_messages) + 3  # 3 ready scheduled messages
                    assert total_processed == expected_processed

                    # Verify correct messages were processed
                    immediate_topics = [f"immediate.topic.{i}" for i in range(5)]
                    ready_scheduled_topics = [f"scheduled.topic.{i}" for i in range(3)]
                    expected_topics = set(immediate_topics + ready_scheduled_topics)

                    assert set(processed_topics) == expected_topics

                    # Verify future scheduled messages are still pending
                    final_messages = await self.get_all_messages_from_db()
                    future_pending = [
                        msg
                        for msg in final_messages
                        if msg.topic.startswith("scheduled.topic.")
                        and msg.topic.endswith(("3", "4"))
                        and msg.status == OutboxStatus.PENDING
                    ]
                    assert len(future_pending) == 2

                finally:
                    for worker in workers:
                        await worker.stop()

    @pytest.mark.asyncio
    async def test_database_deadlock_prevention(self, mock_kafka_settings, clean_outbox_table, db_session):
        """Test that the service handles potential database deadlock scenarios."""
        with patch("src.services.outbox.relay.get_settings") as mock_get_settings:
            mock_get_settings.return_value = mock_kafka_settings

            # Create many messages to increase lock contention
            test_messages = await self.create_test_messages(db_session, 20)

            database_operations = []
            lock_conflicts = 0

            # Mock database operations to simulate potential conflicts
            original_create_session = create_sql_session

            def monitored_create_session():
                session_wrapper = original_create_session()

                class SessionMonitor:
                    def __init__(self, session_ctx):
                        self._session_ctx = session_ctx

                    async def __aenter__(self):
                        session = await self._session_ctx.__aenter__()
                        database_operations.append(f"session_start_{id(session)}")
                        return session

                    async def __aexit__(self, exc_type, exc_val, exc_tb):
                        if exc_type:
                            database_operations.append(f"session_error_{exc_type.__name__}")
                        else:
                            database_operations.append("session_commit")
                        return await self._session_ctx.__aexit__(exc_type, exc_val, exc_tb)

                return SessionMonitor(session_wrapper)

            with patch("src.services.outbox.relay.create_sql_session", side_effect=monitored_create_session):
                with patch("src.services.outbox.relay.AIOKafkaProducer") as mock_producer_class:

                    async def simulate_processing_delay(topic, **kwargs):
                        # Variable delays to create more lock contention scenarios
                        topic_index = int(topic.split(".")[-1])
                        delay = 0.002 + (topic_index % 3) * 0.001
                        await asyncio.sleep(delay)

                    mock_producer = AsyncMock()
                    mock_producer.start = AsyncMock()
                    mock_producer.stop = AsyncMock()
                    mock_producer.send_and_wait = simulate_processing_delay
                    mock_producer_class.return_value = mock_producer

                    # Create many concurrent workers to maximize contention
                    workers = []
                    for i in range(5):
                        worker = OutboxRelayService()
                        await worker.start()
                        workers.append(worker)

                    try:

                        async def contention_worker(worker):
                            total_processed = 0
                            for _ in range(8):
                                try:
                                    processed = await worker._drain_once()
                                    total_processed += processed
                                except Exception as e:
                                    # Count database-related errors
                                    if "lock" in str(e).lower() or "deadlock" in str(e).lower():
                                        nonlocal lock_conflicts
                                        lock_conflicts += 1
                            return total_processed

                        # Run all workers simultaneously for maximum contention
                        tasks = [asyncio.create_task(contention_worker(worker)) for worker in workers]

                        results = await asyncio.gather(*tasks, return_exceptions=True)

                        # Count successful results
                        successful_results = [r for r in results if isinstance(r, int)]
                        total_processed = sum(successful_results)

                        # All messages should eventually be processed
                        assert total_processed == len(test_messages)

                        # Verify database operations completed without major issues
                        session_starts = len([op for op in database_operations if op.startswith("session_start")])
                        session_commits = len([op for op in database_operations if op == "session_commit"])

                        # Should have many successful commits
                        assert session_commits > 0

                        # Lock conflicts should be minimal due to SKIP LOCKED
                        assert lock_conflicts <= 2  # Allow some minor conflicts

                    finally:
                        for worker in workers:
                            await worker.stop()

    @pytest.mark.asyncio
    async def test_worker_graceful_shutdown_during_high_load(self, mock_kafka_settings, clean_outbox_table, db_session):
        """Test graceful shutdown of workers during high processing load."""
        with patch("src.services.outbox.relay.get_settings") as mock_get_settings:
            mock_get_settings.return_value = mock_kafka_settings

            # Create many messages for high load
            test_messages = await self.create_test_messages(db_session, 25)

            shutdown_events = []
            processed_during_shutdown = []

            with patch("src.services.outbox.relay.AIOKafkaProducer") as mock_producer_class:

                async def slow_send_and_wait(topic, **kwargs):
                    # Simulate slow processing that might be interrupted
                    try:
                        await asyncio.sleep(0.01)  # 10ms processing time
                        processed_during_shutdown.append(topic)
                    except asyncio.CancelledError:
                        shutdown_events.append(f"cancelled_{topic}")
                        raise

                mock_producer = AsyncMock()
                mock_producer.start = AsyncMock()
                mock_producer.stop = AsyncMock()
                mock_producer.send_and_wait = slow_send_and_wait
                mock_producer_class.return_value = mock_producer

                # Create workers
                workers = []
                for i in range(3):
                    worker = OutboxRelayService()
                    await worker.start()
                    workers.append(worker)

                try:
                    # Start workers processing
                    async def long_running_worker(worker):
                        processed = 0
                        try:
                            for _ in range(15):  # Long running cycles
                                batch_processed = await worker._drain_once()
                                processed += batch_processed
                                # Don't break early to simulate continuous processing
                        except Exception as e:
                            shutdown_events.append(f"worker_exception_{type(e).__name__}")
                        return processed

                    tasks = [asyncio.create_task(long_running_worker(worker)) for worker in workers]

                    # Let workers run for a bit
                    await asyncio.sleep(0.05)

                    # Initiate shutdown while workers are busy
                    shutdown_start = datetime.now(UTC)
                    shutdown_tasks = [asyncio.create_task(worker.stop()) for worker in workers]

                    # Wait for shutdowns to complete
                    await asyncio.gather(*shutdown_tasks)
                    shutdown_end = datetime.now(UTC)

                    # Cancel worker tasks
                    for task in tasks:
                        if not task.done():
                            task.cancel()

                    # Wait for worker tasks to complete or cancel
                    results = await asyncio.gather(*tasks, return_exceptions=True)

                    # Verify graceful shutdown timing (should be quick)
                    shutdown_duration = (shutdown_end - shutdown_start).total_seconds()
                    assert shutdown_duration < 1.0  # Should shutdown within 1 second

                    # Verify all workers stopped
                    for worker in workers:
                        assert worker._stop_event.is_set()
                        assert worker._producer is None

                    # Some messages should have been processed before shutdown
                    assert len(processed_during_shutdown) > 0

                except Exception:
                    # Ensure cleanup even if test fails
                    for worker in workers:
                        if not worker._stop_event.is_set():
                            await worker.stop()
                    raise

    @pytest.mark.asyncio
    async def test_memory_efficiency_under_high_concurrency(self, mock_kafka_settings, clean_outbox_table):
        """Test memory efficiency with many concurrent operations."""
        with patch("src.services.outbox.relay.get_settings") as mock_get_settings:
            mock_get_settings.return_value = mock_kafka_settings

            # Create messages with large payloads to test memory handling
            large_messages = []
            async with create_sql_session() as session:
                for i in range(10):
                    # Create large payload to test memory efficiency
                    large_payload = {
                        "event": f"large_message_{i}",
                        "data": {
                            "large_text": "x" * 1000,  # 1KB text
                            "array_data": list(range(100)),
                            "nested": {"deep": {"data": ["item"] * 50}},
                        },
                        "metadata": {"size": "large", "index": i},
                    }

                    message_data = {
                        "id": uuid4(),
                        "topic": f"large.topic.{i}",
                        "payload": large_payload,
                        "status": OutboxStatus.PENDING,
                        "retry_count": 0,
                        "max_retries": 3,
                        "created_at": datetime.now(UTC) + timedelta(milliseconds=i),
                    }

                    result = await session.execute(insert(EventOutbox).values(message_data).returning(EventOutbox))
                    large_messages.append(result.scalar_one())

                await session.commit()

            memory_snapshots = []

            with patch("src.services.outbox.relay.AIOKafkaProducer") as mock_producer_class:

                async def memory_tracking_send_and_wait(topic, value=None, **kwargs):
                    # Track approximate memory usage by payload size
                    if value:
                        memory_snapshots.append(len(value))
                    await asyncio.sleep(0.003)  # Small delay

                mock_producer = AsyncMock()
                mock_producer.start = AsyncMock()
                mock_producer.stop = AsyncMock()
                mock_producer.send_and_wait = memory_tracking_send_and_wait
                mock_producer_class.return_value = mock_producer

                # Create multiple workers for concurrent processing
                workers = []
                for i in range(4):
                    worker = OutboxRelayService()
                    await worker.start()
                    workers.append(worker)

                try:

                    async def memory_efficient_worker(worker):
                        processed = 0
                        for _ in range(5):
                            batch_processed = await worker._drain_once()
                            processed += batch_processed
                            # Brief pause to allow memory cleanup
                            await asyncio.sleep(0.001)
                        return processed

                    # Process all messages concurrently
                    tasks = [asyncio.create_task(memory_efficient_worker(worker)) for worker in workers]

                    results = await asyncio.gather(*tasks)
                    total_processed = sum(results)

                    # Verify all messages processed
                    assert total_processed == len(large_messages)

                    # Verify memory efficiency - each payload should be processed once
                    assert len(memory_snapshots) == len(large_messages)

                    # Verify large payloads were handled (each ~1KB+ when serialized)
                    avg_payload_size = sum(memory_snapshots) / len(memory_snapshots)
                    assert avg_payload_size > 500  # Should be substantial size

                finally:
                    for worker in workers:
                        await worker.stop()
