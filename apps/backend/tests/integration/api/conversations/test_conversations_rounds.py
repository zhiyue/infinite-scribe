"""Integration tests for conversation rounds API endpoints."""

from uuid import UUID, uuid4

import pytest
from tests.integration.api.auth_test_helpers import create_and_verify_test_user, perform_login


class TestConversationRoundsCreate:
    """Test cases for creating conversation rounds."""

    @pytest.mark.asyncio
    async def test_create_round_success(self, client_with_lifespan, pg_session, _mock_email_service_instance_methods):
        """Test successful round creation."""
        # Arrange - create user and session
        user_data = await create_and_verify_test_user(client_with_lifespan, pg_session)
        login_response = await perform_login(client_with_lifespan, user_data["email"], user_data["password"])
        token = login_response[1]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create session
        from tests.integration.api.auth_test_helpers import create_test_novel

        novel_id = await create_test_novel(pg_session, user_data["email"], "Rounds Test Novel")
        session_data = {"scope_type": "GENESIS", "scope_id": novel_id}
        session_response = await client_with_lifespan.post(
            "/api/v1/conversations/sessions", json=session_data, headers=headers
        )
        assert session_response.status_code == 201
        session_id = session_response.json()["data"]["id"]

        # Act - create round
        round_data = {
            "role": "USER",
            "input": {"message": "Hello, please help me write a story"},
            "model": "gpt-4",
            "correlation_id": "test-correlation-123",
        }
        response = await client_with_lifespan.post(
            f"/api/v1/conversations/sessions/{session_id}/rounds", json=round_data, headers=headers
        )

        # Assert
        if response.status_code != 201:
            print(f"Error response: {response.text}")
        assert response.status_code == 201
        data = response.json()

        assert data["code"] == 0
        assert "创建轮次成功" in data["msg"]
        assert "data" in data

        round_obj = data["data"]
        assert UUID(round_obj["session_id"]) == UUID(session_id)
        assert round_obj["role"] == "USER"
        assert round_obj["input"] == {"message": "Hello, please help me write a story"}
        assert round_obj["model"] == "gpt-4"
        assert round_obj["correlation_id"] == "test-correlation-123"
        assert round_obj["round_path"] == "1"  # First round
        assert "created_at" in round_obj
        assert round_obj["output"] is None  # Output not set yet

    @pytest.mark.asyncio
    async def test_create_round_assistant_role(
        self, client_with_lifespan, pg_session, _mock_email_service_instance_methods
    ):
        """Test creating round with ASSISTANT role."""
        # Arrange
        user_data = await create_and_verify_test_user(client_with_lifespan, pg_session)
        login_response = await perform_login(client_with_lifespan, user_data["email"], user_data["password"])
        token = login_response[1]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create session
        from tests.integration.api.auth_test_helpers import create_test_novel

        novel_id = await create_test_novel(pg_session, user_data["email"], "Assistant Round Test Novel")
        session_data = {"scope_type": "GENESIS", "scope_id": novel_id}
        session_response = await client_with_lifespan.post(
            "/api/v1/conversations/sessions", json=session_data, headers=headers
        )
        assert session_response.status_code == 201
        session_id = session_response.json()["data"]["id"]

        # Act
        round_data = {
            "role": "ASSISTANT",
            "input": {"context": "Story writing request"},
            "model": "claude-3",
        }
        response = await client_with_lifespan.post(
            f"/api/v1/conversations/sessions/{session_id}/rounds", json=round_data, headers=headers
        )

        # Assert
        assert response.status_code == 201
        data = response.json()
        round_obj = data["data"]
        assert round_obj["role"] == "ASSISTANT"
        assert round_obj["model"] == "claude-3"

    @pytest.mark.asyncio
    async def test_create_round_session_not_found(
        self, client_with_lifespan, pg_session, _mock_email_service_instance_methods
    ):
        """Test creating round for non-existent session."""
        # Arrange
        user_data = await create_and_verify_test_user(client_with_lifespan, pg_session)
        login_response = await perform_login(client_with_lifespan, user_data["email"], user_data["password"])
        token = login_response[1]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        nonexistent_session = str(uuid4())
        round_data = {"role": "USER", "input": {"message": "test"}}

        # Act
        response = await client_with_lifespan.post(
            f"/api/v1/conversations/sessions/{nonexistent_session}/rounds", json=round_data, headers=headers
        )

        # Assert
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_create_round_unauthorized(self, client_with_lifespan):
        """Test creating round without authentication."""
        round_data = {"role": "USER", "input": {"message": "test"}}
        response = await client_with_lifespan.post(f"/api/v1/conversations/sessions/{uuid4()}/rounds", json=round_data)
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_round_invalid_role(
        self, client_with_lifespan, pg_session, _mock_email_service_instance_methods
    ):
        """Test creating round with invalid role."""
        # Arrange
        user_data = await create_and_verify_test_user(client_with_lifespan, pg_session)
        login_response = await perform_login(client_with_lifespan, user_data["email"], user_data["password"])
        token = login_response[1]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create session
        from tests.integration.api.auth_test_helpers import create_test_novel

        novel_id = await create_test_novel(pg_session, user_data["email"], "Invalid Role Test Novel")
        session_data = {"scope_type": "GENESIS", "scope_id": novel_id}
        session_response = await client_with_lifespan.post(
            "/api/v1/conversations/sessions", json=session_data, headers=headers
        )
        assert session_response.status_code == 201
        session_id = session_response.json()["data"]["id"]

        # Act
        round_data = {"role": "INVALID_ROLE", "input": {"message": "test"}}
        response = await client_with_lifespan.post(
            f"/api/v1/conversations/sessions/{session_id}/rounds", json=round_data, headers=headers
        )

        # Assert
        assert response.status_code == 422  # Validation error


class TestConversationRoundsList:
    """Test cases for listing conversation rounds."""

    @pytest.mark.asyncio
    async def test_list_rounds_success(self, client_with_lifespan, pg_session, _mock_email_service_instance_methods):
        """Test successful rounds listing."""
        # Arrange - create user, session, and multiple rounds
        user_data = await create_and_verify_test_user(client_with_lifespan, pg_session)
        login_response = await perform_login(client_with_lifespan, user_data["email"], user_data["password"])
        token = login_response[1]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create session
        from tests.integration.api.auth_test_helpers import create_test_novel

        novel_id = await create_test_novel(pg_session, user_data["email"], "List Rounds Test Novel")
        session_data = {"scope_type": "GENESIS", "scope_id": novel_id}
        session_response = await client_with_lifespan.post(
            "/api/v1/conversations/sessions", json=session_data, headers=headers
        )
        assert session_response.status_code == 201
        session_id = session_response.json()["data"]["id"]

        # Create multiple rounds
        rounds_data = [
            {"role": "USER", "input": {"message": "First message"}, "model": "gpt-4"},
            {"role": "ASSISTANT", "input": {"context": "Response context"}, "model": "claude-3"},
            {"role": "USER", "input": {"message": "Follow-up message"}, "model": "gpt-4"},
        ]

        for round_data in rounds_data:
            response = await client_with_lifespan.post(
                f"/api/v1/conversations/sessions/{session_id}/rounds", json=round_data, headers=headers
            )
            assert response.status_code == 201

        # Act
        response = await client_with_lifespan.get(
            f"/api/v1/conversations/sessions/{session_id}/rounds", headers=headers
        )

        # Assert
        assert response.status_code == 200
        data = response.json()

        assert data["code"] == 0
        assert "获取轮次成功" in data["msg"]
        assert "data" in data

        paginated_data = data["data"]
        assert "items" in paginated_data
        assert "pagination" in paginated_data

        items = paginated_data["items"]
        assert len(items) == 3  # Should return all created rounds

        # Verify first round
        assert items[0]["role"] == "USER"
        assert items[0]["input"] == {"message": "First message"}
        assert items[0]["round_path"] == "1"

        # Verify pagination info
        pagination = paginated_data["pagination"]
        assert pagination["total"] == 3
        assert pagination["page_size"] == 50  # Default limit

    @pytest.mark.asyncio
    async def test_list_rounds_with_pagination(
        self, client_with_lifespan, pg_session, _mock_email_service_instance_methods
    ):
        """Test rounds listing with pagination parameters."""
        # Arrange
        user_data = await create_and_verify_test_user(client_with_lifespan, pg_session)
        login_response = await perform_login(client_with_lifespan, user_data["email"], user_data["password"])
        token = login_response[1]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create session
        from tests.integration.api.auth_test_helpers import create_test_novel

        novel_id = await create_test_novel(pg_session, user_data["email"], "Pagination Test Novel")
        session_data = {"scope_type": "GENESIS", "scope_id": novel_id}
        session_response = await client_with_lifespan.post(
            "/api/v1/conversations/sessions", json=session_data, headers=headers
        )
        assert session_response.status_code == 201
        session_id = session_response.json()["data"]["id"]

        # Create rounds
        for i in range(5):
            round_data = {"role": "USER", "input": {"message": f"Message {i}"}}
            await client_with_lifespan.post(
                f"/api/v1/conversations/sessions/{session_id}/rounds", json=round_data, headers=headers
            )

        # Act - request with limit
        response = await client_with_lifespan.get(
            f"/api/v1/conversations/sessions/{session_id}/rounds?limit=3", headers=headers
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        items = data["data"]["items"]
        assert len(items) <= 3  # Should respect limit
        pagination = data["data"]["pagination"]
        assert pagination["page_size"] == 3

    @pytest.mark.asyncio
    async def test_list_rounds_filter_by_role(
        self, client_with_lifespan, pg_session, _mock_email_service_instance_methods
    ):
        """Test filtering rounds by role."""
        # Arrange
        user_data = await create_and_verify_test_user(client_with_lifespan, pg_session)
        login_response = await perform_login(client_with_lifespan, user_data["email"], user_data["password"])
        token = login_response[1]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create session
        from tests.integration.api.auth_test_helpers import create_test_novel

        novel_id = await create_test_novel(pg_session, user_data["email"], "Filter Role Test Novel")
        session_data = {"scope_type": "GENESIS", "scope_id": novel_id}
        session_response = await client_with_lifespan.post(
            "/api/v1/conversations/sessions", json=session_data, headers=headers
        )
        assert session_response.status_code == 201
        session_id = session_response.json()["data"]["id"]

        # Create rounds with different roles
        await client_with_lifespan.post(
            f"/api/v1/conversations/sessions/{session_id}/rounds",
            json={"role": "USER", "input": {"message": "User message"}},
            headers=headers,
        )
        await client_with_lifespan.post(
            f"/api/v1/conversations/sessions/{session_id}/rounds",
            json={"role": "ASSISTANT", "input": {"context": "Assistant response"}},
            headers=headers,
        )

        # Act - filter by USER role
        response = await client_with_lifespan.get(
            f"/api/v1/conversations/sessions/{session_id}/rounds?role=USER", headers=headers
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        items = data["data"]["items"]
        # Should only return USER rounds
        for item in items:
            assert item["role"] == "USER"

    @pytest.mark.asyncio
    async def test_list_rounds_session_not_found(
        self, client_with_lifespan, pg_session, _mock_email_service_instance_methods
    ):
        """Test listing rounds for non-existent session."""
        user_data = await create_and_verify_test_user(client_with_lifespan, pg_session)
        login_response = await perform_login(client_with_lifespan, user_data["email"], user_data["password"])
        token = login_response[1]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        nonexistent_session = str(uuid4())
        response = await client_with_lifespan.get(
            f"/api/v1/conversations/sessions/{nonexistent_session}/rounds", headers=headers
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_list_rounds_unauthorized(self, client_with_lifespan):
        """Test listing rounds without authentication."""
        response = await client_with_lifespan.get(f"/api/v1/conversations/sessions/{uuid4()}/rounds")
        assert response.status_code == 401


class TestConversationRoundsRetrieve:
    """Test cases for retrieving individual conversation rounds."""

    @pytest.mark.asyncio
    async def test_get_round_success(self, client_with_lifespan, pg_session, _mock_email_service_instance_methods):
        """Test successful round retrieval."""
        # Arrange
        user_data = await create_and_verify_test_user(client_with_lifespan, pg_session)
        login_response = await perform_login(client_with_lifespan, user_data["email"], user_data["password"])
        token = login_response[1]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create session
        from tests.integration.api.auth_test_helpers import create_test_novel

        novel_id = await create_test_novel(pg_session, user_data["email"], "Get Round Test Novel")
        session_data = {"scope_type": "GENESIS", "scope_id": novel_id}
        session_response = await client_with_lifespan.post(
            "/api/v1/conversations/sessions", json=session_data, headers=headers
        )
        assert session_response.status_code == 201
        session_id = session_response.json()["data"]["id"]

        # Create round
        round_data = {
            "role": "USER",
            "input": {"message": "Test message for retrieval"},
            "model": "gpt-4",
        }
        create_response = await client_with_lifespan.post(
            f"/api/v1/conversations/sessions/{session_id}/rounds", json=round_data, headers=headers
        )
        assert create_response.status_code == 201
        round_path = create_response.json()["data"]["round_path"]

        # Act
        response = await client_with_lifespan.get(
            f"/api/v1/conversations/sessions/{session_id}/rounds/{round_path}", headers=headers
        )

        # Assert
        assert response.status_code == 200
        data = response.json()

        assert data["code"] == 0
        assert "获取轮次成功" in data["msg"]

        round_obj = data["data"]
        assert round_obj["role"] == "USER"
        assert round_obj["input"] == {"message": "Test message for retrieval"}
        assert round_obj["model"] == "gpt-4"
        assert round_obj["round_path"] == round_path
        assert UUID(round_obj["session_id"]) == UUID(session_id)

    @pytest.mark.asyncio
    async def test_get_round_not_found(self, client_with_lifespan, pg_session, _mock_email_service_instance_methods):
        """Test retrieving non-existent round."""
        # Arrange
        user_data = await create_and_verify_test_user(client_with_lifespan, pg_session)
        login_response = await perform_login(client_with_lifespan, user_data["email"], user_data["password"])
        token = login_response[1]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create session
        from tests.integration.api.auth_test_helpers import create_test_novel

        novel_id = await create_test_novel(pg_session, user_data["email"], "Round Not Found Test Novel")
        session_data = {"scope_type": "GENESIS", "scope_id": novel_id}
        session_response = await client_with_lifespan.post(
            "/api/v1/conversations/sessions", json=session_data, headers=headers
        )
        assert session_response.status_code == 201
        session_id = session_response.json()["data"]["id"]

        # Act - try to get non-existent round
        response = await client_with_lifespan.get(
            f"/api/v1/conversations/sessions/{session_id}/rounds/999", headers=headers
        )

        # Assert
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_round_session_not_found(
        self, client_with_lifespan, pg_session, _mock_email_service_instance_methods
    ):
        """Test retrieving round from non-existent session."""
        user_data = await create_and_verify_test_user(client_with_lifespan, pg_session)
        login_response = await perform_login(client_with_lifespan, user_data["email"], user_data["password"])
        token = login_response[1]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        nonexistent_session = str(uuid4())
        response = await client_with_lifespan.get(
            f"/api/v1/conversations/sessions/{nonexistent_session}/rounds/1", headers=headers
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_round_unauthorized(self, client_with_lifespan):
        """Test retrieving round without authentication."""
        response = await client_with_lifespan.get(f"/api/v1/conversations/sessions/{uuid4()}/rounds/1")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_round_different_user_forbidden(
        self, client_with_lifespan, pg_session, _mock_email_service_instance_methods
    ):
        """Test that users cannot access rounds from other users' sessions."""
        # Arrange - create first user and session with round
        user1_data = await create_and_verify_test_user(
            client_with_lifespan, pg_session, username="user1", email="user1@example.com"
        )
        login1_response = await perform_login(client_with_lifespan, user1_data["email"], user1_data["password"])
        token1 = login1_response["access_token"]
        headers1 = {"Authorization": f"Bearer {token1}"}

        # Create session for user1
        from tests.integration.api.auth_test_helpers import create_test_novel

        novel_id = await create_test_novel(pg_session, user1_data["email"], "User1 Rounds Test Novel")
        session_data = {"scope_type": "GENESIS", "scope_id": novel_id}
        session_response = await client_with_lifespan.post(
            "/api/v1/conversations/sessions", json=session_data, headers=headers1
        )
        assert session_response.status_code == 201
        session_id = session_response.json()["data"]["id"]

        round_data = {"role": "USER", "input": {"message": "Private round"}}
        round_response = await client_with_lifespan.post(
            f"/api/v1/conversations/sessions/{session_id}/rounds", json=round_data, headers=headers1
        )
        round_path = round_response.json()["data"]["round_path"]

        # Create second user
        user2_data = await create_and_verify_test_user(
            client_with_lifespan, pg_session, username="user2", email="user2@example.com"
        )
        login2_response = await perform_login(client_with_lifespan, user2_data["email"], user2_data["password"])
        token2 = login2_response["access_token"]
        headers2 = {"Authorization": f"Bearer {token2}"}

        # Act - try to access user1's round with user2's token
        response = await client_with_lifespan.get(
            f"/api/v1/conversations/sessions/{session_id}/rounds/{round_path}", headers=headers2
        )

        # Assert - should return 404 to avoid leaking session existence
        assert response.status_code == 404


class TestConversationRoundsAdvanced:
    """Advanced test cases for conversation rounds."""

    @pytest.mark.asyncio
    async def test_create_multiple_rounds_sequence(
        self, client_with_lifespan, pg_session, _mock_email_service_instance_methods
    ):
        """Test creating multiple rounds and verify sequence."""
        # Arrange
        user_data = await create_and_verify_test_user(client_with_lifespan, pg_session)
        login_response = await perform_login(client_with_lifespan, user_data["email"], user_data["password"])
        token = login_response[1]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create session
        from tests.integration.api.auth_test_helpers import create_test_novel

        novel_id = await create_test_novel(pg_session, user_data["email"], "Sequence Test Novel")
        session_data = {"scope_type": "GENESIS", "scope_id": novel_id}
        session_response = await client_with_lifespan.post(
            "/api/v1/conversations/sessions", json=session_data, headers=headers
        )
        assert session_response.status_code == 201
        session_id = session_response.json()["data"]["id"]

        # Act - create rounds in sequence
        round_paths = []
        for i in range(3):
            round_data = {"role": "USER", "input": {"message": f"Message {i+1}"}}
            response = await client_with_lifespan.post(
                f"/api/v1/conversations/sessions/{session_id}/rounds", json=round_data, headers=headers
            )
            assert response.status_code == 201
            round_paths.append(response.json()["data"]["round_path"])

        # Assert - verify round paths are sequential
        assert round_paths == ["1", "2", "3"]

        # Verify all rounds can be retrieved
        for path in round_paths:
            get_response = await client_with_lifespan.get(
                f"/api/v1/conversations/sessions/{session_id}/rounds/{path}", headers=headers
            )
            assert get_response.status_code == 200

    @pytest.mark.asyncio
    async def test_correlation_id_propagation(
        self, client_with_lifespan, pg_session, _mock_email_service_instance_methods
    ):
        """Test that correlation IDs are properly handled."""
        # Arrange
        user_data = await create_and_verify_test_user(client_with_lifespan, pg_session)
        login_response = await perform_login(client_with_lifespan, user_data["email"], user_data["password"])
        token = login_response[1]["access_token"]
        correlation_id = "test-correlation-456"
        headers = {"Authorization": f"Bearer {token}", "X-Correlation-Id": correlation_id}

        # Create session
        from tests.integration.api.auth_test_helpers import create_test_novel

        novel_id = await create_test_novel(pg_session, user_data["email"], "Correlation Test Novel")
        session_data = {"scope_type": "GENESIS", "scope_id": novel_id}
        session_response = await client_with_lifespan.post(
            "/api/v1/conversations/sessions", json=session_data, headers=headers
        )
        assert session_response.status_code == 201
        session_id = session_response.json()["data"]["id"]

        # Act
        round_data = {"role": "USER", "input": {"message": "Correlation test"}}
        response = await client_with_lifespan.post(
            f"/api/v1/conversations/sessions/{session_id}/rounds", json=round_data, headers=headers
        )

        # Assert
        assert response.status_code == 201
        # Check if correlation ID is in response headers
        assert "x-correlation-id" in [h.lower() for h in response.headers]
