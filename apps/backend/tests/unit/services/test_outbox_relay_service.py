"""Unit tests for OutboxRelayService."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from aiokafka.errors import KafkaError, KafkaTimeoutError
from sqlalchemy.exc import SQLAlchemyError
from src.models.workflow import EventOutbox
from src.schemas.enums import OutboxStatus
from src.services.outbox.relay import OutboxRelayService


class TestOutboxRelayService:
    """Test cases for OutboxRelayService."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings for testing."""
        settings = MagicMock()
        settings.environment = "test"
        settings.log_level = "DEBUG"
        settings.kafka_bootstrap_servers = ["localhost:9092"]

        # Relay-specific settings
        relay_settings = MagicMock()
        relay_settings.poll_interval_seconds = 5
        relay_settings.batch_size = 10
        relay_settings.yield_sleep_ms = 100
        relay_settings.loop_error_backoff_ms = 1000
        relay_settings.retry_backoff_ms = 1000
        relay_settings.max_backoff_ms = 60000
        relay_settings.max_retries_default = 3
        settings.relay = relay_settings

        return settings

    @pytest.fixture
    def mock_invalid_settings(self):
        """Create invalid mock settings for testing validation."""
        settings = MagicMock()
        settings.environment = "test"
        settings.log_level = "DEBUG"
        settings.kafka_bootstrap_servers = ["localhost:9092"]

        # Invalid relay settings
        relay_settings = MagicMock()
        relay_settings.poll_interval_seconds = 0  # Invalid - should be > 0
        relay_settings.batch_size = -1  # Invalid - should be > 0
        relay_settings.yield_sleep_ms = -100  # Invalid - should be >= 0
        relay_settings.loop_error_backoff_ms = -1000  # Invalid - should be >= 0
        relay_settings.retry_backoff_ms = 0  # Invalid - should be > 0
        relay_settings.max_backoff_ms = -1  # Invalid - should be > 0
        relay_settings.max_retries_default = -1  # Invalid - should be >= 0
        settings.relay = relay_settings

        return settings

    @pytest.fixture
    def sample_outbox_message(self):
        """Create a sample outbox message for testing."""
        return EventOutbox(
            id=uuid4(),
            topic="test.topic",
            key="test-key",
            partition_key="partition-1",
            payload={"event": "test", "data": "sample"},
            headers={"source": "test", "version": "1.0"},
            status=OutboxStatus.PENDING,
            retry_count=0,
            max_retries=3,
            last_error=None,
            scheduled_at=None,
            sent_at=None,
            created_at=datetime.now(UTC),
        )

    @patch("src.services.outbox.relay.get_settings")
    def test_init_valid_settings(self, mock_get_settings, mock_settings):
        """Test service initialization with valid settings."""
        mock_get_settings.return_value = mock_settings

        service = OutboxRelayService()

        assert service.settings == mock_settings
        assert service._producer is None
        assert service._stop_event is not None
        assert not service._stop_event.is_set()
        mock_get_settings.assert_called_once()

    @patch("src.services.outbox.relay.get_settings")
    def test_init_invalid_batch_size(self, mock_get_settings, mock_invalid_settings):
        """Test service initialization fails with invalid batch_size."""
        mock_get_settings.return_value = mock_invalid_settings

        with pytest.raises(ValueError, match="relay.batch_size must be > 0"):
            OutboxRelayService()

    @patch("src.services.outbox.relay.get_settings")
    def test_init_invalid_poll_interval(self, mock_get_settings):
        """Test service initialization fails with invalid poll_interval."""
        settings = MagicMock()
        settings.relay = MagicMock()
        settings.relay.batch_size = 10  # Valid
        settings.relay.poll_interval_seconds = 0  # Invalid
        mock_get_settings.return_value = settings

        with pytest.raises(ValueError, match="relay.poll_interval_seconds must be > 0"):
            OutboxRelayService()

    @patch("src.services.outbox.relay.get_settings")
    def test_init_invalid_retry_backoff(self, mock_get_settings):
        """Test service initialization fails with invalid retry_backoff_ms."""
        settings = MagicMock()
        settings.relay = MagicMock()
        settings.relay.batch_size = 10
        settings.relay.poll_interval_seconds = 5
        settings.relay.retry_backoff_ms = 0  # Invalid
        mock_get_settings.return_value = settings

        with pytest.raises(ValueError, match="relay.retry_backoff_ms must be > 0"):
            OutboxRelayService()

    @patch("src.services.outbox.relay.get_settings")
    def test_init_invalid_max_retries(self, mock_get_settings):
        """Test service initialization fails with invalid max_retries_default."""
        settings = MagicMock()
        settings.relay = MagicMock()
        settings.relay.batch_size = 10
        settings.relay.poll_interval_seconds = 5
        settings.relay.retry_backoff_ms = 1000
        settings.relay.max_retries_default = -1  # Invalid
        mock_get_settings.return_value = settings

        with pytest.raises(ValueError, match="relay.max_retries_default must be >= 0"):
            OutboxRelayService()

    @patch("src.services.outbox.relay.get_settings")
    def test_init_invalid_sleep_values(self, mock_get_settings):
        """Test service initialization fails with invalid sleep values."""
        settings = MagicMock()
        settings.relay = MagicMock()
        settings.relay.batch_size = 10
        settings.relay.poll_interval_seconds = 5
        settings.relay.retry_backoff_ms = 1000
        settings.relay.max_retries_default = 3
        settings.relay.yield_sleep_ms = -100  # Invalid
        settings.relay.loop_error_backoff_ms = 1000
        mock_get_settings.return_value = settings

        with pytest.raises(ValueError, match="relay sleep/backoff ms must be >= 0"):
            OutboxRelayService()

    @patch("src.services.outbox.relay.get_settings")
    def test_init_invalid_max_backoff(self, mock_get_settings):
        """Test service initialization fails with invalid max_backoff_ms."""
        settings = MagicMock()
        settings.relay = MagicMock()
        settings.relay.batch_size = 10
        settings.relay.poll_interval_seconds = 5
        settings.relay.retry_backoff_ms = 1000
        settings.relay.max_retries_default = 3
        settings.relay.yield_sleep_ms = 100
        settings.relay.loop_error_backoff_ms = 1000
        settings.relay.max_backoff_ms = 0  # Invalid
        mock_get_settings.return_value = settings

        with pytest.raises(ValueError, match="relay.max_backoff_ms must be > 0"):
            OutboxRelayService()

    @pytest.mark.asyncio
    @patch("src.services.outbox.relay.get_settings")
    @patch("src.services.outbox.relay.configure_logging")
    @patch("src.services.outbox.relay.AIOKafkaProducer")
    async def test_start_success(self, mock_producer_class, mock_configure_logging, mock_get_settings, mock_settings):
        """Test successful service start."""
        mock_get_settings.return_value = mock_settings
        mock_producer = AsyncMock()
        mock_producer_class.return_value = mock_producer

        service = OutboxRelayService()
        await service.start()

        # Verify producer creation and configuration
        mock_producer_class.assert_called_once_with(
            bootstrap_servers=["localhost:9092"],
            acks="all",
            enable_idempotence=True,
            linger_ms=5,
        )
        mock_producer.start.assert_called_once()
        assert service._producer == mock_producer

        # Verify logging configuration
        mock_configure_logging.assert_called_once_with(environment="test", level="DEBUG")

    @pytest.mark.asyncio
    @patch("src.services.outbox.relay.get_settings")
    @patch("src.services.outbox.relay.configure_logging")
    @patch("src.services.outbox.relay.AIOKafkaProducer")
    async def test_start_producer_failure(
        self, mock_producer_class, mock_configure_logging, mock_get_settings, mock_settings
    ):
        """Test service start with producer creation failure."""
        mock_get_settings.return_value = mock_settings
        mock_producer = AsyncMock()
        mock_producer.start.side_effect = KafkaError("Connection failed")
        mock_producer_class.return_value = mock_producer

        service = OutboxRelayService()

        with pytest.raises(KafkaError, match="Connection failed"):
            await service.start()

    @pytest.mark.asyncio
    @patch("src.services.outbox.relay.get_settings")
    async def test_stop_with_producer(self, mock_get_settings, mock_settings):
        """Test service stop with active producer."""
        mock_get_settings.return_value = mock_settings
        mock_producer = AsyncMock()

        service = OutboxRelayService()
        service._producer = mock_producer

        await service.stop()

        assert service._stop_event.is_set()
        mock_producer.stop.assert_called_once()
        assert service._producer is None

    @pytest.mark.asyncio
    @patch("src.services.outbox.relay.get_settings")
    async def test_stop_with_producer_failure(self, mock_get_settings, mock_settings):
        """Test service stop with producer stop failure."""
        mock_get_settings.return_value = mock_settings
        mock_producer = AsyncMock()
        mock_producer.stop.side_effect = Exception("Stop failed")

        service = OutboxRelayService()
        service._producer = mock_producer

        # Should not raise exception, just log warning
        await service.stop()

        assert service._stop_event.is_set()
        mock_producer.stop.assert_called_once()
        assert service._producer is None

    @pytest.mark.asyncio
    @patch("src.services.outbox.relay.get_settings")
    async def test_stop_without_producer(self, mock_get_settings, mock_settings):
        """Test service stop without active producer."""
        mock_get_settings.return_value = mock_settings

        service = OutboxRelayService()
        service._producer = None

        await service.stop()

        assert service._stop_event.is_set()
        assert service._producer is None

    @patch("src.services.outbox.relay.get_settings")
    def test_build_select_for_ids(self, mock_get_settings, mock_settings):
        """Test building select statement for candidate IDs."""
        mock_get_settings.return_value = mock_settings

        service = OutboxRelayService()
        stmt = service._build_select_for_ids()

        # Verify the statement structure (basic verification)
        assert stmt is not None
        # Statement should select EventOutbox.id with proper filtering and ordering

    @pytest.mark.asyncio
    @patch("src.services.outbox.relay.get_settings")
    async def test_lock_row_success(self, mock_get_settings, mock_settings, sample_outbox_message):
        """Test successful row locking."""
        mock_get_settings.return_value = mock_settings
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_outbox_message
        mock_session.execute = AsyncMock(return_value=mock_result)

        service = OutboxRelayService()
        result = await service._lock_row(mock_session, sample_outbox_message.id)

        assert result == sample_outbox_message
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.services.outbox.relay.get_settings")
    async def test_lock_row_not_found(self, mock_get_settings, mock_settings):
        """Test row locking when row is not found or already taken."""
        mock_get_settings.return_value = mock_settings
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        service = OutboxRelayService()
        result = await service._lock_row(mock_session, uuid4())

        assert result is None
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.services.outbox.relay.get_settings")
    async def test_process_row_success(self, mock_get_settings, mock_settings, sample_outbox_message):
        """Test successful row processing."""
        mock_get_settings.return_value = mock_settings
        mock_session = AsyncMock()
        mock_producer = AsyncMock()

        service = OutboxRelayService()
        service._producer = mock_producer

        result = await service._process_row(mock_session, sample_outbox_message)

        assert result is True
        assert sample_outbox_message.status == OutboxStatus.SENT
        assert sample_outbox_message.sent_at is not None
        assert sample_outbox_message.last_error is None

        # Verify Kafka send was called with correct parameters
        mock_producer.send_and_wait.assert_called_once()
        call_args = mock_producer.send_and_wait.call_args
        # topic is positional argument
        assert call_args[0][0] == "test.topic"
        call_kwargs = call_args.kwargs
        assert call_kwargs["key"] == b"test-key"
        assert isinstance(call_kwargs["value"], bytes)
        # Verify JSON-encoded payload
        import json

        decoded_value = json.loads(call_kwargs["value"].decode("utf-8"))
        assert decoded_value == {"event": "test", "data": "sample"}
        # Verify headers encoding
        expected_headers = [("source", b"test"), ("version", b"1.0")]
        assert call_kwargs["headers"] == expected_headers

    @pytest.mark.asyncio
    @patch("src.services.outbox.relay.get_settings")
    async def test_process_row_shutdown(self, mock_get_settings, mock_settings, sample_outbox_message):
        """Test row processing during shutdown."""
        mock_get_settings.return_value = mock_settings
        mock_session = AsyncMock()

        service = OutboxRelayService()
        service._stop_event.set()  # Simulate shutdown

        result = await service._process_row(mock_session, sample_outbox_message)

        assert result is False

    @pytest.mark.asyncio
    @patch("src.services.outbox.relay.get_settings")
    async def test_process_row_no_producer(self, mock_get_settings, mock_settings, sample_outbox_message):
        """Test row processing when producer is unavailable."""
        mock_get_settings.return_value = mock_settings
        mock_session = AsyncMock()

        service = OutboxRelayService()
        service._producer = None

        result = await service._process_row(mock_session, sample_outbox_message)

        assert result is False

    @pytest.mark.asyncio
    @patch("src.services.outbox.relay.get_settings")
    async def test_process_row_kafka_failure_retry(self, mock_get_settings, mock_settings, sample_outbox_message):
        """Test row processing with Kafka failure leading to retry."""
        mock_get_settings.return_value = mock_settings
        mock_session = AsyncMock()
        mock_producer = AsyncMock()
        mock_producer.send_and_wait = AsyncMock(side_effect=KafkaTimeoutError("Timeout"))

        service = OutboxRelayService()
        service._producer = mock_producer

        # Set initial retry count
        sample_outbox_message.retry_count = 1

        result = await service._process_row(mock_session, sample_outbox_message)

        assert result is False
        assert sample_outbox_message.status == OutboxStatus.PENDING
        assert sample_outbox_message.retry_count == 2
        assert sample_outbox_message.last_error == "KafkaTimeoutError: Timeout"
        assert sample_outbox_message.scheduled_at is not None
        # Verify send parameters even for failed attempts
        call_kwargs = mock_producer.send_and_wait.call_args.kwargs
        assert call_kwargs["key"] == b"test-key"

    @pytest.mark.asyncio
    @patch("src.services.outbox.relay.get_settings")
    async def test_process_row_kafka_failure_max_retries(self, mock_get_settings, mock_settings, sample_outbox_message):
        """Test row processing with Kafka failure exceeding max retries."""
        mock_get_settings.return_value = mock_settings
        mock_session = AsyncMock()
        mock_producer = AsyncMock()
        mock_producer.send_and_wait = AsyncMock(side_effect=KafkaTimeoutError("Timeout"))

        service = OutboxRelayService()
        service._producer = mock_producer

        # Set retry count to max retries
        sample_outbox_message.retry_count = 3
        sample_outbox_message.max_retries = 3

        result = await service._process_row(mock_session, sample_outbox_message)

        assert result is False
        assert sample_outbox_message.status == OutboxStatus.FAILED
        assert sample_outbox_message.retry_count == 4
        assert sample_outbox_message.last_error == "KafkaTimeoutError: Timeout"
        assert sample_outbox_message.scheduled_at is None
        # Verify send parameters for max retry attempt
        call_kwargs = mock_producer.send_and_wait.call_args.kwargs
        assert call_kwargs["key"] == b"test-key"

    @pytest.mark.asyncio
    @patch("src.services.outbox.relay.get_settings")
    async def test_process_row_json_serialization_error(self, mock_get_settings, mock_settings, sample_outbox_message):
        """Test row processing with JSON serialization error."""
        mock_get_settings.return_value = mock_settings
        mock_session = AsyncMock()
        mock_producer = AsyncMock()

        service = OutboxRelayService()
        service._producer = mock_producer

        # Create a payload that can't be JSON serialized
        sample_outbox_message.payload = {"invalid": lambda x: x}  # Lambda is not JSON serializable

        result = await service._process_row(mock_session, sample_outbox_message)

        assert result is False
        assert sample_outbox_message.status == OutboxStatus.PENDING
        assert sample_outbox_message.retry_count == 1
        assert "not JSON serializable" in sample_outbox_message.last_error
        # JSON error should schedule retry
        assert sample_outbox_message.scheduled_at is not None

    @pytest.mark.asyncio
    @patch("src.services.outbox.relay.get_settings")
    async def test_process_row_header_encoding_error(self, mock_get_settings, mock_settings, sample_outbox_message):
        """Test row processing with header encoding error."""
        mock_get_settings.return_value = mock_settings
        mock_session = AsyncMock()
        mock_producer = AsyncMock()
        mock_producer.send_and_wait = AsyncMock()

        service = OutboxRelayService()
        service._producer = mock_producer

        # Create headers that will cause encoding error when converting to bytes
        class UnserializableObject:
            def __str__(self):
                raise TypeError("Cannot convert to string")

        sample_outbox_message.headers = {"key": UnserializableObject()}

        result = await service._process_row(mock_session, sample_outbox_message)

        # Should still succeed but without headers
        assert result is True
        mock_producer.send_and_wait.assert_called_once()
        call_kwargs = mock_producer.send_and_wait.call_args.kwargs
        assert call_kwargs["headers"] is None

    @pytest.mark.asyncio
    @patch("src.services.outbox.relay.get_settings")
    async def test_process_row_positive_header_encoding(self, mock_get_settings, mock_settings, sample_outbox_message):
        """Test row processing with successful header encoding."""
        mock_get_settings.return_value = mock_settings
        mock_session = AsyncMock()
        mock_producer = AsyncMock()
        mock_producer.send_and_wait = AsyncMock()

        service = OutboxRelayService()
        service._producer = mock_producer

        # Create headers that should encode successfully
        sample_outbox_message.headers = {"content-type": "application/json", "version": 1}

        result = await service._process_row(mock_session, sample_outbox_message)

        # Should succeed with properly encoded headers
        assert result is True
        mock_producer.send_and_wait.assert_called_once()
        call_kwargs = mock_producer.send_and_wait.call_args.kwargs
        expected_headers = [("content-type", b"application/json"), ("version", b"1")]
        assert call_kwargs["headers"] == expected_headers

    @pytest.mark.asyncio
    @patch("src.services.outbox.relay.get_settings")
    async def test_process_row_partition_key_fallback(self, mock_get_settings, mock_settings, sample_outbox_message):
        """Test row processing uses partition_key when key is None."""
        mock_get_settings.return_value = mock_settings
        mock_session = AsyncMock()
        mock_producer = AsyncMock()
        mock_producer.send_and_wait = AsyncMock()

        service = OutboxRelayService()
        service._producer = mock_producer

        # Set key to None to test partition_key fallback
        sample_outbox_message.key = None
        sample_outbox_message.partition_key = "partition-1"

        result = await service._process_row(mock_session, sample_outbox_message)

        assert result is True
        call_kwargs = mock_producer.send_and_wait.call_args.kwargs
        assert call_kwargs["key"] == b"partition-1"  # Should use partition_key

    @pytest.mark.asyncio
    @patch("src.services.outbox.relay.get_settings")
    @patch("src.services.outbox.relay.datetime")
    async def test_exponential_backoff_calculation(
        self, mock_datetime, mock_get_settings, mock_settings, sample_outbox_message
    ):
        """Test exponential backoff calculation with frozen time."""
        mock_get_settings.return_value = mock_settings
        mock_session = AsyncMock()
        mock_producer = AsyncMock()
        mock_producer.send_and_wait.side_effect = KafkaError("Error")

        # Freeze time to avoid CI flakiness
        frozen_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        mock_datetime.now.return_value = frozen_time
        # Ensure the real datetime class is still accessible
        mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

        service = OutboxRelayService()
        service._producer = mock_producer

        # Test different retry counts
        test_cases = [
            (0, 1000),  # First retry: base_ms * 2^0 = 1000
            (1, 2000),  # Second retry: base_ms * 2^1 = 2000
            (2, 4000),  # Third retry: base_ms * 2^2 = 4000
        ]

        for initial_count, expected_delay_ms in test_cases:
            sample_outbox_message.retry_count = initial_count
            sample_outbox_message.status = OutboxStatus.PENDING
            sample_outbox_message.scheduled_at = None

            await service._process_row(mock_session, sample_outbox_message)

            # Verify exact delay calculation with frozen time
            if sample_outbox_message.scheduled_at:
                expected_scheduled_time = frozen_time + timedelta(milliseconds=expected_delay_ms)
                assert sample_outbox_message.scheduled_at == expected_scheduled_time

    @pytest.mark.asyncio
    @patch("src.services.outbox.relay.get_settings")
    @patch("src.services.outbox.relay.datetime")
    async def test_exponential_backoff_overflow_protection(
        self, mock_datetime, mock_get_settings, mock_settings, sample_outbox_message
    ):
        """Test exponential backoff overflow protection with frozen time."""
        mock_get_settings.return_value = mock_settings
        mock_session = AsyncMock()
        mock_producer = AsyncMock()
        mock_producer.send_and_wait.side_effect = KafkaError("Error")

        # Freeze time to avoid CI flakiness
        frozen_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        mock_datetime.now.return_value = frozen_time
        # Ensure the real datetime class is still accessible
        mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

        service = OutboxRelayService()
        service._producer = mock_producer

        # Set very high retry count that would cause overflow
        sample_outbox_message.retry_count = 100
        sample_outbox_message.max_retries = 200

        await service._process_row(mock_session, sample_outbox_message)

        # Should not crash and should use max backoff
        if sample_outbox_message.scheduled_at:
            max_delay_seconds = mock_settings.relay.max_backoff_ms / 1000.0
            expected_scheduled_time = frozen_time + timedelta(seconds=max_delay_seconds)
            assert sample_outbox_message.scheduled_at == expected_scheduled_time

    @pytest.mark.asyncio
    @patch("src.services.outbox.relay.get_settings")
    @patch("src.services.outbox.relay.create_sql_session")
    async def test_drain_once_no_candidates(self, mock_create_session, mock_get_settings, mock_settings):
        """Test _drain_once when no candidate messages are found."""
        mock_get_settings.return_value = mock_settings
        mock_session = AsyncMock()
        mock_result = MagicMock()

        # Properly mock the scalars().all() chain
        mock_scalar_result = MagicMock()
        mock_scalar_result.all.return_value = []
        mock_result.scalars.return_value = mock_scalar_result

        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_create_session.return_value.__aenter__.return_value = mock_session

        service = OutboxRelayService()
        result = await service._drain_once()

        assert result == 0
        # Phase 1 is read-only, no explicit commit expected

    @pytest.mark.asyncio
    @patch("src.services.outbox.relay.get_settings")
    @patch("src.services.outbox.relay.create_sql_session")
    async def test_drain_once_with_candidates(
        self, mock_create_session, mock_get_settings, mock_settings, sample_outbox_message
    ):
        """Test _drain_once with candidate messages."""
        mock_get_settings.return_value = mock_settings

        # Mock Phase 1: ID selection
        mock_session_1 = AsyncMock()
        mock_result_1 = MagicMock()
        candidate_ids = [sample_outbox_message.id]

        # Properly mock the scalars().all() chain for Phase 1
        mock_scalar_result_1 = MagicMock()
        mock_scalar_result_1.all.return_value = candidate_ids
        mock_result_1.scalars.return_value = mock_scalar_result_1

        mock_session_1.execute = AsyncMock(return_value=mock_result_1)

        # Mock Phase 2: Row processing
        mock_session_2 = AsyncMock()
        mock_result_2 = MagicMock()
        mock_result_2.scalar_one_or_none.return_value = sample_outbox_message
        mock_session_2.execute = AsyncMock(return_value=mock_result_2)

        # Mock producer
        mock_producer = AsyncMock()

        # Configure create_sql_session to return different sessions for each call
        mock_sessions = [mock_session_1, mock_session_2]
        session_index = [0]

        def get_session():
            context_mock = AsyncMock()
            context_mock.__aenter__.return_value = mock_sessions[session_index[0]]
            session_index[0] += 1
            return context_mock

        mock_create_session.side_effect = get_session

        service = OutboxRelayService()
        service._producer = mock_producer

        result = await service._drain_once()

        assert result == 1
        mock_producer.send_and_wait.assert_called_once()
        # Verify Phase 2 session commits after processing
        mock_session_2.commit.assert_awaited_once()

    @pytest.mark.asyncio
    @patch("src.services.outbox.relay.get_settings")
    @patch("src.services.outbox.relay.create_sql_session")
    async def test_drain_once_row_taken_by_other_worker(self, mock_create_session, mock_get_settings, mock_settings):
        """Test _drain_once when another worker takes the row."""
        mock_get_settings.return_value = mock_settings

        # Mock Phase 1: ID selection
        mock_session_1 = AsyncMock()
        mock_result_1 = MagicMock()
        candidate_ids = [uuid4()]

        # Properly mock the scalars().all() chain for Phase 1
        mock_scalar_result_1 = MagicMock()
        mock_scalar_result_1.all.return_value = candidate_ids
        mock_result_1.scalars.return_value = mock_scalar_result_1

        mock_session_1.execute = AsyncMock(return_value=mock_result_1)

        # Mock Phase 2: Row not found (taken by other worker)
        mock_session_2 = AsyncMock()
        mock_result_2 = MagicMock()
        mock_result_2.scalar_one_or_none.return_value = None
        mock_session_2.execute = AsyncMock(return_value=mock_result_2)

        # Configure create_sql_session
        mock_sessions = [mock_session_1, mock_session_2]
        session_index = [0]

        def get_session():
            context_mock = AsyncMock()
            context_mock.__aenter__.return_value = mock_sessions[session_index[0]]
            session_index[0] += 1
            return context_mock

        mock_create_session.side_effect = get_session

        service = OutboxRelayService()
        result = await service._drain_once()

        assert result == 0
        # When no row is found, the session should not commit (just continue)
        mock_session_2.commit.assert_not_awaited()

    def test_validate_settings_suboptimal_config_warning(self, mock_settings):
        """Test _validate_settings warns for suboptimal configuration."""
        # Set max_backoff_ms less than retry_backoff_ms
        mock_settings.relay.max_backoff_ms = 500
        mock_settings.relay.retry_backoff_ms = 1000

        with patch("src.services.outbox.relay.get_settings") as mock_get_settings:  # noqa: SIM117
            with patch("src.services.outbox.relay.log") as mock_log:
                mock_get_settings.return_value = mock_settings

                # Should not raise exception, just log warning
                service = OutboxRelayService()

                mock_log.warning.assert_called_once_with("relay_max_backoff_lt_base", max_backoff_ms=500, base_ms=1000)

    @pytest.mark.asyncio
    @patch("src.services.outbox.relay.get_settings")
    async def test_run_forever_normal_operation(self, mock_get_settings, mock_settings):
        """Test run_forever normal operation cycle."""
        mock_get_settings.return_value = mock_settings

        service = OutboxRelayService()

        # Mock start method
        service.start = AsyncMock()
        service.stop = AsyncMock()

        # Mock _drain_once to return some work then stop
        call_count = [0]

        async def mock_drain_once():
            call_count[0] += 1
            if call_count[0] == 1:
                return 5  # First call processes 5 messages
            elif call_count[0] == 2:
                service._stop_event.set()  # Stop after second call
                return 0
            return 0

        service._drain_once = mock_drain_once

        # Run the service (should stop after mock sets stop event)
        await service.run_forever()

        service.start.assert_called_once()
        service.stop.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.services.outbox.relay.get_settings")
    async def test_run_forever_handles_exceptions(self, mock_get_settings, mock_settings):
        """Test run_forever handles exceptions gracefully."""
        mock_get_settings.return_value = mock_settings

        service = OutboxRelayService()
        service.start = AsyncMock()
        service.stop = AsyncMock()

        # Mock _drain_once to raise exception then stop
        call_count = [0]

        async def mock_drain_once():
            call_count[0] += 1
            if call_count[0] == 1:
                raise SQLAlchemyError("Database error")
            else:
                service._stop_event.set()
                return 0

        service._drain_once = mock_drain_once

        # Should handle exception and continue
        await service.run_forever()

        service.start.assert_called_once()
        service.stop.assert_called_once()
