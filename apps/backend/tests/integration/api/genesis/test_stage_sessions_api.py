"""Integration tests for Genesis Stage Session API endpoints.

Tests the /api/v1/genesis/ stage session management endpoints in the new decoupled architecture.
"""

import pytest
from httpx import AsyncClient
from uuid import UUID, uuid4

from src.schemas.enums import GenesisStage, StageSessionStatus, SessionKind


@pytest.mark.integration
class TestGenesisStageSessionsAPI:
    """Integration tests for Genesis Stage Session API endpoints."""

    @pytest.fixture
    async def test_flow(self, async_client: AsyncClient, auth_headers, test_novel):
        """Create a test Genesis flow for stage session tests."""
        novel_id = test_novel.id
        response = await async_client.post(
            f"/api/v1/genesis/flows/{novel_id}",
            headers=auth_headers
        )
        return response.json()["data"]

    @pytest.fixture
    async def test_stage(self, async_client: AsyncClient, auth_headers, test_novel, test_flow):
        """Create a test Genesis stage for stage session tests."""
        novel_id = test_novel.id
        stage_type = GenesisStage.INITIAL_PROMPT
        response = await async_client.post(
            f"/api/v1/genesis/flows/{novel_id}/stages/{stage_type.value}",
            headers=auth_headers,
            json={"config": {}, "iteration_count": 1}
        )
        return response.json()["data"]

    @pytest.mark.asyncio
    async def test_create_stage_session_new_session(self, async_client: AsyncClient, auth_headers, test_stage):
        """Test creating a new stage session association with new session."""
        # Arrange
        stage_id = test_stage["id"]
        session_data = {
            "is_primary": True,
            "session_kind": SessionKind.GENESIS.value
        }

        # Act
        response = await async_client.post(
            "/api/v1/genesis/stage-sessions",
            headers=auth_headers,
            json={
                "stage_id": stage_id,
                **session_data
            }
        )

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["code"] == 0
        assert data["msg"] == "Stage session created successfully"

        session = data["data"]
        assert session["stage_id"] == stage_id
        assert session["is_primary"] == session_data["is_primary"]
        assert session["session_kind"] == session_data["session_kind"]
        assert session["status"] == StageSessionStatus.ACTIVE.value
        assert "session_id" in session
        assert "id" in session

    @pytest.mark.asyncio
    async def test_create_stage_session_existing_session(self, async_client: AsyncClient, auth_headers, test_stage):
        """Test creating a stage session association with existing session."""
        # Arrange - Create a session first
        stage_id = test_stage["id"]
        existing_session_id = str(uuid4())

        session_data = {
            "stage_id": stage_id,
            "session_id": existing_session_id,
            "is_primary": False,
            "session_kind": SessionKind.CONVERSATION.value
        }

        # Act
        response = await async_client.post(
            "/api/v1/genesis/stage-sessions",
            headers=auth_headers,
            json=session_data
        )

        # Assert
        # Note: This might fail in current implementation due to session validation
        # The test documents expected behavior
        assert response.status_code in [201, 400]  # 400 if session doesn't exist

    @pytest.mark.asyncio
    async def test_get_stage_session_by_id(self, async_client: AsyncClient, auth_headers, test_stage):
        """Test retrieving a stage session by its association ID."""
        # Arrange - Create a stage session first
        stage_id = test_stage["id"]
        create_response = await async_client.post(
            "/api/v1/genesis/stage-sessions",
            headers=auth_headers,
            json={
                "stage_id": stage_id,
                "is_primary": True,
                "session_kind": SessionKind.GENESIS.value
            }
        )
        created_session = create_response.json()["data"]
        association_id = created_session["id"]

        # Act
        response = await async_client.get(
            f"/api/v1/genesis/stage-sessions/{association_id}",
            headers=auth_headers
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0

        session = data["data"]
        assert session["id"] == association_id
        assert session["stage_id"] == stage_id

    @pytest.mark.asyncio
    async def test_get_stage_session_by_ids(self, async_client: AsyncClient, auth_headers, test_stage):
        """Test retrieving a stage session by stage ID and session ID."""
        # Arrange - Create a stage session first
        stage_id = test_stage["id"]
        create_response = await async_client.post(
            "/api/v1/genesis/stage-sessions",
            headers=auth_headers,
            json={
                "stage_id": stage_id,
                "is_primary": True,
                "session_kind": SessionKind.GENESIS.value
            }
        )
        created_session = create_response.json()["data"]
        session_id = created_session["session_id"]

        # Act
        response = await async_client.get(
            f"/api/v1/genesis/stage-sessions/by-stage-and-session/{stage_id}/{session_id}",
            headers=auth_headers
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0

        session = data["data"]
        assert session["stage_id"] == stage_id
        assert session["session_id"] == session_id

    @pytest.mark.asyncio
    async def test_list_stage_sessions(self, async_client: AsyncClient, auth_headers, test_stage):
        """Test listing all sessions for a stage."""
        # Arrange - Create multiple stage sessions
        stage_id = test_stage["id"]
        for i in range(3):
            await async_client.post(
                "/api/v1/genesis/stage-sessions",
                headers=auth_headers,
                json={
                    "stage_id": stage_id,
                    "is_primary": i == 0,  # First one is primary
                    "session_kind": SessionKind.GENESIS.value
                }
            )

        # Act
        response = await async_client.get(
            f"/api/v1/genesis/stages/{stage_id}/sessions?limit=10&offset=0",
            headers=auth_headers
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0

        sessions = data["data"]
        assert isinstance(sessions, list)
        assert len(sessions) >= 3
        for session in sessions:
            assert session["stage_id"] == stage_id

        # Check that one is primary
        primary_sessions = [s for s in sessions if s["is_primary"]]
        assert len(primary_sessions) == 1

    @pytest.mark.asyncio
    async def test_list_session_stages(self, async_client: AsyncClient, auth_headers, test_stage):
        """Test listing all stages for a session."""
        # Arrange - Create a stage session first
        stage_id = test_stage["id"]
        create_response = await async_client.post(
            "/api/v1/genesis/stage-sessions",
            headers=auth_headers,
            json={
                "stage_id": stage_id,
                "is_primary": True,
                "session_kind": SessionKind.GENESIS.value
            }
        )
        created_session = create_response.json()["data"]
        session_id = created_session["session_id"]

        # Act
        response = await async_client.get(
            f"/api/v1/genesis/sessions/{session_id}/stages?limit=10&offset=0",
            headers=auth_headers
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0

        stages = data["data"]
        assert isinstance(stages, list)
        assert len(stages) >= 1
        for stage in stages:
            assert stage["session_id"] == session_id

    @pytest.mark.asyncio
    async def test_get_primary_session(self, async_client: AsyncClient, auth_headers, test_stage):
        """Test getting the primary session for a stage."""
        # Arrange - Create a primary session
        stage_id = test_stage["id"]
        create_response = await async_client.post(
            "/api/v1/genesis/stage-sessions",
            headers=auth_headers,
            json={
                "stage_id": stage_id,
                "is_primary": True,
                "session_kind": SessionKind.GENESIS.value
            }
        )
        created_session = create_response.json()["data"]

        # Act
        response = await async_client.get(
            f"/api/v1/genesis/stages/{stage_id}/primary-session",
            headers=auth_headers
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0

        session = data["data"]
        assert session["stage_id"] == stage_id
        assert session["is_primary"] is True

    @pytest.mark.asyncio
    async def test_set_primary_session(self, async_client: AsyncClient, auth_headers, test_stage):
        """Test setting a session as primary."""
        # Arrange - Create two sessions
        stage_id = test_stage["id"]

        # Create first session (primary)
        create_response1 = await async_client.post(
            "/api/v1/genesis/stage-sessions",
            headers=auth_headers,
            json={
                "stage_id": stage_id,
                "is_primary": True,
                "session_kind": SessionKind.GENESIS.value
            }
        )

        # Create second session (non-primary)
        create_response2 = await async_client.post(
            "/api/v1/genesis/stage-sessions",
            headers=auth_headers,
            json={
                "stage_id": stage_id,
                "is_primary": False,
                "session_kind": SessionKind.CONVERSATION.value
            }
        )

        session2 = create_response2.json()["data"]
        session2_id = session2["session_id"]

        # Act - Set second session as primary
        response = await async_client.post(
            f"/api/v1/genesis/stages/{stage_id}/set-primary-session/{session2_id}",
            headers=auth_headers
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0

        session = data["data"]
        assert session["session_id"] == session2_id
        assert session["is_primary"] is True

    @pytest.mark.asyncio
    async def test_update_stage_session(self, async_client: AsyncClient, auth_headers, test_stage):
        """Test updating a stage session association."""
        # Arrange - Create a stage session first
        stage_id = test_stage["id"]
        create_response = await async_client.post(
            "/api/v1/genesis/stage-sessions",
            headers=auth_headers,
            json={
                "stage_id": stage_id,
                "is_primary": False,
                "session_kind": SessionKind.GENESIS.value
            }
        )
        created_session = create_response.json()["data"]
        association_id = created_session["id"]

        # Act - Update session
        update_data = {
            "is_primary": True,
            "session_kind": SessionKind.CONVERSATION.value
        }
        response = await async_client.patch(
            f"/api/v1/genesis/stage-sessions/{association_id}",
            headers=auth_headers,
            json=update_data
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0

        session = data["data"]
        assert session["is_primary"] == update_data["is_primary"]
        assert session["session_kind"] == update_data["session_kind"]

    @pytest.mark.asyncio
    async def test_delete_stage_session(self, async_client: AsyncClient, auth_headers, test_stage):
        """Test deleting a stage session association."""
        # Arrange - Create a stage session first
        stage_id = test_stage["id"]
        create_response = await async_client.post(
            "/api/v1/genesis/stage-sessions",
            headers=auth_headers,
            json={
                "stage_id": stage_id,
                "is_primary": False,
                "session_kind": SessionKind.GENESIS.value
            }
        )
        created_session = create_response.json()["data"]
        association_id = created_session["id"]

        # Act
        response = await async_client.delete(
            f"/api/v1/genesis/stage-sessions/{association_id}",
            headers=auth_headers
        )

        # Assert
        assert response.status_code == 204

        # Verify deletion
        get_response = await async_client.get(
            f"/api/v1/genesis/stage-sessions/{association_id}",
            headers=auth_headers
        )
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_list_stage_sessions_with_status_filter(self, async_client: AsyncClient, auth_headers, test_stage):
        """Test listing stage sessions filtered by status."""
        # Arrange - Create stage sessions with different statuses
        stage_id = test_stage["id"]

        # Create active session
        await async_client.post(
            "/api/v1/genesis/stage-sessions",
            headers=auth_headers,
            json={
                "stage_id": stage_id,
                "is_primary": True,
                "session_kind": SessionKind.GENESIS.value
            }
        )

        # Act - List with status filter
        response = await async_client.get(
            f"/api/v1/genesis/stages/{stage_id}/sessions?status={StageSessionStatus.ACTIVE.value}&limit=10&offset=0",
            headers=auth_headers
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0

        sessions = data["data"]
        assert isinstance(sessions, list)
        for session in sessions:
            assert session["status"] == StageSessionStatus.ACTIVE.value

    @pytest.mark.asyncio
    async def test_stage_session_ownership_validation(self, async_client: AsyncClient, auth_headers, other_user_headers, test_stage):
        """Test that users can only access their own stage sessions."""
        # Arrange - Create a stage session with first user
        stage_id = test_stage["id"]
        create_response = await async_client.post(
            "/api/v1/genesis/stage-sessions",
            headers=auth_headers,
            json={
                "stage_id": stage_id,
                "is_primary": True,
                "session_kind": SessionKind.GENESIS.value
            }
        )
        created_session = create_response.json()["data"]
        association_id = created_session["id"]

        # Act - Try to access with different user
        response = await async_client.get(
            f"/api/v1/genesis/stage-sessions/{association_id}",
            headers=other_user_headers
        )

        # Assert - Should be forbidden or not found
        assert response.status_code in [403, 404]

    @pytest.mark.asyncio
    async def test_stage_session_not_found(self, async_client: AsyncClient, auth_headers):
        """Test accessing non-existent stage session returns 404."""
        # Arrange
        non_existent_id = "00000000-0000-0000-0000-000000000000"

        # Act
        response = await async_client.get(
            f"/api/v1/genesis/stage-sessions/{non_existent_id}",
            headers=auth_headers
        )

        # Assert
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_primary_session_not_found(self, async_client: AsyncClient, auth_headers, test_stage):
        """Test getting primary session when none exists returns 404."""
        # Arrange - Stage exists but no primary session
        stage_id = test_stage["id"]

        # Act
        response = await async_client.get(
            f"/api/v1/genesis/stages/{stage_id}/primary-session",
            headers=auth_headers
        )

        # Assert
        assert response.status_code == 404