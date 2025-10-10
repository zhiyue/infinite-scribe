"""Integration tests for legacy Genesis API endpoints.

Tests the /api/v1/genesis/ endpoints in genesis.py (legacy implementation).
NOTE: These tests are for the old implementation that should be deprecated.
"""

import pytest
from httpx import AsyncClient
from uuid import UUID

from src.schemas.enums import GenesisStatus, GenesisStage, StageStatus, StageSessionStatus


@pytest.mark.integration
class TestLegacyGenesisAPI:
    """Integration tests for legacy Genesis API endpoints (genesis.py)."""

    @pytest.mark.asyncio
    async def test_ensure_genesis_flow_creates_new_flow(self, async_client: AsyncClient, auth_headers, test_novel):
        """Test ensuring Genesis flow exists - creates new flow."""
        # Arrange
        novel_id = test_novel.id

        # Act - Create Genesis flow
        response = await async_client.post(
            f"/api/v1/genesis/flows/{novel_id}",
            headers=auth_headers
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["novel_id"] == str(novel_id)
        assert data["status"] == GenesisStatus.IN_PROGRESS.value
        assert data["current_stage"] == GenesisStage.INITIAL_PROMPT.value
        assert data["version"] == 1
        assert isinstance(data["state"], dict)
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

    @pytest.mark.asyncio
    async def test_ensure_genesis_flow_returns_existing_flow(self, async_client: AsyncClient, auth_headers, test_novel):
        """Test ensuring Genesis flow exists - returns existing flow."""
        # Arrange - Create a flow first
        novel_id = test_novel.id
        first_response = await async_client.post(
            f"/api/v1/genesis/flows/{novel_id}",
            headers=auth_headers
        )
        first_flow = first_response.json()

        # Act - Try to create again
        second_response = await async_client.post(
            f"/api/v1/genesis/flows/{novel_id}",
            headers=auth_headers
        )

        # Assert - Should return same flow
        assert second_response.status_code == 200
        second_flow = second_response.json()
        assert first_flow["id"] == second_flow["id"]
        assert first_flow["version"] == second_flow["version"]

    @pytest.mark.asyncio
    async def test_get_genesis_flow_with_stages(self, async_client: AsyncClient, auth_headers, test_novel):
        """Test getting Genesis flow with stages information."""
        # Arrange - Create a flow first
        novel_id = test_novel.id
        await async_client.post(
            f"/api/v1/genesis/flows/{novel_id}",
            headers=auth_headers
        )

        # Act - Get the flow
        response = await async_client.get(
            f"/api/v1/genesis/flows/{novel_id}",
            headers=auth_headers
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "flow" in data
        assert "stages" in data

        flow_data = data["flow"]
        assert flow_data["novel_id"] == str(novel_id)
        assert flow_data["status"] == GenesisStatus.IN_PROGRESS.value

        stages_data = data["stages"]
        assert isinstance(stages_data, list)

    @pytest.mark.asyncio
    async def test_update_genesis_flow_advance_stage(self, async_client: AsyncClient, auth_headers, test_novel):
        """Test updating Genesis flow to advance stage."""
        # Arrange - Create a flow first
        novel_id = test_novel.id
        await async_client.post(
            f"/api/v1/genesis/flows/{novel_id}",
            headers=auth_headers
        )

        # Act - Update flow to advance stage
        update_data = {
            "current_stage": GenesisStage.WORLD_BUILDING.value,
            "expected_version": 1
        }
        response = await async_client.put(
            f"/api/v1/genesis/flows/{novel_id}",
            headers=auth_headers,
            json=update_data
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["current_stage"] == GenesisStage.WORLD_BUILDING.value
        assert data["version"] == 2

    @pytest.mark.asyncio
    async def test_update_genesis_flow_complete(self, async_client: AsyncClient, auth_headers, test_novel):
        """Test completing a Genesis flow."""
        # Arrange - Create a flow first
        novel_id = test_novel.id
        await async_client.post(
            f"/api/v1/genesis/flows/{novel_id}",
            headers=auth_headers
        )

        # Act - Complete the flow
        update_data = {
            "status": GenesisStatus.COMPLETED.value,
            "expected_version": 1,
            "state": {"completed_reason": "Manual completion"}
        }
        response = await async_client.put(
            f"/api/v1/genesis/flows/{novel_id}",
            headers=auth_headers,
            json=update_data
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == GenesisStatus.COMPLETED.value
        assert data["version"] == 2

    @pytest.mark.asyncio
    async def test_create_genesis_stage(self, async_client: AsyncClient, auth_headers, test_novel):
        """Test creating a Genesis stage."""
        # Arrange - Create a flow first
        novel_id = test_novel.id
        await async_client.post(
            f"/api/v1/genesis/flows/{novel_id}",
            headers=auth_headers
        )

        # Act - Create a stage
        stage_type = GenesisStage.INITIAL_PROMPT
        stage_data = {
            "config": {"max_iterations": 3, "temperature": 0.7}
        }
        response = await async_client.post(
            f"/api/v1/genesis/flows/{novel_id}/stages/{stage_type.value}",
            headers=auth_headers,
            json=stage_data
        )

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["stage"] == stage_type.value
        assert data["status"] == StageStatus.PENDING.value
        assert data["config"] == stage_data["config"]

    @pytest.mark.asyncio
    async def test_get_genesis_stage(self, async_client: AsyncClient, auth_headers, test_novel):
        """Test getting a Genesis stage with sessions."""
        # Arrange - Create flow and stage first
        novel_id = test_novel.id
        await async_client.post(
            f"/api/v1/genesis/flows/{novel_id}",
            headers=auth_headers
        )

        stage_type = GenesisStage.INITIAL_PROMPT
        create_response = await async_client.post(
            f"/api/v1/genesis/flows/{novel_id}/stages/{stage_type.value}",
            headers=auth_headers,
            json={"config": {}}
        )
        created_stage = create_response.json()
        stage_id = created_stage["id"]

        # Act - Get the stage
        response = await async_client.get(
            f"/api/v1/genesis/stages/{stage_id}",
            headers=auth_headers
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "stage" in data
        assert "sessions" in data

        stage_data = data["stage"]
        assert stage_data["id"] == stage_id
        assert stage_data["stage"] == stage_type.value

        sessions_data = data["sessions"]
        assert isinstance(sessions_data, list)

    @pytest.mark.asyncio
    async def test_update_genesis_stage_complete(self, async_client: AsyncClient, auth_headers, test_novel):
        """Test completing a Genesis stage."""
        # Arrange - Create flow and stage first
        novel_id = test_novel.id
        await async_client.post(
            f"/api/v1/genesis/flows/{novel_id}",
            headers=auth_headers
        )

        stage_type = GenesisStage.INITIAL_PROMPT
        create_response = await async_client.post(
            f"/api/v1/genesis/flows/{novel_id}/stages/{stage_type.value}",
            headers=auth_headers,
            json={"config": {}}
        )
        created_stage = create_response.json()
        stage_id = created_stage["id"]

        # Act - Complete the stage
        update_data = {
            "status": StageStatus.COMPLETED.value,
            "result": {"output": "Stage completed successfully"},
            "metrics": {"duration_ms": 1500}
        }
        response = await async_client.put(
            f"/api/v1/genesis/stages/{stage_id}",
            headers=auth_headers,
            json=update_data
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == StageStatus.COMPLETED.value
        assert data["result"] == update_data["result"]
        assert data["metrics"] == update_data["metrics"]

    @pytest.mark.asyncio
    async def test_create_stage_session(self, async_client: AsyncClient, auth_headers, test_novel):
        """Test creating a stage session association."""
        # Arrange - Create flow and stage first
        novel_id = test_novel.id
        await async_client.post(
            f"/api/v1/genesis/flows/{novel_id}",
            headers=auth_headers
        )

        stage_type = GenesisStage.INITIAL_PROMPT
        create_response = await async_client.post(
            f"/api/v1/genesis/flows/{novel_id}/stages/{stage_type.value}",
            headers=auth_headers,
            json={"config": {}}
        )
        created_stage = create_response.json()
        stage_id = created_stage["id"]

        # Act - Create stage session
        session_data = {
            "is_primary": True,
            "session_kind": "genesis"
        }
        response = await async_client.post(
            f"/api/v1/genesis/stages/{stage_id}/sessions",
            headers=auth_headers,
            json=session_data
        )

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["stage_id"] == stage_id
        assert data["is_primary"] == session_data["is_primary"]
        assert data["session_kind"] == session_data["session_kind"]

    @pytest.mark.asyncio
    async def test_list_stage_sessions(self, async_client: AsyncClient, auth_headers, test_novel):
        """Test listing stage sessions."""
        # Arrange - Create flow, stage, and session first
        novel_id = test_novel.id
        await async_client.post(
            f"/api/v1/genesis/flows/{novel_id}",
            headers=auth_headers
        )

        stage_type = GenesisStage.INITIAL_PROMPT
        create_response = await async_client.post(
            f"/api/v1/genesis/flows/{novel_id}/stages/{stage_type.value}",
            headers=auth_headers,
            json={"config": {}}
        )
        created_stage = create_response.json()
        stage_id = created_stage["id"]

        # Create a session
        await async_client.post(
            f"/api/v1/genesis/stages/{stage_id}/sessions",
            headers=auth_headers,
            json={"is_primary": True, "session_kind": "genesis"}
        )

        # Act - List sessions
        response = await async_client.get(
            f"/api/v1/genesis/stages/{stage_id}/sessions",
            headers=auth_headers
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        for session in data:
            assert session["stage_id"] == stage_id

    @pytest.mark.asyncio
    async def test_set_primary_session(self, async_client: AsyncClient, auth_headers, test_novel):
        """Test setting a session as primary."""
        # Arrange - Create flow, stage, and sessions first
        novel_id = test_novel.id
        await async_client.post(
            f"/api/v1/genesis/flows/{novel_id}",
            headers=auth_headers
        )

        stage_type = GenesisStage.INITIAL_PROMPT
        create_response = await async_client.post(
            f"/api/v1/genesis/flows/{novel_id}/stages/{stage_type.value}",
            headers=auth_headers,
            json={"config": {}}
        )
        created_stage = create_response.json()
        stage_id = created_stage["id"]

        # Create two sessions
        session1_response = await async_client.post(
            f"/api/v1/genesis/stages/{stage_id}/sessions",
            headers=auth_headers,
            json={"is_primary": True, "session_kind": "genesis"}
        )

        session2_response = await async_client.post(
            f"/api/v1/genesis/stages/{stage_id}/sessions",
            headers=auth_headers,
            json={"is_primary": False, "session_kind": "conversation"}
        )

        session2 = session2_response.json()
        session2_id = session2["session_id"]

        # Act - Set second session as primary
        response = await async_client.put(
            f"/api/v1/genesis/stages/{stage_id}/sessions/{session2_id}/primary",
            headers=auth_headers
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == session2_id
        assert data["is_primary"] is True

    @pytest.mark.asyncio
    async def test_list_genesis_flows(self, async_client: AsyncClient, auth_headers, test_novel):
        """Test listing Genesis flows by status."""
        # Arrange - Create a flow first
        novel_id = test_novel.id
        await async_client.post(
            f"/api/v1/genesis/flows/{novel_id}",
            headers=auth_headers
        )

        # Act - List flows
        response = await async_client.get(
            f"/api/v1/genesis/flows?status={GenesisStatus.IN_PROGRESS.value}&limit=10&offset=0",
            headers=auth_headers
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "flows" in data
        assert "total" in data
        assert "offset" in data
        assert "limit" in data

        flows = data["flows"]
        assert isinstance(flows, list)
        assert len(flows) >= 1
        for flow in flows:
            assert flow["status"] == GenesisStatus.IN_PROGRESS.value

    @pytest.mark.asyncio
    async def test_genesis_flow_not_found(self, async_client: AsyncClient, auth_headers, test_novel):
        """Test getting non-existent Genesis flow returns 404."""
        # Arrange
        novel_id = test_novel.id

        # Act - Try to get non-existent flow
        response = await async_client.get(
            f"/api/v1/genesis/flows/{novel_id}",
            headers=auth_headers
        )

        # Assert
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_genesis_stage_not_implemented(self, async_client: AsyncClient, auth_headers, test_novel):
        """Test that general stage update returns 501 (not implemented)."""
        # Arrange - Create flow and stage first
        novel_id = test_novel.id
        await async_client.post(
            f"/api/v1/genesis/flows/{novel_id}",
            headers=auth_headers
        )

        stage_type = GenesisStage.INITIAL_PROMPT
        create_response = await async_client.post(
            f"/api/v1/genesis/flows/{novel_id}/stages/{stage_type.value}",
            headers=auth_headers,
            json={"config": {}}
        )
        created_stage = create_response.json()
        stage_id = created_stage["id"]

        # Act - Try general update (not completion)
        update_data = {
            "config": {"new_setting": True}
        }
        response = await async_client.put(
            f"/api/v1/genesis/stages/{stage_id}",
            headers=auth_headers,
            json=update_data
        )

        # Assert
        assert response.status_code == 501