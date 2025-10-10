"""Integration tests for Genesis Stage API endpoints.

Tests the /api/v1/genesis/ stage management endpoints in the new decoupled architecture.
"""

import pytest
from httpx import AsyncClient
from uuid import UUID

from src.schemas.enums import GenesisStage, StageStatus


@pytest.mark.integration
class TestGenesisStagesAPI:
    """Integration tests for Genesis Stage API endpoints."""

    @pytest.fixture
    async def test_flow(self, async_client: AsyncClient, auth_headers, test_novel):
        """Create a test Genesis flow for stage tests."""
        novel_id = test_novel.id
        response = await async_client.post(
            f"/api/v1/genesis/flows/{novel_id}",
            headers=auth_headers
        )
        return response.json()["data"]

    @pytest.mark.asyncio
    async def test_create_stage_success(self, async_client: AsyncClient, auth_headers, test_novel, test_flow):
        """Test creating a new Genesis stage."""
        # Arrange
        novel_id = test_novel.id
        stage_type = GenesisStage.INITIAL_PROMPT
        stage_data = {
            "config": {"max_iterations": 3, "temperature": 0.7},
            "iteration_count": 1
        }

        # Act
        response = await async_client.post(
            f"/api/v1/genesis/flows/{novel_id}/stages/{stage_type.value}",
            headers=auth_headers,
            json=stage_data
        )

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["code"] == 0
        assert data["msg"] == "Genesis stage created successfully"

        stage = data["data"]
        assert stage["flow_id"] == test_flow["id"]
        assert stage["stage"] == stage_type.value
        assert stage["status"] == StageStatus.PENDING.value
        assert stage["config"] == stage_data["config"]
        assert stage["iteration_count"] == stage_data["iteration_count"]
        assert "id" in stage
        assert "created_at" in stage

    @pytest.mark.asyncio
    async def test_get_stage_by_id(self, async_client: AsyncClient, auth_headers, test_novel, test_flow):
        """Test retrieving a stage by its ID."""
        # Arrange - Create a stage first
        novel_id = test_novel.id
        stage_type = GenesisStage.INITIAL_PROMPT
        create_response = await async_client.post(
            f"/api/v1/genesis/flows/{novel_id}/stages/{stage_type.value}",
            headers=auth_headers,
            json={"config": {}, "iteration_count": 1}
        )
        created_stage = create_response.json()["data"]
        stage_id = created_stage["id"]

        # Act
        response = await async_client.get(
            f"/api/v1/genesis/stages/{stage_id}",
            headers=auth_headers
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["msg"] == "Genesis stage retrieved successfully"

        stage = data["data"]
        assert stage["id"] == stage_id
        assert stage["stage"] == stage_type.value

    @pytest.mark.asyncio
    async def test_get_stage_by_flow_and_stage(self, async_client: AsyncClient, auth_headers, test_novel, test_flow):
        """Test retrieving a stage by flow ID and stage type."""
        # Arrange - Create a stage first
        novel_id = test_novel.id
        stage_type = GenesisStage.WORLD_BUILDING
        flow_id = test_flow["id"]
        await async_client.post(
            f"/api/v1/genesis/flows/{novel_id}/stages/{stage_type.value}",
            headers=auth_headers,
            json={"config": {}, "iteration_count": 1}
        )

        # Act
        response = await async_client.get(
            f"/api/v1/genesis/stages/by-flow-and-stage/{flow_id}/{stage_type.value}",
            headers=auth_headers
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0

        stage = data["data"]
        assert stage["flow_id"] == flow_id
        assert stage["stage"] == stage_type.value

    @pytest.mark.asyncio
    async def test_update_stage_complete(self, async_client: AsyncClient, auth_headers, test_novel, test_flow):
        """Test completing a stage."""
        # Arrange - Create a stage first
        novel_id = test_novel.id
        stage_type = GenesisStage.INITIAL_PROMPT
        create_response = await async_client.post(
            f"/api/v1/genesis/flows/{novel_id}/stages/{stage_type.value}",
            headers=auth_headers,
            json={"config": {}, "iteration_count": 1}
        )
        created_stage = create_response.json()["data"]
        stage_id = created_stage["id"]

        # Act - Complete the stage
        update_data = {
            "status": StageStatus.COMPLETED.value,
            "result": {"output": "Stage completed successfully"},
            "metrics": {"duration_ms": 1500}
        }
        response = await async_client.patch(
            f"/api/v1/genesis/stages/{stage_id}",
            headers=auth_headers,
            json=update_data
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["msg"] == "Genesis stage updated successfully"

        stage = data["data"]
        assert stage["status"] == StageStatus.COMPLETED.value
        assert stage["result"] == update_data["result"]
        assert stage["metrics"] == update_data["metrics"]

    @pytest.mark.asyncio
    async def test_update_stage_failed(self, async_client: AsyncClient, auth_headers, test_novel, test_flow):
        """Test failing a stage."""
        # Arrange - Create a stage first
        novel_id = test_novel.id
        stage_type = GenesisStage.INITIAL_PROMPT
        create_response = await async_client.post(
            f"/api/v1/genesis/flows/{novel_id}/stages/{stage_type.value}",
            headers=auth_headers,
            json={"config": {}, "iteration_count": 1}
        )
        created_stage = create_response.json()["data"]
        stage_id = created_stage["id"]

        # Act - Fail the stage
        update_data = {
            "status": StageStatus.FAILED.value,
            "result": {"error": "Stage failed due to validation error"}
        }
        response = await async_client.patch(
            f"/api/v1/genesis/stages/{stage_id}",
            headers=auth_headers,
            json=update_data
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0

        stage = data["data"]
        assert stage["status"] == StageStatus.FAILED.value
        assert stage["result"] == update_data["result"]

    @pytest.mark.asyncio
    async def test_update_stage_config(self, async_client: AsyncClient, auth_headers, test_novel, test_flow):
        """Test updating stage configuration."""
        # Arrange - Create a stage first
        novel_id = test_novel.id
        stage_type = GenesisStage.INITIAL_PROMPT
        create_response = await async_client.post(
            f"/api/v1/genesis/flows/{novel_id}/stages/{stage_type.value}",
            headers=auth_headers,
            json={"config": {"temperature": 0.5}, "iteration_count": 1}
        )
        created_stage = create_response.json()["data"]
        stage_id = created_stage["id"]

        # Act - Update config
        update_data = {
            "config": {"temperature": 0.8, "max_tokens": 1000}
        }
        response = await async_client.patch(
            f"/api/v1/genesis/stages/{stage_id}",
            headers=auth_headers,
            json=update_data
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0

        stage = data["data"]
        assert stage["config"] == update_data["config"]

    @pytest.mark.asyncio
    async def test_increment_stage_iteration(self, async_client: AsyncClient, auth_headers, test_novel, test_flow):
        """Test incrementing stage iteration count."""
        # Arrange - Create a stage first
        novel_id = test_novel.id
        stage_type = GenesisStage.INITIAL_PROMPT
        create_response = await async_client.post(
            f"/api/v1/genesis/flows/{novel_id}/stages/{stage_type.value}",
            headers=auth_headers,
            json={"config": {}, "iteration_count": 1}
        )
        created_stage = create_response.json()["data"]
        stage_id = created_stage["id"]
        original_count = created_stage["iteration_count"]

        # Act
        response = await async_client.post(
            f"/api/v1/genesis/stages/{stage_id}/increment-iteration",
            headers=auth_headers
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["msg"] == "Genesis stage iteration incremented successfully"

        stage = data["data"]
        assert stage["iteration_count"] == original_count + 1

    @pytest.mark.asyncio
    async def test_list_stages_by_flow(self, async_client: AsyncClient, auth_headers, test_novel, test_flow):
        """Test listing stages filtered by flow ID."""
        # Arrange - Create multiple stages
        novel_id = test_novel.id
        flow_id = test_flow["id"]
        stage_types = [GenesisStage.INITIAL_PROMPT, GenesisStage.WORLD_BUILDING]

        for stage_type in stage_types:
            await async_client.post(
                f"/api/v1/genesis/flows/{novel_id}/stages/{stage_type.value}",
                headers=auth_headers,
                json={"config": {}, "iteration_count": 1}
            )

        # Act
        response = await async_client.get(
            f"/api/v1/genesis/stages?flow_id={flow_id}&limit=10&offset=0",
            headers=auth_headers
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["msg"] == "Genesis stages retrieved successfully"

        stages = data["data"]
        assert isinstance(stages, list)
        assert len(stages) >= 2
        for stage in stages:
            assert stage["flow_id"] == flow_id

    @pytest.mark.asyncio
    async def test_list_stages_requires_flow_id(self, async_client: AsyncClient, auth_headers):
        """Test that listing stages requires flow_id for security."""
        # Act - Try to list without flow_id
        response = await async_client.get(
            "/api/v1/genesis/stages?limit=10&offset=0",
            headers=auth_headers
        )

        # Assert
        assert response.status_code == 400
        data = response.json()
        assert "flow_id parameter is required" in data["detail"]

    @pytest.mark.asyncio
    async def test_delete_stage(self, async_client: AsyncClient, auth_headers, test_novel, test_flow):
        """Test deleting a stage."""
        # Arrange - Create a stage first
        novel_id = test_novel.id
        stage_type = GenesisStage.INITIAL_PROMPT
        create_response = await async_client.post(
            f"/api/v1/genesis/flows/{novel_id}/stages/{stage_type.value}",
            headers=auth_headers,
            json={"config": {}, "iteration_count": 1}
        )
        created_stage = create_response.json()["data"]
        stage_id = created_stage["id"]

        # Act
        response = await async_client.delete(
            f"/api/v1/genesis/stages/{stage_id}",
            headers=auth_headers
        )

        # Assert
        assert response.status_code == 204

        # Verify deletion
        get_response = await async_client.get(
            f"/api/v1/genesis/stages/{stage_id}",
            headers=auth_headers
        )
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_stage_rounds_empty(self, async_client: AsyncClient, auth_headers, test_novel, test_flow):
        """Test getting conversation rounds for a stage with no sessions."""
        # Arrange - Create a stage first
        novel_id = test_novel.id
        stage_type = GenesisStage.INITIAL_PROMPT
        create_response = await async_client.post(
            f"/api/v1/genesis/flows/{novel_id}/stages/{stage_type.value}",
            headers=auth_headers,
            json={"config": {}, "iteration_count": 1}
        )
        created_stage = create_response.json()["data"]
        stage_id = created_stage["id"]

        # Act
        response = await async_client.get(
            f"/api/v1/genesis/stages/{stage_id}/rounds?limit=10&offset=0",
            headers=auth_headers
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert "Retrieved 0 conversation rounds" in data["msg"]

        rounds = data["data"]
        assert isinstance(rounds, list)
        assert len(rounds) == 0

    @pytest.mark.asyncio
    async def test_stage_ownership_validation(self, async_client: AsyncClient, auth_headers, other_user_headers, test_novel, test_flow):
        """Test that users can only access their own stages."""
        # Arrange - Create a stage with first user
        novel_id = test_novel.id
        stage_type = GenesisStage.INITIAL_PROMPT
        create_response = await async_client.post(
            f"/api/v1/genesis/flows/{novel_id}/stages/{stage_type.value}",
            headers=auth_headers,
            json={"config": {}, "iteration_count": 1}
        )
        created_stage = create_response.json()["data"]
        stage_id = created_stage["id"]

        # Act - Try to access with different user
        response = await async_client.get(
            f"/api/v1/genesis/stages/{stage_id}",
            headers=other_user_headers
        )

        # Assert - Should be forbidden or not found
        assert response.status_code in [403, 404]

    @pytest.mark.asyncio
    async def test_stage_not_found(self, async_client: AsyncClient, auth_headers):
        """Test accessing non-existent stage returns 404."""
        # Arrange
        non_existent_id = "00000000-0000-0000-0000-000000000000"

        # Act
        response = await async_client.get(
            f"/api/v1/genesis/stages/{non_existent_id}",
            headers=auth_headers
        )

        # Assert
        assert response.status_code == 404