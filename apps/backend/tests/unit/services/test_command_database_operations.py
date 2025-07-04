"""Unit tests for command service database operations."""

import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.common.services.command_service import CommandService
from src.models.db import CommandStatus


@pytest.fixture
def command_service():
    """Create command service instance."""
    return CommandService()


@pytest.fixture
def mock_db():
    """Create mock database session."""
    return AsyncMock()


class TestCommandInboxOperations:
    """Test command inbox database operations."""
    
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
        assert params['status'] == CommandStatus.RECEIVED.value
    
    @pytest.mark.asyncio
    async def test_update_command_status_success(self, command_service, mock_db):
        """Test successful command status update."""
        # Setup
        command_id = uuid4()
        status = CommandStatus.COMPLETED
        
        # Execute
        await command_service._update_command_status(
            command_id=command_id,
            status=status,
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
        assert params['error_message'] is None
    
    @pytest.mark.asyncio
    async def test_update_command_status_with_error(self, command_service, mock_db):
        """Test command status update with error message."""
        # Setup
        command_id = uuid4()
        status = CommandStatus.FAILED
        error_message = "Processing failed"
        
        # Execute
        await command_service._update_command_status(
            command_id=command_id,
            status=status,
            error_message=error_message,
            db=mock_db
        )
        
        # Verify database call
        call_args = mock_db.execute.call_args
        params = call_args[1]
        assert params['status'] == status.value
        assert params['error_message'] == error_message


class TestDomainEventOperations:
    """Test domain event database operations."""
    
    @pytest.mark.asyncio
    async def test_insert_domain_event(self, command_service, mock_db):
        """Test domain event insertion."""
        # Setup
        event_type = "Genesis.Session.Created"
        aggregate_id = str(uuid4())
        command_id = uuid4()
        payload = {"test": "data"}
        user_id = "test-user"
        causation_id = str(uuid4())
        
        # Execute
        await command_service._insert_domain_event(
            event_type=event_type,
            aggregate_id=aggregate_id,
            command_id=command_id,
            payload=payload,
            causation_id=causation_id,
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
        assert params['causation_id'] == causation_id
        assert params['aggregate_type'] == 'GENESIS_SESSION'
        assert params['event_version'] == 1
        assert json.loads(params['payload']) == payload
        
        # Check metadata
        metadata = json.loads(params['metadata'])
        assert metadata['user_id'] == user_id
        assert metadata['source_service'] == 'api-gateway'
        assert 'timestamp' in metadata
    
    @pytest.mark.asyncio
    async def test_insert_domain_event_without_causation(self, command_service, mock_db):
        """Test domain event insertion without causation ID."""
        # Setup
        event_type = "Genesis.Session.Created"
        aggregate_id = str(uuid4())
        command_id = uuid4()
        payload = {"test": "data"}
        
        # Execute
        await command_service._insert_domain_event(
            event_type=event_type,
            aggregate_id=aggregate_id,
            command_id=command_id,
            payload=payload,
            db=mock_db
        )
        
        # Verify database call
        call_args = mock_db.execute.call_args
        params = call_args[1]
        assert params['causation_id'] is None


class TestQueryOperations:
    """Test query database operations."""
    
    @pytest.mark.asyncio
    async def test_get_existing_command_id_found(self, command_service, mock_db):
        """Test existing command ID lookup when found."""
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
        
        # Check SQL contains expected conditions
        sql = str(call_args[0][0])
        assert "SELECT id FROM command_inbox" in sql
        assert "WHERE session_id" in sql
        assert "AND command_type" in sql
        assert "AND status IN" in sql
        
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
    async def test_get_last_event_id_found(self, command_service, mock_db):
        """Test last event ID lookup when found."""
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
        
        # Check SQL
        sql = str(call_args[0][0])
        assert "SELECT event_id FROM domain_events" in sql
        assert "WHERE aggregate_id" in sql
        assert "AND aggregate_type = 'GENESIS_SESSION'" in sql
        assert "ORDER BY id DESC" in sql
        
        # Check parameters
        params = call_args[1]
        assert params['aggregate_id'] == str(session_id)
    
    @pytest.mark.asyncio
    async def test_get_last_event_id_not_found(self, command_service, mock_db):
        """Test last event ID lookup when not found."""
        # Setup
        session_id = uuid4()
        
        # Mock empty database response
        mock_result = AsyncMock()
        mock_result.fetchone.return_value = None
        mock_db.execute.return_value = mock_result
        
        # Execute
        result = await command_service._get_last_event_id(
            session_id=session_id,
            db=mock_db
        )
        
        # Verify result
        assert result is None