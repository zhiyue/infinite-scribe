"""Basic unit tests for command service."""

import json
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from src.common.services.command_service import CommandService
from src.models.api import CommandRequest, CommandResponse, ErrorResponse
from src.models.database import CommandInbox


@pytest.fixture
def command_service():
    """Create command service instance."""
    from src.common.services.event_publisher import EventPublisher
    event_publisher = EventPublisher()
    return CommandService(event_publisher)


@pytest.fixture
def mock_session():
    """Create mock database session."""
    session = AsyncMock()
    session.begin = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.execute = AsyncMock()
    session.flush = AsyncMock()
    return session


@pytest.fixture
def sample_command_request():
    """Create sample command request."""
    return CommandRequest(
        session_id=str(uuid4()),
        command_type="RequestConceptGeneration",
        payload={
            "topic": "科幻小说",
            "requirements": ["创新", "深度"]
        }
    )


class TestCommandServiceBasic:
    """Test basic command service functionality."""
    
    @pytest.mark.asyncio
    async def test_process_command_success(self, command_service, mock_session, sample_command_request):
        """Test successful command processing."""
        # Setup mocks
        mock_session.execute.return_value.scalars.return_value.first.return_value = None
        
        # Execute
        result = await command_service.process_command(sample_command_request, mock_session)
        
        # Assertions
        assert isinstance(result, CommandResponse)
        assert result.success is True
        assert result.correlation_id is not None
        
        # Verify database operations
        assert mock_session.execute.call_count >= 1
        assert mock_session.commit.called
    
    @pytest.mark.asyncio
    async def test_process_command_duplicate_detection(self, command_service, mock_session, sample_command_request):
        """Test duplicate command detection."""
        # Setup mocks for duplicate detection
        existing_command = CommandInbox(
            command_id=str(uuid4()),
            session_id=sample_command_request.session_id,
            command_type=sample_command_request.command_type,
            payload=sample_command_request.payload,
            status="COMPLETED"
        )
        mock_session.execute.return_value.scalars.return_value.first.return_value = existing_command
        
        # Execute
        result = await command_service.process_command(sample_command_request, mock_session)
        
        # Assertions
        assert isinstance(result, CommandResponse)
        assert result.success is False
        assert result.error.code == "DUPLICATE_COMMAND"
        assert mock_session.rollback.called
    
    @pytest.mark.asyncio
    async def test_process_command_unknown_type(self, command_service, mock_session):
        """Test processing unknown command type."""
        # Setup
        unknown_command = CommandRequest(
            session_id=str(uuid4()),
            command_type="UnknownCommand",
            payload={}
        )
        mock_session.execute.return_value.scalars.return_value.first.return_value = None
        
        # Execute
        result = await command_service.process_command(unknown_command, mock_session)
        
        # Assertions
        assert isinstance(result, CommandResponse)
        assert result.success is False
        assert result.error.code == "UNKNOWN_COMMAND"
    
    @pytest.mark.asyncio
    async def test_process_command_transaction_error(self, command_service, mock_session, sample_command_request):
        """Test command processing with transaction error."""
        # Setup mocks to simulate transaction error
        mock_session.execute.side_effect = Exception("Database error")
        
        # Execute
        result = await command_service.process_command(sample_command_request, mock_session)
        
        # Assertions
        assert isinstance(result, CommandResponse)
        assert result.success is False
        assert result.error.code == "TRANSACTION_ERROR"
        assert mock_session.rollback.called
    
    @pytest.mark.asyncio
    async def test_get_command_status_found(self, command_service, mock_session):
        """Test getting command status when command exists."""
        # Setup
        command_id = str(uuid4())
        mock_command = CommandInbox(
            command_id=command_id,
            session_id=str(uuid4()),
            command_type="TestCommand",
            status="COMPLETED",
            payload={}
        )
        mock_session.execute.return_value.scalars.return_value.first.return_value = mock_command
        
        # Execute
        result = await command_service.get_command_status(command_id, mock_session)
        
        # Assertions
        assert result is not None
        assert result['command_id'] == command_id
        assert result['status'] == "COMPLETED"
    
    @pytest.mark.asyncio
    async def test_get_command_status_not_found(self, command_service, mock_session):
        """Test getting command status when command doesn't exist."""
        # Setup
        command_id = str(uuid4())
        mock_session.execute.return_value.scalars.return_value.first.return_value = None
        
        # Execute
        result = await command_service.get_command_status(command_id, mock_session)
        
        # Assertions
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_failed_commands(self, command_service, mock_session):
        """Test getting failed commands."""
        # Setup
        mock_failed_commands = [
            CommandInbox(
                command_id=str(uuid4()),
                session_id=str(uuid4()),
                command_type="TestCommand",
                status="FAILED",
                payload={}
            )
        ]
        mock_session.execute.return_value.scalars.return_value.all.return_value = mock_failed_commands
        
        # Execute
        result = await command_service.get_failed_commands(mock_session, limit=10)
        
        # Assertions
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]['status'] == "FAILED"