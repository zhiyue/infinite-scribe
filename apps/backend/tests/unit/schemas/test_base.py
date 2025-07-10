"""Unit tests for base schema classes."""

import pytest
from datetime import UTC, datetime, timedelta
from unittest.mock import Mock, patch

from pydantic import Field
from src.schemas.base import BaseSchema, TimestampMixin, BaseDBModel


class TestBaseSchema:
    """Test cases for BaseSchema."""

    def test_base_schema_config(self):
        """Test BaseSchema configuration."""
        # Test that BaseSchema has the expected configuration
        config = BaseSchema.model_config
        
        assert config["from_attributes"] is True
        assert config["validate_assignment"] is True
        assert config["str_strip_whitespace"] is True
        assert config["use_enum_values"] is True

    def test_base_schema_inheritance(self):
        """Test that schemas can inherit from BaseSchema."""
        class TestSchema(BaseSchema):
            name: str
            age: int
        
        # Test creating instance
        schema = TestSchema(name="  John  ", age=25)
        assert schema.name == "John"  # Whitespace should be stripped
        assert schema.age == 25

    def test_base_schema_from_attributes(self):
        """Test that BaseSchema can be created from object attributes."""
        class TestSchema(BaseSchema):
            name: str
            value: int
        
        # Create a mock object with attributes
        mock_obj = Mock()
        mock_obj.name = "test"
        mock_obj.value = 42
        
        # Test creating schema from object
        schema = TestSchema.model_validate(mock_obj)
        assert schema.name == "test"
        assert schema.value == 42

    def test_base_schema_str_strip_whitespace(self):
        """Test that BaseSchema strips whitespace from strings."""
        class TestSchema(BaseSchema):
            text: str
        
        schema = TestSchema(text="  hello world  ")
        assert schema.text == "hello world"


class TestTimestampMixin:
    """Test cases for TimestampMixin."""

    def test_timestamp_mixin_fields(self):
        """Test that TimestampMixin has required timestamp fields."""
        class TestModel(TimestampMixin):
            name: str
        
        # Test that fields exist
        assert "created_at" in TestModel.model_fields
        assert "updated_at" in TestModel.model_fields

    def test_timestamp_mixin_auto_set_timestamps_dict(self):
        """Test that timestamps are automatically set when created from dict."""
        class TestModel(TimestampMixin):
            name: str
        
        # Test creating without timestamps
        with patch("src.schemas.base.datetime") as mock_datetime:
            mock_now = datetime(2021, 1, 1, 12, 0, 0, tzinfo=UTC)
            mock_datetime.now.return_value = mock_now
            mock_datetime.now.side_effect = lambda tz: mock_now
            
            model = TestModel(name="test")
            
            assert model.created_at == mock_now
            assert model.updated_at == mock_now

    def test_timestamp_mixin_preserve_existing_timestamps_dict(self):
        """Test that existing timestamps are preserved."""
        class TestModel(TimestampMixin):
            name: str
        
        existing_created = datetime(2020, 1, 1, 12, 0, 0, tzinfo=UTC)
        existing_updated = datetime(2020, 6, 1, 12, 0, 0, tzinfo=UTC)
        
        # Test creating with existing timestamps
        model = TestModel(
            name="test",
            created_at=existing_created,
            updated_at=existing_updated
        )
        
        assert model.created_at == existing_created
        assert model.updated_at == existing_updated

    def test_timestamp_mixin_partial_timestamps_dict(self):
        """Test behavior when only one timestamp is provided."""
        class TestModel(TimestampMixin):
            name: str
        
        existing_created = datetime(2020, 1, 1, 12, 0, 0, tzinfo=UTC)
        
        with patch("src.schemas.base.datetime") as mock_datetime:
            mock_now = datetime(2021, 1, 1, 12, 0, 0, tzinfo=UTC)
            mock_datetime.now.return_value = mock_now
            mock_datetime.now.side_effect = lambda tz: mock_now
            
            # Test with only created_at provided
            model = TestModel(name="test", created_at=existing_created)
            
            assert model.created_at == existing_created
            assert model.updated_at == mock_now

    def test_timestamp_mixin_non_dict_data(self):
        """Test that non-dict data passes through unchanged."""
        class TestModel(TimestampMixin):
            name: str
        
        # Create simple object (non-dict) that can be used with from_attributes
        class SimpleObj:
            def __init__(self):
                self.name = "test"
                self.created_at = datetime(2020, 1, 1, tzinfo=UTC)
                self.updated_at = datetime(2020, 6, 1, tzinfo=UTC)
        
        obj = SimpleObj()
        
        model = TestModel.model_validate(obj)
        assert model.name == "test"
        assert model.created_at == datetime(2020, 1, 1, tzinfo=UTC)
        assert model.updated_at == datetime(2020, 6, 1, tzinfo=UTC)


class TestBaseDBModel:
    """Test cases for BaseDBModel."""

    def test_base_db_model_config(self):
        """Test BaseDBModel configuration."""
        config = BaseDBModel.model_config
        
        assert config["from_attributes"] is True
        assert config["validate_assignment"] is True
        assert config["str_strip_whitespace"] is True
        assert config["use_enum_values"] is True

    def test_base_db_model_auto_update_timestamp_dict(self):
        """Test automatic updated_at setting from dict."""
        class TestModel(BaseDBModel):
            name: str
            updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
        
        with patch("src.schemas.base.datetime") as mock_datetime:
            mock_now = datetime(2021, 1, 1, 12, 0, 0, tzinfo=UTC)
            mock_datetime.now.return_value = mock_now
            mock_datetime.now.side_effect = lambda tz: mock_now
            
            # Test creating without updated_at
            model = TestModel(name="test")
            assert model.updated_at == mock_now

    def test_base_db_model_preserve_existing_updated_at_dict(self):
        """Test that existing updated_at is preserved."""
        class TestModel(BaseDBModel):
            name: str
            updated_at: datetime
        
        existing_updated = datetime(2020, 1, 1, 12, 0, 0, tzinfo=UTC)
        
        # Test creating with existing updated_at
        model = TestModel(name="test", updated_at=existing_updated)
        assert model.updated_at == existing_updated

    def test_base_db_model_no_updated_at_field(self):
        """Test behavior when model doesn't have updated_at field."""
        class TestModel(BaseDBModel):
            name: str
        
        # Should work fine without updated_at field
        model = TestModel(name="test")
        assert model.name == "test"

    def test_base_db_model_non_dict_data(self):
        """Test that non-dict data passes through unchanged."""
        class TestModel(BaseDBModel):
            name: str
            updated_at: datetime
        
        mock_obj = Mock()
        mock_obj.name = "test"
        mock_obj.updated_at = datetime(2020, 1, 1, tzinfo=UTC)
        
        model = TestModel.model_validate(mock_obj)
        assert model.name == "test"
        assert model.updated_at == datetime(2020, 1, 1, tzinfo=UTC)

    def test_base_db_model_setattr_auto_update(self):
        """Test that setting attributes auto-updates updated_at."""
        class TestModel(BaseDBModel):
            name: str
            value: int = 0
            updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
        
        initial_time = datetime(2020, 1, 1, 12, 0, 0, tzinfo=UTC)
        model = TestModel(name="test", value=10, updated_at=initial_time)
        
        # Verify initial state
        assert model.updated_at == initial_time
        
        with patch("src.schemas.base.datetime") as mock_datetime:
            new_time = datetime(2021, 1, 1, 12, 0, 0, tzinfo=UTC)
            mock_datetime.now.return_value = new_time
            mock_datetime.now.side_effect = lambda tz: new_time
            
            # Set a different attribute (not updated_at)
            model.name = "new_name"
            
            # updated_at should be automatically updated
            assert model.updated_at == new_time

    def test_base_db_model_setattr_updated_at_directly(self):
        """Test that setting updated_at directly doesn't trigger auto-update."""
        class TestModel(BaseDBModel):
            name: str
            updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
        
        initial_time = datetime(2020, 1, 1, 12, 0, 0, tzinfo=UTC)
        model = TestModel(name="test", updated_at=initial_time)
        
        # Set updated_at directly
        new_time = datetime(2021, 1, 1, 12, 0, 0, tzinfo=UTC)
        model.updated_at = new_time
        
        # Should keep the value we set, not auto-update again
        assert model.updated_at == new_time

    def test_base_db_model_setattr_no_updated_at_field(self):
        """Test that models without updated_at field work normally."""
        class TestModel(BaseDBModel):
            name: str
            value: int = 0
        
        model = TestModel(name="test", value=10)
        
        # Should work fine without updated_at field
        model.name = "new_name"
        assert model.name == "new_name"

    def test_base_db_model_setattr_internal_attributes(self):
        """Test that setting internal Pydantic attributes doesn't trigger auto-update."""
        class TestModel(BaseDBModel):
            name: str
            updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
        
        initial_time = datetime(2020, 1, 1, 12, 0, 0, tzinfo=UTC)
        model = TestModel(name="test", updated_at=initial_time)
        
        # Setting internal attributes shouldn't trigger auto-update
        # This would normally happen during Pydantic's internal operations
        super(BaseDBModel, model).__setattr__("_BaseDBModel__pydantic_extra__", {})
        
        # updated_at should remain unchanged
        assert model.updated_at == initial_time

    def test_base_db_model_setattr_no_hasattr_updated_at(self):
        """Test setattr behavior when object doesn't have updated_at attribute."""
        class TestModel(BaseDBModel):
            name: str
        
        model = TestModel(name="test")
        
        # This should work without errors even though there's no updated_at
        model.name = "new_name"
        assert model.name == "new_name"