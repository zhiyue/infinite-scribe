"""Unit tests for NovelService."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from src.common.services.novel_service import NovelService
from src.models.novel import Novel
from src.schemas.enums import NovelStatus
from src.schemas.novel.create import NovelCreateRequest
from src.schemas.novel.update import NovelUpdateRequest


class TestNovelService:
    """Test cases for NovelService."""

    @pytest.fixture
    def novel_service(self):
        """Create NovelService instance."""
        return NovelService()

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def sample_novel(self):
        """Create sample novel for testing."""
        return Novel(
            id=uuid4(),
            user_id=1,
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
            writing_style=None,
            status=None,
            target_chapters=None,
            version=1,
        )

    @pytest.mark.asyncio
    async def test_list_user_novels_success(self, novel_service, mock_db, sample_novel):
        """Test successful listing of user novels."""
        # Arrange - Mock both count and data queries
        mock_count_result = Mock()
        mock_count_result.scalar.return_value = 1

        mock_data_result = Mock()
        mock_data_result.scalars.return_value.all.return_value = [sample_novel]

        # Return count result first, then data result
        mock_db.execute.side_effect = [mock_count_result, mock_data_result]

        # Act
        result = await novel_service.list_user_novels(mock_db, user_id=1)

        # Assert
        assert result["success"] is True
        assert "novels" in result
        assert len(result["novels"]) == 1
        assert result["novels"][0].title == "Test Novel"
        assert result["total"] == 1
        assert mock_db.execute.call_count == 2  # Count + data queries

    @pytest.mark.asyncio
    async def test_list_user_novels_with_filters(self, novel_service, mock_db, sample_novel):
        """Test listing novels with status filter."""
        # Arrange - Mock both count and data queries
        mock_count_result = Mock()
        mock_count_result.scalar.return_value = 1

        mock_data_result = Mock()
        mock_data_result.scalars.return_value.all.return_value = [sample_novel]

        # Return count result first, then data result
        mock_db.execute.side_effect = [mock_count_result, mock_data_result]

        # Act
        result = await novel_service.list_user_novels(mock_db, user_id=1, skip=5, limit=10, status_filter="GENESIS")

        # Assert
        assert result["success"] is True
        assert len(result["novels"]) == 1
        assert result["total"] == 1
        assert mock_db.execute.call_count == 2  # Count + data queries

    @pytest.mark.asyncio
    async def test_list_user_novels_empty_result(self, novel_service, mock_db):
        """Test listing novels with no results."""
        # Arrange - Mock both count and data queries
        mock_count_result = Mock()
        mock_count_result.scalar.return_value = 0

        mock_data_result = Mock()
        mock_data_result.scalars.return_value.all.return_value = []

        # Return count result first, then data result
        mock_db.execute.side_effect = [mock_count_result, mock_data_result]

        # Act
        result = await novel_service.list_user_novels(mock_db, user_id=1)

        # Assert
        assert result["success"] is True
        assert result["novels"] == []
        assert result["total"] == 0
        assert mock_db.execute.call_count == 2  # Count + data queries

    @pytest.mark.asyncio
    async def test_list_user_novels_database_error(self, novel_service, mock_db):
        """Test listing novels with database error."""
        # Arrange
        mock_db.execute.side_effect = Exception("Database error")

        # Act
        result = await novel_service.list_user_novels(mock_db, user_id=1)

        # Assert
        assert result["success"] is False
        assert "error" in result
        assert result["error"] == "An error occurred while retrieving novels"

    @pytest.mark.asyncio
    async def test_create_novel_success(self, novel_service, mock_db, sample_create_request, sample_novel):
        """Test successful novel creation."""
        # Arrange
        mock_db.add = Mock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        # Mock the novel creation
        with patch("src.common.services.novel_service.Novel") as mock_novel:
            mock_novel.return_value = sample_novel

            # Act
            result = await novel_service.create_novel(mock_db, user_id=1, novel_data=sample_create_request)

            # Assert
            assert result["success"] is True
            assert "novel" in result
            assert result["novel"].title == "Test Novel"
            mock_db.add.assert_called_once()
            mock_db.commit.assert_called_once()
            mock_db.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_novel_integrity_error(self, novel_service, mock_db, sample_create_request):
        """Test novel creation with integrity error."""
        # Arrange
        mock_db.add = Mock()
        mock_db.commit = AsyncMock(
            side_effect=IntegrityError("Integrity constraint violated", {}, ValueError("constraint violation"))
        )
        mock_db.rollback = AsyncMock()

        # Act
        result = await novel_service.create_novel(mock_db, user_id=1, novel_data=sample_create_request)

        # Assert
        assert result["success"] is False
        assert result["error"] == "Novel creation failed due to data constraints"
        mock_db.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_novel_general_error(self, novel_service, mock_db, sample_create_request):
        """Test novel creation with general error."""
        # Arrange
        mock_db.add = Mock(side_effect=Exception("Database error"))
        mock_db.rollback = AsyncMock()

        # Act
        result = await novel_service.create_novel(mock_db, user_id=1, novel_data=sample_create_request)

        # Assert
        assert result["success"] is False
        assert result["error"] == "An error occurred while creating the novel"
        mock_db.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_novel_success(self, novel_service, mock_db, sample_novel):
        """Test successful novel retrieval."""
        # Arrange
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_novel
        mock_db.execute.return_value = mock_result

        # Act
        result = await novel_service.get_novel(mock_db, user_id=1, novel_id=sample_novel.id)

        # Assert
        assert result["success"] is True
        assert "novel" in result
        assert result["novel"].id == sample_novel.id
        assert result["novel"].title == "Test Novel"
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_novel_not_found(self, novel_service, mock_db):
        """Test novel retrieval when novel not found."""
        # Arrange
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        # Act
        result = await novel_service.get_novel(mock_db, user_id=1, novel_id=uuid4())

        # Assert
        assert result["success"] is False
        assert result["error"] == "Novel not found"
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_novel_database_error(self, novel_service, mock_db):
        """Test novel retrieval with database error."""
        # Arrange
        mock_db.execute.side_effect = Exception("Database error")

        # Act
        result = await novel_service.get_novel(mock_db, user_id=1, novel_id=uuid4())

        # Assert
        assert result["success"] is False
        assert result["error"] == "An error occurred while retrieving the novel"

    @pytest.mark.asyncio
    async def test_update_novel_success(self, novel_service, mock_db, sample_novel, sample_update_request):
        """Test successful novel update."""
        # Arrange
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_novel
        mock_db.execute.return_value = mock_result
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        # Act
        result = await novel_service.update_novel(
            mock_db, user_id=1, novel_id=sample_novel.id, update_data=sample_update_request
        )

        # Assert
        assert result["success"] is True
        assert "novel" in result
        assert sample_novel.version == 2  # Version should be incremented
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_novel_not_found(self, novel_service, mock_db, sample_update_request):
        """Test novel update when novel not found."""
        # Arrange
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        # Act
        result = await novel_service.update_novel(
            mock_db, user_id=1, novel_id=uuid4(), update_data=sample_update_request
        )

        # Assert
        assert result["success"] is False
        assert result["error"] == "Novel not found"

    @pytest.mark.asyncio
    async def test_update_novel_version_conflict(self, novel_service, mock_db, sample_novel):
        """Test novel update with version conflict."""
        # Arrange
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_novel
        mock_db.execute.return_value = mock_result

        # Create update request with wrong version
        update_request = NovelUpdateRequest(
            title="Updated Title", theme=None, writing_style=None, status=None, target_chapters=None, version=999
        )

        # Act
        result = await novel_service.update_novel(
            mock_db, user_id=1, novel_id=sample_novel.id, update_data=update_request
        )

        # Assert
        assert result["success"] is False
        assert result["error_code"] == "CONFLICT"
        assert "modified by another process" in result["error"]

    @pytest.mark.asyncio
    async def test_update_novel_database_error(self, novel_service, mock_db, sample_novel, sample_update_request):
        """Test novel update with database error."""
        # Arrange
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_novel
        mock_db.execute.return_value = mock_result
        mock_db.commit = AsyncMock(side_effect=Exception("Database error"))
        mock_db.rollback = AsyncMock()

        # Act
        result = await novel_service.update_novel(
            mock_db, user_id=1, novel_id=sample_novel.id, update_data=sample_update_request
        )

        # Assert
        assert result["success"] is False
        assert result["error"] == "An error occurred while updating the novel"
        mock_db.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_novel_success(self, novel_service, mock_db, sample_novel):
        """Test successful novel deletion."""
        # Arrange
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_novel
        mock_db.execute.return_value = mock_result
        mock_db.delete = AsyncMock()
        mock_db.commit = AsyncMock()

        # Act
        result = await novel_service.delete_novel(mock_db, user_id=1, novel_id=sample_novel.id)

        # Assert
        assert result["success"] is True
        assert result["message"] == "Novel deleted successfully"
        mock_db.delete.assert_called_once_with(sample_novel)
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_novel_not_found(self, novel_service, mock_db):
        """Test novel deletion when novel not found."""
        # Arrange
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        # Act
        result = await novel_service.delete_novel(mock_db, user_id=1, novel_id=uuid4())

        # Assert
        assert result["success"] is False
        assert result["error"] == "Novel not found"

    @pytest.mark.asyncio
    async def test_delete_novel_database_error(self, novel_service, mock_db, sample_novel):
        """Test novel deletion with database error."""
        # Arrange
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_novel
        mock_db.execute.return_value = mock_result
        mock_db.delete = AsyncMock(side_effect=Exception("Database error"))
        mock_db.rollback = AsyncMock()

        # Act
        result = await novel_service.delete_novel(mock_db, user_id=1, novel_id=sample_novel.id)

        # Assert
        assert result["success"] is False
        assert result["error"] == "An error occurred while deleting the novel"
        mock_db.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_novel_chapters_success(self, novel_service, mock_db, sample_novel):
        """Test successful retrieval of novel chapters."""
        # Arrange
        # Mock novel ownership check
        mock_novel_result = Mock()
        mock_novel_result.scalar_one_or_none.return_value = sample_novel

        # Mock chapters query result
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
        result = await novel_service.get_novel_chapters(mock_db, user_id=1, novel_id=sample_novel.id)

        # Assert
        assert result["success"] is True
        assert "chapters" in result
        assert len(result["chapters"]) == 1
        assert result["chapters"][0]["title"] == "Chapter 1"
        assert result["chapters"][0]["chapter_number"] == 1
        assert mock_db.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_get_novel_chapters_novel_not_found(self, novel_service, mock_db):
        """Test getting chapters when novel not found."""
        # Arrange
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        # Act
        result = await novel_service.get_novel_chapters(mock_db, user_id=1, novel_id=uuid4())

        # Assert
        assert result["success"] is False
        assert result["error"] == "Novel not found"
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_novel_characters_success(self, novel_service, mock_db, sample_novel):
        """Test successful retrieval of novel characters."""
        # Arrange
        # Mock novel ownership check
        mock_novel_result = Mock()
        mock_novel_result.scalar_one_or_none.return_value = sample_novel

        # Mock characters query result
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
        result = await novel_service.get_novel_characters(mock_db, user_id=1, novel_id=sample_novel.id)

        # Assert
        assert result["success"] is True
        assert "characters" in result
        assert len(result["characters"]) == 1
        assert result["characters"][0]["name"] == "Test Character"
        assert result["characters"][0]["role"] == "PROTAGONIST"
        assert mock_db.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_get_novel_stats_success(self, novel_service, mock_db, sample_novel):
        """Test successful retrieval of novel statistics."""
        # Arrange
        # Mock novel ownership check
        mock_novel_result = Mock()
        mock_novel_result.scalar_one_or_none.return_value = sample_novel

        # Mock chapter count queries
        mock_total_count_result = Mock()
        mock_total_count_result.scalar.return_value = 5

        mock_published_count_result = Mock()
        mock_published_count_result.scalar.return_value = 3

        mock_db.execute.side_effect = [mock_novel_result, mock_total_count_result, mock_published_count_result]

        # Act
        result = await novel_service.get_novel_stats(mock_db, user_id=1, novel_id=sample_novel.id)

        # Assert
        assert result["success"] is True
        assert "stats" in result
        stats = result["stats"]
        assert stats.total_chapters == 5
        assert stats.published_chapters == 3
        assert stats.target_chapters == sample_novel.target_chapters
        assert stats.progress_percentage == 30.0  # 3/10 * 100
        assert mock_db.execute.call_count == 3

    @pytest.mark.asyncio
    async def test_get_novel_stats_novel_not_found(self, novel_service, mock_db):
        """Test getting stats when novel not found."""
        # Arrange
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        # Act
        result = await novel_service.get_novel_stats(mock_db, user_id=1, novel_id=uuid4())

        # Assert
        assert result["success"] is False
        assert result["error"] == "Novel not found"
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_novel_stats_database_error(self, novel_service, mock_db, sample_novel):
        """Test getting stats with database error."""
        # Arrange
        mock_db.execute.side_effect = Exception("Database error")

        # Act
        result = await novel_service.get_novel_stats(mock_db, user_id=1, novel_id=sample_novel.id)

        # Assert
        assert result["success"] is False
        assert result["error"] == "An error occurred while retrieving novel statistics"
