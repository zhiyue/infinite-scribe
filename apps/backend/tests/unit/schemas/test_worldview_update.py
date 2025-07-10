"""Unit tests for worldview update schemas."""

import pytest
from pydantic import ValidationError
from src.schemas.enums import WorldviewEntryType
from src.schemas.worldview.update import (
    StoryArcUpdateRequest,
    WorldviewEntryUpdateRequest,
)


class TestWorldviewEntryUpdateRequest:
    """Test cases for WorldviewEntryUpdateRequest."""

    def test_valid_update_single_field(self):
        """Test valid update with single field."""
        request = WorldviewEntryUpdateRequest(name="新条目名称")

        assert request.name == "新条目名称"
        assert request.entry_type is None
        assert request.description is None
        assert request.tags is None

    def test_valid_update_multiple_fields(self):
        """Test valid update with multiple fields."""
        request = WorldviewEntryUpdateRequest(
            entry_type=WorldviewEntryType.LOCATION,
            name="魔法学院",
            description="一个神秘的魔法学院",
            tags=["魔法", "学院", "教育"],
        )

        assert request.entry_type == WorldviewEntryType.LOCATION
        assert request.name == "魔法学院"
        assert request.description == "一个神秘的魔法学院"
        assert request.tags == ["魔法", "学院", "教育"]

    def test_valid_update_with_entry_type_only(self):
        """Test valid update with entry_type only."""
        request = WorldviewEntryUpdateRequest(entry_type=WorldviewEntryType.CONCEPT)

        assert request.entry_type == WorldviewEntryType.CONCEPT
        assert request.name is None
        assert request.description is None
        assert request.tags is None

    def test_valid_update_with_description_only(self):
        """Test valid update with description only."""
        request = WorldviewEntryUpdateRequest(description="更新后的描述")

        assert request.description == "更新后的描述"
        assert request.entry_type is None
        assert request.name is None
        assert request.tags is None

    def test_valid_update_with_tags_only(self):
        """Test valid update with tags only."""
        request = WorldviewEntryUpdateRequest(tags=["标签1", "标签2"])

        assert request.tags == ["标签1", "标签2"]
        assert request.entry_type is None
        assert request.name is None
        assert request.description is None

    def test_valid_update_with_empty_tags_list(self):
        """Test valid update with empty tags list."""
        request = WorldviewEntryUpdateRequest(tags=[])

        assert request.tags == []
        assert request.entry_type is None
        assert request.name is None
        assert request.description is None

    def test_invalid_update_no_fields(self):
        """Test invalid update with no fields provided."""
        with pytest.raises(ValidationError) as exc_info:
            WorldviewEntryUpdateRequest()

        assert "至少需要提供一个字段进行更新" in str(exc_info.value)

    def test_invalid_update_all_none_fields(self):
        """Test invalid update with all fields explicitly set to None."""
        with pytest.raises(ValidationError) as exc_info:
            WorldviewEntryUpdateRequest(entry_type=None, name=None, description=None, tags=None)

        assert "至少需要提供一个字段进行更新" in str(exc_info.value)

    def test_invalid_name_too_long(self):
        """Test invalid update with name too long."""
        long_name = "x" * 256  # Exceeds max_length=255

        with pytest.raises(ValidationError) as exc_info:
            WorldviewEntryUpdateRequest(name=long_name)

        assert "String should have at most 255 characters" in str(exc_info.value)


class TestStoryArcUpdateRequest:
    """Test cases for StoryArcUpdateRequest."""

    def test_valid_update_single_field(self):
        """Test valid update with single field."""
        request = StoryArcUpdateRequest(title="新故事弧")

        assert request.title == "新故事弧"
        assert request.summary is None
        assert request.start_chapter_number is None
        assert request.end_chapter_number is None
        assert request.status is None

    def test_valid_update_multiple_fields(self):
        """Test valid update with multiple fields."""
        request = StoryArcUpdateRequest(
            title="主角觉醒篇",
            summary="主角发现自己的力量",
            start_chapter_number=1,
            end_chapter_number=10,
            status="COMPLETED",
        )

        assert request.title == "主角觉醒篇"
        assert request.summary == "主角发现自己的力量"
        assert request.start_chapter_number == 1
        assert request.end_chapter_number == 10
        assert request.status == "COMPLETED"

    def test_valid_update_with_summary_only(self):
        """Test valid update with summary only."""
        request = StoryArcUpdateRequest(summary="更新后的摘要")

        assert request.summary == "更新后的摘要"
        assert request.title is None
        assert request.start_chapter_number is None
        assert request.end_chapter_number is None
        assert request.status is None

    def test_valid_update_with_start_chapter_only(self):
        """Test valid update with start_chapter_number only."""
        request = StoryArcUpdateRequest(start_chapter_number=5)

        assert request.start_chapter_number == 5
        assert request.title is None
        assert request.summary is None
        assert request.end_chapter_number is None
        assert request.status is None

    def test_valid_update_with_end_chapter_only(self):
        """Test valid update with end_chapter_number only."""
        request = StoryArcUpdateRequest(end_chapter_number=15)

        assert request.end_chapter_number == 15
        assert request.title is None
        assert request.summary is None
        assert request.start_chapter_number is None
        assert request.status is None

    def test_valid_update_with_status_only(self):
        """Test valid update with status only."""
        request = StoryArcUpdateRequest(status="ACTIVE")

        assert request.status == "ACTIVE"
        assert request.title is None
        assert request.summary is None
        assert request.start_chapter_number is None
        assert request.end_chapter_number is None

    def test_valid_chapter_numbers_equal(self):
        """Test valid update with equal start and end chapter numbers."""
        request = StoryArcUpdateRequest(start_chapter_number=5, end_chapter_number=5)

        assert request.start_chapter_number == 5
        assert request.end_chapter_number == 5

    def test_valid_chapter_numbers_end_greater(self):
        """Test valid update with end chapter greater than start."""
        request = StoryArcUpdateRequest(start_chapter_number=3, end_chapter_number=8)

        assert request.start_chapter_number == 3
        assert request.end_chapter_number == 8

    def test_invalid_update_no_fields(self):
        """Test invalid update with no fields provided."""
        with pytest.raises(ValidationError) as exc_info:
            StoryArcUpdateRequest()

        assert "至少需要提供一个字段进行更新" in str(exc_info.value)

    def test_invalid_update_all_none_fields(self):
        """Test invalid update with all fields explicitly set to None."""
        with pytest.raises(ValidationError) as exc_info:
            StoryArcUpdateRequest(
                title=None, summary=None, start_chapter_number=None, end_chapter_number=None, status=None
            )

        assert "至少需要提供一个字段进行更新" in str(exc_info.value)

    def test_invalid_title_too_long(self):
        """Test invalid update with title too long."""
        long_title = "x" * 256  # Exceeds max_length=255

        with pytest.raises(ValidationError) as exc_info:
            StoryArcUpdateRequest(title=long_title)

        assert "String should have at most 255 characters" in str(exc_info.value)

    def test_invalid_status_too_long(self):
        """Test invalid update with status too long."""
        long_status = "x" * 51  # Exceeds max_length=50

        with pytest.raises(ValidationError) as exc_info:
            StoryArcUpdateRequest(status=long_status)

        assert "String should have at most 50 characters" in str(exc_info.value)

    def test_invalid_start_chapter_zero(self):
        """Test invalid update with start_chapter_number = 0."""
        with pytest.raises(ValidationError) as exc_info:
            StoryArcUpdateRequest(start_chapter_number=0)

        assert "Input should be greater than or equal to 1" in str(exc_info.value)

    def test_invalid_start_chapter_negative(self):
        """Test invalid update with negative start_chapter_number."""
        with pytest.raises(ValidationError) as exc_info:
            StoryArcUpdateRequest(start_chapter_number=-1)

        assert "Input should be greater than or equal to 1" in str(exc_info.value)

    def test_invalid_end_chapter_zero(self):
        """Test invalid update with end_chapter_number = 0."""
        with pytest.raises(ValidationError) as exc_info:
            StoryArcUpdateRequest(end_chapter_number=0)

        assert "Input should be greater than or equal to 1" in str(exc_info.value)

    def test_invalid_end_chapter_negative(self):
        """Test invalid update with negative end_chapter_number."""
        with pytest.raises(ValidationError) as exc_info:
            StoryArcUpdateRequest(end_chapter_number=-1)

        assert "Input should be greater than or equal to 1" in str(exc_info.value)

    def test_invalid_chapter_numbers_end_less_than_start(self):
        """Test invalid update with end chapter less than start chapter."""
        with pytest.raises(ValidationError) as exc_info:
            StoryArcUpdateRequest(start_chapter_number=10, end_chapter_number=5)

        assert "结束章节号不能小于开始章节号" in str(exc_info.value)

    def test_invalid_chapter_numbers_large_difference(self):
        """Test invalid update with large difference (end < start)."""
        with pytest.raises(ValidationError) as exc_info:
            StoryArcUpdateRequest(start_chapter_number=100, end_chapter_number=1)

        assert "结束章节号不能小于开始章节号" in str(exc_info.value)
