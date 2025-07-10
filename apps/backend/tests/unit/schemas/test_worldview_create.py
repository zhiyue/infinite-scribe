"""Unit tests for worldview create schemas."""

from uuid import uuid4

import pytest
from pydantic import ValidationError
from src.schemas.enums import WorldviewEntryType
from src.schemas.worldview.create import StoryArcCreateRequest, WorldviewEntryCreateRequest


class TestWorldviewEntryCreateRequest:
    """Test cases for WorldviewEntryCreateRequest schema."""

    def test_valid_entry_minimal_fields(self):
        """Test valid entry creation with minimal required fields."""
        novel_id = uuid4()
        
        entry = WorldviewEntryCreateRequest(
            novel_id=novel_id,
            entry_type=WorldviewEntryType.LOCATION,
            name="Ancient Library"
        )
        
        assert entry.novel_id == novel_id
        assert entry.entry_type == WorldviewEntryType.LOCATION
        assert entry.name == "Ancient Library"
        assert entry.description is None
        assert entry.tags is None

    def test_valid_entry_all_fields(self):
        """Test valid entry creation with all fields."""
        novel_id = uuid4()
        
        entry = WorldviewEntryCreateRequest(
            novel_id=novel_id,
            entry_type=WorldviewEntryType.ORGANIZATION,
            name="The Guild",
            description="A powerful organization controlling trade",
            tags=["guild", "trade", "political"]
        )
        
        assert entry.novel_id == novel_id
        assert entry.entry_type == WorldviewEntryType.ORGANIZATION
        assert entry.name == "The Guild"
        assert entry.description == "A powerful organization controlling trade"
        assert entry.tags == ["guild", "trade", "political"]

    def test_valid_different_entry_types(self):
        """Test valid creation with different entry types."""
        novel_id = uuid4()
        
        # Test CONCEPT type
        entry1 = WorldviewEntryCreateRequest(
            novel_id=novel_id,
            entry_type=WorldviewEntryType.CONCEPT,
            name="Magic System"
        )
        assert entry1.entry_type == WorldviewEntryType.CONCEPT
        
        # Test TECHNOLOGY type
        entry2 = WorldviewEntryCreateRequest(
            novel_id=novel_id,
            entry_type=WorldviewEntryType.TECHNOLOGY,
            name="Skyships"
        )
        assert entry2.entry_type == WorldviewEntryType.TECHNOLOGY

    def test_valid_empty_tags_list(self):
        """Test valid entry with empty tags list."""
        novel_id = uuid4()
        
        entry = WorldviewEntryCreateRequest(
            novel_id=novel_id,
            entry_type=WorldviewEntryType.ITEM,
            name="Sacred Sword",
            tags=[]
        )
        
        assert entry.tags == []

    def test_name_max_length_validation(self):
        """Test name field max length validation."""
        novel_id = uuid4()
        
        # Test valid length (255 chars)
        valid_name = "A" * 255
        entry = WorldviewEntryCreateRequest(
            novel_id=novel_id,
            entry_type=WorldviewEntryType.OTHER,
            name=valid_name
        )
        assert len(entry.name) == 255
        
        # Test invalid length (256 chars)
        invalid_name = "A" * 256
        with pytest.raises(ValidationError):
            WorldviewEntryCreateRequest(
                novel_id=novel_id,
                entry_type=WorldviewEntryType.OTHER,
                name=invalid_name
            )


class TestStoryArcCreateRequest:
    """Test cases for StoryArcCreateRequest schema."""

    def test_valid_arc_minimal_fields(self):
        """Test valid arc creation with minimal required fields."""
        novel_id = uuid4()
        
        arc = StoryArcCreateRequest(
            novel_id=novel_id,
            title="The Hero's Journey"
        )
        
        assert arc.novel_id == novel_id
        assert arc.title == "The Hero's Journey"
        assert arc.summary is None
        assert arc.start_chapter_number is None
        assert arc.end_chapter_number is None
        assert arc.status == "PLANNED"

    def test_valid_arc_all_fields(self):
        """Test valid arc creation with all fields."""
        novel_id = uuid4()
        
        arc = StoryArcCreateRequest(
            novel_id=novel_id,
            title="The Rising Conflict",
            summary="A story arc about escalating tensions",
            start_chapter_number=5,
            end_chapter_number=12,
            status="IN_PROGRESS"
        )
        
        assert arc.novel_id == novel_id
        assert arc.title == "The Rising Conflict"
        assert arc.summary == "A story arc about escalating tensions"
        assert arc.start_chapter_number == 5
        assert arc.end_chapter_number == 12
        assert arc.status == "IN_PROGRESS"

    def test_valid_chapter_numbers_equal(self):
        """Test valid arc where start and end chapter numbers are equal."""
        novel_id = uuid4()
        
        arc = StoryArcCreateRequest(
            novel_id=novel_id,
            title="Single Chapter Arc",
            start_chapter_number=7,
            end_chapter_number=7
        )
        
        assert arc.start_chapter_number == 7
        assert arc.end_chapter_number == 7

    def test_valid_chapter_numbers_proper_order(self):
        """Test valid arc where end chapter number is greater than start."""
        novel_id = uuid4()
        
        arc = StoryArcCreateRequest(
            novel_id=novel_id,
            title="Multi Chapter Arc",
            start_chapter_number=3,
            end_chapter_number=8
        )
        
        assert arc.start_chapter_number == 3
        assert arc.end_chapter_number == 8

    def test_invalid_chapter_numbers_wrong_order(self):
        """Test invalid arc where end chapter number is less than start."""
        novel_id = uuid4()
        
        with pytest.raises(ValidationError) as exc_info:
            StoryArcCreateRequest(
                novel_id=novel_id,
                title="Invalid Arc",
                start_chapter_number=10,
                end_chapter_number=5
            )
        
        assert "结束章节号不能小于开始章节号" in str(exc_info.value)

    def test_valid_partial_chapter_numbers(self):
        """Test valid arc with only start or only end chapter number."""
        novel_id = uuid4()
        
        # Only start chapter number
        arc1 = StoryArcCreateRequest(
            novel_id=novel_id,
            title="Arc with start only",
            start_chapter_number=5
        )
        assert arc1.start_chapter_number == 5
        assert arc1.end_chapter_number is None
        
        # Only end chapter number
        arc2 = StoryArcCreateRequest(
            novel_id=novel_id,
            title="Arc with end only",
            end_chapter_number=10
        )
        assert arc2.start_chapter_number is None
        assert arc2.end_chapter_number == 10

    def test_invalid_chapter_number_zero(self):
        """Test invalid chapter numbers (zero or negative)."""
        novel_id = uuid4()
        
        # Test start chapter number zero
        with pytest.raises(ValidationError):
            StoryArcCreateRequest(
                novel_id=novel_id,
                title="Invalid start",
                start_chapter_number=0
            )
        
        # Test end chapter number zero
        with pytest.raises(ValidationError):
            StoryArcCreateRequest(
                novel_id=novel_id,
                title="Invalid end",
                end_chapter_number=0
            )

    def test_title_max_length_validation(self):
        """Test title field max length validation."""
        novel_id = uuid4()
        
        # Test valid length (255 chars)
        valid_title = "A" * 255
        arc = StoryArcCreateRequest(
            novel_id=novel_id,
            title=valid_title
        )
        assert len(arc.title) == 255
        
        # Test invalid length (256 chars)
        invalid_title = "A" * 256
        with pytest.raises(ValidationError):
            StoryArcCreateRequest(
                novel_id=novel_id,
                title=invalid_title
            )

    def test_status_max_length_validation(self):
        """Test status field max length validation."""
        novel_id = uuid4()
        
        # Test valid length (50 chars)
        valid_status = "A" * 50
        arc = StoryArcCreateRequest(
            novel_id=novel_id,
            title="Test Arc",
            status=valid_status
        )
        assert len(arc.status) == 50
        
        # Test invalid length (51 chars)
        invalid_status = "A" * 51
        with pytest.raises(ValidationError):
            StoryArcCreateRequest(
                novel_id=novel_id,
                title="Test Arc",
                status=invalid_status
            )