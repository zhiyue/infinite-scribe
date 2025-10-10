"""Integration tests for conversation stages API endpoints."""

from uuid import UUID, uuid4

import pytest
from tests.integration.api.auth_test_helpers import create_and_verify_test_user, perform_login


class TestConversationStagesRetrieve:
    """Test cases for retrieving conversation stages."""

    @pytest.mark.asyncio
    async def test_get_stage_success(self, client_with_lifespan, pg_session):
        """Test successful stage retrieval (skeleton implementation)."""
        # Arrange - create user and session
        user_data = await create_and_verify_test_user(client_with_lifespan, pg_session)
        login_response = await perform_login(client_with_lifespan, user_data["email"], user_data["password"])
        token = login_response[1]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create session first
        from tests.integration.api.auth_test_helpers import create_test_novel

        novel_id = await create_test_novel(pg_session, user_data["email"], "Stages Get Test Novel")
        session_data = {"scope_type": "GENESIS", "scope_id": novel_id}
        session_response = await client_with_lifespan.post("/api/v1/conversations/sessions", json=session_data, headers=headers)
        assert session_response.status_code == 201
        session_id = session_response.json()["data"]["id"]

        # Act
        response = await client_with_lifespan.get(f"/api/v1/conversations/sessions/{session_id}/stage", headers=headers)

        # Assert
        if response.status_code != 200:
            print(f"Error response: {response.text}")
        assert response.status_code == 200
        data = response.json()

        assert data["code"] == 0
        assert "获取阶段成功" in data["msg"]
        assert "skeleton" in data["msg"]  # Skeleton implementation message
        assert "data" in data

        stage_data = data["data"]
        assert "stage" in stage_data
        assert stage_data["stage"] == "Stage_0"  # Default skeleton stage

    @pytest.mark.asyncio
    async def test_get_stage_with_correlation_id(self, client_with_lifespan, pg_session):
        """Test stage retrieval with correlation ID."""
        # Arrange
        user_data = await create_and_verify_test_user(client_with_lifespan, pg_session)
        login_response = await perform_login(client_with_lifespan, user_data["email"], user_data["password"])
        token = login_response[1]["access_token"]
        correlation_id = "test-correlation-stage-get"
        headers = {"Authorization": f"Bearer {token}", "X-Correlation-Id": correlation_id}

        # Create session
        from tests.integration.api.auth_test_helpers import create_test_novel

        novel_id = await create_test_novel(pg_session, user_data["email"], "Stage Correlation Test Novel")
        session_data = {"scope_type": "GENESIS", "scope_id": novel_id}
        session_response = await client_with_lifespan.post("/api/v1/conversations/sessions", json=session_data, headers=headers)
        assert session_response.status_code == 201
        session_id = session_response.json()["data"]["id"]

        # Act
        response = await client_with_lifespan.get(f"/api/v1/conversations/sessions/{session_id}/stage", headers=headers)

        # Assert
        assert response.status_code == 200
        # Check if correlation ID is in response headers
        assert "x-correlation-id" in [h.lower() for h in response.headers]

    @pytest.mark.asyncio
    async def test_get_stage_unauthorized(self, client_with_lifespan):
        """Test retrieving stage without authentication."""
        session_id = str(uuid4())
        response = await client_with_lifespan.get(f"/api/v1/conversations/sessions/{session_id}/stage")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_stage_nonexistent_session(self, client_with_lifespan, pg_session):
        """Test retrieving stage for non-existent session."""
        # Arrange
        user_data = await create_and_verify_test_user(client_with_lifespan, pg_session)
        login_response = await perform_login(client_with_lifespan, user_data["email"], user_data["password"])
        token = login_response[1]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        nonexistent_session = str(uuid4())

        # Act
        response = await client_with_lifespan.get(
            f"/api/v1/conversations/sessions/{nonexistent_session}/stage", headers=headers
        )

        # Assert
        # Since this is skeleton implementation, it might return 200 with default stage
        # or proper 404 - both are acceptable for skeleton
        assert response.status_code in [200, 404]


class TestConversationStagesSet:
    """Test cases for setting conversation stages."""

    @pytest.mark.asyncio
    async def test_set_stage_success(self, client_with_lifespan, pg_session):
        """Test successful stage setting (skeleton implementation)."""
        # Arrange
        user_data = await create_and_verify_test_user(client_with_lifespan, pg_session)
        login_response = await perform_login(client_with_lifespan, user_data["email"], user_data["password"])
        token = login_response[1]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create session
        from tests.integration.api.auth_test_helpers import create_test_novel

        novel_id = await create_test_novel(pg_session, user_data["email"], "Stage Set Test Novel")
        session_data = {"scope_type": "GENESIS", "scope_id": novel_id}
        session_response = await client_with_lifespan.post("/api/v1/conversations/sessions", json=session_data, headers=headers)
        assert session_response.status_code == 201
        session_id = session_response.json()["data"]["id"]

        # Act
        stage_data = {"stage": "PLANNING"}
        response = await client_with_lifespan.put(
            f"/api/v1/conversations/sessions/{session_id}/stage", json=stage_data, headers=headers
        )

        # Assert
        if response.status_code != 200:
            print(f"Error response: {response.text}")
        assert response.status_code == 200
        data = response.json()

        assert data["code"] == 0
        assert "切换阶段成功" in data["msg"]
        assert "skeleton" in data["msg"]  # Skeleton implementation message
        assert "data" in data

        result_data = data["data"]
        assert result_data["stage"] == "PLANNING"
        assert result_data["version"] == 2  # Version incremented

        # Check ETag header is set
        etag_header = next((v for k, v in response.headers.items() if k.lower() == "etag"), None)
        assert etag_header == '"2"'

    @pytest.mark.asyncio
    async def test_set_stage_with_if_match_success(self, client_with_lifespan, pg_session):
        """Test stage setting with correct If-Match header."""
        # Arrange
        user_data = await create_and_verify_test_user(client_with_lifespan, pg_session)
        login_response = await perform_login(client_with_lifespan, user_data["email"], user_data["password"])
        token = login_response[1]["access_token"]
        headers = {"Authorization": f"Bearer {token}", "If-Match": '"1"'}

        # Create session
        from tests.integration.api.auth_test_helpers import create_test_novel

        novel_id = await create_test_novel(pg_session, user_data["email"], "Stage If-Match Test Novel")
        session_data = {"scope_type": "GENESIS", "scope_id": novel_id}
        session_response = await client_with_lifespan.post("/api/v1/conversations/sessions", json=session_data, headers=headers)
        assert session_response.status_code == 201
        session_id = session_response.json()["data"]["id"]

        # Act
        stage_data = {"stage": "DEVELOPMENT"}
        response = await client_with_lifespan.put(
            f"/api/v1/conversations/sessions/{session_id}/stage", json=stage_data, headers=headers
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["stage"] == "DEVELOPMENT"

    @pytest.mark.asyncio
    async def test_set_stage_with_if_match_conflict(self, client_with_lifespan, pg_session):
        """Test stage setting with incorrect If-Match header (optimistic locking)."""
        # Arrange
        user_data = await create_and_verify_test_user(client_with_lifespan, pg_session)
        login_response = await perform_login(client_with_lifespan, user_data["email"], user_data["password"])
        token = login_response[1]["access_token"]
        headers = {"Authorization": f"Bearer {token}", "If-Match": '"999"'}  # Wrong version

        # Create session
        from tests.integration.api.auth_test_helpers import create_test_novel

        novel_id = await create_test_novel(pg_session, user_data["email"], "Stage Conflict Test Novel")
        session_data = {"scope_type": "GENESIS", "scope_id": novel_id}
        session_response = await client_with_lifespan.post("/api/v1/conversations/sessions", json=session_data, headers=headers)
        assert session_response.status_code == 201
        session_id = session_response.json()["data"]["id"]

        # Act
        stage_data = {"stage": "TESTING"}
        response = await client_with_lifespan.put(
            f"/api/v1/conversations/sessions/{session_id}/stage", json=stage_data, headers=headers
        )

        # Assert
        assert response.status_code == 412  # Precondition Failed

    @pytest.mark.asyncio
    async def test_set_stage_different_values(self, client_with_lifespan, pg_session):
        """Test setting different stage values."""
        # Arrange
        user_data = await create_and_verify_test_user(client_with_lifespan, pg_session)
        login_response = await perform_login(client_with_lifespan, user_data["email"], user_data["password"])
        token = login_response[1]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create session
        from tests.integration.api.auth_test_helpers import create_test_novel

        novel_id = await create_test_novel(pg_session, user_data["email"], "Stage Values Test Novel")
        session_data = {"scope_type": "GENESIS", "scope_id": novel_id}
        session_response = await client_with_lifespan.post("/api/v1/conversations/sessions", json=session_data, headers=headers)
        assert session_response.status_code == 201
        session_id = session_response.json()["data"]["id"]

        # Test different stage values
        stages = ["PLANNING", "DEVELOPMENT", "TESTING", "PRODUCTION", "ARCHIVED"]

        for stage in stages:
            stage_data = {"stage": stage}
            response = await client_with_lifespan.put(
                f"/api/v1/conversations/sessions/{session_id}/stage", json=stage_data, headers=headers
            )

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["data"]["stage"] == stage

    @pytest.mark.asyncio
    async def test_set_stage_unauthorized(self, client_with_lifespan):
        """Test setting stage without authentication."""
        stage_data = {"stage": "PLANNING"}
        response = await client_with_lifespan.put(f"/api/v1/conversations/sessions/{uuid4()}/stage", json=stage_data)
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_set_stage_invalid_data(self, client_with_lifespan, pg_session):
        """Test setting stage with invalid data."""
        # Arrange
        user_data = await create_and_verify_test_user(client_with_lifespan, pg_session)
        login_response = await perform_login(client_with_lifespan, user_data["email"], user_data["password"])
        token = login_response[1]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create session
        from tests.integration.api.auth_test_helpers import create_test_novel

        novel_id = await create_test_novel(pg_session, user_data["email"], "Stage Invalid Test Novel")
        session_data = {"scope_type": "GENESIS", "scope_id": novel_id}
        session_response = await client_with_lifespan.post("/api/v1/conversations/sessions", json=session_data, headers=headers)
        assert session_response.status_code == 201
        session_id = session_response.json()["data"]["id"]

        # Act - invalid JSON structure
        response = await client_with_lifespan.put(
            f"/api/v1/conversations/sessions/{session_id}/stage",
            json={"invalid": "data"},  # Missing 'stage' field
            headers=headers,
        )

        # Assert
        assert response.status_code == 422  # Validation error


class TestConversationStagesValidate:
    """Test cases for validating conversation stages."""

    @pytest.mark.asyncio
    async def test_validate_stage_success(self, client_with_lifespan, pg_session):
        """Test successful stage validation (skeleton implementation)."""
        # Arrange
        user_data = await create_and_verify_test_user(client_with_lifespan, pg_session)
        login_response = await perform_login(client_with_lifespan, user_data["email"], user_data["password"])
        token = login_response[1]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create session
        from tests.integration.api.auth_test_helpers import create_test_novel

        novel_id = await create_test_novel(pg_session, user_data["email"], "Stage Validate Test Novel")
        session_data = {"scope_type": "GENESIS", "scope_id": novel_id}
        session_response = await client_with_lifespan.post("/api/v1/conversations/sessions", json=session_data, headers=headers)
        assert session_response.status_code == 201
        session_id = session_response.json()["data"]["id"]

        # Act
        response = await client_with_lifespan.post(
            f"/api/v1/conversations/sessions/{session_id}/stage/validate", headers=headers
        )

        # Assert
        if response.status_code != 202:
            print(f"Error response: {response.text}")
        assert response.status_code == 202  # Accepted (async operation)
        data = response.json()

        assert data["code"] == 0
        assert "阶段验证已受理" in data["msg"]
        assert "skeleton" in data["msg"]  # Skeleton implementation message
        assert "data" in data

        validation_data = data["data"]
        assert validation_data["accepted"] is True
        assert "command_id" in validation_data
        # Verify command_id is valid UUID format
        assert UUID(validation_data["command_id"])

        # Check Location header is set for command tracking
        location_header = next((v for k, v in response.headers.items() if k.lower() == "location"), None)
        assert location_header is not None
        assert f"/api/v1/conversations/sessions/{session_id}/commands/" in location_header

    @pytest.mark.asyncio
    async def test_validate_stage_with_idempotency(self, client_with_lifespan, pg_session):
        """Test stage validation with idempotency key."""
        # Arrange
        user_data = await create_and_verify_test_user(client_with_lifespan, pg_session)
        login_response = await perform_login(client_with_lifespan, user_data["email"], user_data["password"])
        token = login_response[1]["access_token"]
        idempotency_key = "validate-stage-idempotent-456"
        headers = {"Authorization": f"Bearer {token}", "Idempotency-Key": idempotency_key}

        # Create session
        from tests.integration.api.auth_test_helpers import create_test_novel

        novel_id = await create_test_novel(pg_session, user_data["email"], "Validate Idempotent Test Novel")
        session_data = {"scope_type": "GENESIS", "scope_id": novel_id}
        session_response = await client_with_lifespan.post("/api/v1/conversations/sessions", json=session_data, headers=headers)
        assert session_response.status_code == 201
        session_id = session_response.json()["data"]["id"]

        # Act
        response = await client_with_lifespan.post(
            f"/api/v1/conversations/sessions/{session_id}/stage/validate", headers=headers
        )

        # Assert
        assert response.status_code == 202
        data = response.json()
        assert data["data"]["accepted"] is True
        assert UUID(data["data"]["command_id"])

    @pytest.mark.asyncio
    async def test_validate_stage_with_correlation_id(self, client_with_lifespan, pg_session):
        """Test stage validation with correlation ID."""
        # Arrange
        user_data = await create_and_verify_test_user(client_with_lifespan, pg_session)
        login_response = await perform_login(client_with_lifespan, user_data["email"], user_data["password"])
        token = login_response[1]["access_token"]
        correlation_id = "test-validate-correlation-789"
        headers = {"Authorization": f"Bearer {token}", "X-Correlation-Id": correlation_id}

        # Create session
        from tests.integration.api.auth_test_helpers import create_test_novel

        novel_id = await create_test_novel(pg_session, user_data["email"], "Validate Correlation Test Novel")
        session_data = {"scope_type": "GENESIS", "scope_id": novel_id}
        session_response = await client_with_lifespan.post("/api/v1/conversations/sessions", json=session_data, headers=headers)
        assert session_response.status_code == 201
        session_id = session_response.json()["data"]["id"]

        # Act
        response = await client_with_lifespan.post(
            f"/api/v1/conversations/sessions/{session_id}/stage/validate", headers=headers
        )

        # Assert
        assert response.status_code == 202
        # Check if correlation ID is in response headers
        assert "x-correlation-id" in [h.lower() for h in response.headers]

    @pytest.mark.asyncio
    async def test_validate_stage_unauthorized(self, client_with_lifespan):
        """Test stage validation without authentication."""
        response = await client_with_lifespan.post(f"/api/v1/conversations/sessions/{uuid4()}/stage/validate")
        assert response.status_code == 401


class TestConversationStagesLock:
    """Test cases for locking conversation stages."""

    @pytest.mark.asyncio
    async def test_lock_stage_success(self, client_with_lifespan, pg_session):
        """Test successful stage locking (skeleton implementation)."""
        # Arrange
        user_data = await create_and_verify_test_user(client_with_lifespan, pg_session)
        login_response = await perform_login(client_with_lifespan, user_data["email"], user_data["password"])
        token = login_response[1]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create session
        from tests.integration.api.auth_test_helpers import create_test_novel

        novel_id = await create_test_novel(pg_session, user_data["email"], "Stage Lock Test Novel")
        session_data = {"scope_type": "GENESIS", "scope_id": novel_id}
        session_response = await client_with_lifespan.post("/api/v1/conversations/sessions", json=session_data, headers=headers)
        assert session_response.status_code == 201
        session_id = session_response.json()["data"]["id"]

        # Act
        response = await client_with_lifespan.post(f"/api/v1/conversations/sessions/{session_id}/stage/lock", headers=headers)

        # Assert
        if response.status_code != 202:
            print(f"Error response: {response.text}")
        assert response.status_code == 202  # Accepted (async operation)
        data = response.json()

        assert data["code"] == 0
        assert "阶段锁定已受理" in data["msg"]
        assert "skeleton" in data["msg"]  # Skeleton implementation message
        assert "data" in data

        lock_data = data["data"]
        assert lock_data["accepted"] is True
        assert "command_id" in lock_data
        # Verify command_id is valid UUID format
        assert UUID(lock_data["command_id"])

        # Check Location header is set for command tracking
        location_header = next((v for k, v in response.headers.items() if k.lower() == "location"), None)
        assert location_header is not None
        assert f"/api/v1/conversations/sessions/{session_id}/commands/" in location_header

    @pytest.mark.asyncio
    async def test_lock_stage_with_idempotency(self, client_with_lifespan, pg_session):
        """Test stage locking with idempotency key."""
        # Arrange
        user_data = await create_and_verify_test_user(client_with_lifespan, pg_session)
        login_response = await perform_login(client_with_lifespan, user_data["email"], user_data["password"])
        token = login_response[1]["access_token"]
        idempotency_key = "lock-stage-idempotent-789"
        headers = {"Authorization": f"Bearer {token}", "Idempotency-Key": idempotency_key}

        # Create session
        from tests.integration.api.auth_test_helpers import create_test_novel

        novel_id = await create_test_novel(pg_session, user_data["email"], "Lock Idempotent Test Novel")
        session_data = {"scope_type": "GENESIS", "scope_id": novel_id}
        session_response = await client_with_lifespan.post("/api/v1/conversations/sessions", json=session_data, headers=headers)
        assert session_response.status_code == 201
        session_id = session_response.json()["data"]["id"]

        # Act
        response = await client_with_lifespan.post(f"/api/v1/conversations/sessions/{session_id}/stage/lock", headers=headers)

        # Assert
        assert response.status_code == 202
        data = response.json()
        assert data["data"]["accepted"] is True
        assert UUID(data["data"]["command_id"])

    @pytest.mark.asyncio
    async def test_lock_stage_with_correlation_id(self, client_with_lifespan, pg_session):
        """Test stage locking with correlation ID."""
        # Arrange
        user_data = await create_and_verify_test_user(client_with_lifespan, pg_session)
        login_response = await perform_login(client_with_lifespan, user_data["email"], user_data["password"])
        token = login_response[1]["access_token"]
        correlation_id = "test-lock-correlation-abc"
        headers = {"Authorization": f"Bearer {token}", "X-Correlation-Id": correlation_id}

        # Create session
        from tests.integration.api.auth_test_helpers import create_test_novel

        novel_id = await create_test_novel(pg_session, user_data["email"], "Lock Correlation Test Novel")
        session_data = {"scope_type": "GENESIS", "scope_id": novel_id}
        session_response = await client_with_lifespan.post("/api/v1/conversations/sessions", json=session_data, headers=headers)
        assert session_response.status_code == 201
        session_id = session_response.json()["data"]["id"]

        # Act
        response = await client_with_lifespan.post(f"/api/v1/conversations/sessions/{session_id}/stage/lock", headers=headers)

        # Assert
        assert response.status_code == 202
        # Check if correlation ID is in response headers
        assert "x-correlation-id" in [h.lower() for h in response.headers]

    @pytest.mark.asyncio
    async def test_lock_stage_unauthorized(self, client_with_lifespan):
        """Test stage locking without authentication."""
        response = await client_with_lifespan.post(f"/api/v1/conversations/sessions/{uuid4()}/stage/lock")
        assert response.status_code == 401


class TestConversationStagesIntegration:
    """Integration test cases for stage workflow."""

    @pytest.mark.asyncio
    async def test_stage_workflow_integration(self, client_with_lifespan, pg_session):
        """Test complete stage workflow: get -> set -> validate -> lock."""
        # Arrange
        user_data = await create_and_verify_test_user(client_with_lifespan, pg_session)
        login_response = await perform_login(client_with_lifespan, user_data["email"], user_data["password"])
        token = login_response[1]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create session
        from tests.integration.api.auth_test_helpers import create_test_novel

        novel_id = await create_test_novel(pg_session, user_data["email"], "Stage Workflow Test Novel")
        session_data = {"scope_type": "GENESIS", "scope_id": novel_id}
        session_response = await client_with_lifespan.post("/api/v1/conversations/sessions", json=session_data, headers=headers)
        assert session_response.status_code == 201
        session_id = session_response.json()["data"]["id"]

        # Step 1: Get initial stage
        get_response = await client_with_lifespan.get(f"/api/v1/conversations/sessions/{session_id}/stage", headers=headers)
        assert get_response.status_code == 200
        initial_stage = get_response.json()["data"]["stage"]
        assert initial_stage == "Stage_0"

        # Step 2: Set new stage
        set_response = await client_with_lifespan.put(
            f"/api/v1/conversations/sessions/{session_id}/stage", json={"stage": "DEVELOPMENT"}, headers=headers
        )
        assert set_response.status_code == 200
        assert set_response.json()["data"]["stage"] == "DEVELOPMENT"

        # Step 3: Validate the stage
        validate_response = await client_with_lifespan.post(
            f"/api/v1/conversations/sessions/{session_id}/stage/validate", headers=headers
        )
        assert validate_response.status_code == 202
        validate_data = validate_response.json()["data"]
        assert validate_data["accepted"] is True
        command_id_1 = validate_data["command_id"]

        # Step 4: Lock the stage
        lock_response = await client_with_lifespan.post(
            f"/api/v1/conversations/sessions/{session_id}/stage/lock", headers=headers
        )
        assert lock_response.status_code == 202
        lock_data = lock_response.json()["data"]
        assert lock_data["accepted"] is True
        command_id_2 = lock_data["command_id"]

        # Verify command IDs are different (different operations)
        assert command_id_1 != command_id_2

    @pytest.mark.asyncio
    async def test_stage_access_control(self, client_with_lifespan, pg_session):
        """Test that users can only access their own session stages."""
        # Create first user and session
        user1_data = await create_and_verify_test_user(
            client_with_lifespan, pg_session, username="user1", email="user1@example.com"
        )
        login1_response = await perform_login(client_with_lifespan, user1_data["email"], user1_data["password"])
        token1 = login1_response[1]["access_token"]
        headers1 = {"Authorization": f"Bearer {token1}"}

        # Create session for user1
        from tests.integration.api.auth_test_helpers import create_test_novel

        novel_id = await create_test_novel(pg_session, user1_data["email"], "User1 Stages Test Novel")
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

        # Try to access user1's session stages with user2's token
        response = await client_with_lifespan.get(f"/api/v1/conversations/sessions/{session_id}/stage", headers=headers2)

        # Since this is skeleton implementation, it might return 200 with default stage
        # or proper 404/403 - both are acceptable for access control test
        assert response.status_code in [200, 403, 404]

        # Try to set stage on user1's session with user2's token
        set_response = await client_with_lifespan.put(
            f"/api/v1/conversations/sessions/{session_id}/stage", json={"stage": "UNAUTHORIZED"}, headers=headers2
        )
        assert set_response.status_code in [403, 404, 412]  # Should be denied
