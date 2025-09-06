"""Integration tests for novel management endpoints."""

import pytest
from httpx import AsyncClient
from src.models.novel import Novel
from src.models.user import User
from src.schemas.enums import NovelStatus


@pytest.mark.integration
class TestNovelEndpointsIntegration:
    """Integration tests for novel management endpoints."""

    # Using global test_user and auth_headers fixtures from clients.py

    @pytest.mark.asyncio
    async def test_create_novel_success(self, async_client: AsyncClient, auth_headers):
        """Test successful novel creation."""
        # Arrange
        novel_data = {
            "title": "Integration Test Novel",
            "theme": "Science Fiction",
            "writing_style": "Technical",
            "target_chapters": 15,
        }

        # Act
        response = await async_client.post("/api/v1/novels", json=novel_data, headers=auth_headers)

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Integration Test Novel"
        assert data["theme"] == "Science Fiction"
        assert data["writing_style"] == "Technical"
        assert data["target_chapters"] == 15
        assert data["completed_chapters"] == 0
        assert data["status"] == "GENESIS"
        assert data["version"] == 1
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

    @pytest.mark.asyncio
    async def test_create_novel_validation_error(self, async_client: AsyncClient, auth_headers):
        """Test novel creation with validation errors."""
        # Arrange
        invalid_data = {
            "title": "",  # Empty title should fail
            "target_chapters": 0,  # Below minimum
        }

        # Act
        response = await async_client.post("/api/v1/novels", json=invalid_data, headers=auth_headers)

        # Assert
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    @pytest.mark.asyncio
    async def test_create_novel_unauthorized(self, async_client: AsyncClient):
        """Test novel creation without authentication."""
        # Arrange
        novel_data = {"title": "Test Novel", "target_chapters": 10}

        # Act
        response = await async_client.post("/api/v1/novels", json=novel_data)

        # Assert
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_user_novels_empty(self, async_client: AsyncClient, auth_headers):
        """Test listing novels when user has no novels."""
        # Act
        response = await async_client.get("/api/v1/novels", headers=auth_headers)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data == []

    @pytest.mark.asyncio
    async def test_full_novel_workflow(self, async_client: AsyncClient, auth_headers):
        """Test complete novel management workflow: create, read, update, delete."""
        # Step 1: Create novel
        novel_data = {
            "title": "Workflow Test Novel",
            "theme": "Fantasy",
            "writing_style": "Epic",
            "target_chapters": 20,
        }

        create_response = await async_client.post("/api/v1/novels", json=novel_data, headers=auth_headers)
        assert create_response.status_code == 201
        created_novel = create_response.json()
        novel_id = created_novel["id"]

        # Step 2: List novels (should include our novel)
        list_response = await async_client.get("/api/v1/novels", headers=auth_headers)
        assert list_response.status_code == 200
        novels_list = list_response.json()
        assert len(novels_list) == 1
        assert novels_list[0]["id"] == novel_id
        assert novels_list[0]["title"] == "Workflow Test Novel"

        # Step 3: Get specific novel
        get_response = await async_client.get(f"/api/v1/novels/{novel_id}", headers=auth_headers)
        assert get_response.status_code == 200
        retrieved_novel = get_response.json()
        assert retrieved_novel["id"] == novel_id
        assert retrieved_novel["title"] == "Workflow Test Novel"
        assert retrieved_novel["version"] == 1

        # Step 4: Update novel
        update_data = {
            "title": "Updated Workflow Novel",
            "theme": "Updated Fantasy",
            "version": 1,
        }
        update_response = await async_client.put(
            f"/api/v1/novels/{novel_id}", json=update_data, headers=auth_headers
        )
        assert update_response.status_code == 200
        updated_novel = update_response.json()
        assert updated_novel["title"] == "Updated Workflow Novel"
        assert updated_novel["theme"] == "Updated Fantasy"
        assert updated_novel["version"] == 2

        # Step 5: Test optimistic locking (version conflict)
        conflict_data = {
            "title": "Should Conflict",
            "version": 1,  # Wrong version
        }
        conflict_response = await async_client.put(
            f"/api/v1/novels/{novel_id}", json=conflict_data, headers=auth_headers
        )
        assert conflict_response.status_code == 409
        assert "modified by another process" in conflict_response.json()["detail"]

        # Step 6: Get novel stats
        stats_response = await async_client.get(f"/api/v1/novels/{novel_id}/stats", headers=auth_headers)
        assert stats_response.status_code == 200
        stats = stats_response.json()
        assert stats["novel_id"] == novel_id
        assert stats["total_chapters"] == 0
        assert stats["published_chapters"] == 0
        assert stats["target_chapters"] == 20
        assert stats["progress_percentage"] == 0

        # Step 7: Delete novel (now returns 204 No Content)
        delete_response = await async_client.delete(f"/api/v1/novels/{novel_id}", headers=auth_headers)
        assert delete_response.status_code == 204
        # No response body expected for 204 No Content

        # Step 8: Verify deletion
        get_deleted_response = await async_client.get(f"/api/v1/novels/{novel_id}", headers=auth_headers)
        assert get_deleted_response.status_code == 404

        # Step 9: List novels should be empty again
        final_list_response = await async_client.get("/api/v1/novels", headers=auth_headers)
        assert final_list_response.status_code == 200
        final_novels_list = final_list_response.json()
        assert final_novels_list == []

    @pytest.mark.asyncio
    async def test_list_novels_with_pagination(self, async_client: AsyncClient, auth_headers):
        """Test novel listing with pagination."""
        # Create multiple novels
        for i in range(5):
            novel_data = {
                "title": f"Test Novel {i+1}",
                "target_chapters": 10,
            }
            response = await async_client.post("/api/v1/novels", json=novel_data, headers=auth_headers)
            assert response.status_code == 201

        # Test pagination
        response = await async_client.get("/api/v1/novels?skip=2&limit=2", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

        # Test limit enforcement
        response = await async_client.get("/api/v1/novels?limit=3", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3

    @pytest.mark.asyncio
    async def test_list_novels_with_status_filter(
        self, async_client: AsyncClient, auth_headers, pg_session, test_user
    ):
        """Test novel listing with status filter."""
        # Create novel with GENESIS status (default)
        novel_data = {"title": "Genesis Novel", "target_chapters": 10}
        response = await async_client.post("/api/v1/novels", json=novel_data, headers=auth_headers)
        assert response.status_code == 201

        # Manually create another novel with different status using the same user
        generating_novel = Novel(
            user_id=test_user.id,  # Use the same user as authenticated in auth_headers
            title="Generating Novel",
            target_chapters=15,
            status=NovelStatus.GENERATING,
        )
        pg_session.add(generating_novel)
        await pg_session.commit()

        # Test filtering by GENESIS status
        response = await async_client.get("/api/v1/novels?status_filter=GENESIS", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["title"] == "Genesis Novel"
        assert data[0]["status"] == "GENESIS"

        # Test filtering by GENERATING status
        response = await async_client.get("/api/v1/novels?status_filter=GENERATING", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["title"] == "Generating Novel"
        assert data[0]["status"] == "GENERATING"

    @pytest.mark.asyncio
    async def test_get_novel_not_found(self, async_client: AsyncClient, auth_headers):
        """Test getting a non-existent novel."""
        # Use a random UUID
        fake_id = "550e8400-e29b-41d4-a716-446655440000"

        response = await async_client.get(f"/api/v1/novels/{fake_id}", headers=auth_headers)
        assert response.status_code == 404
        assert response.json()["detail"] == "Novel not found"

    @pytest.mark.asyncio
    async def test_update_novel_not_found(self, async_client: AsyncClient, auth_headers):
        """Test updating a non-existent novel."""
        # Use a random UUID
        fake_id = "550e8400-e29b-41d4-a716-446655440000"
        update_data = {"title": "Should Not Update"}

        response = await async_client.put(f"/api/v1/novels/{fake_id}", json=update_data, headers=auth_headers)
        assert response.status_code == 404
        assert response.json()["detail"] == "Novel not found"

    @pytest.mark.asyncio
    async def test_delete_novel_not_found(self, async_client: AsyncClient, auth_headers):
        """Test deleting a non-existent novel."""
        # Use a random UUID
        fake_id = "550e8400-e29b-41d4-a716-446655440000"

        response = await async_client.delete(f"/api/v1/novels/{fake_id}", headers=auth_headers)
        assert response.status_code == 404
        assert response.json()["detail"] == "Novel not found"

    @pytest.mark.asyncio
    async def test_novel_ownership_isolation(self, async_client: AsyncClient, pg_session):
        """Test that users can only access their own novels."""
        # Create two users
        import random
        import time

        # Use microseconds + random to ensure uniqueness across parallel tests
        timestamp1 = str(int(time.time() * 1000000)) + "_" + str(random.randint(1000, 9999))
        timestamp2 = str(int(time.time() * 1000000)) + "_" + str(random.randint(1000, 9999))

        user1 = User(
            username=f"user1_{timestamp1}",
            email=f"user1_{timestamp1}@example.com",
            password_hash="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj6QlTUpSxKO",
            is_active=True,
            is_verified=True,
        )
        user2 = User(
            username=f"user2_{timestamp2}",
            email=f"user2_{timestamp2}@example.com",
            password_hash="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj6QlTUpSxKO",
            is_active=True,
            is_verified=True,
        )
        pg_session.add_all([user1, user2])
        await pg_session.commit()
        await pg_session.refresh(user1)
        await pg_session.refresh(user2)

        # Create auth headers for both users
        from src.common.services.jwt_service import jwt_service

        access_token1, _, _ = jwt_service.create_access_token(
            str(user1.id), {"email": user1.email, "username": user1.username}
        )
        headers1 = {"Authorization": f"Bearer {access_token1}"}

        access_token2, _, _ = jwt_service.create_access_token(
            str(user2.id), {"email": user2.email, "username": user2.username}
        )
        headers2 = {"Authorization": f"Bearer {access_token2}"}

        # User1 creates a novel
        novel_data = {"title": "User1 Novel", "target_chapters": 10}
        response = await async_client.post("/api/v1/novels", json=novel_data, headers=headers1)
        assert response.status_code == 201
        novel_id = response.json()["id"]

        # User2 should not be able to access User1's novel
        response = await async_client.get(f"/api/v1/novels/{novel_id}", headers=headers2)
        assert response.status_code == 404

        # User2 should not be able to update User1's novel
        update_data = {"title": "Hijacked Novel"}
        response = await async_client.put(f"/api/v1/novels/{novel_id}", json=update_data, headers=headers2)
        assert response.status_code == 404

        # User2 should not be able to delete User1's novel
        response = await async_client.delete(f"/api/v1/novels/{novel_id}", headers=headers2)
        assert response.status_code == 404

        # User1 should still be able to access their novel
        response = await async_client.get(f"/api/v1/novels/{novel_id}", headers=headers1)
        assert response.status_code == 200
        assert response.json()["title"] == "User1 Novel"

    @pytest.mark.asyncio
    async def test_get_novel_chapters_empty(self, async_client: AsyncClient, auth_headers):
        """Test getting chapters for a novel with no chapters."""
        # Create novel
        novel_data = {"title": "No Chapters Novel", "target_chapters": 10}
        response = await async_client.post("/api/v1/novels", json=novel_data, headers=auth_headers)
        assert response.status_code == 201
        novel_id = response.json()["id"]

        # Get chapters (should be empty)
        response = await async_client.get(f"/api/v1/novels/{novel_id}/chapters", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data == []

    @pytest.mark.asyncio
    async def test_get_novel_characters_empty(self, async_client: AsyncClient, auth_headers):
        """Test getting characters for a novel with no characters."""
        # Create novel
        novel_data = {"title": "No Characters Novel", "target_chapters": 10}
        response = await async_client.post("/api/v1/novels", json=novel_data, headers=auth_headers)
        assert response.status_code == 201
        novel_id = response.json()["id"]

        # Get characters (should be empty)
        response = await async_client.get(f"/api/v1/novels/{novel_id}/characters", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data == []

    @pytest.mark.asyncio
    async def test_invalid_uuid_format(self, async_client: AsyncClient, auth_headers):
        """Test endpoints with invalid UUID format."""
        invalid_id = "not-a-uuid"

        # Test various endpoints with invalid UUID
        endpoints = [
            f"/api/v1/novels/{invalid_id}",
            f"/api/v1/novels/{invalid_id}/chapters",
            f"/api/v1/novels/{invalid_id}/characters",
            f"/api/v1/novels/{invalid_id}/stats",
        ]

        for endpoint in endpoints:
            response = await async_client.get(endpoint, headers=auth_headers)
            assert response.status_code == 422  # Validation error for invalid UUID

        # Test PUT and DELETE with invalid UUID
        response = await async_client.put(
            f"/api/v1/novels/{invalid_id}", json={"title": "test"}, headers=auth_headers
        )
        assert response.status_code == 422

        response = await async_client.delete(f"/api/v1/novels/{invalid_id}", headers=auth_headers)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_novel_title_length_validation(self, async_client: AsyncClient, auth_headers):
        """Test novel title length validation."""
        # Test with title that's too long (over 255 characters)
        long_title = "x" * 256
        novel_data = {"title": long_title, "target_chapters": 10}

        response = await async_client.post("/api/v1/novels", json=novel_data, headers=auth_headers)
        assert response.status_code == 422

        # Test with valid length title
        valid_title = "x" * 255
        novel_data = {"title": valid_title, "target_chapters": 10}

        response = await async_client.post("/api/v1/novels", json=novel_data, headers=auth_headers)
        assert response.status_code == 201
        assert response.json()["title"] == valid_title

    @pytest.mark.asyncio
    async def test_target_chapters_validation(self, async_client: AsyncClient, auth_headers):
        """Test target chapters validation."""
        # Test with invalid target_chapters (too high)
        novel_data = {"title": "Test Novel", "target_chapters": 1001}  # Over limit
        response = await async_client.post("/api/v1/novels", json=novel_data, headers=auth_headers)
        assert response.status_code == 422

        # Test with invalid target_chapters (zero/negative)
        novel_data = {"title": "Test Novel", "target_chapters": 0}
        response = await async_client.post("/api/v1/novels", json=novel_data, headers=auth_headers)
        assert response.status_code == 422

        # Test with valid target_chapters
        novel_data = {"title": "Test Novel", "target_chapters": 50}
        response = await async_client.post("/api/v1/novels", json=novel_data, headers=auth_headers)
        assert response.status_code == 201
        assert response.json()["target_chapters"] == 50
