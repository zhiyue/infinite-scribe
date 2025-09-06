"""Unit tests for novel management endpoints."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
from src.api.routes.v1.novels import (
    create_novel,
    delete_novel,
    get_novel,
    get_novel_chapters,
    get_novel_characters,
    get_novel_stats,
    list_user_novels,
    update_novel,
)
from src.models.user import User
from src.schemas.enums import NovelStatus
from src.schemas.novel.create import NovelCreateRequest
from src.schemas.novel.read import NovelProgress, NovelResponse, NovelSummary
from src.schemas.novel.update import NovelUpdateRequest


class TestNovelRoutes:
    """Test cases for novel management routes."""

    @pytest.fixture
    def mock_user(self):
        """Create mock user."""
        user = Mock(spec=User)
        user.id = 1
        user.username = "testuser"
        user.email = "test@example.com"
        return user

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
    def sample_create_request(self):
        """Create sample novel creation request."""
        return NovelCreateRequest(
            title="New Novel",
            theme="Science Fiction",
            writing_style="Technical",
            target_chapters=20,
        )

    @pytest.fixture
    def sample_update_request(self):
        """Create sample novel update request."""
        return NovelUpdateRequest(
            title="Updated Novel",
            theme="Updated Theme",
            version=1,
        )

    @pytest.mark.asyncio
    async def test_list_user_novels_success(self, mock_user, sample_novel_summary):
        """Test successful listing of user novels."""
        # Arrange
        mock_db = AsyncMock()
        expected_result = {"success": True, "novels": [sample_novel_summary], "total": 1}

        # Mock novel_service.list_user_novels
        with patch("src.api.routes.v1.novels.novel_service") as mock_service:
            mock_service.list_user_novels = AsyncMock(return_value=expected_result)

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
            assert result.data is not None
            assert len(result.data.items) == 1
            assert result.data.items[0].title == "Test Novel"
            mock_service.list_user_novels.assert_called_once_with(
                db=mock_db,
                user_id=mock_user.id,
                skip=0,
                limit=50,
                status_filter=None,
                search=None,
                sort_by="updated_at",
                sort_order="desc",
            )

    @pytest.mark.asyncio
    async def test_list_user_novels_with_filters(self, mock_user, sample_novel_summary):
        """Test listing novels with filters."""
        # Arrange
        mock_db = AsyncMock()
        expected_result = {"success": True, "novels": [sample_novel_summary], "total": 1}

        # Mock novel_service.list_user_novels
        with patch("src.api.routes.v1.novels.novel_service") as mock_service:
            mock_service.list_user_novels = AsyncMock(return_value=expected_result)

            # Act
            result = await list_user_novels(
                page=2,
                page_size=25,
                status_filter=NovelStatus.GENESIS,
                search="test",
                sort_by="title",
                sort_order="asc",
                db=mock_db,
                current_user=mock_user,
            )

            # Assert
            from src.schemas.base import PaginatedApiResponse

            assert isinstance(result, PaginatedApiResponse)
            assert result.code == 0
            assert result.data is not None
            assert len(result.data.items) == 1
            mock_service.list_user_novels.assert_called_once_with(
                db=mock_db,
                user_id=mock_user.id,
                skip=25,
                limit=25,
                status_filter=NovelStatus.GENESIS,
                search="test",
                sort_by="title",
                sort_order="asc",
            )

    @pytest.mark.asyncio
    async def test_list_user_novels_service_error(self, mock_user):
        """Test listing novels with service error."""
        # Arrange
        mock_db = AsyncMock()
        error_result = {"success": False, "error": "Database connection failed"}

        # Mock novel_service.list_user_novels to return error
        with patch("src.api.routes.v1.novels.novel_service") as mock_service:
            mock_service.list_user_novels = AsyncMock(return_value=error_result)

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
    async def test_list_user_novels_exception(self, mock_user):
        """Test listing novels with unexpected exception."""
        # Arrange
        mock_db = AsyncMock()

        # Mock novel_service.list_user_novels to raise exception
        with patch("src.api.routes.v1.novels.novel_service") as mock_service:
            mock_service.list_user_novels = AsyncMock(side_effect=Exception("Unexpected error"))

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
            assert "获取小说列表时发生错误" in result.msg
            assert result.data is None

    @pytest.mark.asyncio
    async def test_create_novel_success(self, mock_user, sample_create_request, sample_novel_response):
        """Test successful novel creation."""
        # Arrange
        mock_db = AsyncMock()
        expected_result = {"success": True, "novel": sample_novel_response}

        # Mock novel_service.create_novel
        with patch("src.api.routes.v1.novels.novel_service") as mock_service:
            mock_service.create_novel = AsyncMock(return_value=expected_result)

            # Act
            result = await create_novel(sample_create_request, mock_db, mock_user)

            # Assert
            from src.schemas.base import ApiResponse

            assert isinstance(result, ApiResponse)
            assert result.code == 0
            assert result.data.title == "Test Novel"
            assert result.data.status == NovelStatus.GENESIS
            mock_service.create_novel.assert_called_once_with(mock_db, mock_user.id, sample_create_request)

    @pytest.mark.asyncio
    async def test_create_novel_service_error(self, mock_user, sample_create_request):
        """Test novel creation with service error."""
        # Arrange
        mock_db = AsyncMock()
        error_result = {"success": False, "error": "Database connection failed"}

        # Mock novel_service.create_novel to return error
        with patch("src.api.routes.v1.novels.novel_service") as mock_service:
            mock_service.create_novel = AsyncMock(return_value=error_result)

            # Act
            result = await create_novel(sample_create_request, mock_db, mock_user)

            # Assert
            from src.schemas.base import ApiResponse

            assert isinstance(result, ApiResponse)
            assert result.code == 500
            assert result.msg == "Database connection failed"
            assert result.data is None

    @pytest.mark.asyncio
    async def test_create_novel_constraint_error(self, mock_user, sample_create_request):
        """Test novel creation with constraint error."""
        # Arrange
        mock_db = AsyncMock()
        error_result = {"success": False, "error": "Novel creation failed due to constraint violation"}

        # Mock novel_service.create_novel to return constraint error
        with patch("src.api.routes.v1.novels.novel_service") as mock_service:
            mock_service.create_novel = AsyncMock(return_value=error_result)

            # Act
            result = await create_novel(sample_create_request, mock_db, mock_user)

            # Assert
            from src.schemas.base import ApiResponse

            assert isinstance(result, ApiResponse)
            assert result.code == 400
            assert "constraint" in result.msg.lower()
            assert result.data is None

    @pytest.mark.asyncio
    async def test_create_novel_exception(self, mock_user, sample_create_request):
        """Test novel creation with unexpected exception."""
        # Arrange
        mock_db = AsyncMock()

        # Mock novel_service.create_novel to raise exception
        with patch("src.api.routes.v1.novels.novel_service") as mock_service:
            mock_service.create_novel = AsyncMock(side_effect=Exception("Unexpected error"))

            # Act
            result = await create_novel(sample_create_request, mock_db, mock_user)

            # Assert
            from src.schemas.base import ApiResponse

            assert isinstance(result, ApiResponse)
            assert result.code == 500
            assert "创建小说时发生错误" in result.msg
            assert result.data is None

    @pytest.mark.asyncio
    async def test_get_novel_success(self, mock_user, sample_novel_response):
        """Test successful novel retrieval."""
        # Arrange
        mock_db = AsyncMock()
        novel_id = uuid4()
        expected_result = {"success": True, "novel": sample_novel_response}

        # Mock novel_service.get_novel
        with patch("src.api.routes.v1.novels.novel_service") as mock_service:
            mock_service.get_novel = AsyncMock(return_value=expected_result)

            # Act
            result = await get_novel(novel_id, mock_db, mock_user)

            # Assert
            from src.schemas.base import ApiResponse

            assert isinstance(result, ApiResponse)
            assert result.code == 0
            assert result.data.title == "Test Novel"
            assert result.data.status == NovelStatus.GENESIS
            mock_service.get_novel.assert_called_once_with(mock_db, mock_user.id, novel_id)

    @pytest.mark.asyncio
    async def test_get_novel_not_found(self, mock_user):
        """Test novel retrieval when novel not found."""
        # Arrange
        mock_db = AsyncMock()
        novel_id = uuid4()
        error_result = {"success": False, "error": "Novel not found"}

        # Mock novel_service.get_novel to return not found
        with patch("src.api.routes.v1.novels.novel_service") as mock_service:
            mock_service.get_novel = AsyncMock(return_value=error_result)

            # Act
            result = await get_novel(novel_id, mock_db, mock_user)

            # Assert
            from src.schemas.base import ApiResponse

            assert isinstance(result, ApiResponse)
            assert result.code == 404
            assert result.msg == "Novel not found"
            assert result.data is None

    @pytest.mark.asyncio
    async def test_get_novel_service_error(self, mock_user):
        """Test novel retrieval with service error."""
        # Arrange
        mock_db = AsyncMock()
        novel_id = uuid4()
        error_result = {"success": False, "error": "Database connection failed"}

        # Mock novel_service.get_novel to return error
        with patch("src.api.routes.v1.novels.novel_service") as mock_service:
            mock_service.get_novel = AsyncMock(return_value=error_result)

            # Act
            result = await get_novel(novel_id, mock_db, mock_user)

            # Assert
            from src.schemas.base import ApiResponse

            assert isinstance(result, ApiResponse)
            assert result.code == 500
            assert result.msg == "Database connection failed"
            assert result.data is None

    @pytest.mark.asyncio
    async def test_get_novel_exception(self, mock_user):
        """Test novel retrieval with unexpected exception."""
        # Arrange
        mock_db = AsyncMock()
        novel_id = uuid4()

        # Mock novel_service.get_novel to raise exception
        with patch("src.api.routes.v1.novels.novel_service") as mock_service:
            mock_service.get_novel = AsyncMock(side_effect=Exception("Unexpected error"))

            # Act
            result = await get_novel(novel_id, mock_db, mock_user)

            # Assert
            from src.schemas.base import ApiResponse

            assert isinstance(result, ApiResponse)
            assert result.code == 500
            assert "获取小说详情时发生错误" in result.msg
            assert result.data is None

    @pytest.mark.asyncio
    async def test_update_novel_success(self, mock_user, sample_update_request, sample_novel_response):
        """Test successful novel update."""
        # Arrange
        mock_db = AsyncMock()
        novel_id = uuid4()
        # Update sample response to reflect the version increment
        updated_response = sample_novel_response.model_copy(update={"version": 2})
        expected_result = {"success": True, "novel": updated_response}

        # Mock novel_service.update_novel
        with patch("src.api.routes.v1.novels.novel_service") as mock_service:
            mock_service.update_novel = AsyncMock(return_value=expected_result)

            # Act
            result = await update_novel(novel_id, sample_update_request, mock_db, mock_user)

            # Assert
            from src.schemas.base import ApiResponse

            assert isinstance(result, ApiResponse)
            assert result.code == 0
            assert result.data.title == "Test Novel"
            assert result.data.version == 2  # Version should be incremented
            mock_service.update_novel.assert_called_once_with(mock_db, mock_user.id, novel_id, sample_update_request)

    @pytest.mark.asyncio
    async def test_update_novel_not_found(self, mock_user, sample_update_request):
        """Test novel update when novel not found."""
        # Arrange
        mock_db = AsyncMock()
        novel_id = uuid4()
        error_result = {"success": False, "error": "Novel not found"}

        # Mock novel_service.update_novel to return not found
        with patch("src.api.routes.v1.novels.novel_service") as mock_service:
            mock_service.update_novel = AsyncMock(return_value=error_result)

            # Act
            result = await update_novel(novel_id, sample_update_request, mock_db, mock_user)

            # Assert
            from src.schemas.base import ApiResponse

            assert isinstance(result, ApiResponse)
            assert result.code == 404
            assert result.msg == "Novel not found"
            assert result.data is None

    @pytest.mark.asyncio
    async def test_update_novel_version_conflict(self, mock_user):
        """Test novel update with version conflict."""
        # Arrange
        mock_db = AsyncMock()
        novel_id = uuid4()
        error_result = {
            "success": False,
            "error": "Novel has been modified by another process. Please refresh and try again.",
            "error_code": "CONFLICT",
        }

        # Create update request with wrong version
        update_request = NovelUpdateRequest(title="Updated Title", version=1)

        # Mock novel_service.update_novel to return conflict
        with patch("src.api.routes.v1.novels.novel_service") as mock_service:
            mock_service.update_novel = AsyncMock(return_value=error_result)

            # Act
            result = await update_novel(novel_id, update_request, mock_db, mock_user)

            # Assert
            from src.schemas.base import ApiResponse

            assert isinstance(result, ApiResponse)
            assert result.code == 409
            assert "modified by another process" in result.msg
            assert result.data is None

    @pytest.mark.asyncio
    async def test_update_novel_service_error(self, mock_user, sample_update_request):
        """Test novel update with service error."""
        # Arrange
        mock_db = AsyncMock()
        novel_id = uuid4()
        error_result = {"success": False, "error": "Database connection failed"}

        # Mock novel_service.update_novel to return error
        with patch("src.api.routes.v1.novels.novel_service") as mock_service:
            mock_service.update_novel = AsyncMock(return_value=error_result)

            # Act
            result = await update_novel(novel_id, sample_update_request, mock_db, mock_user)

            # Assert
            from src.schemas.base import ApiResponse

            assert isinstance(result, ApiResponse)
            assert result.code == 500
            assert result.msg == "Database connection failed"
            assert result.data is None

    @pytest.mark.asyncio
    async def test_update_novel_exception(self, mock_user, sample_update_request):
        """Test novel update with unexpected exception."""
        # Arrange
        mock_db = AsyncMock()
        novel_id = uuid4()

        # Mock novel_service.update_novel to raise exception
        with patch("src.api.routes.v1.novels.novel_service") as mock_service:
            mock_service.update_novel = AsyncMock(side_effect=Exception("Unexpected error"))

            # Act
            result = await update_novel(novel_id, sample_update_request, mock_db, mock_user)

            # Assert
            from src.schemas.base import ApiResponse

            assert isinstance(result, ApiResponse)
            assert result.code == 500
            assert "更新小说时发生错误" in result.msg
            assert result.data is None

    @pytest.mark.asyncio
    async def test_delete_novel_success(self, mock_user):
        """Test successful novel deletion."""
        # Arrange
        mock_db = AsyncMock()
        novel_id = uuid4()
        expected_result = {"success": True}

        # Mock novel_service.delete_novel
        with patch("src.api.routes.v1.novels.novel_service") as mock_service:
            mock_service.delete_novel = AsyncMock(return_value=expected_result)

            # Act
            result = await delete_novel(novel_id, mock_db, mock_user)

            # Assert
            from src.schemas.base import ApiResponse

            assert isinstance(result, ApiResponse)
            assert result.code == 0
            assert result.msg == "删除小说成功"
            assert result.data is None
            mock_service.delete_novel.assert_called_once_with(mock_db, mock_user.id, novel_id)

    @pytest.mark.asyncio
    async def test_delete_novel_not_found(self, mock_user):
        """Test novel deletion when novel not found."""
        # Arrange
        mock_db = AsyncMock()
        novel_id = uuid4()
        error_result = {"success": False, "error": "Novel not found"}

        # Mock novel_service.delete_novel to return not found
        with patch("src.api.routes.v1.novels.novel_service") as mock_service:
            mock_service.delete_novel = AsyncMock(return_value=error_result)

            # Act
            result = await delete_novel(novel_id, mock_db, mock_user)

            # Assert
            from src.schemas.base import ApiResponse

            assert isinstance(result, ApiResponse)
            assert result.code == 404
            assert result.msg == "Novel not found"
            assert result.data is None

    @pytest.mark.asyncio
    async def test_delete_novel_database_error(self, mock_user):
        """Test novel deletion with database error."""
        # Arrange
        mock_db = AsyncMock()
        novel_id = uuid4()

        # Mock novel_service.delete_novel to raise exception
        with patch("src.api.routes.v1.novels.novel_service") as mock_service:
            mock_service.delete_novel = AsyncMock(side_effect=Exception("Database error"))

            # Act
            result = await delete_novel(novel_id, mock_db, mock_user)

            # Assert
            from src.schemas.base import ApiResponse

            assert isinstance(result, ApiResponse)
            assert result.code == 500
            assert "删除小说时发生错误" in result.msg
            assert result.data is None

    @pytest.mark.asyncio
    async def test_get_novel_chapters_success(self, mock_user):
        """Test successful retrieval of novel chapters."""
        # Arrange
        mock_db = AsyncMock()
        novel_id = uuid4()

        mock_chapter_data = {
            "id": uuid4(),
            "chapter_number": 1,
            "title": "Chapter 1",
            "status": "PUBLISHED",
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }
        expected_result = {"success": True, "chapters": [mock_chapter_data]}

        # Mock novel_service.get_novel_chapters
        with patch("src.api.routes.v1.novels.novel_service") as mock_service:
            mock_service.get_novel_chapters = AsyncMock(return_value=expected_result)

            # Act
            result = await get_novel_chapters(novel_id, mock_db, mock_user)

            # Assert
            from src.schemas.base import ApiResponse

            assert isinstance(result, ApiResponse)
            assert result.code == 0
            assert result.msg == "获取章节列表成功"
            assert len(result.data) == 1
            assert result.data[0]["title"] == "Chapter 1"
            assert result.data[0]["chapter_number"] == 1
            mock_service.get_novel_chapters.assert_called_once_with(mock_db, mock_user.id, novel_id)

    @pytest.mark.asyncio
    async def test_get_novel_chapters_novel_not_found(self, mock_user):
        """Test getting chapters when novel not found."""
        # Arrange
        mock_db = AsyncMock()
        novel_id = uuid4()
        error_result = {"success": False, "error": "Novel not found"}

        # Mock novel_service.get_novel_chapters to return not found
        with patch("src.api.routes.v1.novels.novel_service") as mock_service:
            mock_service.get_novel_chapters = AsyncMock(return_value=error_result)

            # Act
            result = await get_novel_chapters(novel_id, mock_db, mock_user)

            # Assert
            from src.schemas.base import ApiResponse

            assert isinstance(result, ApiResponse)
            assert result.code == 404
            assert result.msg == "Novel not found"
            assert result.data is None

    @pytest.mark.asyncio
    async def test_get_novel_characters_success(self, mock_user):
        """Test successful retrieval of novel characters."""
        # Arrange
        mock_db = AsyncMock()
        novel_id = uuid4()

        mock_character_data = {
            "id": uuid4(),
            "name": "Test Character",
            "role": "PROTAGONIST",
            "description": "A test character",
            "personality_traits": ["brave", "kind"],
            "goals": ["save the world"],
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }
        expected_result = {"success": True, "characters": [mock_character_data]}

        # Mock novel_service.get_novel_characters
        with patch("src.api.routes.v1.novels.novel_service") as mock_service:
            mock_service.get_novel_characters = AsyncMock(return_value=expected_result)

            # Act
            result = await get_novel_characters(novel_id, mock_db, mock_user)

            # Assert
            from src.schemas.base import ApiResponse

            assert isinstance(result, ApiResponse)
            assert result.code == 0
            assert result.msg == "获取角色列表成功"
            assert len(result.data) == 1
            assert result.data[0]["name"] == "Test Character"
            assert result.data[0]["role"] == "PROTAGONIST"
            mock_service.get_novel_characters.assert_called_once_with(mock_db, mock_user.id, novel_id)

    @pytest.mark.asyncio
    async def test_get_novel_characters_novel_not_found(self, mock_user):
        """Test getting characters when novel not found."""
        # Arrange
        mock_db = AsyncMock()
        novel_id = uuid4()
        error_result = {"success": False, "error": "Novel not found"}

        # Mock novel_service.get_novel_characters to return not found
        with patch("src.api.routes.v1.novels.novel_service") as mock_service:
            mock_service.get_novel_characters = AsyncMock(return_value=error_result)

            # Act
            result = await get_novel_characters(novel_id, mock_db, mock_user)

            # Assert
            from src.schemas.base import ApiResponse

            assert isinstance(result, ApiResponse)
            assert result.code == 404
            assert result.msg == "Novel not found"
            assert result.data is None

    @pytest.mark.asyncio
    async def test_get_novel_stats_success(self, mock_user):
        """Test successful retrieval of novel statistics."""
        # Arrange
        mock_db = AsyncMock()
        novel_id = uuid4()

        mock_stats = NovelProgress(
            novel_id=novel_id,
            total_chapters=5,
            published_chapters=3,
            target_chapters=10,
            progress_percentage=30.0,
            last_updated=datetime.now(UTC),
        )
        expected_result = {"success": True, "stats": mock_stats}

        # Mock novel_service.get_novel_stats
        with patch("src.api.routes.v1.novels.novel_service") as mock_service:
            mock_service.get_novel_stats = AsyncMock(return_value=expected_result)

            # Act
            result = await get_novel_stats(novel_id, mock_db, mock_user)

            # Assert
            from src.schemas.base import ApiResponse

            assert isinstance(result, ApiResponse)
            assert result.code == 0
            assert result.msg == "获取统计信息成功"
            assert isinstance(result.data, NovelProgress)
            assert result.data.novel_id == novel_id
            assert result.data.total_chapters == 5
            assert result.data.published_chapters == 3
            assert result.data.target_chapters == 10
            assert result.data.progress_percentage == 30.0
            mock_service.get_novel_stats.assert_called_once_with(mock_db, mock_user.id, novel_id)

    @pytest.mark.asyncio
    async def test_get_novel_stats_novel_not_found(self, mock_user):
        """Test getting stats when novel not found."""
        # Arrange
        mock_db = AsyncMock()
        novel_id = uuid4()
        error_result = {"success": False, "error": "Novel not found"}

        # Mock novel_service.get_novel_stats to return not found
        with patch("src.api.routes.v1.novels.novel_service") as mock_service:
            mock_service.get_novel_stats = AsyncMock(return_value=error_result)

            # Act
            result = await get_novel_stats(novel_id, mock_db, mock_user)

            # Assert
            from src.schemas.base import ApiResponse

            assert isinstance(result, ApiResponse)
            assert result.code == 404
            assert result.msg == "Novel not found"
            assert result.data is None

    @pytest.mark.asyncio
    async def test_get_novel_stats_database_error(self, mock_user):
        """Test getting stats with database error."""
        # Arrange
        mock_db = AsyncMock()
        novel_id = uuid4()

        # Mock novel_service.get_novel_stats to raise exception
        with patch("src.api.routes.v1.novels.novel_service") as mock_service:
            mock_service.get_novel_stats = AsyncMock(side_effect=Exception("Database error"))

            # Act
            result = await get_novel_stats(novel_id, mock_db, mock_user)

            # Assert
            from src.schemas.base import ApiResponse

            assert isinstance(result, ApiResponse)
            assert result.code == 500
            assert "获取统计信息时发生错误" in result.msg
            assert result.data is None
