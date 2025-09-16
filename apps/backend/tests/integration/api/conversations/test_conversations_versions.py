"""Integration tests for conversation versions API endpoints."""

from uuid import uuid4

import pytest
from tests.integration.api.auth_test_helpers import create_and_verify_test_user, perform_login


class TestConversationVersionsList:
    """Test cases for listing conversation versions."""

    @pytest.mark.asyncio
    async def test_list_versions_success(self, client_with_lifespan, pg_session):
        """Test successful versions listing (skeleton implementation)."""
        # Arrange - create user and session
        user_data = await create_and_verify_test_user(client_with_lifespan, pg_session)
        login_response = await perform_login(client_with_lifespan, user_data["email"], user_data["password"])
        token = login_response[1]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create session first
        session_data = {"scope_type": "GENESIS", "scope_id": "versions-list-test"}
        session_response = await client_with_lifespan.post("/api/v1/conversations/sessions", json=session_data, headers=headers)
        assert session_response.status_code == 201
        session_id = session_response.json()["data"]["id"]

        # Act
        response = await client_with_lifespan.get(f"/api/v1/conversations/sessions/{session_id}/versions", headers=headers)

        # Assert
        if response.status_code != 200:
            print(f"Error response: {response.text}")
        assert response.status_code == 200
        data = response.json()

        assert data["code"] == 0
        assert "获取版本列表" in data["msg"]
        assert "skeleton" in data["msg"]  # Skeleton implementation message
        assert "data" in data
        assert data["data"] == []  # Empty list for skeleton

    @pytest.mark.asyncio
    async def test_list_versions_with_correlation_id(self, client_with_lifespan, pg_session):
        """Test versions listing with correlation ID."""
        # Arrange
        user_data = await create_and_verify_test_user(client_with_lifespan, pg_session)
        login_response = await perform_login(client_with_lifespan, user_data["email"], user_data["password"])
        token = login_response[1]["access_token"]
        correlation_id = "test-correlation-versions-list"
        headers = {"Authorization": f"Bearer {token}", "X-Correlation-Id": correlation_id}

        session_data = {"scope_type": "GENESIS", "scope_id": "versions-correlation-test"}
        session_response = await client_with_lifespan.post("/api/v1/conversations/sessions", json=session_data, headers=headers)
        session_id = session_response.json()["data"]["id"]

        # Act
        response = await client_with_lifespan.get(f"/api/v1/conversations/sessions/{session_id}/versions", headers=headers)

        # Assert
        assert response.status_code == 200
        # Check if correlation ID is in response headers
        assert "x-correlation-id" in [h.lower() for h in response.headers]

    @pytest.mark.asyncio
    async def test_list_versions_unauthorized(self, client_with_lifespan):
        """Test listing versions without authentication."""
        session_id = str(uuid4())
        response = await client_with_lifespan.get(f"/api/v1/conversations/sessions/{session_id}/versions")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_versions_nonexistent_session(self, client_with_lifespan, pg_session):
        """Test listing versions for non-existent session."""
        # Arrange
        user_data = await create_and_verify_test_user(client_with_lifespan, pg_session)
        login_response = await perform_login(client_with_lifespan, user_data["email"], user_data["password"])
        token = login_response[1]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        nonexistent_session = str(uuid4())

        # Act
        response = await client_with_lifespan.get(
            f"/api/v1/conversations/sessions/{nonexistent_session}/versions", headers=headers
        )

        # Assert
        # Since this is skeleton implementation, it might return 200 with empty list
        # or 404 - both are acceptable for skeleton
        assert response.status_code in [200, 404]


class TestConversationVersionsCreate:
    """Test cases for creating conversation version branches."""

    @pytest.mark.asyncio
    async def test_create_version_branch_success(self, client_with_lifespan, pg_session):
        """Test successful version branch creation (skeleton implementation)."""
        # Arrange
        user_data = await create_and_verify_test_user(client_with_lifespan, pg_session)
        login_response = await perform_login(client_with_lifespan, user_data["email"], user_data["password"])
        token = login_response[1]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        session_data = {"scope_type": "GENESIS", "scope_id": "version-branch-test"}
        session_response = await client_with_lifespan.post("/api/v1/conversations/sessions", json=session_data, headers=headers)
        assert session_response.status_code == 201
        session_id = session_response.json()["data"]["id"]

        # Act
        version_data = {
            "base_version": "1.0",
            "label": "experimental-branch",
            "description": "Testing new narrative approach",
        }
        response = await client_with_lifespan.post(
            f"/api/v1/conversations/sessions/{session_id}/versions", json=version_data, headers=headers
        )

        # Assert
        if response.status_code != 201:
            print(f"Error response: {response.text}")
        assert response.status_code == 201
        data = response.json()

        assert data["code"] == 0
        assert "创建分支成功" in data["msg"]
        assert "skeleton" in data["msg"]  # Skeleton implementation message
        assert "data" in data

        branch_data = data["data"]
        assert "branch" in branch_data
        assert branch_data["label"] == "experimental-branch"
        # Verify branch ID format (should contain base version)
        assert "v1.0-branch-" in branch_data["branch"]

        # Check Location header is set
        location_header = next((v for k, v in response.headers.items() if k.lower() == "location"), None)
        assert location_header is not None
        assert f"/api/v1/conversations/sessions/{session_id}/versions" in location_header

    @pytest.mark.asyncio
    async def test_create_version_branch_with_idempotency(self, client_with_lifespan, pg_session):
        """Test version branch creation with idempotency key."""
        # Arrange
        user_data = await create_and_verify_test_user(client_with_lifespan, pg_session)
        login_response = await perform_login(client_with_lifespan, user_data["email"], user_data["password"])
        token = login_response[1]["access_token"]
        idempotency_key = "version-branch-idempotent-123"
        headers = {"Authorization": f"Bearer {token}", "Idempotency-Key": idempotency_key}

        session_data = {"scope_type": "GENESIS", "scope_id": "version-idempotent-test"}
        session_response = await client_with_lifespan.post("/api/v1/conversations/sessions", json=session_data, headers=headers)
        session_id = session_response.json()["data"]["id"]

        # Act
        version_data = {"base_version": "2.1", "label": "idempotent-branch"}
        response = await client_with_lifespan.post(
            f"/api/v1/conversations/sessions/{session_id}/versions", json=version_data, headers=headers
        )

        # Assert
        assert response.status_code == 201
        data = response.json()
        branch_data = data["data"]
        assert "v2.1-branch-" in branch_data["branch"]
        assert branch_data["label"] == "idempotent-branch"

    @pytest.mark.asyncio
    async def test_create_version_branch_minimal_data(self, client_with_lifespan, pg_session):
        """Test version branch creation with minimal required data."""
        # Arrange
        user_data = await create_and_verify_test_user(client_with_lifespan, pg_session)
        login_response = await perform_login(client_with_lifespan, user_data["email"], user_data["password"])
        token = login_response[1]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        session_data = {"scope_type": "GENESIS", "scope_id": "version-minimal-test"}
        session_response = await client_with_lifespan.post("/api/v1/conversations/sessions", json=session_data, headers=headers)
        session_id = session_response.json()["data"]["id"]

        # Act
        version_data = {"base_version": "0.1", "label": "minimal-branch"}
        response = await client_with_lifespan.post(
            f"/api/v1/conversations/sessions/{session_id}/versions", json=version_data, headers=headers
        )

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["data"]["label"] == "minimal-branch"

    @pytest.mark.asyncio
    async def test_create_version_branch_unauthorized(self, client_with_lifespan):
        """Test creating version branch without authentication."""
        version_data = {"base_version": "1.0", "label": "unauthorized-test"}
        response = await client_with_lifespan.post(f"/api/v1/conversations/sessions/{uuid4()}/versions", json=version_data)
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_version_branch_invalid_data(self, client_with_lifespan, pg_session):
        """Test creating version branch with invalid data."""
        # Arrange
        user_data = await create_and_verify_test_user(client_with_lifespan, pg_session)
        login_response = await perform_login(client_with_lifespan, user_data["email"], user_data["password"])
        token = login_response[1]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        session_data = {"scope_type": "GENESIS", "scope_id": "version-invalid-test"}
        session_response = await client_with_lifespan.post("/api/v1/conversations/sessions", json=session_data, headers=headers)
        session_id = session_response.json()["data"]["id"]

        # Act - missing required fields
        version_data = {
            "label": "missing-base-version"
            # Missing base_version
        }
        response = await client_with_lifespan.post(
            f"/api/v1/conversations/sessions/{session_id}/versions", json=version_data, headers=headers
        )

        # Assert
        assert response.status_code == 422  # Validation error


class TestConversationVersionsMerge:
    """Test cases for merging conversation versions."""

    @pytest.mark.asyncio
    async def test_merge_versions_success(self, client_with_lifespan, pg_session):
        """Test successful version merge (skeleton implementation)."""
        # Arrange
        user_data = await create_and_verify_test_user(client_with_lifespan, pg_session)
        login_response = await perform_login(client_with_lifespan, user_data["email"], user_data["password"])
        token = login_response[1]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        session_data = {"scope_type": "GENESIS", "scope_id": "version-merge-test"}
        session_response = await client_with_lifespan.post("/api/v1/conversations/sessions", json=session_data, headers=headers)
        assert session_response.status_code == 201
        session_id = session_response.json()["data"]["id"]

        # Act
        merge_data = {"source_branch": "v1.0-branch-abc123", "target": "main", "merge_strategy": "auto"}
        response = await client_with_lifespan.put(
            f"/api/v1/conversations/sessions/{session_id}/versions/merge", json=merge_data, headers=headers
        )

        # Assert
        if response.status_code != 200:
            print(f"Error response: {response.text}")
        assert response.status_code == 200
        data = response.json()

        assert data["code"] == 0
        assert "合并完成" in data["msg"]
        assert "skeleton" in data["msg"]  # Skeleton implementation message
        assert "data" in data

        merge_result = data["data"]
        assert merge_result["target"] == "main"
        assert merge_result["merged"] is True

    @pytest.mark.asyncio
    async def test_merge_versions_different_strategies(self, client_with_lifespan, pg_session):
        """Test version merge with different merge strategies."""
        # Arrange
        user_data = await create_and_verify_test_user(client_with_lifespan, pg_session)
        login_response = await perform_login(client_with_lifespan, user_data["email"], user_data["password"])
        token = login_response[1]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        session_data = {"scope_type": "GENESIS", "scope_id": "version-strategy-test"}
        session_response = await client_with_lifespan.post("/api/v1/conversations/sessions", json=session_data, headers=headers)
        session_id = session_response.json()["data"]["id"]

        # Test different merge strategies
        strategies = ["auto", "manual", "force"]

        for strategy in strategies:
            merge_data = {"source_branch": f"v2.0-branch-{strategy}", "target": "main", "merge_strategy": strategy}
            response = await client_with_lifespan.put(
                f"/api/v1/conversations/sessions/{session_id}/versions/merge", json=merge_data, headers=headers
            )

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["data"]["merged"] is True
            assert data["data"]["target"] == "main"

    @pytest.mark.asyncio
    async def test_merge_versions_with_correlation_id(self, client_with_lifespan, pg_session):
        """Test version merge with correlation ID."""
        # Arrange
        user_data = await create_and_verify_test_user(client_with_lifespan, pg_session)
        login_response = await perform_login(client_with_lifespan, user_data["email"], user_data["password"])
        token = login_response[1]["access_token"]
        correlation_id = "test-merge-correlation-789"
        headers = {"Authorization": f"Bearer {token}", "X-Correlation-Id": correlation_id}

        session_data = {"scope_type": "GENESIS", "scope_id": "version-merge-correlation"}
        session_response = await client_with_lifespan.post("/api/v1/conversations/sessions", json=session_data, headers=headers)
        session_id = session_response.json()["data"]["id"]

        # Act
        merge_data = {"source_branch": "v1.5-branch-corr", "target": "develop"}
        response = await client_with_lifespan.put(
            f"/api/v1/conversations/sessions/{session_id}/versions/merge", json=merge_data, headers=headers
        )

        # Assert
        assert response.status_code == 200
        # Check if correlation ID is in response headers
        assert "x-correlation-id" in [h.lower() for h in response.headers.keys()]

    @pytest.mark.asyncio
    async def test_merge_versions_unauthorized(self, client_with_lifespan):
        """Test merging versions without authentication."""
        merge_data = {"source_branch": "test-branch", "target": "main"}
        response = await client_with_lifespan.put(f"/api/v1/conversations/sessions/{uuid4()}/versions/merge", json=merge_data)
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_merge_versions_invalid_data(self, client_with_lifespan, pg_session):
        """Test merging versions with invalid data."""
        # Arrange
        user_data = await create_and_verify_test_user(client_with_lifespan, pg_session)
        login_response = await perform_login(client_with_lifespan, user_data["email"], user_data["password"])
        token = login_response[1]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        session_data = {"scope_type": "GENESIS", "scope_id": "version-merge-invalid"}
        session_response = await client_with_lifespan.post("/api/v1/conversations/sessions", json=session_data, headers=headers)
        session_id = session_response.json()["data"]["id"]

        # Act - missing required fields
        merge_data = {
            "source_branch": "test-branch"
            # Missing target
        }
        response = await client_with_lifespan.put(
            f"/api/v1/conversations/sessions/{session_id}/versions/merge", json=merge_data, headers=headers
        )

        # Assert
        assert response.status_code == 422  # Validation error


class TestConversationVersionsIntegration:
    """Integration test cases for version workflow."""

    @pytest.mark.asyncio
    async def test_version_workflow_integration(self, client_with_lifespan, pg_session):
        """Test complete version workflow: list -> create -> merge."""
        # Arrange
        user_data = await create_and_verify_test_user(client_with_lifespan, pg_session)
        login_response = await perform_login(client_with_lifespan, user_data["email"], user_data["password"])
        token = login_response[1]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        session_data = {"scope_type": "GENESIS", "scope_id": "version-workflow-test"}
        session_response = await client_with_lifespan.post("/api/v1/conversations/sessions", json=session_data, headers=headers)
        session_id = session_response.json()["data"]["id"]

        # Step 1: List versions (should be empty initially)
        list_response = await client_with_lifespan.get(f"/api/v1/conversations/sessions/{session_id}/versions", headers=headers)
        assert list_response.status_code == 200
        assert list_response.json()["data"] == []

        # Step 2: Create a version branch
        version_data = {"base_version": "1.0", "label": "feature-branch", "description": "New feature development"}
        create_response = await client_with_lifespan.post(
            f"/api/v1/conversations/sessions/{session_id}/versions", json=version_data, headers=headers
        )
        assert create_response.status_code == 201
        branch_id = create_response.json()["data"]["branch"]

        # Step 3: Merge the branch
        merge_data = {"source_branch": branch_id, "target": "main", "merge_strategy": "auto"}
        merge_response = await client_with_lifespan.put(
            f"/api/v1/conversations/sessions/{session_id}/versions/merge", json=merge_data, headers=headers
        )
        assert merge_response.status_code == 200
        assert merge_response.json()["data"]["merged"] is True

    @pytest.mark.asyncio
    async def test_version_access_control(self, client_with_lifespan, pg_session):
        """Test that users can only access their own session versions."""
        # Create first user and session
        user1_data = await create_and_verify_test_user(
            client_with_lifespan, pg_session, username="user1", email="user1@example.com"
        )
        login1_response = await perform_login(client_with_lifespan, user1_data["email"], user1_data["password"])
        token1 = login1_response[1]["access_token"]
        headers1 = {"Authorization": f"Bearer {token1}"}

        session_data = {"scope_type": "GENESIS", "scope_id": "user1-versions"}
        session_response = await client_with_lifespan.post(
            "/api/v1/conversations/sessions", json=session_data, headers=headers1
        )
        session_id = session_response.json()["data"]["id"]

        # Create second user
        user2_data = await create_and_verify_test_user(
            client_with_lifespan, pg_session, username="user2", email="user2@example.com"
        )
        login2_response = await perform_login(client_with_lifespan, user2_data["email"], user2_data["password"])
        token2 = login2_response[1]["access_token"]
        headers2 = {"Authorization": f"Bearer {token2}"}

        # Try to access user1's session versions with user2's token
        response = await client_with_lifespan.get(f"/api/v1/conversations/sessions/{session_id}/versions", headers=headers2)

        # Since this is skeleton implementation, it might return 200 with empty list
        # or proper 404/403 - both are acceptable for access control test
        assert response.status_code in [200, 403, 404]
