"""Integration tests for conversation sessions API endpoints."""

from uuid import UUID, uuid4

import pytest
from tests.integration.api.auth_test_helpers import create_and_verify_test_user, perform_login, create_test_novel


class TestConversationSessionsCreate:
    """Test cases for creating conversation sessions."""

    @pytest.mark.asyncio
    async def test_create_session_success(self, client_with_lifespan, pg_session, _mock_email_service_instance_methods):
        """Test successful session creation with GENESIS scope."""
        # Arrange - create and authenticate user
        user_data = await create_and_verify_test_user(client_with_lifespan, pg_session)
        login_response = await perform_login(client_with_lifespan, user_data["email"], user_data["password"])
        token = login_response[1]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create a novel to use as scope_id
        novel_id = await create_test_novel(pg_session, user_data["email"], "Test Session Novel")

        session_data = {
            "scope_type": "GENESIS",
            "scope_id": novel_id,
            "stage": "PLANNING",
            "initial_state": {"test": "data"},
        }

        # Act
        response = await client_with_lifespan.post("/api/v1/conversations/sessions", json=session_data, headers=headers)

        # Assert
        if response.status_code != 201:
            print(f"Error response: {response.text}")
        assert response.status_code == 201
        data = response.json()

        assert data["code"] == 0
        assert "创建会话成功" in data["msg"]
        assert "data" in data

        session = data["data"]
        assert UUID(session["id"])  # Validate UUID format
        assert session["scope_type"] == "GENESIS"
        assert session["scope_id"] == novel_id
        assert session["status"] == "ACTIVE"  # Default status
        assert session["stage"] == "PLANNING"
        assert session["state"] == {"test": "data"}
        assert session["version"] == 1
        assert "created_at" in session
        assert "updated_at" in session

    @pytest.mark.asyncio
    async def test_create_session_minimal_data(self, client_with_lifespan, pg_session, _mock_email_service_instance_methods):
        """Test session creation with minimal required data."""
        # Arrange
        user_data = await create_and_verify_test_user(client_with_lifespan, pg_session)
        login_response = await perform_login(client_with_lifespan, user_data["email"], user_data["password"])
        token = login_response[1]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create a novel to use as scope_id
        novel_id = await create_test_novel(pg_session, user_data["email"], "Minimal Session Novel")

        session_data = {"scope_type": "GENESIS", "scope_id": novel_id}

        # Act
        response = await client_with_lifespan.post("/api/v1/conversations/sessions", json=session_data, headers=headers)

        # Assert
        assert response.status_code == 201
        data = response.json()
        session = data["data"]
        assert session["scope_type"] == "GENESIS"
        assert session["scope_id"] == novel_id
        assert session["status"] == "ACTIVE"
        assert session["stage"] is None or session["stage"] == ""
        assert session["state"] == {}

    @pytest.mark.asyncio
    async def test_create_session_unauthorized(self, client_with_lifespan):
        """Test session creation without authentication."""
        session_data = {"scope_type": "GENESIS", "scope_id": "test-scope"}

        response = await client_with_lifespan.post("/api/v1/conversations/sessions", json=session_data)

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_session_invalid_scope_type(self, client_with_lifespan, pg_session, _mock_email_service_instance_methods):
        """Test session creation with invalid scope type."""
        # Arrange
        user_data = await create_and_verify_test_user(client_with_lifespan, pg_session)
        login_response = await perform_login(client_with_lifespan, user_data["email"], user_data["password"])
        token = login_response[1]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create a novel to use as scope_id
        novel_id = await create_test_novel(pg_session, user_data["email"], "Invalid Scope Test Novel")

        session_data = {"scope_type": "INVALID_SCOPE", "scope_id": novel_id}

        # Act
        response = await client_with_lifespan.post("/api/v1/conversations/sessions", json=session_data, headers=headers)

        # Assert
        assert response.status_code == 422  # Validation error


class TestConversationSessionsRetrieve:
    """Test cases for retrieving conversation sessions."""

    @pytest.mark.asyncio
    async def test_get_session_success(self, client_with_lifespan, pg_session, _mock_email_service_instance_methods):
        """Test successful session retrieval."""
        # Arrange - create user and session first
        user_data = await create_and_verify_test_user(client_with_lifespan, pg_session)
        login_response = await perform_login(client_with_lifespan, user_data["email"], user_data["password"])
        token = login_response[1]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create a novel to use as scope_id
        novel_id = await create_test_novel(pg_session, user_data["email"], "Retrieve Session Novel")

        # Create session
        session_data = {"scope_type": "GENESIS", "scope_id": novel_id, "stage": "DEVELOPMENT"}
        create_response = await client_with_lifespan.post("/api/v1/conversations/sessions", json=session_data, headers=headers)
        assert create_response.status_code == 201
        session_id = create_response.json()["data"]["id"]

        # Act - retrieve session
        response = await client_with_lifespan.get(f"/api/v1/conversations/sessions/{session_id}", headers=headers)

        # Assert
        assert response.status_code == 200
        data = response.json()

        assert data["code"] == 0
        assert "获取会话成功" in data["msg"]

        session = data["data"]
        assert session["id"] == session_id
        assert session["scope_type"] == "GENESIS"
        assert session["scope_id"] == novel_id
        assert session["stage"] == "DEVELOPMENT"

    @pytest.mark.asyncio
    async def test_get_session_not_found(self, client_with_lifespan, pg_session, _mock_email_service_instance_methods):
        """Test retrieving non-existent session."""
        # Arrange
        user_data = await create_and_verify_test_user(client_with_lifespan, pg_session)
        login_response = await perform_login(client_with_lifespan, user_data["email"], user_data["password"])
        token = login_response[1]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        nonexistent_id = str(uuid4())

        # Act
        response = await client_with_lifespan.get(f"/api/v1/conversations/sessions/{nonexistent_id}", headers=headers)

        # Assert
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_session_unauthorized(self, client_with_lifespan, pg_session, _mock_email_service_instance_methods):
        """Test retrieving session without authentication."""
        # Create session first with authenticated user
        user_data = await create_and_verify_test_user(client_with_lifespan, pg_session)
        login_response = await perform_login(client_with_lifespan, user_data["email"], user_data["password"])
        token = login_response[1]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create a novel to use as scope_id
        novel_id = await create_test_novel(pg_session, user_data["email"], "Auth Test Novel")

        session_data = {"scope_type": "GENESIS", "scope_id": novel_id}
        create_response = await client_with_lifespan.post("/api/v1/conversations/sessions", json=session_data, headers=headers)
        session_id = create_response.json()["data"]["id"]

        # Try to access without auth
        response = await client_with_lifespan.get(f"/api/v1/conversations/sessions/{session_id}")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_session_different_user_forbidden(self, client_with_lifespan, pg_session, _mock_email_service_instance_methods):
        """Test that users cannot access sessions from other users."""
        # Arrange - create first user and session
        user1_data = await create_and_verify_test_user(
            client_with_lifespan, pg_session, username="user1", email="user1@example.com"
        )
        login1_response = await perform_login(client_with_lifespan, user1_data["email"], user1_data["password"])
        token1 = login1_response[1]["access_token"]
        headers1 = {"Authorization": f"Bearer {token1}"}

        # Create a novel for user1
        novel_id = await create_test_novel(pg_session, user1_data["email"], "User1 Session Novel")

        session_data = {"scope_type": "GENESIS", "scope_id": novel_id}
        create_response = await client_with_lifespan.post("/api/v1/conversations/sessions", json=session_data, headers=headers1)
        session_id = create_response.json()["data"]["id"]

        # Create second user
        user2_data = await create_and_verify_test_user(
            client_with_lifespan, pg_session, username="user2", email="user2@example.com"
        )
        login2_response = await perform_login(client_with_lifespan, user2_data["email"], user2_data["password"])
        token2 = login2_response[1]["access_token"]
        headers2 = {"Authorization": f"Bearer {token2}"}

        # Act - try to access user1's session with user2's token
        response = await client_with_lifespan.get(f"/api/v1/conversations/sessions/{session_id}", headers=headers2)

        # Assert - should return 404 to avoid leaking resource existence
        assert response.status_code == 404


class TestConversationSessionsUpdate:
    """Test cases for updating conversation sessions."""

    @pytest.mark.asyncio
    async def test_update_session_success(self, client_with_lifespan, pg_session, _mock_email_service_instance_methods):
        """Test successful session update."""
        # Arrange - create user and session
        user_data = await create_and_verify_test_user(client_with_lifespan, pg_session)
        login_response = await perform_login(client_with_lifespan, user_data["email"], user_data["password"])
        token = login_response[1]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create a novel to use as scope_id
        novel_id = await create_test_novel(pg_session, user_data["email"], "Update Session Novel")

        # Create session
        session_data = {"scope_type": "GENESIS", "scope_id": novel_id, "stage": "PLANNING"}
        create_response = await client_with_lifespan.post("/api/v1/conversations/sessions", json=session_data, headers=headers)
        assert create_response.status_code == 201
        session_id = create_response.json()["data"]["id"]
        etag = create_response.headers.get("ETag")
        print(f"Create response ETag: {etag}")
        print(f"Create response data: {create_response.json()}")

        # Act - update session (without optimistic locking for now)
        update_data = {"status": "PAUSED", "stage": "DEVELOPMENT", "state": {"updated": True}}
        response = await client_with_lifespan.patch(
            f"/api/v1/conversations/sessions/{session_id}", json=update_data, headers=headers
        )

        # Assert
        print(f"Update response status: {response.status_code}")
        print(f"Update response content: {response.text}")
        assert response.status_code == 200
        data = response.json()

        assert data["code"] == 0
        assert "更新会话成功" in data["msg"]

        session = data["data"]
        assert session["status"] == "PAUSED"
        assert session["stage"] == "DEVELOPMENT"
        assert session["state"] == {"updated": True}
        assert session["version"] == 2  # Version should increment

    @pytest.mark.asyncio
    async def test_update_session_optimistic_locking_conflict(self, client_with_lifespan, pg_session, _mock_email_service_instance_methods):
        """Test optimistic locking conflict during update."""
        # Arrange
        user_data = await create_and_verify_test_user(client_with_lifespan, pg_session)
        login_response = await perform_login(client_with_lifespan, user_data["email"], user_data["password"])
        token = login_response[1]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create a novel to use as scope_id
        novel_id = await create_test_novel(pg_session, user_data["email"], "Conflict Test Novel")

        session_data = {"scope_type": "GENESIS", "scope_id": novel_id}
        create_response = await client_with_lifespan.post("/api/v1/conversations/sessions", json=session_data, headers=headers)
        assert create_response.status_code == 201
        session_id = create_response.json()["data"]["id"]

        # Act - try to update with wrong version
        update_data = {"status": "PAUSED"}
        headers_with_wrong_match = {**headers, "If-Match": '"999"'}  # Wrong version
        response = await client_with_lifespan.patch(
            f"/api/v1/conversations/sessions/{session_id}", json=update_data, headers=headers_with_wrong_match
        )

        # Assert - should fail with conflict
        assert response.status_code in [409, 412]  # Conflict or Precondition Failed


class TestConversationSessionsDelete:
    """Test cases for deleting conversation sessions."""

    @pytest.mark.asyncio
    async def test_delete_session_success(self, client_with_lifespan, pg_session, _mock_email_service_instance_methods):
        """Test successful session deletion."""
        # Arrange
        user_data = await create_and_verify_test_user(client_with_lifespan, pg_session)
        login_response = await perform_login(client_with_lifespan, user_data["email"], user_data["password"])
        token = login_response[1]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create a novel to use as scope_id
        novel_id = await create_test_novel(pg_session, user_data["email"], "Delete Test Novel")

        session_data = {"scope_type": "GENESIS", "scope_id": novel_id}
        create_response = await client_with_lifespan.post("/api/v1/conversations/sessions", json=session_data, headers=headers)
        assert create_response.status_code == 201
        session_id = create_response.json()["data"]["id"]

        # Act
        response = await client_with_lifespan.delete(f"/api/v1/conversations/sessions/{session_id}", headers=headers)

        # Assert
        assert response.status_code == 204

        # Verify session is deleted
        get_response = await client_with_lifespan.get(f"/api/v1/conversations/sessions/{session_id}", headers=headers)
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_session_not_found(self, client_with_lifespan, pg_session, _mock_email_service_instance_methods):
        """Test deleting non-existent session."""
        # Arrange
        user_data = await create_and_verify_test_user(client_with_lifespan, pg_session)
        login_response = await perform_login(client_with_lifespan, user_data["email"], user_data["password"])
        token = login_response[1]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        nonexistent_id = str(uuid4())

        # Act
        response = await client_with_lifespan.delete(f"/api/v1/conversations/sessions/{nonexistent_id}", headers=headers)

        # Assert
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_session_unauthorized(self, client_with_lifespan):
        """Test deleting session without authentication."""
        response = await client_with_lifespan.delete(f"/api/v1/conversations/sessions/{uuid4()}")
        assert response.status_code == 401
