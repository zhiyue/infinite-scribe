"""Unit tests for novel management endpoints."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException, status
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
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [Mock()]
        mock_db.execute.return_value = mock_result

        # Mock NovelSummary.model_validate
        with patch("src.api.routes.v1.novels.NovelSummary") as MockNovelSummary:
            MockNovelSummary.model_validate.return_value = sample_novel_summary

            # Act
            result = await list_user_novels(skip=0, limit=50, status_filter=None, db=mock_db, current_user=mock_user)

            # Assert
            assert isinstance(result, list)
            assert len(result) == 1
            assert result[0].title == "Test Novel"
            mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_user_novels_with_filters(self, mock_user, sample_novel_summary):
        """Test listing novels with filters."""
        # Arrange
        mock_db = AsyncMock()
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [Mock()]
        mock_db.execute.return_value = mock_result

        with patch("src.api.routes.v1.novels.NovelSummary") as MockNovelSummary:
            MockNovelSummary.model_validate.return_value = sample_novel_summary

            # Act
            result = await list_user_novels(
                skip=5, limit=25, status_filter="GENESIS", db=mock_db, current_user=mock_user
            )

            # Assert
            assert isinstance(result, list)
            assert len(result) == 1
            mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_user_novels_database_error(self, mock_user):
        """Test listing novels with database error."""
        # Arrange
        mock_db = AsyncMock()
        mock_db.execute.side_effect = Exception("Database error")

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await list_user_novels(skip=0, limit=50, status_filter=None, db=mock_db, current_user=mock_user)

        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "An error occurred while retrieving novels" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_create_novel_success(self, mock_user, sample_create_request, sample_novel_response):
        """Test successful novel creation."""
        # Arrange
        mock_db = AsyncMock()

        # Mock Novel creation
        with patch("src.api.routes.v1.novels.Novel") as MockNovel:
            mock_novel_instance = Mock()
            MockNovel.return_value = mock_novel_instance

            with patch("src.api.routes.v1.novels.NovelResponse") as MockNovelResponse:
                MockNovelResponse.model_validate.return_value = sample_novel_response

                # Act
                result = await create_novel(sample_create_request, mock_db, mock_user)

                # Assert
                assert result.title == "Test Novel"
                assert result.status == NovelStatus.GENESIS
                mock_db.add.assert_called_once_with(mock_novel_instance)
                mock_db.commit.assert_called_once()
                mock_db.refresh.assert_called_once_with(mock_novel_instance)

    @pytest.mark.asyncio
    async def test_create_novel_database_error(self, mock_user, sample_create_request):
        """Test novel creation with database error."""
        # Arrange
        mock_db = AsyncMock()
        mock_db.commit.side_effect = Exception("Database error")
        mock_db.rollback = AsyncMock()

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await create_novel(sample_create_request, mock_db, mock_user)

        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "An error occurred while creating the novel" in exc_info.value.detail
        mock_db.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_novel_success(self, mock_user, sample_novel_response):
        """Test successful novel retrieval."""
        # Arrange
        mock_db = AsyncMock()
        novel_id = uuid4()
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = Mock()
        mock_db.execute.return_value = mock_result

        with patch("src.api.routes.v1.novels.NovelResponse") as MockNovelResponse:
            MockNovelResponse.model_validate.return_value = sample_novel_response

            # Act
            result = await get_novel(novel_id, mock_db, mock_user)

            # Assert
            assert result.title == "Test Novel"
            assert result.status == NovelStatus.GENESIS
            mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_novel_not_found(self, mock_user):
        """Test novel retrieval when novel not found."""
        # Arrange
        mock_db = AsyncMock()
        novel_id = uuid4()
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await get_novel(novel_id, mock_db, mock_user)

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert exc_info.value.detail == "Novel not found"

    @pytest.mark.asyncio
    async def test_get_novel_database_error(self, mock_user):
        """Test novel retrieval with database error."""
        # Arrange
        mock_db = AsyncMock()
        novel_id = uuid4()
        mock_db.execute.side_effect = Exception("Database error")

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await get_novel(novel_id, mock_db, mock_user)

        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "An error occurred while retrieving the novel" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_update_novel_success(self, mock_user, sample_update_request, sample_novel_response):
        """Test successful novel update."""
        # Arrange
        mock_db = AsyncMock()
        novel_id = uuid4()
        mock_novel = Mock()
        mock_novel.version = 1
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_novel
        mock_db.execute.return_value = mock_result

        with patch("src.api.routes.v1.novels.NovelResponse") as MockNovelResponse:
            MockNovelResponse.model_validate.return_value = sample_novel_response

            # Act
            result = await update_novel(novel_id, sample_update_request, mock_db, mock_user)

            # Assert
            assert result.title == "Test Novel"
            assert mock_novel.version == 2  # Version should be incremented
            mock_db.commit.assert_called_once()
            mock_db.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_novel_not_found(self, mock_user, sample_update_request):
        """Test novel update when novel not found."""
        # Arrange
        mock_db = AsyncMock()
        novel_id = uuid4()
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await update_novel(novel_id, sample_update_request, mock_db, mock_user)

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert exc_info.value.detail == "Novel not found"

    @pytest.mark.asyncio
    async def test_update_novel_version_conflict(self, mock_user):
        """Test novel update with version conflict."""
        # Arrange
        mock_db = AsyncMock()
        novel_id = uuid4()
        mock_novel = Mock()
        mock_novel.version = 5
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_novel
        mock_db.execute.return_value = mock_result

        # Create update request with wrong version
        update_request = NovelUpdateRequest(title="Updated Title", version=1)

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await update_novel(novel_id, update_request, mock_db, mock_user)

        assert exc_info.value.status_code == status.HTTP_409_CONFLICT
        assert "modified by another process" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_update_novel_database_error(self, mock_user, sample_update_request):
        """Test novel update with database error."""
        # Arrange
        mock_db = AsyncMock()
        novel_id = uuid4()
        mock_novel = Mock()
        mock_novel.version = 1
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_novel
        mock_db.execute.return_value = mock_result
        mock_db.commit.side_effect = Exception("Database error")
        mock_db.rollback = AsyncMock()

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await update_novel(novel_id, sample_update_request, mock_db, mock_user)

        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "An error occurred while updating the novel" in exc_info.value.detail
        mock_db.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_novel_success(self, mock_user):
        """Test successful novel deletion."""
        # Arrange
        mock_db = AsyncMock()
        novel_id = uuid4()
        mock_novel = Mock()
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_novel
        mock_db.execute.return_value = mock_result

        # Act
        result = await delete_novel(novel_id, mock_db, mock_user)

        # Assert
        assert result.success is True
        assert result.message == "Novel deleted successfully"
        mock_db.delete.assert_called_once_with(mock_novel)
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_novel_not_found(self, mock_user):
        """Test novel deletion when novel not found."""
        # Arrange
        mock_db = AsyncMock()
        novel_id = uuid4()
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await delete_novel(novel_id, mock_db, mock_user)

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert exc_info.value.detail == "Novel not found"

    @pytest.mark.asyncio
    async def test_delete_novel_database_error(self, mock_user):
        """Test novel deletion with database error."""
        # Arrange
        mock_db = AsyncMock()
        novel_id = uuid4()
        mock_novel = Mock()
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_novel
        mock_db.execute.return_value = mock_result
        mock_db.delete.side_effect = Exception("Database error")
        mock_db.rollback = AsyncMock()

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await delete_novel(novel_id, mock_db, mock_user)

        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "An error occurred while deleting the novel" in exc_info.value.detail
        mock_db.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_novel_chapters_success(self, mock_user):
        """Test successful retrieval of novel chapters."""
        # Arrange
        mock_db = AsyncMock()
        novel_id = uuid4()

        # Mock novel ownership check
        mock_novel_result = Mock()
        mock_novel_result.scalar_one_or_none.return_value = Mock()

        # Mock chapters result
        mock_chapter = Mock()
        mock_chapter.id = uuid4()
        mock_chapter.chapter_number = 1
        mock_chapter.title = "Chapter 1"
        mock_chapter.status = "PUBLISHED"
        mock_chapter.created_at = datetime.now(UTC)
        mock_chapter.updated_at = datetime.now(UTC)

        mock_chapters_result = Mock()
        mock_chapters_result.scalars.return_value.all.return_value = [mock_chapter]

        mock_db.execute.side_effect = [mock_novel_result, mock_chapters_result]

        # Act
        result = await get_novel_chapters(novel_id, mock_db, mock_user)

        # Assert
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["title"] == "Chapter 1"
        assert result[0]["chapter_number"] == 1
        assert mock_db.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_get_novel_chapters_novel_not_found(self, mock_user):
        """Test getting chapters when novel not found."""
        # Arrange
        mock_db = AsyncMock()
        novel_id = uuid4()
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await get_novel_chapters(novel_id, mock_db, mock_user)

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert exc_info.value.detail == "Novel not found"

    @pytest.mark.asyncio
    async def test_get_novel_characters_success(self, mock_user):
        """Test successful retrieval of novel characters."""
        # Arrange
        mock_db = AsyncMock()
        novel_id = uuid4()

        # Mock novel ownership check
        mock_novel_result = Mock()
        mock_novel_result.scalar_one_or_none.return_value = Mock()

        # Mock characters result
        mock_character = Mock()
        mock_character.id = uuid4()
        mock_character.name = "Test Character"
        mock_character.role = "PROTAGONIST"
        mock_character.description = "A test character"
        mock_character.personality_traits = ["brave", "kind"]
        mock_character.goals = ["save the world"]
        mock_character.created_at = datetime.now(UTC)
        mock_character.updated_at = datetime.now(UTC)

        mock_characters_result = Mock()
        mock_characters_result.scalars.return_value.all.return_value = [mock_character]

        mock_db.execute.side_effect = [mock_novel_result, mock_characters_result]

        # Act
        result = await get_novel_characters(novel_id, mock_db, mock_user)

        # Assert
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["name"] == "Test Character"
        assert result[0]["role"] == "PROTAGONIST"
        assert mock_db.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_get_novel_characters_novel_not_found(self, mock_user):
        """Test getting characters when novel not found."""
        # Arrange
        mock_db = AsyncMock()
        novel_id = uuid4()
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await get_novel_characters(novel_id, mock_db, mock_user)

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert exc_info.value.detail == "Novel not found"

    @pytest.mark.asyncio
    async def test_get_novel_stats_success(self, mock_user):
        """Test successful retrieval of novel statistics."""
        # Arrange
        mock_db = AsyncMock()
        novel_id = uuid4()

        # Mock novel
        mock_novel = Mock()
        mock_novel.id = novel_id
        mock_novel.target_chapters = 10
        mock_novel.updated_at = datetime.now(UTC)

        # Mock novel ownership check
        mock_novel_result = Mock()
        mock_novel_result.scalar_one_or_none.return_value = mock_novel

        # Mock chapter count queries
        mock_total_count_result = Mock()
        mock_total_count_result.scalar.return_value = 5

        mock_published_count_result = Mock()
        mock_published_count_result.scalar.return_value = 3

        mock_db.execute.side_effect = [mock_novel_result, mock_total_count_result, mock_published_count_result]

        # Act
        result = await get_novel_stats(novel_id, mock_db, mock_user)

        # Assert
        assert isinstance(result, NovelProgress)
        assert result.novel_id == novel_id
        assert result.total_chapters == 5
        assert result.published_chapters == 3
        assert result.target_chapters == 10
        assert result.progress_percentage == 30.0  # 3/10 * 100
        assert mock_db.execute.call_count == 3

    @pytest.mark.asyncio
    async def test_get_novel_stats_novel_not_found(self, mock_user):
        """Test getting stats when novel not found."""
        # Arrange
        mock_db = AsyncMock()
        novel_id = uuid4()
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await get_novel_stats(novel_id, mock_db, mock_user)

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert exc_info.value.detail == "Novel not found"

    @pytest.mark.asyncio
    async def test_get_novel_stats_database_error(self, mock_user):
        """Test getting stats with database error."""
        # Arrange
        mock_db = AsyncMock()
        novel_id = uuid4()
        mock_db.execute.side_effect = Exception("Database error")

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await get_novel_stats(novel_id, mock_db, mock_user)

        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "An error occurred while retrieving novel statistics" in exc_info.value.detail
