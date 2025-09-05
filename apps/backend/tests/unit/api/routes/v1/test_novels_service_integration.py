"""Unit tests for novel routes using service layer."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException, status
from src.api.routes.v1.novels import (
    create_novel,
    delete_novel,
    get_novel,
    list_user_novels,
    update_novel,
)
from src.models.user import User
from src.schemas.enums import NovelStatus
from src.schemas.novel.create import NovelCreateRequest
from src.schemas.novel.read import NovelResponse, NovelSummary
from src.schemas.novel.update import NovelUpdateRequest


class TestNovelRoutesServiceIntegration:
    """Test cases for novel routes with service layer integration."""

    @pytest.fixture
    def mock_user(self):
        """Create mock user."""
        user = Mock(spec=User)
        user.id = 1
        user.username = "testuser"
        user.email = "test@example.com"
        return user

    @pytest.fixture
    def sample_novel_summary(self):
        """Create sample novel summary."""
        return NovelSummary(
            id=uuid4(),
            title="Test Novel",
            theme="Fantasy Adventure",
            status=NovelStatus.GENESIS,
            target_chapters=10,
            completed_chapters=0,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

    @pytest.fixture
    def sample_novel_response(self):
        """Create sample novel response."""
        return NovelResponse(
            id=uuid4(),
            title="Test Novel",
            theme="Fantasy Adventure",
            writing_style="Epic",
            status=NovelStatus.GENESIS,
            target_chapters=10,
            completed_chapters=0,
            version=1,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

    @pytest.mark.asyncio
    async def test_list_user_novels_success(self, mock_user, sample_novel_summary):
        """Test successful listing of user novels using service."""
        # Arrange
        mock_db = AsyncMock()

        with patch("src.api.routes.v1.novels.novel_service") as mock_service:
            mock_service.list_user_novels = AsyncMock(return_value={"success": True, "novels": [sample_novel_summary]})

            # Act
            result = await list_user_novels(skip=0, limit=50, status_filter=None, db=mock_db, current_user=mock_user)

            # Assert
            assert isinstance(result, list)
            assert len(result) == 1
            assert result[0].title == "Test Novel"
            mock_service.list_user_novels.assert_called_once_with(mock_db, 1, 0, 50, None)

    @pytest.mark.asyncio
    async def test_list_user_novels_service_error(self, mock_user):
        """Test listing novels when service returns error."""
        # Arrange
        mock_db = AsyncMock()

        with patch("src.api.routes.v1.novels.novel_service") as mock_service:
            mock_service.list_user_novels.return_value = {"success": False, "error": "Database connection failed"}

            # Act & Assert
            with pytest.raises(HTTPException) as exc_info:
                await list_user_novels(skip=0, limit=50, status_filter=None, db=mock_db, current_user=mock_user)

            assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            assert exc_info.value.detail == "Database connection failed"

    @pytest.mark.asyncio
    async def test_create_novel_success(self, mock_user, sample_novel_response):
        """Test successful novel creation using service."""
        # Arrange
        mock_db = AsyncMock()
        request = NovelCreateRequest(title="New Novel", theme="Science Fiction", target_chapters=20)

        with patch("src.api.routes.v1.novels.novel_service") as mock_service:
            mock_service.create_novel.return_value = {"success": True, "novel": sample_novel_response}

            # Act
            result = await create_novel(request, mock_db, mock_user)

            # Assert
            assert result.title == "Test Novel"
            assert result.status == NovelStatus.GENESIS
            mock_service.create_novel.assert_called_once_with(mock_db, 1, request)

    @pytest.mark.asyncio
    async def test_create_novel_constraint_error(self, mock_user):
        """Test novel creation with constraint error."""
        # Arrange
        mock_db = AsyncMock()
        request = NovelCreateRequest(title="New Novel", target_chapters=20)

        with patch("src.api.routes.v1.novels.novel_service") as mock_service:
            mock_service.create_novel.return_value = {
                "success": False,
                "error": "Novel creation failed due to data constraints",
            }

            # Act & Assert
            with pytest.raises(HTTPException) as exc_info:
                await create_novel(request, mock_db, mock_user)

            assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
            assert "constraint" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_get_novel_success(self, mock_user, sample_novel_response):
        """Test successful novel retrieval using service."""
        # Arrange
        mock_db = AsyncMock()
        novel_id = uuid4()

        with patch("src.api.routes.v1.novels.novel_service") as mock_service:
            mock_service.get_novel.return_value = {"success": True, "novel": sample_novel_response}

            # Act
            result = await get_novel(novel_id, mock_db, mock_user)

            # Assert
            assert result.title == "Test Novel"
            assert result.status == NovelStatus.GENESIS
            mock_service.get_novel.assert_called_once_with(mock_db, 1, novel_id)

    @pytest.mark.asyncio
    async def test_get_novel_not_found(self, mock_user):
        """Test novel retrieval when not found."""
        # Arrange
        mock_db = AsyncMock()
        novel_id = uuid4()

        with patch("src.api.routes.v1.novels.novel_service") as mock_service:
            mock_service.get_novel.return_value = {"success": False, "error": "Novel not found"}

            # Act & Assert
            with pytest.raises(HTTPException) as exc_info:
                await get_novel(novel_id, mock_db, mock_user)

            assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
            assert exc_info.value.detail == "Novel not found"

    @pytest.mark.asyncio
    async def test_update_novel_success(self, mock_user, sample_novel_response):
        """Test successful novel update using service."""
        # Arrange
        mock_db = AsyncMock()
        novel_id = uuid4()
        request = NovelUpdateRequest(title="Updated Novel", version=1)

        with patch("src.api.routes.v1.novels.novel_service") as mock_service:
            mock_service.update_novel.return_value = {"success": True, "novel": sample_novel_response}

            # Act
            result = await update_novel(novel_id, request, mock_db, mock_user)

            # Assert
            assert result.title == "Test Novel"
            mock_service.update_novel.assert_called_once_with(mock_db, 1, novel_id, request)

    @pytest.mark.asyncio
    async def test_update_novel_version_conflict(self, mock_user):
        """Test novel update with version conflict."""
        # Arrange
        mock_db = AsyncMock()
        novel_id = uuid4()
        request = NovelUpdateRequest(title="Updated Novel", version=1)

        with patch("src.api.routes.v1.novels.novel_service") as mock_service:
            mock_service.update_novel.return_value = {
                "success": False,
                "error": "Novel has been modified by another process. Please refresh and try again.",
                "error_code": "CONFLICT",
            }

            # Act & Assert
            with pytest.raises(HTTPException) as exc_info:
                await update_novel(novel_id, request, mock_db, mock_user)

            assert exc_info.value.status_code == status.HTTP_409_CONFLICT
            assert "modified by another process" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_delete_novel_success(self, mock_user):
        """Test successful novel deletion using service."""
        # Arrange
        mock_db = AsyncMock()
        novel_id = uuid4()

        with patch("src.api.routes.v1.novels.novel_service") as mock_service:
            mock_service.delete_novel.return_value = {"success": True, "message": "Novel deleted successfully"}

            # Act
            result = await delete_novel(novel_id, mock_db, mock_user)

            # Assert - DELETE now returns None (204 No Content)
            assert result is None
            mock_service.delete_novel.assert_called_once_with(mock_db, 1, novel_id)

    @pytest.mark.asyncio
    async def test_delete_novel_not_found(self, mock_user):
        """Test novel deletion when not found."""
        # Arrange
        mock_db = AsyncMock()
        novel_id = uuid4()

        with patch("src.api.routes.v1.novels.novel_service") as mock_service:
            mock_service.delete_novel.return_value = {"success": False, "error": "Novel not found"}

            # Act & Assert
            with pytest.raises(HTTPException) as exc_info:
                await delete_novel(novel_id, mock_db, mock_user)

            assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
            assert exc_info.value.detail == "Novel not found"
