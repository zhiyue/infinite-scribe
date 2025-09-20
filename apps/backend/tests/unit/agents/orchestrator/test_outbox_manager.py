"""Unit tests for OutboxManager and its components.

Tests the domain event persistence and capability task enqueueing functionality
with proper isolation and mocking of database dependencies.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from src.agents.orchestrator.outbox_manager import (
    CapabilityTaskEnqueuer,
    DomainEventCreator,
    DomainEventIdempotencyChecker,
    OutboxEntryCreator,
    OutboxManager,
)
from src.models.event import DomainEvent
from src.models.workflow import EventOutbox
from src.schemas.enums import OutboxStatus


class TestDomainEventIdempotencyChecker:
    """Tests for domain event idempotency validation."""

    @pytest.mark.asyncio
    async def test_check_existing_domain_event_found(self):
        """Test finding existing domain event by correlation_id and event_type."""
        # Arrange
        correlation_id = str(uuid4())
        evt_type = "Genesis.Character.Requested"
        existing_event = DomainEvent(
            event_id=uuid4(),
            event_type=evt_type,
            aggregate_type="Genesis",
            aggregate_id="session-123",
            payload={"test": "data"},
            correlation_id=UUID(correlation_id),
        )

        mock_session = AsyncMock()
        mock_session.add = MagicMock()  # Make synchronous
        mock_session.scalar.return_value = existing_event

        # Act
        result = await DomainEventIdempotencyChecker.check_existing_domain_event(
            correlation_id, evt_type, mock_session
        )

        # Assert
        assert result == existing_event
        mock_session.scalar.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_existing_domain_event_not_found(self):
        """Test when no existing domain event is found."""
        # Arrange
        correlation_id = str(uuid4())
        evt_type = "Genesis.Character.Requested"

        mock_session = AsyncMock()
        mock_session.add = MagicMock()  # Make synchronous
        mock_session.scalar.return_value = None

        # Act
        result = await DomainEventIdempotencyChecker.check_existing_domain_event(
            correlation_id, evt_type, mock_session
        )

        # Assert
        assert result is None
        mock_session.scalar.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_existing_domain_event_invalid_uuid(self):
        """Test handling of invalid UUID correlation_id."""
        # Arrange
        correlation_id = "invalid-uuid"
        evt_type = "Genesis.Character.Requested"
        mock_session = AsyncMock()
        mock_session.add = MagicMock()  # Make synchronous

        # Act
        result = await DomainEventIdempotencyChecker.check_existing_domain_event(
            correlation_id, evt_type, mock_session
        )

        # Assert
        assert result is None  # Should return None for invalid UUID


class TestDomainEventCreator:
    """Tests for domain event creation logic."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_logger = MagicMock()
        self.creator = DomainEventCreator(self.mock_logger)

    @pytest.mark.asyncio
    @patch("src.agents.orchestrator.outbox_manager.build_event_type")
    @patch("src.agents.orchestrator.outbox_manager.get_aggregate_type")
    async def test_create_new_domain_event(self, mock_get_aggregate_type, mock_build_event_type):
        """Test creating a new domain event when none exists."""
        # Arrange
        mock_build_event_type.return_value = "Genesis.Character.Requested"
        mock_get_aggregate_type.return_value = "Genesis"

        scope_type = "GENESIS"
        session_id = "session-123"
        event_action = "Character.Requested"
        payload = {"character_type": "hero"}
        correlation_id = str(uuid4())
        causation_id = str(uuid4())

        mock_session = AsyncMock()
        mock_session.add = MagicMock()  # Make synchronous
        mock_session.add = MagicMock()  # Make synchronous
        mock_session.flush = AsyncMock()

        # Mock idempotency check to return None (no existing event)
        self.creator.idempotency_checker.check_existing_domain_event = AsyncMock(return_value=None)

        # Act
        result = await self.creator.create_or_get_domain_event(
            scope_type, session_id, event_action, payload, correlation_id, causation_id, mock_session
        )

        # Assert
        assert isinstance(result, DomainEvent)
        assert result.event_type == "Genesis.Character.Requested"
        assert result.aggregate_type == "Genesis"
        assert result.aggregate_id == session_id
        assert result.payload == payload
        assert result.correlation_id == UUID(correlation_id)
        assert result.causation_id == UUID(causation_id)
        assert result.event_metadata == {"source": "orchestrator"}

        mock_session.add.assert_called_once_with(result)
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.agents.orchestrator.outbox_manager.build_event_type")
    @patch("src.agents.orchestrator.outbox_manager.get_aggregate_type")
    async def test_return_existing_domain_event(self, mock_get_aggregate_type, mock_build_event_type):
        """Test returning existing domain event when found."""
        # Arrange
        mock_build_event_type.return_value = "Genesis.Character.Requested"
        mock_get_aggregate_type.return_value = "Genesis"

        scope_type = "GENESIS"
        session_id = "session-123"
        event_action = "Character.Requested"
        payload = {"character_type": "hero"}
        correlation_id = str(uuid4())
        causation_id = str(uuid4())

        existing_event = DomainEvent(
            event_id=uuid4(),
            event_type="Genesis.Character.Requested",
            aggregate_type="Genesis",
            aggregate_id=session_id,
            payload=payload,
            correlation_id=UUID(correlation_id),
        )

        mock_session = AsyncMock()
        mock_session.add = MagicMock()  # Make synchronous

        # Mock idempotency check to return existing event
        self.creator.idempotency_checker.check_existing_domain_event = AsyncMock(return_value=existing_event)

        # Act
        result = await self.creator.create_or_get_domain_event(
            scope_type, session_id, event_action, payload, correlation_id, causation_id, mock_session
        )

        # Assert
        assert result == existing_event
        mock_session.add.assert_not_called()
        mock_session.flush.assert_not_called()


class TestOutboxEntryCreator:
    """Tests for outbox entry creation logic."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_logger = MagicMock()
        self.creator = OutboxEntryCreator(self.mock_logger)

    @pytest.mark.asyncio
    @patch("src.agents.orchestrator.outbox_manager.get_domain_topic")
    async def test_create_new_outbox_entry(self, mock_get_domain_topic):
        """Test creating a new outbox entry when none exists."""
        # Arrange
        mock_get_domain_topic.return_value = "genesis.domain.events"

        domain_event = DomainEvent(
            event_id=uuid4(),
            event_type="Genesis.Character.Requested",
            aggregate_type="Genesis",
            aggregate_id="session-123",
            payload={"character_type": "hero"},
            correlation_id=uuid4(),
        )

        scope_type = "GENESIS"
        session_id = "session-123"
        correlation_id = str(uuid4())

        mock_session = AsyncMock()
        mock_session.add = MagicMock()  # Make synchronous
        mock_session.scalar.return_value = None  # No existing outbox entry

        # Act
        result = await self.creator.create_or_get_outbox_entry(
            domain_event, scope_type, session_id, correlation_id, mock_session
        )

        # Assert
        assert isinstance(result, EventOutbox)
        assert result.id == domain_event.event_id
        assert result.topic == "genesis.domain.events"
        assert result.key == session_id
        assert result.partition_key == session_id
        assert result.status == OutboxStatus.PENDING

        # Verify payload structure
        expected_payload = {
            "event_id": str(domain_event.event_id),
            "event_type": domain_event.event_type,
            "aggregate_type": domain_event.aggregate_type,
            "aggregate_id": domain_event.aggregate_id,
            "metadata": domain_event.event_metadata or {},
            "character_type": "hero",  # Payload should be flattened
        }
        assert result.payload == expected_payload

        mock_session.add.assert_called_once_with(result)

    @pytest.mark.asyncio
    @patch("src.agents.orchestrator.outbox_manager.get_domain_topic")
    async def test_return_existing_outbox_entry(self, mock_get_domain_topic):
        """Test returning existing outbox entry when found."""
        # Arrange
        mock_get_domain_topic.return_value = "genesis.domain.events"

        domain_event = DomainEvent(
            event_id=uuid4(),
            event_type="Genesis.Character.Requested",
            aggregate_type="Genesis",
            aggregate_id="session-123",
            payload={"character_type": "hero"},
        )

        existing_outbox = EventOutbox(
            id=domain_event.event_id,
            topic="genesis.domain.events",
            key="session-123",
            partition_key="session-123",
            payload={"test": "data"},
            status=OutboxStatus.PENDING,
        )

        scope_type = "GENESIS"
        session_id = "session-123"
        correlation_id = str(uuid4())

        mock_session = AsyncMock()
        mock_session.add = MagicMock()  # Make synchronous
        mock_session.scalar.return_value = existing_outbox

        # Act
        result = await self.creator.create_or_get_outbox_entry(
            domain_event, scope_type, session_id, correlation_id, mock_session
        )

        # Assert
        assert result == existing_outbox
        mock_session.add.assert_not_called()


class TestCapabilityTaskEnqueuer:
    """Tests for capability task enqueueing logic."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_logger = MagicMock()
        self.agent_name = "orchestrator"
        self.enqueuer = CapabilityTaskEnqueuer(self.mock_logger, self.agent_name)

    @pytest.mark.asyncio
    @patch("src.agents.orchestrator.outbox_manager.encode_message")
    @patch("src.agents.orchestrator.outbox_manager.create_sql_session")
    async def test_enqueue_capability_task_success(self, mock_create_session, mock_encode_message):
        """Test successful capability task enqueueing."""
        # Arrange
        capability_message = {
            "type": "Character.Design.GenerationRequested",
            "session_id": "session-123",
            "input": {"character_type": "hero"},
            "_topic": "genesis.character.tasks",
            "_key": "session-123",
        }
        correlation_id = str(uuid4())

        mock_envelope = {
            "id": "msg-123",
            "type": "Character.Design.GenerationRequested",
            "version": 1,
            "data": {"session_id": "session-123", "input": {"character_type": "hero"}},
        }
        mock_encode_message.return_value = mock_envelope

        mock_session = AsyncMock()
        mock_session.add = MagicMock()  # Make synchronous
        mock_create_session.return_value.__aenter__.return_value = mock_session

        # Act
        await self.enqueuer.enqueue_capability_task(capability_message, correlation_id)

        # Assert
        mock_encode_message.assert_called_once()
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()

        # Verify the outbox entry was created correctly
        added_outbox = mock_session.add.call_args[0][0]
        assert isinstance(added_outbox, EventOutbox)
        assert added_outbox.topic == "genesis.character.tasks"
        assert added_outbox.key == "session-123"
        assert added_outbox.payload == mock_envelope
        assert added_outbox.status == OutboxStatus.PENDING

    @pytest.mark.asyncio
    async def test_enqueue_capability_task_missing_topic(self):
        """Test handling of capability message without topic."""
        # Arrange
        capability_message = {
            "type": "Character.Design.GenerationRequested",
            "session_id": "session-123",
            "input": {"character_type": "hero"},
            # Missing _topic
        }
        correlation_id = str(uuid4())

        # Act
        await self.enqueuer.enqueue_capability_task(capability_message, correlation_id)

        # Assert
        self.mock_logger.warning.assert_called_once_with(
            "capability_task_enqueue_skipped", reason="missing_topic", msg=capability_message
        )


class TestOutboxManager:
    """Tests for the unified outbox management interface."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_logger = MagicMock()
        self.agent_name = "orchestrator"
        self.manager = OutboxManager(self.mock_logger, self.agent_name)

    @pytest.mark.asyncio
    @patch("src.agents.orchestrator.outbox_manager.create_sql_session")
    async def test_persist_domain_event_success(self, mock_create_session):
        """Test successful domain event persistence."""
        # Arrange
        scope_type = "GENESIS"
        session_id = "session-123"
        event_action = "Character.Requested"
        payload = {"character_type": "hero"}
        correlation_id = str(uuid4())
        causation_id = str(uuid4())

        mock_domain_event = DomainEvent(
            event_id=uuid4(),
            event_type="Genesis.Character.Requested",
            aggregate_type="Genesis",
            aggregate_id=session_id,
            payload=payload,
        )

        mock_session = AsyncMock()
        mock_session.add = MagicMock()  # Make synchronous
        mock_create_session.return_value.__aenter__.return_value = mock_session

        # Mock the sub-components
        self.manager.domain_event_creator.create_or_get_domain_event = AsyncMock(return_value=mock_domain_event)
        self.manager.outbox_entry_creator.create_or_get_outbox_entry = AsyncMock()

        # Act
        await self.manager.persist_domain_event(
            scope_type=scope_type,
            session_id=session_id,
            event_action=event_action,
            payload=payload,
            correlation_id=correlation_id,
            causation_id=causation_id,
        )

        # Assert
        self.manager.domain_event_creator.create_or_get_domain_event.assert_called_once_with(
            scope_type, session_id, event_action, payload, correlation_id, causation_id, mock_session
        )
        self.manager.outbox_entry_creator.create_or_get_outbox_entry.assert_called_once_with(
            mock_domain_event, scope_type, session_id, correlation_id, mock_session
        )

    @pytest.mark.asyncio
    async def test_enqueue_capability_task_delegates_correctly(self):
        """Test that capability task enqueueing delegates to the enqueuer."""
        # Arrange
        capability_message = {
            "type": "Character.Design.GenerationRequested",
            "session_id": "session-123",
            "_topic": "genesis.character.tasks",
        }
        correlation_id = str(uuid4())

        # Mock the capability enqueuer
        self.manager.capability_enqueuer.enqueue_capability_task = AsyncMock()

        # Act
        await self.manager.enqueue_capability_task(
            capability_message=capability_message, correlation_id=correlation_id
        )

        # Assert
        self.manager.capability_enqueuer.enqueue_capability_task.assert_called_once_with(
            capability_message, correlation_id
        )