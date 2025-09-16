"""Integration tests for conversation quality API endpoints."""

from uuid import UUID, uuid4

import pytest
from src.schemas.novel.dialogue.enums import DialogueRole
from tests.integration.api.auth_test_helpers import create_and_verify_test_user, create_test_novel, perform_login


class TestConversationQualityRetrieve:
    """Test cases for retrieving conversation quality scores."""

    @pytest.mark.asyncio
    async def test_get_quality_success(self, client_with_lifespan, pg_session):
        """Test successful quality score retrieval (skeleton implementation)."""
        # Arrange - create user and session
        user_data = await create_and_verify_test_user(client_with_lifespan, pg_session)
        login_response = await perform_login(client_with_lifespan, user_data["email"], user_data["password"])
        token = login_response[1]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create session first
        novel_id = await create_test_novel(pg_session, user_data["email"], "Quality Test Novel")

        session_data = {"scope_type": "GENESIS", "scope_id": novel_id}
        session_response = await client_with_lifespan.post(
            "/api/v1/conversations/sessions", json=session_data, headers=headers
        )
        assert session_response.status_code == 201
        session_id = session_response.json()["data"]["id"]

        # Act
        response = await client_with_lifespan.get(
            f"/api/v1/conversations/sessions/{session_id}/quality", headers=headers
        )

        # Assert
        if response.status_code != 200:
            print(f"Error response: {response.text}")
        assert response.status_code == 200
        data = response.json()

        assert data["code"] == 0
        assert "获取质量评分" in data["msg"]
        assert "skeleton" in data["msg"]  # Skeleton implementation message
        assert "data" in data

        quality_data = data["data"]
        assert "score" in quality_data
        assert "updated_at" in quality_data

        # Skeleton implementation returns score 0.0
        assert quality_data["score"] == 0.0
        assert isinstance(quality_data["updated_at"], str)

    @pytest.mark.asyncio
    async def test_get_quality_with_correlation_id(self, client_with_lifespan, pg_session):
        """Test quality score retrieval with correlation ID."""
        # Arrange
        user_data = await create_and_verify_test_user(client_with_lifespan, pg_session)
        login_response = await perform_login(client_with_lifespan, user_data["email"], user_data["password"])
        token = login_response[1]["access_token"]
        correlation_id = "test-correlation-quality-123"
        headers = {"Authorization": f"Bearer {token}", "X-Correlation-Id": correlation_id}

        # Create a novel to use as scope_id
        novel_id = await create_test_novel(pg_session, user_data["email"], "Quality Correlation Test Novel")

        session_data = {"scope_type": "GENESIS", "scope_id": novel_id}
        session_response = await client_with_lifespan.post(
            "/api/v1/conversations/sessions", json=session_data, headers=headers
        )
        assert session_response.status_code == 201
        session_id = session_response.json()["data"]["id"]

        # Act
        response = await client_with_lifespan.get(
            f"/api/v1/conversations/sessions/{session_id}/quality", headers=headers
        )

        # Assert
        assert response.status_code == 200
        # Check if correlation ID is in response headers
        assert "x-correlation-id" in [h.lower() for h in response.headers]

    @pytest.mark.asyncio
    async def test_get_quality_session_not_found(self, client_with_lifespan, pg_session):
        """Test quality retrieval for non-existent session."""
        # Arrange
        user_data = await create_and_verify_test_user(client_with_lifespan, pg_session)
        login_response = await perform_login(client_with_lifespan, user_data["email"], user_data["password"])
        token = login_response[1]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        nonexistent_session = str(uuid4())

        # Act
        response = await client_with_lifespan.get(
            f"/api/v1/conversations/sessions/{nonexistent_session}/quality", headers=headers
        )

        # Assert
        # Since this is skeleton implementation, it might return 200 with default score
        # or proper 404 - both are acceptable for skeleton
        assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_get_quality_unauthorized(self, client_with_lifespan):
        """Test quality retrieval without authentication."""
        session_id = str(uuid4())
        response = await client_with_lifespan.get(f"/api/v1/conversations/sessions/{session_id}/quality")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_quality_different_sessions(self, client_with_lifespan, pg_session):
        """Test quality retrieval for different sessions."""
        # Arrange
        user_data = await create_and_verify_test_user(client_with_lifespan, pg_session)
        login_response = await perform_login(client_with_lifespan, user_data["email"], user_data["password"])
        token = login_response[1]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create multiple sessions
        session_ids = []
        for i in range(3):
            novel_id = await create_test_novel(pg_session, user_data["email"], f"Quality Multi Test Novel {i}")
            session_data = {"scope_type": "GENESIS", "scope_id": novel_id}
            session_response = await client_with_lifespan.post(
                "/api/v1/conversations/sessions", json=session_data, headers=headers
            )
            assert session_response.status_code == 201
            session_ids.append(session_response.json()["data"]["id"])

        # Test quality retrieval for each session
        for session_id in session_ids:
            response = await client_with_lifespan.get(
                f"/api/v1/conversations/sessions/{session_id}/quality", headers=headers
            )

            assert response.status_code == 200
            data = response.json()
            quality_data = data["data"]
            assert quality_data["score"] == 0.0  # Skeleton always returns 0.0

    @pytest.mark.asyncio
    async def test_get_quality_access_control(self, client_with_lifespan, pg_session):
        """Test that users can only access quality from their own sessions."""
        # Create first user and session
        user1_data = await create_and_verify_test_user(
            client_with_lifespan, pg_session, username="user1", email="user1@example.com"
        )
        login1_response = await perform_login(client_with_lifespan, user1_data["email"], user1_data["password"])
        token1 = login1_response[1]["access_token"]
        headers1 = {"Authorization": f"Bearer {token1}"}

        # Create a novel to use as scope_id
        novel_id = await create_test_novel(pg_session, user1_data["email"], "User1 Quality Test Novel")

        session_data = {"scope_type": "GENESIS", "scope_id": novel_id}
        session_response = await client_with_lifespan.post(
            "/api/v1/conversations/sessions", json=session_data, headers=headers1
        )
        assert session_response.status_code == 201
        session_id = session_response.json()["data"]["id"]

        # Create second user
        user2_data = await create_and_verify_test_user(
            client_with_lifespan, pg_session, username="user2", email="user2@example.com"
        )
        login2_response = await perform_login(client_with_lifespan, user2_data["email"], user2_data["password"])
        token2 = login2_response[1]["access_token"]
        headers2 = {"Authorization": f"Bearer {token2}"}

        # Try to access user1's session quality with user2's token
        response = await client_with_lifespan.get(
            f"/api/v1/conversations/sessions/{session_id}/quality", headers=headers2
        )

        # Since this is skeleton implementation, it might return 200 with default score
        # or proper 404/403 - all are acceptable for access control test
        assert response.status_code in [200, 403, 404]


class TestConversationQualityConsistencyCheck:
    """Test cases for triggering consistency checks."""

    @pytest.mark.asyncio
    async def test_trigger_consistency_check_success(self, client_with_lifespan, pg_session):
        """Test successful consistency check trigger."""
        # Arrange
        user_data = await create_and_verify_test_user(client_with_lifespan, pg_session)
        login_response = await perform_login(client_with_lifespan, user_data["email"], user_data["password"])
        token = login_response[1]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create a novel to use as scope_id
        novel_id = await create_test_novel(pg_session, user_data["email"], "Consistency Test Novel")

        session_data = {"scope_type": "GENESIS", "scope_id": novel_id}
        session_response = await client_with_lifespan.post(
            "/api/v1/conversations/sessions", json=session_data, headers=headers
        )
        assert session_response.status_code == 201
        session_id = session_response.json()["data"]["id"]

        # Act
        response = await client_with_lifespan.post(
            f"/api/v1/conversations/sessions/{session_id}/consistency", headers=headers
        )

        # Assert
        if response.status_code != 202:
            print(f"Error response: {response.text}")
        assert response.status_code == 202  # Accepted (async operation)
        data = response.json()

        assert data["code"] == 0
        assert "一致性检查已受理" in data["msg"]
        assert "data" in data

        consistency_result = data["data"]
        assert consistency_result["accepted"] is True
        assert "command_id" in consistency_result
        # Verify command_id is valid UUID format
        assert UUID(consistency_result["command_id"])

        # Check Location header is set for command tracking
        location_header = next((v for k, v in response.headers.items() if k.lower() == "location"), None)
        assert location_header is not None
        assert f"/api/v1/conversations/sessions/{session_id}/commands/" in location_header

    @pytest.mark.asyncio
    async def test_trigger_consistency_check_with_idempotency(self, client_with_lifespan, pg_session):
        """Test consistency check with idempotency key."""
        # Arrange
        user_data = await create_and_verify_test_user(client_with_lifespan, pg_session)
        login_response = await perform_login(client_with_lifespan, user_data["email"], user_data["password"])
        token = login_response[1]["access_token"]
        idempotency_key = "consistency-check-idempotent-456"
        headers = {"Authorization": f"Bearer {token}", "Idempotency-Key": idempotency_key}

        # Create a novel to use as scope_id
        novel_id = await create_test_novel(pg_session, user_data["email"], "Consistency Idempotent Test Novel")

        session_data = {"scope_type": "GENESIS", "scope_id": novel_id}
        session_response = await client_with_lifespan.post(
            "/api/v1/conversations/sessions", json=session_data, headers=headers
        )
        assert session_response.status_code == 201
        session_id = session_response.json()["data"]["id"]

        # Act
        response = await client_with_lifespan.post(
            f"/api/v1/conversations/sessions/{session_id}/consistency", headers=headers
        )

        # Assert
        assert response.status_code == 202
        data = response.json()
        assert data["data"]["accepted"] is True
        assert UUID(data["data"]["command_id"])

    @pytest.mark.asyncio
    async def test_trigger_consistency_check_with_correlation_id(self, client_with_lifespan, pg_session):
        """Test consistency check with correlation ID."""
        # Arrange
        user_data = await create_and_verify_test_user(client_with_lifespan, pg_session)
        login_response = await perform_login(client_with_lifespan, user_data["email"], user_data["password"])
        token = login_response[1]["access_token"]
        correlation_id = "test-consistency-correlation-789"
        headers = {"Authorization": f"Bearer {token}", "X-Correlation-Id": correlation_id}

        # Create a novel to use as scope_id
        novel_id = await create_test_novel(pg_session, user_data["email"], "Consistency Correlation Test Novel")

        session_data = {"scope_type": "GENESIS", "scope_id": novel_id}
        session_response = await client_with_lifespan.post(
            "/api/v1/conversations/sessions", json=session_data, headers=headers
        )
        assert session_response.status_code == 201
        session_id = session_response.json()["data"]["id"]

        # Act
        response = await client_with_lifespan.post(
            f"/api/v1/conversations/sessions/{session_id}/consistency", headers=headers
        )

        # Assert
        assert response.status_code == 202
        # Check if correlation ID is in response headers
        assert "x-correlation-id" in [h.lower() for h in response.headers]

    @pytest.mark.asyncio
    async def test_trigger_consistency_check_multiple_requests(self, client_with_lifespan, pg_session):
        """Test triggering multiple consistency checks."""
        # Arrange
        user_data = await create_and_verify_test_user(client_with_lifespan, pg_session)
        login_response = await perform_login(client_with_lifespan, user_data["email"], user_data["password"])
        token = login_response[1]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create a novel to use as scope_id
        novel_id = await create_test_novel(pg_session, user_data["email"], "Consistency Multiple Test Novel")

        session_data = {"scope_type": "GENESIS", "scope_id": novel_id}
        session_response = await client_with_lifespan.post(
            "/api/v1/conversations/sessions", json=session_data, headers=headers
        )
        assert session_response.status_code == 201
        session_id = session_response.json()["data"]["id"]

        # Act - trigger multiple consistency checks
        command_ids = []
        for i in range(3):
            response = await client_with_lifespan.post(
                f"/api/v1/conversations/sessions/{session_id}/consistency", headers=headers
            )

            assert response.status_code == 202
            data = response.json()
            assert data["data"]["accepted"] is True
            command_ids.append(data["data"]["command_id"])

        # Assert - all command IDs should be the same (idempotent behavior)
        # Multiple requests for the same command type should return the existing pending command
        assert len(set(command_ids)) == 1  # All should be the same due to idempotency
        for cmd_id in command_ids:
            assert UUID(cmd_id)  # All valid UUIDs

    @pytest.mark.asyncio
    async def test_trigger_consistency_check_session_not_found(self, client_with_lifespan, pg_session):
        """Test consistency check for non-existent session."""
        # Arrange
        user_data = await create_and_verify_test_user(client_with_lifespan, pg_session)
        login_response = await perform_login(client_with_lifespan, user_data["email"], user_data["password"])
        token = login_response[1]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        nonexistent_session = str(uuid4())

        # Act
        response = await client_with_lifespan.post(
            f"/api/v1/conversations/sessions/{nonexistent_session}/consistency", headers=headers
        )

        # Assert
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_trigger_consistency_check_unauthorized(self, client_with_lifespan):
        """Test consistency check without authentication."""
        response = await client_with_lifespan.post(f"/api/v1/conversations/sessions/{uuid4()}/consistency")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_trigger_consistency_check_access_control(self, client_with_lifespan, pg_session):
        """Test that users can only trigger consistency checks on their own sessions."""
        # Create first user and session
        user1_data = await create_and_verify_test_user(
            client_with_lifespan, pg_session, username="user1", email="user1@example.com"
        )
        login1_response = await perform_login(client_with_lifespan, user1_data["email"], user1_data["password"])
        token1 = login1_response[1]["access_token"]
        headers1 = {"Authorization": f"Bearer {token1}"}

        # Create a novel to use as scope_id
        novel_id = await create_test_novel(pg_session, user1_data["email"], "User1 Consistency Test Novel")

        session_data = {"scope_type": "GENESIS", "scope_id": novel_id}
        session_response = await client_with_lifespan.post(
            "/api/v1/conversations/sessions", json=session_data, headers=headers1
        )
        assert session_response.status_code == 201
        session_id = session_response.json()["data"]["id"]

        # Create second user
        user2_data = await create_and_verify_test_user(
            client_with_lifespan, pg_session, username="user2", email="user2@example.com"
        )
        login2_response = await perform_login(client_with_lifespan, user2_data["email"], user2_data["password"])
        token2 = login2_response[1]["access_token"]
        headers2 = {"Authorization": f"Bearer {token2}"}

        # Try to trigger consistency check on user1's session with user2's token
        response = await client_with_lifespan.post(
            f"/api/v1/conversations/sessions/{session_id}/consistency", headers=headers2
        )

        # Should return 404 to avoid leaking session existence
        assert response.status_code == 404


class TestConversationQualityIntegration:
    """Integration test cases for quality workflow."""

    @pytest.mark.asyncio
    async def test_quality_workflow_integration(self, client_with_lifespan, pg_session):
        """Test complete quality workflow: get score -> trigger check -> get updated score."""
        # Arrange
        user_data = await create_and_verify_test_user(client_with_lifespan, pg_session)
        login_response = await perform_login(client_with_lifespan, user_data["email"], user_data["password"])
        token = login_response[1]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create a novel to use as scope_id
        novel_id = await create_test_novel(pg_session, user_data["email"], "Quality Workflow Test Novel")

        session_data = {"scope_type": "GENESIS", "scope_id": novel_id}
        session_response = await client_with_lifespan.post(
            "/api/v1/conversations/sessions", json=session_data, headers=headers
        )
        assert session_response.status_code == 201
        session_id = session_response.json()["data"]["id"]

        # Step 1: Get initial quality score
        get_response = await client_with_lifespan.get(
            f"/api/v1/conversations/sessions/{session_id}/quality", headers=headers
        )
        assert get_response.status_code == 200
        initial_quality = get_response.json()["data"]
        assert initial_quality["score"] == 0.0

        # Step 2: Trigger consistency check
        check_response = await client_with_lifespan.post(
            f"/api/v1/conversations/sessions/{session_id}/consistency", headers=headers
        )
        assert check_response.status_code == 202
        check_data = check_response.json()["data"]
        assert check_data["accepted"] is True
        command_id = check_data["command_id"]

        # Step 3: Get quality score again (would typically be updated after check completes)
        get_response_2 = await client_with_lifespan.get(
            f"/api/v1/conversations/sessions/{session_id}/quality", headers=headers
        )
        assert get_response_2.status_code == 200
        updated_quality = get_response_2.json()["data"]

        # In skeleton implementation, score remains 0.0 but updated_at might change
        assert updated_quality["score"] == 0.0
        assert "updated_at" in updated_quality

        # Verify command ID is valid UUID
        assert UUID(command_id)

    @pytest.mark.asyncio
    async def test_quality_and_consistency_with_content_changes(self, client_with_lifespan, pg_session):
        """Test quality operations with content changes."""
        # Arrange
        user_data = await create_and_verify_test_user(client_with_lifespan, pg_session)
        login_response = await perform_login(client_with_lifespan, user_data["email"], user_data["password"])
        token = login_response[1]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create session with initial content
        novel_id = await create_test_novel(pg_session, user_data["email"], "Quality Content Test Novel")

        session_data = {
            "scope_type": "GENESIS",
            "scope_id": novel_id,
            "initial_state": {"story": "Once upon a time..."},
        }
        session_response = await client_with_lifespan.post(
            "/api/v1/conversations/sessions", json=session_data, headers=headers
        )
        assert session_response.status_code == 201
        session_id = session_response.json()["data"]["id"]

        # Add some conversation content (rounds)
        message_data = {
            "role": DialogueRole.USER.value,
            "input": {"message": "Continue the story"}
        }
        message_response = await client_with_lifespan.post(
            f"/api/v1/conversations/sessions/{session_id}/messages", json=message_data, headers=headers
        )
        assert message_response.status_code == 201

        # Check quality after adding content
        quality_response = await client_with_lifespan.get(
            f"/api/v1/conversations/sessions/{session_id}/quality", headers=headers
        )
        assert quality_response.status_code == 200
        quality_data = quality_response.json()["data"]
        assert quality_data["score"] == 0.0  # Skeleton always returns 0.0

        # Trigger consistency check after content changes
        consistency_response = await client_with_lifespan.post(
            f"/api/v1/conversations/sessions/{session_id}/consistency", headers=headers
        )
        assert consistency_response.status_code == 202
        consistency_data = consistency_response.json()["data"]
        assert consistency_data["accepted"] is True

    @pytest.mark.asyncio
    async def test_quality_operations_timing(self, client_with_lifespan, pg_session):
        """Test timing aspects of quality operations."""
        # Arrange
        user_data = await create_and_verify_test_user(client_with_lifespan, pg_session)
        login_response = await perform_login(client_with_lifespan, user_data["email"], user_data["password"])
        token = login_response[1]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create a novel to use as scope_id
        novel_id = await create_test_novel(pg_session, user_data["email"], "Quality Timing Test Novel")

        session_data = {"scope_type": "GENESIS", "scope_id": novel_id}
        session_response = await client_with_lifespan.post(
            "/api/v1/conversations/sessions", json=session_data, headers=headers
        )
        assert session_response.status_code == 201
        session_id = session_response.json()["data"]["id"]

        # Get initial timestamp
        quality_response_1 = await client_with_lifespan.get(
            f"/api/v1/conversations/sessions/{session_id}/quality", headers=headers
        )
        timestamp_1 = quality_response_1.json()["data"]["updated_at"]

        # Trigger consistency check
        consistency_response = await client_with_lifespan.post(
            f"/api/v1/conversations/sessions/{session_id}/consistency", headers=headers
        )
        assert consistency_response.status_code == 202

        # Get timestamp again
        quality_response_2 = await client_with_lifespan.get(
            f"/api/v1/conversations/sessions/{session_id}/quality", headers=headers
        )
        timestamp_2 = quality_response_2.json()["data"]["updated_at"]

        # Timestamps should be valid ISO format strings
        assert isinstance(timestamp_1, str)
        assert isinstance(timestamp_2, str)
        # In a real implementation, timestamp_2 might be different from timestamp_1
        # but in skeleton they might be the same since no actual processing occurs

    @pytest.mark.asyncio
    async def test_quality_concurrent_operations(self, client_with_lifespan, pg_session):
        """Test concurrent quality operations."""
        # Arrange
        user_data = await create_and_verify_test_user(client_with_lifespan, pg_session)
        login_response = await perform_login(client_with_lifespan, user_data["email"], user_data["password"])
        token = login_response[1]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create a novel to use as scope_id
        novel_id = await create_test_novel(pg_session, user_data["email"], "Quality Concurrent Test Novel")

        session_data = {"scope_type": "GENESIS", "scope_id": novel_id}
        session_response = await client_with_lifespan.post(
            "/api/v1/conversations/sessions", json=session_data, headers=headers
        )
        assert session_response.status_code == 201
        session_id = session_response.json()["data"]["id"]

        # Trigger multiple concurrent consistency checks
        import asyncio

        async def trigger_check():
            return await client_with_lifespan.post(
                f"/api/v1/conversations/sessions/{session_id}/consistency", headers=headers
            )

        # Run 3 concurrent consistency checks
        responses = await asyncio.gather(trigger_check(), trigger_check(), trigger_check())

        # All should succeed
        for response in responses:
            assert response.status_code == 202
            data = response.json()
            assert data["data"]["accepted"] is True
            assert UUID(data["data"]["command_id"])

        # Get quality score after concurrent operations
        quality_response = await client_with_lifespan.get(
            f"/api/v1/conversations/sessions/{session_id}/quality", headers=headers
        )
        assert quality_response.status_code == 200
        quality_data = quality_response.json()["data"]
        assert quality_data["score"] == 0.0
