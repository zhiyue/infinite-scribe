"""Integration tests for Genesis Flows API.

Tests the complete Genesis flows API according to the design document,
ensuring proper novel ownership validation and API functionality.
"""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.genesis_flows import GenesisFlow
from src.models.novel import Novel
from src.models.user import User
from src.schemas.enums import GenesisStage, GenesisStatus


class TestGenesisFlowsAPI:
    """Test suite for Genesis Flows API endpoints."""

    @pytest.fixture
    async def test_user(self, pg_session: AsyncSession) -> User:
        """Create a test user for the tests."""
        user = User(
            username=f"testuser_{uuid.uuid4().hex[:8]}",
            email=f"test_{uuid.uuid4().hex[:8]}@example.com",
            password_hash="test_hash",
        )
        pg_session.add(user)
        await pg_session.commit()
        await pg_session.refresh(user)
        return user

    @pytest.fixture
    async def other_user(self, pg_session: AsyncSession) -> User:
        """Create another test user for ownership validation tests."""
        user = User(
            username=f"otheruser_{uuid.uuid4().hex[:8]}",
            email=f"other_{uuid.uuid4().hex[:8]}@example.com",
            password_hash="test_hash",
        )
        pg_session.add(user)
        await pg_session.commit()
        await pg_session.refresh(user)
        return user

    @pytest.fixture
    async def test_novel(self, pg_session: AsyncSession, test_user: User) -> Novel:
        """Create a test novel owned by test_user."""
        novel = Novel(
            user_id=test_user.id,
            title="Test Novel",
            theme="Test Theme",
            writing_style="Test Style",
            target_chapters=10,
        )
        pg_session.add(novel)
        await pg_session.commit()
        await pg_session.refresh(novel)
        return novel

    @pytest.fixture
    async def other_novel(self, pg_session: AsyncSession, other_user: User) -> Novel:
        """Create a test novel owned by other_user."""
        novel = Novel(
            user_id=other_user.id,
            title="Other Novel",
            theme="Other Theme",
            writing_style="Other Style",
            target_chapters=5,
        )
        pg_session.add(novel)
        await pg_session.commit()
        await pg_session.refresh(novel)
        return novel

    @pytest.fixture
    def auth_headers(self, test_user: User) -> dict[str, str]:
        """Create authentication headers for test_user."""
        # This would normally use JWT tokens, but for testing we'll mock it
        # Adjust based on your actual authentication implementation
        return {"Authorization": f"Bearer test_token_{test_user.id}"}

    @pytest.fixture
    def other_auth_headers(self, other_user: User) -> dict[str, str]:
        """Create authentication headers for other_user."""
        return {"Authorization": f"Bearer test_token_{other_user.id}"}

    async def test_create_genesis_flow_success(
        self,
        client: TestClient,
        test_novel: Novel,
        auth_headers: dict[str, str],
        pg_session: AsyncSession,
    ):
        """Test successful creation of a Genesis flow."""
        url = f"/api/v1/genesis/flows/{test_novel.id}"

        response = client.post(url, headers=auth_headers)

        assert response.status_code == 201
        data = response.json()
        assert data["code"] == 0
        assert data["msg"] == "Genesis flow created/ensured successfully"

        flow_data = data["data"]
        assert flow_data["novel_id"] == str(test_novel.id)
        assert flow_data["status"] == GenesisStatus.IN_PROGRESS.value
        assert flow_data["current_stage"] == GenesisStage.INITIAL_PROMPT.value
        assert flow_data["version"] == 1
        assert isinstance(flow_data["state"], dict)
        assert "created_at" in flow_data
        assert "updated_at" in flow_data

        # Verify flow was created in database
        from sqlalchemy import select

        result = await pg_session.execute(select(GenesisFlow).where(GenesisFlow.novel_id == test_novel.id))
        db_flow = result.scalar_one()
        assert db_flow.status == GenesisStatus.IN_PROGRESS
        assert db_flow.current_stage == GenesisStage.INITIAL_PROMPT

    async def test_create_genesis_flow_idempotent(
        self,
        client: TestClient,
        test_novel: Novel,
        auth_headers: dict[str, str],
        pg_session: AsyncSession,
    ):
        """Test that creating a flow multiple times is idempotent."""
        url = f"/api/v1/genesis/flows/{test_novel.id}"

        # First creation
        response1 = client.post(url, headers=auth_headers)
        assert response1.status_code == 201
        flow_id_1 = response1.json()["data"]["id"]

        # Second creation should return the same flow
        response2 = client.post(url, headers=auth_headers)
        assert response2.status_code == 201
        flow_id_2 = response2.json()["data"]["id"]

        assert flow_id_1 == flow_id_2

    async def test_create_genesis_flow_unauthorized(
        self,
        client: TestClient,
        other_novel: Novel,
        auth_headers: dict[str, str],
    ):
        """Test that creating a flow for another user's novel fails."""
        url = f"/api/v1/genesis/flows/{other_novel.id}"

        response = client.post(url, headers=auth_headers)

        assert response.status_code == 404
        assert "Novel not found or you don't have permission" in response.json()["detail"]

    async def test_create_genesis_flow_no_auth(
        self,
        client: TestClient,
        test_novel: Novel,
    ):
        """Test that creating a flow without authentication fails."""
        url = f"/api/v1/genesis/flows/{test_novel.id}"

        response = client.post(url)

        assert response.status_code == 401

    async def test_get_genesis_flow_success(
        self,
        client: TestClient,
        test_novel: Novel,
        auth_headers: dict[str, str],
        pg_session: AsyncSession,
    ):
        """Test successful retrieval of a Genesis flow."""
        # First create a flow
        flow = GenesisFlow(
            novel_id=test_novel.id,
            status=GenesisStatus.IN_PROGRESS,
            current_stage=GenesisStage.WORLDVIEW,
            version=1,
            state={"test": "data"},
        )
        pg_session.add(flow)
        await pg_session.commit()
        await pg_session.refresh(flow)

        url = f"/api/v1/genesis/flows/{test_novel.id}"

        response = client.get(url, headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["msg"] == "Genesis flow retrieved successfully"

        flow_data = data["data"]
        assert flow_data["id"] == str(flow.id)
        assert flow_data["novel_id"] == str(test_novel.id)
        assert flow_data["status"] == GenesisStatus.IN_PROGRESS.value
        assert flow_data["current_stage"] == GenesisStage.WORLDVIEW.value
        assert flow_data["state"] == {"test": "data"}

    async def test_get_genesis_flow_not_found(
        self,
        client: TestClient,
        test_novel: Novel,
        auth_headers: dict[str, str],
    ):
        """Test getting a flow that doesn't exist."""
        url = f"/api/v1/genesis/flows/{test_novel.id}"

        response = client.get(url, headers=auth_headers)

        assert response.status_code == 404
        assert "Genesis flow not found for this novel" in response.json()["detail"]

    async def test_get_genesis_flow_unauthorized(
        self,
        client: TestClient,
        other_novel: Novel,
        auth_headers: dict[str, str],
    ):
        """Test that getting a flow for another user's novel fails."""
        url = f"/api/v1/genesis/flows/{other_novel.id}"

        response = client.get(url, headers=auth_headers)

        assert response.status_code == 404
        assert "Novel not found or you don't have permission" in response.json()["detail"]

    async def test_update_genesis_flow_success(
        self,
        client: TestClient,
        test_novel: Novel,
        auth_headers: dict[str, str],
        pg_session: AsyncSession,
    ):
        """Test successful update of a Genesis flow."""
        # Create a flow first
        flow = GenesisFlow(
            novel_id=test_novel.id,
            status=GenesisStatus.IN_PROGRESS,
            current_stage=GenesisStage.INITIAL_PROMPT,
            version=1,
            state={},
        )
        pg_session.add(flow)
        await pg_session.commit()
        await pg_session.refresh(flow)

        url = f"/api/v1/genesis/flows/{flow.id}"
        update_data = {"current_stage": GenesisStage.WORLDVIEW.value}

        response = client.patch(
            url,
            json=update_data,
            headers={**auth_headers, "If-Match": '"1"'},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["msg"] == "Genesis flow updated successfully"

        flow_data = data["data"]
        assert flow_data["current_stage"] == GenesisStage.WORLDVIEW.value
        assert flow_data["version"] == 2  # Version should increment

    async def test_update_genesis_flow_version_conflict(
        self,
        client: TestClient,
        test_novel: Novel,
        auth_headers: dict[str, str],
        pg_session: AsyncSession,
    ):
        """Test version conflict when updating a Genesis flow."""
        # Create a flow first
        flow = GenesisFlow(
            novel_id=test_novel.id,
            status=GenesisStatus.IN_PROGRESS,
            current_stage=GenesisStage.INITIAL_PROMPT,
            version=2,  # Higher version
            state={},
        )
        pg_session.add(flow)
        await pg_session.commit()
        await pg_session.refresh(flow)

        url = f"/api/v1/genesis/flows/{flow.id}"
        update_data = {"current_stage": GenesisStage.WORLDVIEW.value}

        response = client.patch(
            url,
            json=update_data,
            headers={**auth_headers, "If-Match": '"1"'},  # Wrong version
        )

        assert response.status_code == 409
        assert "Version conflict" in response.json()["detail"]

    async def test_list_genesis_flows_success(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        pg_session: AsyncSession,
        test_user: User,
    ):
        """Test successful listing of Genesis flows."""
        # Create test novels and flows
        novel1 = Novel(
            user_id=test_user.id,
            title="Novel 1",
            theme="Theme 1",
            writing_style="Style 1",
            target_chapters=5,
        )
        novel2 = Novel(
            user_id=test_user.id,
            title="Novel 2",
            theme="Theme 2",
            writing_style="Style 2",
            target_chapters=10,
        )
        pg_session.add_all([novel1, novel2])
        await pg_session.commit()
        await pg_session.refresh(novel1)
        await pg_session.refresh(novel2)

        flow1 = GenesisFlow(
            novel_id=novel1.id,
            status=GenesisStatus.IN_PROGRESS,
            current_stage=GenesisStage.INITIAL_PROMPT,
            version=1,
            state={},
        )
        flow2 = GenesisFlow(
            novel_id=novel2.id,
            status=GenesisStatus.COMPLETED,
            current_stage=GenesisStage.FINISHED,
            version=1,
            state={},
        )
        pg_session.add_all([flow1, flow2])
        await pg_session.commit()

        # Test listing all IN_PROGRESS flows (default)
        response = client.get("/api/v1/genesis/flows", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert len(data["data"]) >= 1  # At least one IN_PROGRESS flow

        # Test filtering by status
        response = client.get("/api/v1/genesis/flows?status=COMPLETED", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        flows = data["data"]
        assert all(flow["status"] == "COMPLETED" for flow in flows)

    async def test_nonexistent_novel(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ):
        """Test operations on a non-existent novel."""
        fake_novel_id = uuid.uuid4()
        url = f"/api/v1/genesis/flows/{fake_novel_id}"

        response = client.post(url, headers=auth_headers)

        assert response.status_code == 404
        assert "Novel not found" in response.json()["detail"]

    async def test_api_headers_and_correlation_id(
        self,
        client: TestClient,
        test_novel: Novel,
        auth_headers: dict[str, str],
    ):
        """Test that proper headers and correlation IDs are returned."""
        url = f"/api/v1/genesis/flows/{test_novel.id}"
        correlation_id = "test-correlation-123"

        response = client.post(url, headers={**auth_headers, "X-Correlation-Id": correlation_id})

        assert response.status_code == 201

        # Check response headers
        assert "X-Correlation-Id" in response.headers
        assert response.headers["X-Correlation-Id"] == correlation_id
        assert "ETag" in response.headers

        # ETag should be version in quotes
        etag = response.headers["ETag"]
        assert etag.startswith('"') and etag.endswith('"')
        version = int(etag.strip('"'))
        assert version >= 1
