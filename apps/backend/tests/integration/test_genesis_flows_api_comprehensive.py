"""Comprehensive integration tests for Genesis Flows API.

Tests the complete Genesis flows API according to the design document,
ensuring proper novel ownership validation and API functionality.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.main import app
from src.database import get_db
from src.middleware.auth import get_current_user, require_auth
from src.models.genesis_flows import GenesisFlow
from src.models.novel import Novel
from src.models.user import User
from src.schemas.enums import GenesisStage, GenesisStatus


class TestGenesisFlowsAPIComprehensive:
    """Comprehensive test suite for Genesis Flows API endpoints."""

    @pytest.fixture
    async def test_user(self, pg_session: AsyncSession) -> User:
        """Create a test user for the tests."""
        user = User(
            username=f"testuser_{uuid.uuid4().hex[:8]}",
            email=f"test_{uuid.uuid4().hex[:8]}@example.com",
            password_hash="test_hash",
            is_active=True,
            is_verified=True,
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
            is_active=True,
            is_verified=True,
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
    def client(self, pg_session: AsyncSession, test_user: User) -> TestClient:
        """Create test client with proper dependency overrides."""
        # Override database dependency
        app.dependency_overrides[get_db] = lambda: pg_session

        # Override authentication dependencies
        app.dependency_overrides[get_current_user] = lambda: test_user
        app.dependency_overrides[require_auth] = lambda: test_user

        client = TestClient(app)

        yield client

        # Cleanup
        app.dependency_overrides.clear()

    @pytest.fixture
    def other_client(self, pg_session: AsyncSession, other_user: User) -> TestClient:
        """Create test client for other_user with proper dependency overrides."""
        # Override database dependency
        app.dependency_overrides[get_db] = lambda: pg_session

        # Override authentication dependencies
        app.dependency_overrides[get_current_user] = lambda: other_user
        app.dependency_overrides[require_auth] = lambda: other_user

        client = TestClient(app)

        yield client

        # Cleanup
        app.dependency_overrides.clear()

    async def test_create_genesis_flow_success(
        self,
        client: TestClient,
        test_novel: Novel,
        pg_session: AsyncSession,
    ):
        """Test successful creation of a Genesis flow."""
        url = f"/api/v1/genesis/flows/{test_novel.id}"

        response = client.post(url)

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
        result = await pg_session.execute(
            select(GenesisFlow).where(GenesisFlow.novel_id == test_novel.id)
        )
        db_flow = result.scalar_one()
        assert db_flow.status == GenesisStatus.IN_PROGRESS
        assert db_flow.current_stage == GenesisStage.INITIAL_PROMPT

    async def test_create_genesis_flow_idempotent(
        self,
        client: TestClient,
        test_novel: Novel,
        pg_session: AsyncSession,
    ):
        """Test that creating a flow multiple times is idempotent."""
        url = f"/api/v1/genesis/flows/{test_novel.id}"

        # First creation
        response1 = client.post(url)
        assert response1.status_code == 201
        flow_id_1 = response1.json()["data"]["id"]

        # Second creation should return the same flow
        response2 = client.post(url)
        assert response2.status_code == 201
        flow_id_2 = response2.json()["data"]["id"]

        assert flow_id_1 == flow_id_2

        # Verify only one flow exists in database
        result = await pg_session.execute(
            select(GenesisFlow).where(GenesisFlow.novel_id == test_novel.id)
        )
        flows = result.scalars().all()
        assert len(flows) == 1

    async def test_create_genesis_flow_unauthorized(
        self,
        other_client: TestClient,
        test_novel: Novel,
    ):
        """Test that creating a flow for another user's novel fails."""
        url = f"/api/v1/genesis/flows/{test_novel.id}"

        response = other_client.post(url)

        assert response.status_code == 404
        assert "Novel not found or you don't have permission" in response.json()["detail"]

    async def test_create_genesis_flow_no_auth(self, test_novel: Novel):
        """Test that creating a flow without authentication fails."""
        # Create client without auth override
        no_auth_client = TestClient(app)
        url = f"/api/v1/genesis/flows/{test_novel.id}"

        response = no_auth_client.post(url)

        assert response.status_code == 401

    async def test_get_genesis_flow_success(
        self,
        client: TestClient,
        test_novel: Novel,
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

        response = client.get(url)

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
    ):
        """Test getting a flow that doesn't exist."""
        url = f"/api/v1/genesis/flows/{test_novel.id}"

        response = client.get(url)

        assert response.status_code == 404
        assert "Genesis flow not found for this novel" in response.json()["detail"]

    async def test_get_genesis_flow_unauthorized(
        self,
        other_client: TestClient,
        test_novel: Novel,
    ):
        """Test that getting a flow for another user's novel fails."""
        url = f"/api/v1/genesis/flows/{test_novel.id}"

        response = other_client.get(url)

        assert response.status_code == 404
        assert "Novel not found or you don't have permission" in response.json()["detail"]

    async def test_update_genesis_flow_success(
        self,
        client: TestClient,
        test_novel: Novel,
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
            headers={"If-Match": '"1"'},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["msg"] == "Genesis flow updated successfully"

        flow_data = data["data"]
        assert flow_data["current_stage"] == GenesisStage.WORLDVIEW.value
        assert flow_data["version"] == 2  # Version should increment

        # Verify in database
        await pg_session.refresh(flow)
        assert flow.current_stage == GenesisStage.WORLDVIEW
        assert flow.version == 2

    async def test_update_genesis_flow_complete_status(
        self,
        client: TestClient,
        test_novel: Novel,
        pg_session: AsyncSession,
    ):
        """Test updating a Genesis flow to completed status."""
        # Create a flow first
        flow = GenesisFlow(
            novel_id=test_novel.id,
            status=GenesisStatus.IN_PROGRESS,
            current_stage=GenesisStage.PLOT_OUTLINE,
            version=1,
            state={},
        )
        pg_session.add(flow)
        await pg_session.commit()
        await pg_session.refresh(flow)

        url = f"/api/v1/genesis/flows/{flow.id}"
        update_data = {"status": GenesisStatus.COMPLETED.value}

        response = client.patch(
            url,
            json=update_data,
            headers={"If-Match": '"1"'},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["msg"] == "Genesis flow updated successfully"

        flow_data = data["data"]
        assert flow_data["status"] == GenesisStatus.COMPLETED.value
        assert flow_data["version"] == 2

    async def test_update_genesis_flow_version_conflict(
        self,
        client: TestClient,
        test_novel: Novel,
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
            headers={"If-Match": '"1"'},  # Wrong version
        )

        assert response.status_code == 409
        assert "Version conflict" in response.json()["detail"]

    async def test_update_genesis_flow_invalid_if_match(
        self,
        client: TestClient,
        test_novel: Novel,
        pg_session: AsyncSession,
    ):
        """Test invalid If-Match header."""
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
            headers={"If-Match": "invalid"},
        )

        assert response.status_code == 400
        assert "Invalid If-Match header" in response.json()["detail"]

    async def test_list_genesis_flows_success(
        self,
        client: TestClient,
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
        response = client.get("/api/v1/genesis/flows")

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert len(data["data"]) >= 1  # At least one IN_PROGRESS flow

        # Test filtering by status
        response = client.get("/api/v1/genesis/flows?status=COMPLETED")

        assert response.status_code == 200
        data = response.json()
        flows = data["data"]
        assert all(flow["status"] == "COMPLETED" for flow in flows)

    async def test_list_genesis_flows_pagination(
        self,
        client: TestClient,
        pg_session: AsyncSession,
        test_user: User,
    ):
        """Test pagination in listing Genesis flows."""
        # Create multiple novels and flows
        novels = []
        flows = []
        for i in range(5):
            novel = Novel(
                user_id=test_user.id,
                title=f"Novel {i}",
                theme=f"Theme {i}",
                writing_style=f"Style {i}",
                target_chapters=5,
            )
            novels.append(novel)

        pg_session.add_all(novels)
        await pg_session.commit()

        for novel in novels:
            await pg_session.refresh(novel)
            flow = GenesisFlow(
                novel_id=novel.id,
                status=GenesisStatus.IN_PROGRESS,
                current_stage=GenesisStage.INITIAL_PROMPT,
                version=1,
                state={},
            )
            flows.append(flow)

        pg_session.add_all(flows)
        await pg_session.commit()

        # Test pagination
        response = client.get("/api/v1/genesis/flows?limit=3&offset=0")
        assert response.status_code == 200
        data = response.json()
        first_page = data["data"]
        assert len(first_page) <= 3

        response = client.get("/api/v1/genesis/flows?limit=3&offset=3")
        assert response.status_code == 200
        data = response.json()
        second_page = data["data"]

        # Ensure no overlap between pages
        first_ids = {flow["id"] for flow in first_page}
        second_ids = {flow["id"] for flow in second_page}
        assert first_ids.isdisjoint(second_ids)

    async def test_nonexistent_novel(
        self,
        client: TestClient,
    ):
        """Test operations on a non-existent novel."""
        fake_novel_id = uuid.uuid4()
        url = f"/api/v1/genesis/flows/{fake_novel_id}"

        response = client.post(url)

        assert response.status_code == 404
        assert "Novel not found" in response.json()["detail"]

    async def test_api_headers_and_correlation_id(
        self,
        client: TestClient,
        test_novel: Novel,
    ):
        """Test that proper headers and correlation IDs are returned."""
        url = f"/api/v1/genesis/flows/{test_novel.id}"
        correlation_id = "test-correlation-123"

        response = client.post(
            url,
            headers={"X-Correlation-Id": correlation_id}
        )

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

    async def test_flow_state_persistence(
        self,
        client: TestClient,
        test_novel: Novel,
        pg_session: AsyncSession,
    ):
        """Test that flow state is properly persisted and retrieved."""
        # Create a flow with complex state
        flow = GenesisFlow(
            novel_id=test_novel.id,
            status=GenesisStatus.IN_PROGRESS,
            current_stage=GenesisStage.WORLDVIEW,
            version=1,
            state={
                "worldview": {
                    "magic_system": "elemental",
                    "technology_level": "medieval",
                    "regions": ["kingdom_a", "kingdom_b"]
                },
                "progress": {
                    "steps_completed": 3,
                    "total_steps": 10
                }
            },
        )
        pg_session.add(flow)
        await pg_session.commit()
        await pg_session.refresh(flow)

        url = f"/api/v1/genesis/flows/{test_novel.id}"

        response = client.get(url)

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["state"]["worldview"]["magic_system"] == "elemental"
        assert data["state"]["progress"]["steps_completed"] == 3

    async def test_flow_lifecycle_complete(
        self,
        client: TestClient,
        test_novel: Novel,
        pg_session: AsyncSession,
    ):
        """Test complete flow lifecycle from creation to completion."""
        # 1. Create flow
        url = f"/api/v1/genesis/flows/{test_novel.id}"
        response = client.post(url)
        assert response.status_code == 201
        flow_data = response.json()["data"]
        flow_id = flow_data["id"]

        # 2. Advance through stages
        stages = [
            GenesisStage.WORLDVIEW,
            GenesisStage.CHARACTERS,
            GenesisStage.PLOT_OUTLINE,
        ]

        for i, stage in enumerate(stages, 2):  # Start from version 2
            url = f"/api/v1/genesis/flows/{flow_id}"
            update_data = {"current_stage": stage.value}

            response = client.patch(
                url,
                json=update_data,
                headers={"If-Match": f'"{i-1}"'},
            )

            assert response.status_code == 200
            flow_data = response.json()["data"]
            assert flow_data["current_stage"] == stage.value
            assert flow_data["version"] == i

        # 3. Complete the flow
        url = f"/api/v1/genesis/flows/{flow_id}"
        update_data = {"status": GenesisStatus.COMPLETED.value}

        response = client.patch(
            url,
            json=update_data,
            headers={"If-Match": f'"{len(stages)+1}"'},
        )

        assert response.status_code == 200
        flow_data = response.json()["data"]
        assert flow_data["status"] == GenesisStatus.COMPLETED.value

    async def test_concurrent_flow_updates(
        self,
        test_novel: Novel,
        pg_session: AsyncSession,
        test_user: User,
    ):
        """Test concurrent updates to the same flow handle version conflicts."""
        # Create a flow
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

        # Create two separate clients
        client1 = TestClient(app)
        client2 = TestClient(app)

        # Override dependencies for both clients
        app.dependency_overrides[get_db] = lambda: pg_session
        app.dependency_overrides[get_current_user] = lambda: test_user
        app.dependency_overrides[require_auth] = lambda: test_user

        try:
            url = f"/api/v1/genesis/flows/{flow.id}"

            # First client updates successfully
            response1 = client1.patch(
                url,
                json={"current_stage": GenesisStage.WORLDVIEW.value},
                headers={"If-Match": '"1"'},
            )
            assert response1.status_code == 200

            # Second client tries to update with old version - should fail
            response2 = client2.patch(
                url,
                json={"current_stage": GenesisStage.CHARACTERS.value},
                headers={"If-Match": '"1"'},  # Old version
            )
            assert response2.status_code == 409
            assert "Version conflict" in response2.json()["detail"]

        finally:
            app.dependency_overrides.clear()

    async def test_invalid_uuid_parameters(self, client: TestClient):
        """Test handling of invalid UUID parameters."""
        # Invalid novel_id
        response = client.post("/api/v1/genesis/flows/invalid-uuid")
        assert response.status_code == 422  # Validation error

        # Invalid flow_id
        response = client.patch("/api/v1/genesis/flows/invalid-uuid", json={})
        assert response.status_code == 422  # Validation error

    async def test_empty_update_request(
        self,
        client: TestClient,
        test_novel: Novel,
        pg_session: AsyncSession,
    ):
        """Test update request with no valid changes."""
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

        response = client.patch(
            url,
            json={},  # Empty update
            headers={"If-Match": '"1"'},
        )

        assert response.status_code == 400
        assert "No valid updates provided" in response.json()["detail"]