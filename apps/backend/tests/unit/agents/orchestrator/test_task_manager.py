"""Unit tests for TaskManager and its components.

Tests the async task lifecycle management functionality with proper isolation
and mocking of database dependencies.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from src.agents.orchestrator.task_manager import (
    TaskCompleter,
    TaskCreator,
    TaskIdempotencyChecker,
    TaskManager,
)
from src.models.workflow import AsyncTask
from src.schemas.enums import TaskStatus


class TestTaskIdempotencyChecker:
    """Tests for task idempotency validation."""

    @pytest.mark.asyncio
    async def test_check_existing_task_found(self):
        """Test finding existing RUNNING/PENDING task."""
        # Arrange
        trig_cmd_id = uuid4()
        task_type = "Character.Design.Generation"

        existing_task = AsyncTask(
            id=uuid4(),
            task_type=task_type,
            triggered_by_command_id=trig_cmd_id,
            status=TaskStatus.RUNNING,
            started_at=datetime.now(UTC),
            input_data={"session_id": "session-123"},
        )

        mock_session = AsyncMock()
        mock_session.add = MagicMock()  # Make synchronous
        mock_session.scalar.return_value = existing_task

        # Act
        result = await TaskIdempotencyChecker.check_existing_task(trig_cmd_id, task_type, mock_session)

        # Assert
        assert result == existing_task
        mock_session.scalar.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_existing_task_not_found(self):
        """Test when no existing RUNNING/PENDING task is found."""
        # Arrange
        trig_cmd_id = uuid4()
        task_type = "Character.Design.Generation"

        mock_session = AsyncMock()
        mock_session.add = MagicMock()  # Make synchronous
        mock_session.scalar.return_value = None

        # Act
        result = await TaskIdempotencyChecker.check_existing_task(trig_cmd_id, task_type, mock_session)

        # Assert
        assert result is None
        mock_session.scalar.assert_called_once()


class TestTaskCreator:
    """Tests for task creation logic."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_logger = MagicMock()
        self.creator = TaskCreator(self.mock_logger)

    @pytest.mark.asyncio
    @patch("src.agents.orchestrator.task_manager.create_sql_session")
    async def test_create_task_success(self, mock_create_session):
        """Test successful task creation when no duplicate exists."""
        # Arrange
        correlation_id = str(uuid4())
        session_id = "session-123"
        task_type = "Character.Design.Generation"
        input_data = {"character_type": "hero"}

        mock_session = AsyncMock()
        mock_session.add = MagicMock()  # Make synchronous
        mock_create_session.return_value.__aenter__.return_value = mock_session

        # Mock idempotency check to return None (no existing task)
        self.creator.idempotency_checker.check_existing_task = AsyncMock(return_value=None)

        # Act
        await self.creator.create_task(correlation_id, session_id, task_type, input_data)

        # Assert
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()

        # Verify the task was created correctly
        added_task = mock_session.add.call_args[0][0]
        assert isinstance(added_task, AsyncTask)
        assert added_task.task_type == task_type
        assert added_task.triggered_by_command_id == UUID(correlation_id)
        assert added_task.status == TaskStatus.RUNNING
        assert added_task.input_data == {"session_id": session_id, **input_data}

    @pytest.mark.asyncio
    @patch("src.agents.orchestrator.task_manager.create_sql_session")
    async def test_create_task_duplicate_found(self, mock_create_session):
        """Test task creation when duplicate already exists."""
        # Arrange
        correlation_id = str(uuid4())
        session_id = "session-123"
        task_type = "Character.Design.Generation"
        input_data = {"character_type": "hero"}

        existing_task = AsyncTask(
            id=uuid4(),
            task_type=task_type,
            triggered_by_command_id=UUID(correlation_id),
            status=TaskStatus.RUNNING,
        )

        mock_session = AsyncMock()
        mock_session.add = MagicMock()  # Make synchronous
        mock_create_session.return_value.__aenter__.return_value = mock_session

        # Mock idempotency check to return existing task
        self.creator.idempotency_checker.check_existing_task = AsyncMock(return_value=existing_task)

        # Act
        await self.creator.create_task(correlation_id, session_id, task_type, input_data)

        # Assert
        mock_session.add.assert_not_called()
        mock_session.flush.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_task_empty_task_type(self):
        """Test handling of empty task type."""
        # Arrange
        correlation_id = str(uuid4())
        session_id = "session-123"
        task_type = ""
        input_data = {"character_type": "hero"}

        # Act
        await self.creator.create_task(correlation_id, session_id, task_type, input_data)

        # Assert
        self.mock_logger.warning.assert_called_once_with(
            "orchestrator_async_task_skipped",
            reason="empty_task_type",
            correlation_id=correlation_id,
            session_id=session_id,
        )

    @pytest.mark.asyncio
    async def test_create_task_invalid_correlation_id(self):
        """Test handling of invalid correlation_id."""
        # Arrange
        correlation_id = "invalid-uuid"
        session_id = "session-123"
        task_type = "Character.Design.Generation"
        input_data = {"character_type": "hero"}

        # Act
        await self.creator.create_task(correlation_id, session_id, task_type, input_data)

        # Assert
        self.mock_logger.warning.assert_called_once_with(
            "orchestrator_async_task_correlation_parse_failed",
            correlation_id=correlation_id,
            error="badly formed hexadecimal UUID string",
        )

    def test_parse_correlation_id_valid(self):
        """Test parsing valid correlation_id."""
        # Arrange
        correlation_id = str(uuid4())

        # Act
        result = self.creator._parse_correlation_id(correlation_id)

        # Assert
        assert result == UUID(correlation_id)

    def test_parse_correlation_id_invalid(self):
        """Test parsing invalid correlation_id."""
        # Arrange
        correlation_id = "invalid-uuid"

        # Act
        result = self.creator._parse_correlation_id(correlation_id)

        # Assert
        assert result is None

    def test_parse_correlation_id_none(self):
        """Test parsing None correlation_id."""
        # Act
        result = self.creator._parse_correlation_id(None)

        # Assert
        assert result is None


class TestTaskCompleter:
    """Tests for task completion logic."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_logger = MagicMock()
        self.completer = TaskCompleter(self.mock_logger)

    @pytest.mark.asyncio
    @patch("src.agents.orchestrator.task_manager.create_sql_session")
    @patch("src.common.utils.datetime_utils.utc_now")
    async def test_complete_task_success(self, mock_utc_now, mock_create_session):
        """Test successful task completion."""
        # Arrange
        correlation_id = str(uuid4())
        expect_task_prefix = "Character.Design"
        result_data = {"character_id": "char-123", "name": "Hero"}

        mock_now = datetime.now(UTC)
        mock_utc_now.return_value = mock_now

        task_to_complete = AsyncTask(
            id=uuid4(),
            task_type="Character.Design.Generation",
            triggered_by_command_id=UUID(correlation_id),
            status=TaskStatus.RUNNING,
            started_at=datetime.now(UTC),
        )

        mock_session = AsyncMock()
        mock_session.add = MagicMock()  # Make synchronous
        mock_create_session.return_value.__aenter__.return_value = mock_session

        # Mock finding the task
        self.completer._find_task_to_complete = AsyncMock(return_value=task_to_complete)

        # Act
        await self.completer.complete_task(correlation_id, expect_task_prefix, result_data)

        # Assert
        assert task_to_complete.status == TaskStatus.COMPLETED
        assert task_to_complete.completed_at is not None  # Just check it was set
        assert task_to_complete.result_data == result_data
        mock_session.add.assert_called_once_with(task_to_complete)

    @pytest.mark.asyncio
    async def test_complete_task_no_correlation_id(self):
        """Test task completion with no correlation_id."""
        # Arrange
        correlation_id = None
        expect_task_prefix = "Character.Design"
        result_data = {"character_id": "char-123"}

        # Act
        await self.completer.complete_task(correlation_id, expect_task_prefix, result_data)

        # Assert
        self.mock_logger.warning.assert_called_once_with(
            "orchestrator_async_task_complete_skipped",
            reason="no_correlation_id",
            expect_task_prefix=expect_task_prefix,
        )

    @pytest.mark.asyncio
    async def test_complete_task_invalid_correlation_id(self):
        """Test task completion with invalid correlation_id."""
        # Arrange
        correlation_id = "invalid-uuid"
        expect_task_prefix = "Character.Design"
        result_data = {"character_id": "char-123"}

        # Act
        await self.completer.complete_task(correlation_id, expect_task_prefix, result_data)

        # Assert
        self.mock_logger.warning.assert_called_once_with(
            "orchestrator_async_task_complete_correlation_parse_failed",
            correlation_id=correlation_id,
            error="badly formed hexadecimal UUID string",
        )

    @pytest.mark.asyncio
    @patch("src.agents.orchestrator.task_manager.create_sql_session")
    async def test_complete_task_not_found(self, mock_create_session):
        """Test task completion when task is not found."""
        # Arrange
        correlation_id = str(uuid4())
        expect_task_prefix = "Character.Design"
        result_data = {"character_id": "char-123"}

        mock_session = AsyncMock()
        mock_session.add = MagicMock()  # Make synchronous
        mock_create_session.return_value.__aenter__.return_value = mock_session

        # Mock finding no task
        self.completer._find_task_to_complete = AsyncMock(return_value=None)

        # Act
        await self.completer.complete_task(correlation_id, expect_task_prefix, result_data)

        # Assert
        self.completer._find_task_to_complete.assert_called_once()
        mock_session.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_find_task_to_complete_success(self):
        """Test finding task to complete successfully."""
        # Arrange
        trig_cmd_id = uuid4()
        expect_task_prefix = "Character.Design"

        task_to_complete = AsyncTask(
            id=uuid4(),
            task_type="Character.Design.Generation",
            triggered_by_command_id=trig_cmd_id,
            status=TaskStatus.RUNNING,
        )

        mock_session = AsyncMock()
        mock_session.add = MagicMock()  # Make synchronous
        mock_session.scalar.return_value = task_to_complete

        # Act
        result = await self.completer._find_task_to_complete(trig_cmd_id, expect_task_prefix, mock_session)

        # Assert
        assert result == task_to_complete
        mock_session.scalar.assert_called_once()

    @pytest.mark.asyncio
    async def test_find_task_to_complete_not_found(self):
        """Test when no task is found to complete."""
        # Arrange
        trig_cmd_id = uuid4()
        expect_task_prefix = "Character.Design"

        mock_session = AsyncMock()
        mock_session.add = MagicMock()  # Make synchronous
        mock_session.scalar.return_value = None

        # Act
        result = await self.completer._find_task_to_complete(trig_cmd_id, expect_task_prefix, mock_session)

        # Assert
        assert result is None
        self.mock_logger.warning.assert_called_once_with(
            "orchestrator_async_task_not_found_for_completion",
            correlation_id=str(trig_cmd_id),
            expect_task_prefix=expect_task_prefix,
            trig_cmd_id=str(trig_cmd_id),
        )


class TestTaskManager:
    """Tests for the unified task management interface."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_logger = MagicMock()
        self.manager = TaskManager(self.mock_logger)

    @pytest.mark.asyncio
    async def test_create_async_task_delegates_correctly(self):
        """Test that async task creation delegates to the creator."""
        # Arrange
        correlation_id = str(uuid4())
        session_id = "session-123"
        task_type = "Character.Design.Generation"
        input_data = {"character_type": "hero"}

        # Mock the task creator
        self.manager.creator.create_task = AsyncMock()

        # Act
        await self.manager.create_async_task(
            correlation_id=correlation_id, session_id=session_id, task_type=task_type, input_data=input_data
        )

        # Assert
        self.manager.creator.create_task.assert_called_once_with(correlation_id, session_id, task_type, input_data)

    @pytest.mark.asyncio
    async def test_complete_async_task_delegates_correctly(self):
        """Test that async task completion delegates to the completer."""
        # Arrange
        correlation_id = str(uuid4())
        expect_task_prefix = "Character.Design"
        result_data = {"character_id": "char-123", "name": "Hero"}

        # Mock the task completer
        self.manager.completer.complete_task = AsyncMock()

        # Act
        await self.manager.complete_async_task(
            correlation_id=correlation_id, expect_task_prefix=expect_task_prefix, result_data=result_data
        )

        # Assert
        self.manager.completer.complete_task.assert_called_once_with(
            correlation_id, expect_task_prefix, result_data
        )