"""Integration tests for Genesis Flow API endpoints.

Tests the /api/v1/genesis/ flow management endpoints in the new decoupled architecture.
"""

import pytest
from httpx import AsyncClient
from uuid import UUID

from src.schemas.enums import GenesisStatus, GenesisStage


@pytest.mark.integration
class TestGenesisFlowsAPI:
    """Integration tests for Genesis Flow API endpoints."""

    @pytest.mark.asyncio
    async def test_create_or_get_flow_creates_new_flow(self, async_client: AsyncClient, auth_headers, test_novel):
        """Test creating a new Genesis flow for a novel."""
        # Arrange
        novel_id = test_novel.id

        # Act - Create Genesis flow
        response = await async_client.post(
            f"/api/v1/genesis/flows/{novel_id}",
            headers=auth_headers
        )

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["code"] == 0
        assert data["msg"] == "Genesis flow created/ensured successfully"

        flow_data = data["data"]
        assert flow_data["novel_id"] == str(novel_id)
        assert flow_data["status"] == GenesisStatus.IN_PROGRESS.value
        assert flow_data["current_stage"] == GenesisStage.INITIAL_PROMPT.value
        assert flow_data["version"] == 1
        assert isinstance(flow_data["state"], dict)
        assert "id" in flow_data
        assert "created_at" in flow_data
        assert "updated_at" in flow_data

    @pytest.mark.asyncio
    async def test_create_or_get_flow_returns_existing_flow(self, async_client: AsyncClient, auth_headers, test_novel):
        """Test that creating a flow again returns the existing flow (idempotent)."""
        # Arrange - Create a flow first
        novel_id = test_novel.id
        first_response = await async_client.post(
            f"/api/v1/genesis/flows/{novel_id}",
            headers=auth_headers
        )
        first_flow = first_response.json()["data"]

        # Act - Try to create again
        second_response = await async_client.post(
            f"/api/v1/genesis/flows/{novel_id}",
            headers=auth_headers
        )

        # Assert - Should return same flow
        assert second_response.status_code == 201
        second_flow = second_response.json()["data"]
        assert first_flow["id"] == second_flow["id"]
        assert first_flow["version"] == second_flow["version"]
        assert first_flow["created_at"] == second_flow["created_at"]

    @pytest.mark.asyncio
    async def test_get_flow_by_novel_success(self, async_client: AsyncClient, auth_headers, test_novel):
        """Test retrieving a flow by novel ID."""
        # Arrange - Create a flow first
        novel_id = test_novel.id
        create_response = await async_client.post(
            f"/api/v1/genesis/flows/{novel_id}",
            headers=auth_headers
        )
        created_flow = create_response.json()["data"]

        # Act - Get the flow
        response = await async_client.get(
            f"/api/v1/genesis/flows/{novel_id}",
            headers=auth_headers
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["msg"] == "Genesis flow retrieved successfully"

        flow_data = data["data"]
        assert flow_data["id"] == created_flow["id"]
        assert flow_data["novel_id"] == str(novel_id)
        assert flow_data["status"] == GenesisStatus.IN_PROGRESS.value

    @pytest.mark.asyncio
    async def test_get_flow_by_novel_not_found(self, async_client: AsyncClient, auth_headers, test_novel):
        """Test retrieving a non-existent flow returns 404."""
        # Arrange - Use a novel that doesn't have a flow
        novel_id = test_novel.id

        # Act - Try to get non-existent flow
        response = await async_client.get(
            f"/api/v1/genesis/flows/{novel_id}",
            headers=auth_headers
        )

        # Assert
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_update_flow_advance_stage(self, async_client: AsyncClient, auth_headers, test_novel):
        """Test updating a flow to advance to next stage."""
        # Arrange - Create a flow first
        novel_id = test_novel.id
        create_response = await async_client.post(
            f"/api/v1/genesis/flows/{novel_id}",
            headers=auth_headers
        )
        created_flow = create_response.json()["data"]
        flow_id = created_flow["id"]

        # Act - Update flow to advance stage
        update_data = {
            "current_stage": GenesisStage.WORLD_BUILDING.value,
            "expected_version": 1
        }
        response = await async_client.patch(
            f"/api/v1/genesis/flows/{flow_id}",
            headers=auth_headers,
            json=update_data
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["msg"] == "Genesis flow updated successfully"

        flow_data = data["data"]
        assert flow_data["current_stage"] == GenesisStage.WORLD_BUILDING.value
        assert flow_data["version"] == 2

    @pytest.mark.asyncio
    async def test_update_flow_complete(self, async_client: AsyncClient, auth_headers, test_novel):
        """Test completing a Genesis flow."""
        # Arrange - Create a flow first
        novel_id = test_novel.id
        create_response = await async_client.post(
            f"/api/v1/genesis/flows/{novel_id}",
            headers=auth_headers
        )
        created_flow = create_response.json()["data"]
        flow_id = created_flow["id"]

        # Act - Complete the flow
        update_data = {
            "status": GenesisStatus.COMPLETED.value,
            "expected_version": 1
        }
        response = await async_client.patch(
            f"/api/v1/genesis/flows/{flow_id}",
            headers=auth_headers,
            json=update_data
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0

        flow_data = data["data"]
        assert flow_data["status"] == GenesisStatus.COMPLETED.value
        assert flow_data["version"] == 2

    @pytest.mark.asyncio
    async def test_update_flow_version_conflict(self, async_client: AsyncClient, auth_headers, test_novel):
        """Test updating a flow with wrong version causes conflict."""
        # Arrange - Create a flow first
        novel_id = test_novel.id
        create_response = await async_client.post(
            f"/api/v1/genesis/flows/{novel_id}",
            headers=auth_headers
        )
        created_flow = create_response.json()["data"]
        flow_id = created_flow["id"]

        # Act - Try to update with wrong version
        update_data = {
            "current_stage": GenesisStage.WORLD_BUILDING.value,
            "expected_version": 999  # Wrong version
        }
        response = await async_client.patch(
            f"/api/v1/genesis/flows/{flow_id}",
            headers=auth_headers,
            json=update_data
        )

        # Assert
        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_list_flows_by_status(self, async_client: AsyncClient, auth_headers, test_novel):
        """Test listing flows filtered by status."""
        # Arrange - Create a flow first
        novel_id = test_novel.id
        await async_client.post(
            f"/api/v1/genesis/flows/{novel_id}",
            headers=auth_headers
        )

        # Act - List flows with IN_PROGRESS status
        response = await async_client.get(
            f"/api/v1/genesis/flows?status={GenesisStatus.IN_PROGRESS.value}&limit=10&offset=0",
            headers=auth_headers
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["msg"] == "Genesis flows retrieved successfully"

        flows = data["data"]
        assert isinstance(flows, list)
        assert len(flows) >= 1
        for flow in flows:
            assert flow["status"] == GenesisStatus.IN_PROGRESS.value

    @pytest.mark.asyncio
    async def test_delete_flow_not_implemented(self, async_client: AsyncClient, auth_headers, test_novel):
        """Test that flow deletion returns 501 (not implemented)."""
        # Arrange - Create a flow first
        novel_id = test_novel.id
        create_response = await async_client.post(
            f"/api/v1/genesis/flows/{novel_id}",
            headers=auth_headers
        )
        created_flow = create_response.json()["data"]
        flow_id = created_flow["id"]

        # Act - Try to delete flow
        response = await async_client.delete(
            f"/api/v1/genesis/flows/{flow_id}",
            headers=auth_headers
        )

        # Assert
        assert response.status_code == 501

    @pytest.mark.asyncio
    async def test_flow_ownership_validation(self, async_client: AsyncClient, auth_headers, other_user_headers, test_novel):
        """Test that users can only access their own flows."""
        # Arrange - Create a flow with first user
        novel_id = test_novel.id
        await async_client.post(
            f"/api/v1/genesis/flows/{novel_id}",
            headers=auth_headers
        )

        # Act - Try to access with different user
        response = await async_client.get(
            f"/api/v1/genesis/flows/{novel_id}",
            headers=other_user_headers
        )

        # Assert - Should be forbidden or not found
        assert response.status_code in [403, 404]

    @pytest.mark.asyncio
    async def test_flow_invalid_novel_id(self, async_client: AsyncClient, auth_headers):
        """Test creating flow with invalid novel ID."""
        # Arrange
        invalid_novel_id = "00000000-0000-0000-0000-000000000000"

        # Act
        response = await async_client.post(
            f"/api/v1/genesis/flows/{invalid_novel_id}",
            headers=auth_headers
        )

        # Assert
        assert response.status_code in [404, 500]