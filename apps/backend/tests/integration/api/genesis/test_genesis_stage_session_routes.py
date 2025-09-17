"""Integration tests for Genesis Stage Session route endpoints."""

from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from src.schemas.enums import GenesisStage, StageSessionStatus


@pytest.mark.integration
class TestGenesisStageSessionRoutes:
    """Integration tests for Genesis stage session route endpoints in stage_sessions.py."""

    @pytest.fixture
    async def test_flow(self, pg_session, test_novel):
        """Create a test Genesis flow for stage session tests."""
        from src.models.genesis_flows import GenesisFlow
        from src.schemas.enums import GenesisStatus
        from uuid import uuid4

        flow = GenesisFlow(
            id=uuid4(),
            novel_id=test_novel.id,
            status=GenesisStatus.IN_PROGRESS,
            current_stage=GenesisStage.INITIAL_PROMPT,
            version=1,
            state={}
        )
        pg_session.add(flow)
        await pg_session.commit()
        await pg_session.refresh(flow)
        return flow

    @pytest.fixture
    async def test_stage(self, pg_session, test_flow):
        """Create a test Genesis stage for stage session tests."""
        from src.models.genesis_flows import GenesisStageRecord
        from src.schemas.enums import StageStatus
        from uuid import uuid4

        stage = GenesisStageRecord(
            id=uuid4(),
            flow_id=test_flow.id,
            stage=GenesisStage.INITIAL_PROMPT,
            status=StageStatus.RUNNING,
            config={},
            iteration_count=1
        )
        pg_session.add(stage)
        await pg_session.commit()
        await pg_session.refresh(stage)
        return stage

    @pytest.mark.asyncio
    async def test_create_stage_session_new_session(
        self, async_client: AsyncClient, auth_headers, test_stage, test_novel
    ):
        """Test creating a new stage session association with new session."""
        # Arrange
        stage_id = test_stage.id
        novel_id = test_novel.id
        session_data = {"novel_id": str(novel_id), "is_primary": True, "session_kind": "GENESIS"}

        # Act
        response = await async_client.post(
            f"/api/v1/genesis/stages/{stage_id}/sessions", headers=auth_headers, json=session_data
        )

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["code"] == 0
        assert data["msg"] == "Stage session association created successfully"

        # Verify response structure (tuple of session_id and stage_session_response)
        session_id, stage_session = data["data"]
        assert isinstance(session_id, str)
        assert UUID(session_id)  # Validate it's a valid UUID

        # Verify stage session response
        assert stage_session["stage_id"] == stage_id
        assert stage_session["session_id"] == session_id
        assert stage_session["is_primary"] == session_data["is_primary"]
        assert stage_session["session_kind"] == session_data["session_kind"]
        assert stage_session["status"] == StageSessionStatus.ACTIVE.value
        assert "id" in stage_session
        assert "created_at" in stage_session
        assert "updated_at" in stage_session

    @pytest.mark.asyncio
    async def test_create_stage_session_existing_session(
        self, async_client: AsyncClient, auth_headers, test_stage, test_novel
    ):
        """Test creating a stage session association with existing session."""
        # Arrange - First create a stage session to get an existing session
        stage_id = test_stage.id
        novel_id = test_novel.id

        # Create first session
        response1 = await async_client.post(
            f"/api/v1/genesis/stages/{stage_id}/sessions",
            headers=auth_headers,
            json={"novel_id": str(novel_id), "is_primary": False, "session_kind": "GENESIS"},
        )
        existing_session_id = response1.json()["data"][0]

        # Now try to bind this existing session to the same stage (should work)
        session_data = {
            "session_id": existing_session_id,
            "novel_id": str(novel_id),
            "is_primary": False,
            "session_kind": "CONVERSATION",
        }

        # Act
        response = await async_client.post(
            f"/api/v1/genesis/stages/{stage_id}/sessions", headers=auth_headers, json=session_data
        )

        # Assert - This creates a new association, not reusing the existing one
        assert response.status_code == 201
        data = response.json()
        assert data["code"] == 0

        session_id, stage_session = data["data"]
        assert session_id == existing_session_id
        assert stage_session["session_id"] == existing_session_id
        assert stage_session["session_kind"] == "CONVERSATION"

    @pytest.mark.asyncio
    async def test_create_stage_session_invalid_session(
        self, async_client: AsyncClient, auth_headers, test_stage, test_novel
    ):
        """Test creating stage session with non-existent session ID fails."""
        # Arrange
        stage_id = test_stage.id
        novel_id = test_novel.id
        non_existent_session_id = str(uuid4())

        session_data = {
            "session_id": non_existent_session_id,
            "novel_id": str(novel_id),
            "is_primary": False,
            "session_kind": "GENESIS",
        }

        # Act
        response = await async_client.post(
            f"/api/v1/genesis/stages/{stage_id}/sessions", headers=auth_headers, json=session_data
        )

        # Assert
        assert response.status_code == 400
        assert "Invalid session or scope validation failed" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_list_stage_sessions_empty(self, async_client: AsyncClient, auth_headers, test_stage):
        """Test listing stage sessions when none exist."""
        # Arrange
        stage_id = test_stage.id

        # Act
        response = await async_client.get(f"/api/v1/genesis/stages/{stage_id}/sessions", headers=auth_headers)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["msg"] == "Stage sessions retrieved successfully"
        assert data["data"] == []

    @pytest.mark.asyncio
    async def test_list_stage_sessions_with_data(self, async_client: AsyncClient, auth_headers, test_stage, test_novel):
        """Test listing stage sessions with existing sessions."""
        # Arrange - Create multiple stage sessions
        stage_id = test_stage.id
        novel_id = test_novel.id

        session_ids = []
        for i in range(3):
            response = await async_client.post(
                f"/api/v1/genesis/stages/{stage_id}/sessions",
                headers=auth_headers,
                json={
                    "novel_id": str(novel_id),
                    "is_primary": i == 0,  # First one is primary
                    "session_kind": "GENESIS",
                },
            )
            session_id, _ = response.json()["data"]
            session_ids.append(session_id)

        # Act
        response = await async_client.get(f"/api/v1/genesis/stages/{stage_id}/sessions", headers=auth_headers)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["msg"] == "Stage sessions retrieved successfully"

        sessions = data["data"]
        assert isinstance(sessions, list)
        assert len(sessions) == 3

        # Verify all sessions belong to the stage
        for session in sessions:
            assert session["stage_id"] == stage_id
            assert session["session_id"] in session_ids

        # Check that exactly one is primary
        primary_sessions = [s for s in sessions if s["is_primary"]]
        assert len(primary_sessions) == 1

    @pytest.mark.asyncio
    async def test_list_stage_sessions_with_status_filter(
        self, async_client: AsyncClient, auth_headers, test_stage, test_novel
    ):
        """Test listing stage sessions with status filter."""
        # Arrange - Create a stage session
        stage_id = test_stage.id
        novel_id = test_novel.id

        await async_client.post(
            f"/api/v1/genesis/stages/{stage_id}/sessions",
            headers=auth_headers,
            json={"novel_id": str(novel_id), "is_primary": True, "session_kind": "GENESIS"},
        )

        # Act - List with status filter
        response = await async_client.get(
            f"/api/v1/genesis/stages/{stage_id}/sessions?status={StageSessionStatus.ACTIVE.value}", headers=auth_headers
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0

        sessions = data["data"]
        assert len(sessions) == 1
        assert sessions[0]["status"] == StageSessionStatus.ACTIVE.value

    @pytest.mark.asyncio
    async def test_list_stage_sessions_with_pagination(
        self, async_client: AsyncClient, auth_headers, test_stage, test_novel
    ):
        """Test listing stage sessions with pagination parameters."""
        # Arrange - Create multiple stage sessions
        stage_id = test_stage.id
        novel_id = test_novel.id

        for i in range(5):
            await async_client.post(
                f"/api/v1/genesis/stages/{stage_id}/sessions",
                headers=auth_headers,
                json={"novel_id": str(novel_id), "is_primary": False, "session_kind": "GENESIS"},
            )

        # Act - List with pagination
        response = await async_client.get(
            f"/api/v1/genesis/stages/{stage_id}/sessions?limit=3&offset=0", headers=auth_headers
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        sessions = data["data"]
        assert len(sessions) <= 3

        # Test second page
        response2 = await async_client.get(
            f"/api/v1/genesis/stages/{stage_id}/sessions?limit=3&offset=3", headers=auth_headers
        )
        assert response2.status_code == 200
        sessions2 = response2.json()["data"]
        assert len(sessions2) <= 2  # Remaining sessions

    @pytest.mark.asyncio
    async def test_list_stage_sessions_invalid_stage(self, async_client: AsyncClient, auth_headers):
        """Test listing sessions for non-existent stage returns empty list."""
        # Arrange
        non_existent_stage_id = str(uuid4())

        # Act
        response = await async_client.get(
            f"/api/v1/genesis/stages/{non_existent_stage_id}/sessions", headers=auth_headers
        )

        # Assert - Service returns empty list for non-existent stage
        assert response.status_code == 200
        data = response.json()
        assert data["data"] == []

    @pytest.mark.asyncio
    async def test_create_stage_session_unauthorized(self, async_client: AsyncClient, test_stage, test_novel):
        """Test creating stage session without authentication fails."""
        # Arrange
        stage_id = test_stage.id
        novel_id = test_novel.id

        session_data = {"novel_id": str(novel_id), "is_primary": True, "session_kind": "GENESIS"}

        # Act - No auth headers
        response = await async_client.post(f"/api/v1/genesis/stages/{stage_id}/sessions", json=session_data)

        # Assert
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_stage_sessions_unauthorized(self, async_client: AsyncClient, test_stage):
        """Test listing stage sessions without authentication fails."""
        # Arrange
        stage_id = test_stage.id

        # Act - No auth headers
        response = await async_client.get(f"/api/v1/genesis/stages/{stage_id}/sessions")

        # Assert
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_stage_session_cors_headers(self, async_client: AsyncClient, auth_headers, test_stage):
        """Test that CORS headers are properly set."""
        # Arrange
        stage_id = test_stage.id

        # Act
        response = await async_client.get(f"/api/v1/genesis/stages/{stage_id}/sessions", headers=auth_headers)

        # Assert
        assert response.status_code == 200
        # Check for correlation ID header (from set_common_headers)
        assert "X-Correlation-Id" in response.headers

    @pytest.mark.asyncio
    async def test_create_stage_session_invalid_json(self, async_client: AsyncClient, auth_headers, test_stage):
        """Test creating stage session with invalid JSON data fails."""
        # Arrange
        stage_id = test_stage.id

        # Act - Missing required fields
        response = await async_client.post(
            f"/api/v1/genesis/stages/{stage_id}/sessions",
            headers=auth_headers,
            json={"is_primary": True},  # Missing novel_id
        )

        # Assert
        assert response.status_code == 422  # Pydantic validation error

    @pytest.mark.asyncio
    async def test_list_stage_sessions_invalid_query_params(self, async_client: AsyncClient, auth_headers, test_stage):
        """Test listing stage sessions with invalid query parameters."""
        # Arrange
        stage_id = test_stage.id

        # Act - Invalid limit value
        response = await async_client.get(f"/api/v1/genesis/stages/{stage_id}/sessions?limit=-1", headers=auth_headers)

        # Assert
        assert response.status_code == 422  # Query parameter validation error
