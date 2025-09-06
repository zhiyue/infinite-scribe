"""Unit tests for novel routes using service layer."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
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
            mock_service.list_user_novels = AsyncMock(
                return_value={"success": True, "novels": [sample_novel_summary], "total": 1}
            )

            # Act
            result = await list_user_novels(
                page=1,
                page_size=50,
                status_filter=None,
                search=None,
                sort_by="updated_at",
                sort_order="desc",
                db=mock_db,
                current_user=mock_user,
            )

            # Assert
            from src.schemas.base import PaginatedApiResponse

            assert isinstance(result, PaginatedApiResponse)
            assert result.code == 0
            assert len(result.data.items) == 1
            assert result.data.items[0].title == "Test Novel"
            mock_service.list_user_novels.assert_called_once_with(
                db=mock_db,
                user_id=1,
                skip=0,
                limit=50,
                status_filter=None,
                search=None,
                sort_by="updated_at",
                sort_order="desc",
            )

    @pytest.mark.asyncio
    async def test_list_user_novels_service_error(self, mock_user):
        """Test listing novels when service returns error."""
        # Arrange
        mock_db = AsyncMock()

        with patch("src.api.routes.v1.novels.novel_service") as mock_service:
            mock_service.list_user_novels = AsyncMock(return_value={"success": False, "error": "Database connection failed"})

            # Act
            result = await list_user_novels(
                page=1,
                page_size=50,
                status_filter=None,
                search=None,
                sort_by="updated_at",
                sort_order="desc",
                db=mock_db,
                current_user=mock_user,
            )

            # Assert
            from src.schemas.base import PaginatedApiResponse

            assert isinstance(result, PaginatedApiResponse)
            assert result.code == 500
            assert result.msg == "Database connection failed"
            assert result.data is None

    @pytest.mark.asyncio
    async def test_create_novel_success(self, mock_user, sample_novel_response):
        """Test successful novel creation using service."""
        # Arrange
        mock_db = AsyncMock()
        request = NovelCreateRequest(title="New Novel", theme="Science Fiction", target_chapters=20)

        with patch("src.api.routes.v1.novels.novel_service") as mock_service:
            mock_service.create_novel = AsyncMock(return_value={"success": True, "novel": sample_novel_response})

            # Act
            result = await create_novel(request, mock_db, mock_user)

            # Assert
            from src.schemas.base import ApiResponse

            assert isinstance(result, ApiResponse)
            assert result.code == 0
            assert result.data.title == "Test Novel"
            assert result.data.status == NovelStatus.GENESIS
            mock_service.create_novel.assert_called_once_with(mock_db, 1, request)

    @pytest.mark.asyncio
    async def test_create_novel_constraint_error(self, mock_user):
        """Test novel creation with constraint error."""
        # Arrange
        mock_db = AsyncMock()
        request = NovelCreateRequest(title="New Novel", target_chapters=20)

        with patch("src.api.routes.v1.novels.novel_service") as mock_service:
            mock_service.create_novel = AsyncMock(return_value={
                "success": False,
                "error": "Novel creation failed due to data constraints",
            })

            # Act
            result = await create_novel(request, mock_db, mock_user)

            # Assert
            from src.schemas.base import ApiResponse

            assert isinstance(result, ApiResponse)
            assert result.code == 400
            assert "constraint" in result.msg.lower()
            assert result.data is None

    @pytest.mark.asyncio
    async def test_get_novel_success(self, mock_user, sample_novel_response):
        """Test successful novel retrieval using service."""
        # Arrange
        mock_db = AsyncMock()
        novel_id = uuid4()

        with patch("src.api.routes.v1.novels.novel_service") as mock_service:
            mock_service.get_novel = AsyncMock(return_value={"success": True, "novel": sample_novel_response})

            # Act
            result = await get_novel(novel_id, mock_db, mock_user)

            # Assert
            from src.schemas.base import ApiResponse

            assert isinstance(result, ApiResponse)
            assert result.code == 0
            assert result.data.title == "Test Novel"
            assert result.data.status == NovelStatus.GENESIS
            mock_service.get_novel.assert_called_once_with(mock_db, 1, novel_id)

    @pytest.mark.asyncio
    async def test_get_novel_not_found(self, mock_user):
        """Test novel retrieval when not found."""
        # Arrange
        mock_db = AsyncMock()
        novel_id = uuid4()

        with patch("src.api.routes.v1.novels.novel_service") as mock_service:
            mock_service.get_novel = AsyncMock(return_value={"success": False, "error": "Novel not found"})

            # Act
            result = await get_novel(novel_id, mock_db, mock_user)

            # Assert
            from src.schemas.base import ApiResponse

            assert isinstance(result, ApiResponse)
            assert result.code == 404
            assert result.msg == "Novel not found"
            assert result.data is None

    @pytest.mark.asyncio
    async def test_update_novel_success(self, mock_user, sample_novel_response):
        """Test successful novel update using service."""
        # Arrange
        mock_db = AsyncMock()
        novel_id = uuid4()
        request = NovelUpdateRequest(title="Updated Novel", version=1)

        with patch("src.api.routes.v1.novels.novel_service") as mock_service:
            mock_service.update_novel = AsyncMock(return_value={"success": True, "novel": sample_novel_response})

            # Act
            result = await update_novel(novel_id, request, mock_db, mock_user)

            # Assert
            from src.schemas.base import ApiResponse

            assert isinstance(result, ApiResponse)
            assert result.code == 0
            assert result.data.title == "Test Novel"
            mock_service.update_novel.assert_called_once_with(mock_db, 1, novel_id, request)

    @pytest.mark.asyncio
    async def test_update_novel_version_conflict(self, mock_user):
        """Test novel update with version conflict."""
        # Arrange
        mock_db = AsyncMock()
        novel_id = uuid4()
        request = NovelUpdateRequest(title="Updated Novel", version=1)

        with patch("src.api.routes.v1.novels.novel_service") as mock_service:
            mock_service.update_novel = AsyncMock(return_value={
                "success": False,
                "error": "Novel has been modified by another process. Please refresh and try again.",
                "error_code": "CONFLICT",
            })

            # Act
            result = await update_novel(novel_id, request, mock_db, mock_user)

            # Assert
            from src.schemas.base import ApiResponse

            assert isinstance(result, ApiResponse)
            assert result.code == 409
            assert "modified by another process" in result.msg
            assert result.data is None

    @pytest.mark.asyncio
    async def test_delete_novel_success(self, mock_user):
        """Test successful novel deletion using service."""
        # Arrange
        mock_db = AsyncMock()
        novel_id = uuid4()

        with patch("src.api.routes.v1.novels.novel_service") as mock_service:
            mock_service.delete_novel = AsyncMock(return_value={"success": True})

            # Act
            result = await delete_novel(novel_id, mock_db, mock_user)

            # Assert
            from src.schemas.base import ApiResponse

            assert isinstance(result, ApiResponse)
            assert result.code == 0
            assert result.msg == "删除小说成功"
            assert result.data is None
            mock_service.delete_novel.assert_called_once_with(mock_db, 1, novel_id)

    @pytest.mark.asyncio
    async def test_delete_novel_not_found(self, mock_user):
        """Test novel deletion when not found."""
        # Arrange
        mock_db = AsyncMock()
        novel_id = uuid4()

        with patch("src.api.routes.v1.novels.novel_service") as mock_service:
            mock_service.delete_novel = AsyncMock(return_value={"success": False, "error": "Novel not found"})

            # Act
            result = await delete_novel(novel_id, mock_db, mock_user)

            # Assert
            from src.schemas.base import ApiResponse

            assert isinstance(result, ApiResponse)
            assert result.code == 404
            assert result.msg == "Novel not found"
            assert result.data is None
