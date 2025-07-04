"""Unit tests for Genesis command API endpoints."""

import json
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from src.api.main import app
from src.common.services.command_service import DuplicateCommandError
from src.models.api import CommandResult
from src.models.db import CommandStatus


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def session_id():
    """Generate a test session ID."""
    return uuid4()


@pytest.fixture
def auth_headers():
    """Generate auth headers with test JWT token."""
    return {"Authorization": "Bearer test-token"}


class TestProcessCommand:
    """Test the process_command endpoint."""
    
    @patch('src.api.routes.v1.genesis.command_service.process_command')
    @patch('src.api.routes.v1.genesis.get_db_session')
    def test_process_concept_generation_command_success(
        self, mock_get_db, mock_process_command, client, session_id, auth_headers
    ):
        """Test successful concept generation command processing."""
        # Setup mocks
        mock_db = AsyncMock()
        mock_get_db.return_value.__aenter__.return_value = mock_db
        
        command_id = uuid4()
        mock_process_command.return_value = CommandResult(
            command_id=command_id,
            status=CommandStatus.COMPLETED.value,
            message="Command processed successfully"
        )
        
        # Test data
        request_data = {
            "command_type": "RequestConceptGeneration",
            "payload": {
                "theme_preferences": ["科幻", "悬疑"],
                "style_preferences": ["快节奏", "第一人称"]
            }
        }
        
        # Make request
        response = client.post(
            f"/api/v1/genesis/sessions/{session_id}/commands",
            json=request_data,
            headers=auth_headers
        )
        
        # Assertions
        assert response.status_code == status.HTTP_202_ACCEPTED
        data = response.json()
        assert data["command_id"] == str(command_id)
        assert data["status"] == CommandStatus.COMPLETED.value
        assert data["message"] == "Command accepted for processing"
        
        # Verify service was called correctly
        mock_process_command.assert_called_once_with(
            session_id=session_id,
            command_type="RequestConceptGeneration",
            payload=request_data["payload"],
            db=mock_db,
            user_id="user-placeholder"
        )
    
    @patch('src.api.routes.v1.genesis.command_service.process_command')
    @patch('src.api.routes.v1.genesis.get_db_session')
    def test_process_sync_command_success(
        self, mock_get_db, mock_process_command, client, session_id, auth_headers
    ):
        """Test successful synchronous command processing."""
        # Setup mocks
        mock_db = AsyncMock()
        mock_get_db.return_value.__aenter__.return_value = mock_db
        
        command_id = uuid4()
        mock_process_command.return_value = CommandResult(
            command_id=command_id,
            status=CommandStatus.COMPLETED.value,
            message="Command processed successfully"
        )
        
        # Test data
        request_data = {
            "command_type": "ConfirmStage",
            "payload": {"stage": "CONCEPT_SELECTION"}
        }
        
        # Make request
        response = client.post(
            f"/api/v1/genesis/sessions/{session_id}/commands",
            json=request_data,
            headers=auth_headers
        )
        
        # Assertions
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["command_id"] == str(command_id)
        assert data["status"] == CommandStatus.COMPLETED.value
        assert data["message"] == "Command processed successfully"
    
    @patch('src.api.routes.v1.genesis.command_service.process_command')
    @patch('src.api.routes.v1.genesis.get_db_session')
    def test_process_command_duplicate_error(
        self, mock_get_db, mock_process_command, client, session_id, auth_headers
    ):
        """Test duplicate command handling."""
        # Setup mocks
        mock_db = AsyncMock()
        mock_get_db.return_value.__aenter__.return_value = mock_db
        
        existing_command_id = uuid4()
        mock_process_command.side_effect = DuplicateCommandError(
            "Command already processing",
            existing_command_id=existing_command_id
        )
        
        # Test data
        request_data = {
            "command_type": "RequestConceptGeneration",
            "payload": {}
        }
        
        # Make request
        response = client.post(
            f"/api/v1/genesis/sessions/{session_id}/commands",
            json=request_data,
            headers=auth_headers
        )
        
        # Assertions
        assert response.status_code == status.HTTP_409_CONFLICT
        data = response.json()
        assert data["detail"]["error_code"] == "DUPLICATE_COMMAND"
        assert data["detail"]["message"] == "Command already processing"
        assert data["detail"]["duplicate_command_id"] == str(existing_command_id)
    
    def test_process_command_unsupported_type(
        self, client, session_id, auth_headers
    ):
        """Test unsupported command type handling."""
        # Test data
        request_data = {
            "command_type": "UnsupportedCommand",
            "payload": {}
        }
        
        # Make request
        response = client.post(
            f"/api/v1/genesis/sessions/{session_id}/commands",
            json=request_data,
            headers=auth_headers
        )
        
        # Assertions
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Unsupported command type" in response.json()["detail"]
    
    def test_process_command_missing_auth(self, client, session_id):
        """Test command processing without authentication."""
        # Test data
        request_data = {
            "command_type": "RequestConceptGeneration",
            "payload": {}
        }
        
        # Make request without auth headers
        response = client.post(
            f"/api/v1/genesis/sessions/{session_id}/commands",
            json=request_data
        )
        
        # Assertions
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_process_command_invalid_payload(
        self, client, session_id, auth_headers
    ):
        """Test command processing with invalid payload."""
        # Test data - missing command_type
        request_data = {
            "payload": {}
        }
        
        # Make request
        response = client.post(
            f"/api/v1/genesis/sessions/{session_id}/commands",
            json=request_data,
            headers=auth_headers
        )
        
        # Assertions
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    @patch('src.api.routes.v1.genesis.command_service.process_command')
    @patch('src.api.routes.v1.genesis.get_db_session')
    def test_process_command_service_error(
        self, mock_get_db, mock_process_command, client, session_id, auth_headers
    ):
        """Test internal service error handling."""
        # Setup mocks
        mock_db = AsyncMock()
        mock_get_db.return_value.__aenter__.return_value = mock_db
        mock_process_command.side_effect = Exception("Internal service error")
        
        # Test data
        request_data = {
            "command_type": "RequestConceptGeneration",
            "payload": {}
        }
        
        # Make request
        response = client.post(
            f"/api/v1/genesis/sessions/{session_id}/commands",
            json=request_data,
            headers=auth_headers
        )
        
        # Assertions
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


class TestGetSessionStatus:
    """Test the get_session_status endpoint."""
    
    @patch('src.api.routes.v1.genesis.AsyncSession.execute')
    @patch('src.api.routes.v1.genesis.get_db_session')
    def test_get_session_status_success(
        self, mock_get_db, mock_execute, client, session_id, auth_headers
    ):
        """Test successful session status retrieval."""
        # Setup mocks
        mock_db = AsyncMock()
        mock_get_db.return_value.__aenter__.return_value = mock_db
        
        # Mock database response
        mock_row = AsyncMock()
        mock_row.__getitem__.side_effect = lambda i: {
            0: session_id,
            1: "IN_PROGRESS", 
            2: "CONCEPT_SELECTION",
            3: {"confirmed_theme": "科幻"},
            4: "2024-01-01T10:00:00Z",
            5: "2024-01-01T10:05:00Z"
        }[i]
        
        mock_result = AsyncMock()
        mock_result.fetchone.return_value = mock_row
        mock_execute.return_value = mock_result
        
        # Make request
        response = client.get(
            f"/api/v1/genesis/sessions/{session_id}/status",
            headers=auth_headers
        )
        
        # Assertions
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["session_id"] == str(session_id)
        assert data["status"] == "IN_PROGRESS"
        assert data["current_stage"] == "CONCEPT_SELECTION"
    
    @patch('src.api.routes.v1.genesis.AsyncSession.execute')
    @patch('src.api.routes.v1.genesis.get_db_session')
    def test_get_session_status_not_found(
        self, mock_get_db, mock_execute, client, session_id, auth_headers
    ):
        """Test session not found handling."""
        # Setup mocks
        mock_db = AsyncMock()
        mock_get_db.return_value.__aenter__.return_value = mock_db
        
        # Mock empty database response
        mock_result = AsyncMock()
        mock_result.fetchone.return_value = None
        mock_execute.return_value = mock_result
        
        # Make request
        response = client.get(
            f"/api/v1/genesis/sessions/{session_id}/status",
            headers=auth_headers
        )
        
        # Assertions
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestCreateSession:
    """Test the create_session endpoint."""
    
    @patch('src.api.routes.v1.genesis.AsyncSession.execute')
    @patch('src.api.routes.v1.genesis.AsyncSession.commit')
    @patch('src.api.routes.v1.genesis.get_db_session')
    def test_create_session_success(
        self, mock_get_db, mock_commit, mock_execute, client, auth_headers
    ):
        """Test successful session creation."""
        # Setup mocks
        mock_db = AsyncMock()
        mock_get_db.return_value.__aenter__.return_value = mock_db
        
        # Make request
        response = client.post(
            "/api/v1/genesis/sessions",
            headers=auth_headers
        )
        
        # Assertions
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "session_id" in data
        assert data["status"] == "IN_PROGRESS"
        assert data["current_stage"] == "CONCEPT_SELECTION"
        assert data["message"] == "Genesis session created successfully"
        
        # Verify database operations were called
        mock_execute.assert_called_once()
        mock_commit.assert_called_once()
    
    @patch('src.api.routes.v1.genesis.AsyncSession.execute')
    @patch('src.api.routes.v1.genesis.get_db_session')
    def test_create_session_database_error(
        self, mock_get_db, mock_execute, client, auth_headers
    ):
        """Test session creation with database error."""
        # Setup mocks
        mock_db = AsyncMock()
        mock_get_db.return_value.__aenter__.return_value = mock_db
        mock_execute.side_effect = Exception("Database error")
        
        # Make request
        response = client.post(
            "/api/v1/genesis/sessions",
            headers=auth_headers
        )
        
        # Assertions
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR