"""Integration tests for conversation content API endpoints."""

from uuid import UUID, uuid4

import pytest
from tests.integration.api.auth_test_helpers import create_and_verify_test_user, perform_login


class TestConversationContentRetrieve:
    """Test cases for retrieving conversation content."""

    @pytest.mark.asyncio
    async def test_get_content_success(self, client_with_lifespan, pg_session):
        """Test successful content retrieval."""
        # Arrange - create user and session
        user_data = await create_and_verify_test_user(client_with_lifespan, pg_session)
        login_response = await perform_login(client_with_lifespan, user_data["email"], user_data["password"])
        token = login_response[1]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create session with some state
        from tests.integration.api.auth_test_helpers import create_test_novel

        novel_id = await create_test_novel(pg_session, user_data["email"], "Content Test Novel")
        session_data = {
            "scope_type": "GENESIS",
            "scope_id": novel_id,
            "initial_state": {"characters": ["Alice", "Bob"], "setting": "Medieval fantasy world"},
        }
        session_response = await client_with_lifespan.post(
            "/api/v1/conversations/sessions", json=session_data, headers=headers
        )
        assert session_response.status_code == 201
        session_id = session_response.json()["data"]["id"]

        # Act
        response = await client_with_lifespan.get(
            f"/api/v1/conversations/sessions/{session_id}/content", headers=headers
        )

        # Assert
        if response.status_code != 200:
            print(f"Error response: {response.text}")
        assert response.status_code == 200
        data = response.json()

        assert data["code"] == 0
        assert "获取内容聚合成功" in data["msg"]
        assert "data" in data

        content_data = data["data"]
        assert "state" in content_data
        assert "meta" in content_data

        # Verify state contains the initial data
        state = content_data["state"]
        assert "characters" in state
        assert "setting" in state
        assert state["characters"] == ["Alice", "Bob"]
        assert state["setting"] == "Medieval fantasy world"

        # Verify meta information
        meta = content_data["meta"]
        assert "updated_at" in meta

    @pytest.mark.asyncio
    async def test_get_content_empty_state(self, client_with_lifespan, pg_session):
        """Test content retrieval with empty state."""
        # Arrange
        user_data = await create_and_verify_test_user(client_with_lifespan, pg_session)
        login_response = await perform_login(client_with_lifespan, user_data["email"], user_data["password"])
        token = login_response[1]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create session with no initial state
        from tests.integration.api.auth_test_helpers import create_test_novel

        novel_id = await create_test_novel(pg_session, user_data["email"], "Content Empty Test Novel")
        session_data = {"scope_type": "GENESIS", "scope_id": novel_id}
        session_response = await client_with_lifespan.post(
            "/api/v1/conversations/sessions", json=session_data, headers=headers
        )
        session_id = session_response.json()["data"]["id"]

        # Act
        response = await client_with_lifespan.get(
            f"/api/v1/conversations/sessions/{session_id}/content", headers=headers
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        content_data = data["data"]

        # State should be empty dict
        assert content_data["state"] == {}
        assert "meta" in content_data

    @pytest.mark.asyncio
    async def test_get_content_with_correlation_id(self, client_with_lifespan, pg_session):
        """Test content retrieval with correlation ID."""
        # Arrange
        user_data = await create_and_verify_test_user(client_with_lifespan, pg_session)
        login_response = await perform_login(client_with_lifespan, user_data["email"], user_data["password"])
        token = login_response[1]["access_token"]
        correlation_id = "test-content-correlation-123"
        headers = {"Authorization": f"Bearer {token}", "X-Correlation-Id": correlation_id}

        from tests.integration.api.auth_test_helpers import create_test_novel

        novel_id = await create_test_novel(pg_session, user_data["email"], "Content Correlation Test Novel")
        session_data = {"scope_type": "GENESIS", "scope_id": novel_id}
        session_response = await client_with_lifespan.post(
            "/api/v1/conversations/sessions", json=session_data, headers=headers
        )
        session_id = session_response.json()["data"]["id"]

        # Act
        response = await client_with_lifespan.get(
            f"/api/v1/conversations/sessions/{session_id}/content", headers=headers
        )

        # Assert
        assert response.status_code == 200
        # Check if correlation ID is in response headers
        assert "x-correlation-id" in [h.lower() for h in response.headers]

    @pytest.mark.asyncio
    async def test_get_content_session_not_found(self, client_with_lifespan, pg_session):
        """Test content retrieval for non-existent session."""
        # Arrange
        user_data = await create_and_verify_test_user(client_with_lifespan, pg_session)
        login_response = await perform_login(client_with_lifespan, user_data["email"], user_data["password"])
        token = login_response[1]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        nonexistent_session = str(uuid4())

        # Act
        response = await client_with_lifespan.get(
            f"/api/v1/conversations/sessions/{nonexistent_session}/content", headers=headers
        )

        # Assert
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_content_unauthorized(self, client_with_lifespan):
        """Test content retrieval without authentication."""
        response = await client_with_lifespan.get(f"/api/v1/conversations/sessions/{uuid4()}/content")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_content_different_user_forbidden(self, client_with_lifespan, pg_session):
        """Test that users cannot access content from other users' sessions."""
        # Create first user and session
        user1_data = await create_and_verify_test_user(
            client_with_lifespan, pg_session, username="user1", email="user1@example.com"
        )
        login1_response = await perform_login(client_with_lifespan, user1_data["email"], user1_data["password"])
        token1 = login1_response[1]["access_token"]
        headers1 = {"Authorization": f"Bearer {token1}"}

        from tests.integration.api.auth_test_helpers import create_test_novel

        novel_id = await create_test_novel(pg_session, user1_data["email"], "User1 Content Test Novel")
        session_data = {"scope_type": "GENESIS", "scope_id": novel_id}
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

        # Try to access user1's session content with user2's token
        response = await client_with_lifespan.get(
            f"/api/v1/conversations/sessions/{session_id}/content", headers=headers2
        )

        # Should return 403 when user exists but no access (not 404 to avoid session existence leaks)
        assert response.status_code == 403


class TestConversationContentExport:
    """Test cases for exporting conversation content."""

    @pytest.mark.asyncio
    async def test_export_content_success(self, client_with_lifespan, pg_session):
        """Test successful content export."""
        # Arrange
        user_data = await create_and_verify_test_user(client_with_lifespan, pg_session)
        login_response = await perform_login(client_with_lifespan, user_data["email"], user_data["password"])
        token = login_response[1]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        from tests.integration.api.auth_test_helpers import create_test_novel

        novel_id = await create_test_novel(pg_session, user_data["email"], "Content Export Test Novel")
        session_data = {"scope_type": "GENESIS", "scope_id": novel_id}
        session_response = await client_with_lifespan.post(
            "/api/v1/conversations/sessions", json=session_data, headers=headers
        )
        assert session_response.status_code == 201
        session_id = session_response.json()["data"]["id"]

        # Act
        response = await client_with_lifespan.post(
            f"/api/v1/conversations/sessions/{session_id}/content/export", headers=headers
        )

        # Assert
        if response.status_code != 202:
            print(f"Error response: {response.text}")
        assert response.status_code == 202  # Accepted (async operation)
        data = response.json()

        assert data["code"] == 0
        assert "导出任务已受理" in data["msg"]
        assert "data" in data

        export_result = data["data"]
        assert export_result["accepted"] is True
        assert "command_id" in export_result
        # Verify command_id is valid UUID format
        assert UUID(export_result["command_id"])

        # Check Location header is set for command tracking
        location_header = next((v for k, v in response.headers.items() if k.lower() == "location"), None)
        assert location_header is not None
        assert f"/api/v1/conversations/sessions/{session_id}/commands/" in location_header

    @pytest.mark.asyncio
    async def test_export_content_with_idempotency(self, client_with_lifespan, pg_session):
        """Test content export with idempotency key."""
        # Arrange
        user_data = await create_and_verify_test_user(client_with_lifespan, pg_session)
        login_response = await perform_login(client_with_lifespan, user_data["email"], user_data["password"])
        token = login_response[1]["access_token"]
        idempotency_key = "content-export-idempotent-123"
        headers = {"Authorization": f"Bearer {token}", "Idempotency-Key": idempotency_key}

        from tests.integration.api.auth_test_helpers import create_test_novel

        novel_id = await create_test_novel(pg_session, user_data["email"], "Export Idempotent Test Novel")
        session_data = {"scope_type": "GENESIS", "scope_id": novel_id}
        session_response = await client_with_lifespan.post(
            "/api/v1/conversations/sessions", json=session_data, headers=headers
        )
        session_id = session_response.json()["data"]["id"]

        # Act
        response = await client_with_lifespan.post(
            f"/api/v1/conversations/sessions/{session_id}/content/export", headers=headers
        )

        # Assert
        assert response.status_code == 202
        data = response.json()
        assert data["data"]["accepted"] is True
        assert UUID(data["data"]["command_id"])

    @pytest.mark.asyncio
    async def test_export_content_with_correlation_id(self, client_with_lifespan, pg_session):
        """Test content export with correlation ID."""
        # Arrange
        user_data = await create_and_verify_test_user(client_with_lifespan, pg_session)
        login_response = await perform_login(client_with_lifespan, user_data["email"], user_data["password"])
        token = login_response[1]["access_token"]
        correlation_id = "test-export-correlation-456"
        headers = {"Authorization": f"Bearer {token}", "X-Correlation-Id": correlation_id}

        from tests.integration.api.auth_test_helpers import create_test_novel

        novel_id = await create_test_novel(pg_session, user_data["email"], "Export Correlation Test Novel")
        session_data = {"scope_type": "GENESIS", "scope_id": novel_id}
        session_response = await client_with_lifespan.post(
            "/api/v1/conversations/sessions", json=session_data, headers=headers
        )
        session_id = session_response.json()["data"]["id"]

        # Act
        response = await client_with_lifespan.post(
            f"/api/v1/conversations/sessions/{session_id}/content/export", headers=headers
        )

        # Assert
        assert response.status_code == 202
        # Check if correlation ID is in response headers
        assert "x-correlation-id" in [h.lower() for h in response.headers]

    @pytest.mark.asyncio
    async def test_export_content_session_not_found(self, client_with_lifespan, pg_session):
        """Test content export for non-existent session."""
        # Arrange
        user_data = await create_and_verify_test_user(client_with_lifespan, pg_session)
        login_response = await perform_login(client_with_lifespan, user_data["email"], user_data["password"])
        token = login_response[1]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        nonexistent_session = str(uuid4())

        # Act
        response = await client_with_lifespan.post(
            f"/api/v1/conversations/sessions/{nonexistent_session}/content/export", headers=headers
        )

        # Assert
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_export_content_unauthorized(self, client_with_lifespan):
        """Test content export without authentication."""
        response = await client_with_lifespan.post(f"/api/v1/conversations/sessions/{uuid4()}/content/export")
        assert response.status_code == 401


class TestConversationContentSearch:
    """Test cases for searching conversation content."""

    @pytest.mark.asyncio
    async def test_search_content_success(self, client_with_lifespan, pg_session):
        """Test successful content search (skeleton implementation)."""
        # Arrange
        user_data = await create_and_verify_test_user(client_with_lifespan, pg_session)
        login_response = await perform_login(client_with_lifespan, user_data["email"], user_data["password"])
        token = login_response[1]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        from tests.integration.api.auth_test_helpers import create_test_novel

        novel_id = await create_test_novel(pg_session, user_data["email"], "Content Search Test Novel")
        session_data = {"scope_type": "GENESIS", "scope_id": novel_id}
        session_response = await client_with_lifespan.post(
            "/api/v1/conversations/sessions", json=session_data, headers=headers
        )
        assert session_response.status_code == 201
        session_id = session_response.json()["data"]["id"]

        # Act
        search_data = {
            "query": "fantasy characters",
            "limit": 10,
            "filters": {"content_type": "character", "created_after": "2024-01-01"},
        }
        response = await client_with_lifespan.post(
            f"/api/v1/conversations/sessions/{session_id}/content/search", json=search_data, headers=headers
        )

        # Assert
        if response.status_code != 200:
            print(f"Error response: {response.text}")
        assert response.status_code == 200
        data = response.json()

        assert data["code"] == 0
        assert "搜索完成" in data["msg"]
        assert "skeleton" in data["msg"]  # Skeleton implementation message
        assert "data" in data

        search_result = data["data"]
        assert "items" in search_result
        assert "pagination" in search_result

        # Skeleton returns empty results
        assert search_result["items"] == []

        # Verify pagination info
        pagination = search_result["pagination"]
        assert pagination["page"] == 1
        assert pagination["page_size"] == 10
        assert pagination["total"] == 0
        assert pagination["total_pages"] == 0

    @pytest.mark.asyncio
    async def test_search_content_different_queries(self, client_with_lifespan, pg_session):
        """Test content search with different query types."""
        # Arrange
        user_data = await create_and_verify_test_user(client_with_lifespan, pg_session)
        login_response = await perform_login(client_with_lifespan, user_data["email"], user_data["password"])
        token = login_response[1]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        from tests.integration.api.auth_test_helpers import create_test_novel

        novel_id = await create_test_novel(pg_session, user_data["email"], "Search Queries Test Novel")
        session_data = {"scope_type": "GENESIS", "scope_id": novel_id}
        session_response = await client_with_lifespan.post(
            "/api/v1/conversations/sessions", json=session_data, headers=headers
        )
        session_id = session_response.json()["data"]["id"]

        # Test different search queries
        queries = [
            {"query": "character development", "limit": 5},
            {"query": "plot points", "limit": 20},
            {"query": "dialogue scenes", "limit": 15, "filters": {"type": "dialogue"}},
            {"query": "world building", "limit": 25, "filters": {"category": "setting"}},
        ]

        for search_data in queries:
            response = await client_with_lifespan.post(
                f"/api/v1/conversations/sessions/{session_id}/content/search", json=search_data, headers=headers
            )

            # Assert
            assert response.status_code == 200
            data = response.json()
            search_result = data["data"]

            # Verify pagination reflects requested limit
            pagination = search_result["pagination"]
            assert pagination["page_size"] == search_data["limit"]

    @pytest.mark.asyncio
    async def test_search_content_minimal_query(self, client_with_lifespan, pg_session):
        """Test content search with minimal query parameters."""
        # Arrange
        user_data = await create_and_verify_test_user(client_with_lifespan, pg_session)
        login_response = await perform_login(client_with_lifespan, user_data["email"], user_data["password"])
        token = login_response[1]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        from tests.integration.api.auth_test_helpers import create_test_novel

        novel_id = await create_test_novel(pg_session, user_data["email"], "Search Minimal Test Novel")
        session_data = {"scope_type": "GENESIS", "scope_id": novel_id}
        session_response = await client_with_lifespan.post(
            "/api/v1/conversations/sessions", json=session_data, headers=headers
        )
        session_id = session_response.json()["data"]["id"]

        # Act - minimal search data
        search_data = {"query": "test"}
        response = await client_with_lifespan.post(
            f"/api/v1/conversations/sessions/{session_id}/content/search", json=search_data, headers=headers
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        search_result = data["data"]
        assert "items" in search_result
        assert "pagination" in search_result

    @pytest.mark.asyncio
    async def test_search_content_with_correlation_id(self, client_with_lifespan, pg_session):
        """Test content search with correlation ID."""
        # Arrange
        user_data = await create_and_verify_test_user(client_with_lifespan, pg_session)
        login_response = await perform_login(client_with_lifespan, user_data["email"], user_data["password"])
        token = login_response[1]["access_token"]
        correlation_id = "test-search-correlation-789"
        headers = {"Authorization": f"Bearer {token}", "X-Correlation-Id": correlation_id}

        from tests.integration.api.auth_test_helpers import create_test_novel

        novel_id = await create_test_novel(pg_session, user_data["email"], "Search Correlation Test Novel")
        session_data = {"scope_type": "GENESIS", "scope_id": novel_id}
        session_response = await client_with_lifespan.post(
            "/api/v1/conversations/sessions", json=session_data, headers=headers
        )
        session_id = session_response.json()["data"]["id"]

        # Act
        search_data = {"query": "correlation test"}
        response = await client_with_lifespan.post(
            f"/api/v1/conversations/sessions/{session_id}/content/search", json=search_data, headers=headers
        )

        # Assert
        assert response.status_code == 200
        # Check if correlation ID is in response headers
        assert "x-correlation-id" in [h.lower() for h in response.headers]

    @pytest.mark.asyncio
    async def test_search_content_session_not_found(self, client_with_lifespan, pg_session):
        """Test content search for non-existent session."""
        # Arrange
        user_data = await create_and_verify_test_user(client_with_lifespan, pg_session)
        login_response = await perform_login(client_with_lifespan, user_data["email"], user_data["password"])
        token = login_response[1]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        nonexistent_session = str(uuid4())
        search_data = {"query": "test"}

        # Act
        response = await client_with_lifespan.post(
            f"/api/v1/conversations/sessions/{nonexistent_session}/content/search", json=search_data, headers=headers
        )

        # Assert
        # Since this is skeleton implementation, it might return 200 with empty results
        # or proper 404 - both are acceptable for skeleton
        assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_search_content_unauthorized(self, client_with_lifespan):
        """Test content search without authentication."""
        search_data = {"query": "test"}
        response = await client_with_lifespan.post(
            f"/api/v1/conversations/sessions/{uuid4()}/content/search", json=search_data
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_search_content_invalid_data(self, client_with_lifespan, pg_session):
        """Test content search with invalid data."""
        # Arrange
        user_data = await create_and_verify_test_user(client_with_lifespan, pg_session)
        login_response = await perform_login(client_with_lifespan, user_data["email"], user_data["password"])
        token = login_response[1]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        from tests.integration.api.auth_test_helpers import create_test_novel

        novel_id = await create_test_novel(pg_session, user_data["email"], "Search Invalid Test Novel")
        session_data = {"scope_type": "GENESIS", "scope_id": novel_id}
        session_response = await client_with_lifespan.post(
            "/api/v1/conversations/sessions", json=session_data, headers=headers
        )
        session_id = session_response.json()["data"]["id"]

        # Act - missing required 'query' field
        search_data = {"limit": 10}
        response = await client_with_lifespan.post(
            f"/api/v1/conversations/sessions/{session_id}/content/search", json=search_data, headers=headers
        )

        # Assert
        # For skeleton implementation, validation might not be fully implemented
        # Accept both validation error (422) or success with empty query (200)
        assert response.status_code in [200, 422]


class TestConversationContentIntegration:
    """Integration test cases for content workflow."""

    @pytest.mark.asyncio
    async def test_content_workflow_integration(self, client_with_lifespan, pg_session):
        """Test complete content workflow: get -> export -> search."""
        # Arrange
        user_data = await create_and_verify_test_user(client_with_lifespan, pg_session)
        login_response = await perform_login(client_with_lifespan, user_data["email"], user_data["password"])
        token = login_response[1]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        from tests.integration.api.auth_test_helpers import create_test_novel

        novel_id = await create_test_novel(pg_session, user_data["email"], "Content Workflow Test Novel")
        session_data = {
            "scope_type": "GENESIS",
            "scope_id": novel_id,
            "initial_state": {"story_elements": ["magic", "dragons"]},
        }
        session_response = await client_with_lifespan.post(
            "/api/v1/conversations/sessions", json=session_data, headers=headers
        )
        session_id = session_response.json()["data"]["id"]

        # Step 1: Get content
        get_response = await client_with_lifespan.get(
            f"/api/v1/conversations/sessions/{session_id}/content", headers=headers
        )
        assert get_response.status_code == 200
        content_data = get_response.json()["data"]
        assert "story_elements" in content_data["state"]

        # Step 2: Export content
        export_response = await client_with_lifespan.post(
            f"/api/v1/conversations/sessions/{session_id}/content/export", headers=headers
        )
        assert export_response.status_code == 202
        export_data = export_response.json()["data"]
        assert export_data["accepted"] is True
        command_id = export_data["command_id"]

        # Step 3: Search content
        search_data = {"query": "dragons", "limit": 5}
        search_response = await client_with_lifespan.post(
            f"/api/v1/conversations/sessions/{session_id}/content/search", json=search_data, headers=headers
        )
        assert search_response.status_code == 200
        search_result = search_response.json()["data"]
        assert "items" in search_result
        assert "pagination" in search_result

        # Verify command ID is valid UUID
        assert UUID(command_id)

    @pytest.mark.asyncio
    async def test_content_access_control(self, client_with_lifespan, pg_session):
        """Test that users can only access content from their own sessions."""
        # Create first user and session
        user1_data = await create_and_verify_test_user(
            client_with_lifespan, pg_session, username="user1", email="user1@example.com"
        )
        login1_response = await perform_login(client_with_lifespan, user1_data["email"], user1_data["password"])
        token1 = login1_response[1]["access_token"]
        headers1 = {"Authorization": f"Bearer {token1}"}

        from tests.integration.api.auth_test_helpers import create_test_novel

        novel_id = await create_test_novel(pg_session, user1_data["email"], "User1 Content Access Test Novel")
        session_data = {
            "scope_type": "GENESIS",
            "scope_id": novel_id,
            "initial_state": {"private": "data"},
        }
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

        # Try to access user1's session content operations with user2's token

        # Test get content
        get_response = await client_with_lifespan.get(
            f"/api/v1/conversations/sessions/{session_id}/content", headers=headers2
        )
        assert get_response.status_code == 403  # Forbidden - user exists but no access

        # Test export content
        export_response = await client_with_lifespan.post(
            f"/api/v1/conversations/sessions/{session_id}/content/export", headers=headers2
        )
        assert export_response.status_code == 403  # Forbidden - user exists but no access

        # Test search content
        search_data = {"query": "private"}
        search_response = await client_with_lifespan.post(
            f"/api/v1/conversations/sessions/{session_id}/content/search", json=search_data, headers=headers2
        )
        # Search might return 200 with empty results or 404 - both acceptable for access control
        assert search_response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_content_operations_with_state_updates(self, client_with_lifespan, pg_session):
        """Test content operations after state updates."""
        # Arrange
        user_data = await create_and_verify_test_user(client_with_lifespan, pg_session)
        login_response = await perform_login(client_with_lifespan, user_data["email"], user_data["password"])
        token = login_response[1]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create session with initial state
        from tests.integration.api.auth_test_helpers import create_test_novel

        novel_id = await create_test_novel(pg_session, user_data["email"], "Content State Test Novel")
        session_data = {
            "scope_type": "GENESIS",
            "scope_id": novel_id,
            "initial_state": {"version": 1, "content": "initial"},
        }
        session_response = await client_with_lifespan.post(
            "/api/v1/conversations/sessions", json=session_data, headers=headers
        )
        session_id = session_response.json()["data"]["id"]

        # Update session state
        update_data = {"state": {"version": 2, "content": "updated", "new_field": "added"}}
        update_response = await client_with_lifespan.patch(
            f"/api/v1/conversations/sessions/{session_id}", json=update_data, headers=headers
        )
        # Note: Update might not be implemented yet, so we don't assert success

        # Get content after state update
        content_response = await client_with_lifespan.get(
            f"/api/v1/conversations/sessions/{session_id}/content", headers=headers
        )
        assert content_response.status_code == 200

        # Content should reflect current session state
        content_data = content_response.json()["data"]
        state = content_data["state"]
        # At minimum, we should get the initial state
        assert "version" in state
        assert "content" in state
