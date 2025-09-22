"""Unit tests for command status updater fixes."""

import pytest
from uuid import uuid4, UUID
from unittest.mock import AsyncMock, Mock

from src.schemas.enums import CommandStatus
from src.services.command.command_status_updater import CommandStatusUpdater, CommandUpdateResult, CommandEventType
from src.models.workflow import CommandInbox


class TestCommandStatusUpdaterFixes:
    """Test fixes for command status updater."""

    @pytest.fixture
    def updater(self):
        """Create command status updater instance."""
        mock_event_publisher = Mock()
        return CommandStatusUpdater(event_publisher=mock_event_publisher)

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        db = AsyncMock()
        db.scalar.return_value = None
        return db

    async def test_unknown_event_type_with_invalid_uuid(self, updater, mock_db):
        """Test handling unknown event type with invalid UUID format."""
        event = {
            "event_type": "Unknown.InvalidType",
            "command_id": "not-a-valid-uuid",
            "payload": {}
        }

        result = await updater.handle_command_event(mock_db, event)

        assert result.success is False
        assert "Invalid command_id format" in result.error_message
        assert isinstance(result.command_id, UUID)  # Should return a valid UUID even if input was invalid

    async def test_unknown_event_type_with_valid_uuid(self, updater, mock_db):
        """Test handling unknown event type with valid UUID format."""
        command_id = str(uuid4())
        event = {
            "event_type": "Unknown.InvalidType",
            "command_id": command_id,
            "payload": {}
        }

        result = await updater.handle_command_event(mock_db, event)

        assert result.success is False
        assert f"Unknown event type: Unknown.InvalidType" in result.error_message
        assert str(result.command_id) == command_id

    async def test_idempotent_duplicate_completed_event(self, updater, mock_db):
        """Test idempotent duplicate handling for completed command."""
        command_id = uuid4()
        event = {
            "event_type": "Command.Completed",
            "command_id": str(command_id),
            "payload": {}
        }

        # Mock command already in COMPLETED state
        existing_command = Mock(spec=CommandInbox)
        existing_command.id = command_id
        existing_command.status = CommandStatus.COMPLETED
        mock_db.scalar.return_value = existing_command

        result = await updater.handle_command_event(mock_db, event)

        assert result.success is True
        assert result.command_id == command_id
        assert result.old_status == CommandStatus.COMPLETED
        assert result.new_status == CommandStatus.COMPLETED
        assert result.should_notify is False

    async def test_idempotent_duplicate_started_event(self, updater, mock_db):
        """Test idempotent duplicate handling for started command."""
        command_id = uuid4()
        event = {
            "event_type": "Command.Started",
            "command_id": str(command_id),
            "payload": {}
        }

        # Mock command already in PROCESSING state
        existing_command = Mock(spec=CommandInbox)
        existing_command.id = command_id
        existing_command.status = CommandStatus.PROCESSING
        mock_db.scalar.return_value = existing_command

        result = await updater.handle_command_event(mock_db, event)

        assert result.success is True
        assert result.command_id == command_id
        assert result.old_status == CommandStatus.PROCESSING
        assert result.new_status == CommandStatus.PROCESSING
        assert result.should_notify is False

    async def test_idempotent_duplicate_progress_event(self, updater, mock_db):
        """Test idempotent duplicate handling for progress events in completed state."""
        command_id = uuid4()
        event = {
            "event_type": "Command.Progress",
            "command_id": str(command_id),
            "payload": {"progress": 50}
        }

        # Mock command in COMPLETED state - progress events are idempotent for completed commands
        existing_command = Mock(spec=CommandInbox)
        existing_command.id = command_id
        existing_command.status = CommandStatus.COMPLETED
        mock_db.scalar.return_value = existing_command

        result = await updater.handle_command_event(mock_db, event)

        assert result.success is True
        assert result.command_id == command_id
        assert result.old_status == CommandStatus.COMPLETED
        assert result.new_status == CommandStatus.COMPLETED
        assert result.should_notify is False

    async def test_invalid_transition_not_idempotent(self, updater, mock_db):
        """Test invalid transition that is not idempotent duplicate."""
        command_id = uuid4()
        event = {
            "event_type": "Command.Started",
            "command_id": str(command_id),
            "payload": {}
        }

        # Mock command in COMPLETED state - cannot start again
        existing_command = Mock(spec=CommandInbox)
        existing_command.id = command_id
        existing_command.status = CommandStatus.COMPLETED
        mock_db.scalar.return_value = existing_command

        result = await updater.handle_command_event(mock_db, event)

        assert result.success is False
        assert "Invalid state transition" in result.error_message
        assert result.command_id == command_id
        assert result.old_status == CommandStatus.COMPLETED
        assert result.new_status == CommandStatus.COMPLETED

    def test_is_idempotent_duplicate_method(self, updater):
        """Test _is_idempotent_duplicate method directly."""
        # Test COMPLETED event with COMPLETED status
        assert updater._is_idempotent_duplicate(
            CommandStatus.COMPLETED, CommandEventType.COMPLETED
        ) is True

        # Test STARTED event with PROCESSING status
        assert updater._is_idempotent_duplicate(
            CommandStatus.PROCESSING, CommandEventType.STARTED
        ) is True

        # Test FAILED event with FAILED status
        assert updater._is_idempotent_duplicate(
            CommandStatus.FAILED, CommandEventType.FAILED
        ) is True

        # Test TIMEOUT event with FAILED status
        assert updater._is_idempotent_duplicate(
            CommandStatus.FAILED, CommandEventType.TIMEOUT
        ) is True

        # Test CANCELLED event with FAILED status
        assert updater._is_idempotent_duplicate(
            CommandStatus.FAILED, CommandEventType.CANCELLED
        ) is True

        # Test PROGRESS event (idempotent when status matches)
        assert updater._is_idempotent_duplicate(
            CommandStatus.PROCESSING, CommandEventType.PROGRESS
        ) is True

        assert updater._is_idempotent_duplicate(
            CommandStatus.COMPLETED, CommandEventType.PROGRESS
        ) is True

        assert updater._is_idempotent_duplicate(
            CommandStatus.RECEIVED, CommandEventType.PROGRESS
        ) is True

        # Test non-idempotent cases
        assert updater._is_idempotent_duplicate(
            CommandStatus.RECEIVED, CommandEventType.COMPLETED
        ) is False

        assert updater._is_idempotent_duplicate(
            CommandStatus.PROCESSING, CommandEventType.COMPLETED
        ) is False

    async def test_missing_command_id_in_event(self, updater, mock_db):
        """Test handling event with missing command_id."""
        event = {
            "event_type": "Command.Started",
            "payload": {}
        }

        result = await updater.handle_command_event(mock_db, event)

        assert result.success is False
        assert "Missing command_id in event" in result.error_message
        assert isinstance(result.command_id, UUID)  # Should return a valid UUID

    async def test_command_not_found(self, updater, mock_db):
        """Test handling event for non-existent command."""
        command_id = uuid4()
        event = {
            "event_type": "Command.Started",
            "command_id": str(command_id),
            "payload": {}
        }

        # Mock command not found
        mock_db.scalar.return_value = None

        result = await updater.handle_command_event(mock_db, event)

        assert result.success is False
        assert f"Command not found: {command_id}" in result.error_message
        assert result.command_id == command_id