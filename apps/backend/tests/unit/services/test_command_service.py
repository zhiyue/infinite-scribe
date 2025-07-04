"""Unit tests for command service."""

import json
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from src.common.services.command_service import CommandService, DuplicateCommandError
from src.models.api import CommandResult
from src.models.db import CommandStatus


@pytest.fixture
def command_service():
    """Create command service instance."""
    return CommandService()


@pytest.fixture
def mock_db():
    """Create mock database session."""
    mock_db = AsyncMock()
    mock_db.begin = AsyncMock()
    return mock_db


@pytest.fixture
def session_id():
    """Generate test session ID."""
    return uuid4()


class TestProcessCommand:
    """Test command processing functionality."""
    
    @pytest.mark.asyncio
    @patch('src.common.services.command_service.event_publisher')
    async def test_process_command_success(
        self, mock_event_publisher, command_service, mock_db, session_id
    ):
        """Test successful command processing."""
        # Setup mocks
        mock_db.execute = AsyncMock()
        mock_db.begin.return_value.__aenter__ = AsyncMock()
        mock_db.begin.return_value.__aexit__ = AsyncMock()
        
        # Mock event publisher
        outbox_id = uuid4()
        mock_event_publisher.publish_domain_event.return_value = outbox_id
        
        # Mock queries
        command_service._get_last_event_id = AsyncMock(return_value=None)
        
        # Test data
        command_type = "RequestConceptGeneration"
        payload = {"theme_preferences": ["科幻"]}
        user_id = "test-user"
        
        # Execute
        result = await command_service.process_command(
            session_id=session_id,
            command_type=command_type,
            payload=payload,
            db=mock_db,
            user_id=user_id
        )
        
        # Assertions
        assert isinstance(result, CommandResult)
        assert result.status == CommandStatus.COMPLETED.value
        assert result.message == "Command processed successfully"
        
        # Verify event publisher was called
        mock_event_publisher.publish_domain_event.assert_called_once()
        
        # Verify database operations
        assert mock_db.execute.call_count >= 3
    
    @pytest.mark.asyncio
    async def test_process_command_duplicate_error(
        self, command_service, mock_db, session_id
    ):
        """Test duplicate command detection."""
        # Setup mocks to raise IntegrityError
        mock_db.execute = AsyncMock(side_effect=IntegrityError("", "", ""))
        mock_db.begin.return_value.__aenter__ = AsyncMock()
        mock_db.begin.return_value.__aexit__ = AsyncMock()
        
        # Mock existing command ID lookup
        existing_command_id = uuid4()
        command_service._get_existing_command_id = AsyncMock(
            return_value=existing_command_id
        )
        
        # Test data
        command_type = "RequestConceptGeneration"
        payload = {}
        
        # Execute and verify exception
        with pytest.raises(DuplicateCommandError) as exc_info:
            await command_service.process_command(
                session_id=session_id,
                command_type=command_type,
                payload=payload,
                db=mock_db
            )
        
        assert exc_info.value.existing_command_id == existing_command_id
    
    @pytest.mark.asyncio
    async def test_process_command_with_idempotency_key(
        self, command_service, mock_db, session_id
    ):
        """Test command processing with custom idempotency key."""
        # Setup mocks
        mock_db.execute = AsyncMock()
        mock_db.begin.return_value.__aenter__ = AsyncMock()
        mock_db.begin.return_value.__aexit__ = AsyncMock()
        
        # Mock dependencies
        command_service._get_last_event_id = AsyncMock(return_value=None)
        
        with patch('src.common.services.command_service.event_publisher'):
            # Test data
            idempotency_key = "custom-key-123"
            
            # Execute
            result = await command_service.process_command(
                session_id=session_id,
                command_type="ConfirmStage",
                payload={"stage": "CONCEPT_SELECTION"},
                db=mock_db,
                idempotency_key=idempotency_key
            )
            
            # Verify success
            assert result.status == CommandStatus.COMPLETED.value


class TestEventTypeGeneration:
    """Test event type generation logic."""
    
    def test_generate_event_type_known_commands(self, command_service):
        """Test event type generation for known command types."""
        test_cases = [
            ("RequestConceptGeneration", "Genesis.Session.Requested"),
            ("ConfirmStage", "Genesis.Session.Confirmed"),
            ("SubmitFeedback", "Genesis.Session.Submitted"),
            ("CreateSession", "Genesis.Session.Created"),
            ("UpdateSession", "Genesis.Session.Updated"),
            ("CompleteSession", "Genesis.Session.Completed"),
        ]
        
        for command_type, expected_event_type in test_cases:
            result = command_service._generate_event_type(command_type)
            assert result == expected_event_type
    
    def test_generate_event_type_unknown_command(self, command_service):
        """Test event type generation for unknown command types."""
        unknown_command = "UnknownCommand"
        result = command_service._generate_event_type(unknown_command)
        assert result == "Genesis.Session.Requested"
    
    def test_official_verbs_validation(self, command_service):
        """Test that all mapped verbs are in the official verbs list."""
        command_to_verb = {
            'RequestConceptGeneration': 'Requested',
            'ConfirmStage': 'Confirmed',
            'SubmitFeedback': 'Submitted',
            'CreateSession': 'Created',
            'UpdateSession': 'Updated',
            'CompleteSession': 'Completed',
        }
        
        for verb in command_to_verb.values():
            assert verb in command_service.OFFICIAL_VERBS


class TestDatabaseOperations:
    """Test database operation helpers."""
    
    @pytest.mark.asyncio
    async def test_insert_command_inbox(self, command_service, mock_db):
        """Test command inbox insertion."""
        # Setup
        command_id = uuid4()
        session_id = uuid4()
        command_type = "TestCommand"
        payload = {"test": "data"}
        idempotency_key = "test-key"
        
        # Execute
        await command_service._insert_command_inbox(
            command_id=command_id,
            session_id=session_id,
            command_type=command_type,
            payload=payload,
            idempotency_key=idempotency_key,
            db=mock_db
        )
        
        # Verify database call
        mock_db.execute.assert_called_once()
        call_args = mock_db.execute.call_args
        
        # Check SQL contains expected fields
        sql = str(call_args[0][0])
        assert "INSERT INTO command_inbox" in sql
        assert "command_type" in sql
        assert "idempotency_key" in sql
        
        # Check parameters
        params = call_args[1]
        assert params['id'] == command_id
        assert params['session_id'] == session_id
        assert params['command_type'] == command_type
        assert params['idempotency_key'] == idempotency_key
        assert json.loads(params['payload']) == payload
    
    @pytest.mark.asyncio
    async def test_insert_domain_event(self, command_service, mock_db):
        """Test domain event insertion."""
        # Setup
        event_type = "Genesis.Session.Created"
        aggregate_id = str(uuid4())
        command_id = uuid4()
        payload = {"test": "data"}
        user_id = "test-user"
        
        # Execute
        await command_service._insert_domain_event(
            event_type=event_type,
            aggregate_id=aggregate_id,
            command_id=command_id,
            payload=payload,
            user_id=user_id,
            db=mock_db
        )
        
        # Verify database call
        mock_db.execute.assert_called_once()
        call_args = mock_db.execute.call_args
        
        # Check SQL contains expected fields
        sql = str(call_args[0][0])
        assert "INSERT INTO domain_events" in sql
        assert "event_type" in sql
        assert "aggregate_type" in sql
        
        # Check parameters
        params = call_args[1]
        assert params['event_type'] == event_type
        assert params['aggregate_id'] == aggregate_id
        assert params['correlation_id'] == str(command_id)
        assert params['aggregate_type'] == 'GENESIS_SESSION'
        assert json.loads(params['payload']) == payload
        
        # Check metadata
        metadata = json.loads(params['metadata'])
        assert metadata['user_id'] == user_id
        assert metadata['source_service'] == 'api-gateway'
    
    @pytest.mark.asyncio
    async def test_update_command_status(self, command_service, mock_db):
        """Test command status update."""
        # Setup
        command_id = uuid4()
        status = CommandStatus.COMPLETED
        error_message = None
        
        # Execute
        await command_service._update_command_status(
            command_id=command_id,
            status=status,
            error_message=error_message,
            db=mock_db
        )
        
        # Verify database call
        mock_db.execute.assert_called_once()
        call_args = mock_db.execute.call_args
        
        # Check SQL
        sql = str(call_args[0][0])
        assert "UPDATE command_inbox" in sql
        assert "status" in sql
        
        # Check parameters
        params = call_args[1]
        assert params['status'] == status.value
        assert params['command_id'] == command_id
        assert params['error_message'] == error_message
    
    @pytest.mark.asyncio
    async def test_get_existing_command_id(self, command_service, mock_db):
        """Test existing command ID lookup."""
        # Setup
        session_id = uuid4()
        command_type = "TestCommand"
        existing_id = uuid4()
        
        # Mock database response
        mock_row = [existing_id]
        mock_result = AsyncMock()
        mock_result.fetchone.return_value = mock_row
        mock_db.execute.return_value = mock_result
        
        # Execute
        result = await command_service._get_existing_command_id(
            session_id=session_id,
            command_type=command_type,
            db=mock_db
        )
        
        # Verify result
        assert result == existing_id
        
        # Verify database call
        mock_db.execute.assert_called_once()
        call_args = mock_db.execute.call_args
        
        # Check parameters
        params = call_args[1]
        assert params['session_id'] == session_id
        assert params['command_type'] == command_type
    
    @pytest.mark.asyncio
    async def test_get_existing_command_id_not_found(self, command_service, mock_db):
        """Test existing command ID lookup when not found."""
        # Setup
        session_id = uuid4()
        command_type = "TestCommand"
        
        # Mock empty database response
        mock_result = AsyncMock()
        mock_result.fetchone.return_value = None
        mock_db.execute.return_value = mock_result
        
        # Execute
        result = await command_service._get_existing_command_id(
            session_id=session_id,
            command_type=command_type,
            db=mock_db
        )
        
        # Verify result
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_last_event_id(self, command_service, mock_db):
        """Test last event ID lookup."""
        # Setup
        session_id = uuid4()
        last_event_id = str(uuid4())
        
        # Mock database response
        mock_row = [last_event_id]
        mock_result = AsyncMock()
        mock_result.fetchone.return_value = mock_row
        mock_db.execute.return_value = mock_result
        
        # Execute
        result = await command_service._get_last_event_id(
            session_id=session_id,
            db=mock_db
        )
        
        # Verify result
        assert result == last_event_id
        
        # Verify database call
        mock_db.execute.assert_called_once()
        call_args = mock_db.execute.call_args
        
        # Check parameters
        params = call_args[1]
        assert params['aggregate_id'] == str(session_id)


class TestDuplicateCommandError:
    """Test DuplicateCommandError exception."""
    
    def test_duplicate_command_error_creation(self):
        """Test DuplicateCommandError creation."""
        message = "Test error"
        command_id = uuid4()
        
        error = DuplicateCommandError(message, existing_command_id=command_id)
        
        assert str(error) == message
        assert error.existing_command_id == command_id
    
    def test_duplicate_command_error_without_id(self):
        """Test DuplicateCommandError creation without existing ID."""
        message = "Test error"
        
        error = DuplicateCommandError(message)
        
        assert str(error) == message
        assert error.existing_command_id is None