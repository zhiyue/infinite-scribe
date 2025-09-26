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
        result = await DomainEventIdempotencyChecker.check_existing_domain_event(correlation_id, evt_type, mock_session)

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
        result = await DomainEventIdempotencyChecker.check_existing_domain_event(correlation_id, evt_type, mock_session)

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
        result = await DomainEventIdempotencyChecker.check_existing_domain_event(correlation_id, evt_type, mock_session)

        # Assert
        assert result is None  # Should return None for invalid UUID

    @pytest.mark.asyncio
    @patch("src.agents.orchestrator.outbox_manager.logger")
    async def test_check_existing_domain_event_database_error(self, mock_logger):
        """Test database error handling with module-level logger."""
        # Arrange
        correlation_id = str(uuid4())
        evt_type = "Genesis.Character.Requested"

        mock_session = AsyncMock()
        mock_session.scalar.side_effect = Exception("Database connection failed")

        # Act
        result = await DomainEventIdempotencyChecker.check_existing_domain_event(correlation_id, evt_type, mock_session)

        # Assert
        assert result is None  # Should return None for database error
        mock_logger.warning.assert_called_once()

        # Verify the logged error contains expected information
        call_args = mock_logger.warning.call_args
        assert call_args[0][0] == "orchestrator_domain_event_check_failed"
        assert call_args[1]["correlation_id"] == correlation_id
        assert call_args[1]["evt_type"] == evt_type
        assert call_args[1]["error"] == "Database connection failed"
        assert call_args[1]["error_type"] == "Exception"
        assert "数据库查询失败" in call_args[1]["message"]


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
        # Check that source is correctly set in event_metadata
        assert result.event_metadata.get("source") == "orchestrator"

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

        # Verify payload structure - new nested format
        assert "system" in result.payload
        assert "data" in result.payload
        assert "schema_version" in result.payload
        assert result.payload["schema_version"] == "v1"

        # Verify system layer
        system = result.payload["system"]
        assert system["event_id"] == str(domain_event.event_id)
        assert system["event_type"] == domain_event.event_type
        assert system["aggregate_type"] == domain_event.aggregate_type
        assert system["aggregate_id"] == domain_event.aggregate_id

        # Verify data layer
        data = result.payload["data"]
        assert data["character_type"] == "hero"

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

    def test_build_outbox_payload_no_conflicts(self):
        """Test _build_outbox_payload with no conflicting fields."""
        # Arrange
        domain_event = DomainEvent(
            event_id=uuid4(),
            event_type="Genesis.Character.Requested",
            aggregate_type="Genesis",
            aggregate_id="session-123",
            payload={"character_type": "hero", "description": "A brave hero"},
            event_metadata={"source": "test"},
        )
        domain_event.created_at = MagicMock()
        domain_event.created_at.isoformat.return_value = "2023-01-01T00:00:00Z"

        # Act
        result = self.creator._build_outbox_payload(domain_event)

        # Assert - 新的分层结构
        # 验证顶层结构
        assert "system" in result
        assert "data" in result
        assert "schema_version" in result
        assert result["schema_version"] == "v1"

        # 验证system层
        system = result["system"]
        assert system["event_id"] == str(domain_event.event_id)
        assert system["event_type"] == "Genesis.Character.Requested"
        assert system["aggregate_type"] == "Genesis"
        assert system["aggregate_id"] == "session-123"
        assert system["metadata"] == {"source": "test"}
        assert system["created_at"] == "2023-01-01T00:00:00Z"

        # 验证data层包含业务数据
        data = result["data"]
        assert data["character_type"] == "hero"
        assert data["description"] == "A brave hero"

        # 新设计不会产生冲突警告，因为业务数据完全隔离在data层
        # 不再检查warning调用

    def test_build_outbox_payload_with_conflicts(self):
        """Test _build_outbox_payload with conflicting system fields."""
        # Arrange
        domain_event = DomainEvent(
            event_id=uuid4(),
            event_type="Genesis.Character.Requested",
            aggregate_type="Genesis",
            aggregate_id="session-123",
            payload={
                "character_type": "hero",
                "description": "A brave hero",
                # Conflicting system fields
                "event_id": "malicious-event-id",
                "event_type": "Malicious.Event.Type",
                "metadata": {"malicious": "data"},
            },
            event_metadata={"source": "test"},
        )
        domain_event.created_at = MagicMock()
        domain_event.created_at.isoformat.return_value = "2023-01-01T00:00:00Z"

        # Act
        result = self.creator._build_outbox_payload(domain_event)

        # Assert - 新的分层结构
        # 验证顶层结构
        assert "system" in result
        assert "data" in result
        assert "schema_version" in result
        assert result["schema_version"] == "v1"

        # 验证system层包含真实的系统元数据（不会被业务数据覆盖）
        system = result["system"]
        assert system["event_id"] == str(domain_event.event_id)
        assert system["event_type"] == "Genesis.Character.Requested"
        assert system["aggregate_type"] == "Genesis"
        assert system["aggregate_id"] == "session-123"
        assert system["metadata"] == {"source": "test"}

        # 验证data层包含所有业务数据（包括与system字段同名的数据）
        data = result["data"]
        assert data["character_type"] == "hero"
        assert data["description"] == "A brave hero"
        assert data["event_id"] == "malicious-event-id"
        assert data["event_type"] == "Malicious.Event.Type"
        assert data["metadata"] == {"malicious": "data"}

        # 新的Builder设计不会产生冲突警告，因为完全命名空间隔离
        # 不再检查warning调用

        # 新的Builder设计不会产生冲突警告，因为完全命名空间隔离
        # 不再检查warning调用

    def test_build_outbox_payload_all_protected_fields(self):
        """Test _build_outbox_payload when all protected fields are in payload."""
        # Arrange
        domain_event = DomainEvent(
            event_id=uuid4(),
            event_type="Genesis.Character.Requested",
            aggregate_type="Genesis",
            aggregate_id="session-123",
            payload={
                # All protected fields
                "event_id": "malicious-event-id",
                "event_type": "Malicious.Event.Type",
                "aggregate_type": "Malicious.Aggregate",
                "aggregate_id": "malicious-aggregate-id",
                "metadata": {"malicious": "data"},
                "created_at": "2020-01-01T00:00:00Z",
                # Safe fields
                "character_type": "hero",
            },
            event_metadata={"source": "test"},
        )
        domain_event.created_at = MagicMock()
        domain_event.created_at.isoformat.return_value = "2023-01-01T00:00:00Z"

        # Act
        result = self.creator._build_outbox_payload(domain_event)

        # Assert - 新的分层结构
        # 验证顶层结构
        assert "system" in result
        assert "data" in result
        assert "schema_version" in result
        assert result["schema_version"] == "v1"

        # 验证system层的系统元数据
        system = result["system"]
        assert system["event_id"] == str(domain_event.event_id)
        assert system["event_type"] == "Genesis.Character.Requested"
        assert system["aggregate_type"] == "Genesis"
        assert system["aggregate_id"] == "session-123"
        assert system["metadata"] == {"source": "test"}
        assert system["created_at"] == "2023-01-01T00:00:00Z"

        # 验证data层包含所有业务数据（包括原来的冲突字段，现在安全地隔离在data层）
        data = result["data"]
        assert data["character_type"] == "hero"
        assert data["event_id"] == "malicious-event-id"
        assert data["event_type"] == "Malicious.Event.Type"
        assert data["aggregate_type"] == "Malicious.Aggregate"
        assert data["aggregate_id"] == "malicious-aggregate-id"
        assert data["metadata"] == {"malicious": "data"}
        assert data["created_at"] == "2020-01-01T00:00:00Z"

        # 新的Builder设计不会产生冲突警告，因为业务数据完全隔离在data层
        # 不再检查warning调用

        # 新的Builder设计不会产生冲突警告，因为业务数据完全隔离在data层
        # 不再检查warning调用

    def test_build_outbox_payload_empty_payload(self):
        """Test _build_outbox_payload with empty payload."""
        # Arrange
        domain_event = DomainEvent(
            event_id=uuid4(),
            event_type="Genesis.Character.Requested",
            aggregate_type="Genesis",
            aggregate_id="session-123",
            payload=None,
            event_metadata={"source": "test"},
        )
        domain_event.created_at = MagicMock()
        domain_event.created_at.isoformat.return_value = "2023-01-01T00:00:00Z"

        # Act
        result = self.creator._build_outbox_payload(domain_event)

        # Assert - 新的分层结构
        # 验证顶层结构
        assert "system" in result
        assert "data" in result
        assert "schema_version" in result
        assert result["schema_version"] == "v1"

        # 验证system层
        system = result["system"]
        assert system["event_id"] == str(domain_event.event_id)
        assert system["event_type"] == "Genesis.Character.Requested"
        assert system["aggregate_type"] == "Genesis"
        assert system["aggregate_id"] == "session-123"
        assert system["metadata"] == {"source": "test"}
        assert system["created_at"] == "2023-01-01T00:00:00Z"

        # 验证data层为空（因为没有业务payload）
        assert result["data"] == {}

        # 不检查warning调用，因为新设计不会产生冲突

    def test_build_outbox_payload_created_at_exception(self):
        """Test _build_outbox_payload when created_at access raises exception."""
        # Arrange
        domain_event = DomainEvent(
            event_id=uuid4(),
            event_type="Genesis.Character.Requested",
            aggregate_type="Genesis",
            aggregate_id="session-123",
            payload={"character_type": "hero"},
            event_metadata={"source": "test"},
        )
        # Mock created_at to raise an exception when accessed
        domain_event.created_at = MagicMock()
        domain_event.created_at.isoformat.side_effect = Exception("Created at not available")

        # Act
        result = self.creator._build_outbox_payload(domain_event)

        # Assert - 新的分层结构
        # 验证顶层结构
        assert "system" in result
        assert "data" in result
        assert "schema_version" in result
        assert result["schema_version"] == "v1"

        # 验证system层（没有created_at因为格式化失败）
        system = result["system"]
        assert system["event_id"] == str(domain_event.event_id)
        assert system["event_type"] == "Genesis.Character.Requested"
        assert system["aggregate_type"] == "Genesis"
        assert system["aggregate_id"] == "session-123"
        assert system["metadata"] == {"source": "test"}
        # created_at should not be in system when exception occurs
        assert "created_at" not in system

        # 验证data层包含业务数据
        data = result["data"]
        assert data["character_type"] == "hero"


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
        await self.manager.enqueue_capability_task(capability_message=capability_message, correlation_id=correlation_id)

        # Assert
        self.manager.capability_enqueuer.enqueue_capability_task.assert_called_once_with(
            capability_message, correlation_id
        )
