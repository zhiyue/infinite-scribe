"""Tests for custom logging processors"""

from src.core.logging.processors import SerializationFallbackProcessor, StandardFieldsProcessor
from src.core.logging.types import ErrorType


class TestSerializationFallbackProcessor:
    """Test serialization fallback processor"""

    def test_handles_serializable_objects(self):
        """Test processor handles normal serializable objects"""
        processor = SerializationFallbackProcessor()

        event_dict = {"message": "Test", "count": 42, "items": [1, 2, 3], "data": {"key": "value"}}

        # Execute
        result = processor(None, None, event_dict)

        # Assert - should not modify serializable objects
        assert result["message"] == "Test"
        assert result["count"] == 42
        assert result["items"] == [1, 2, 3]
        assert result["data"] == {"key": "value"}
        assert "serialization_fallback" not in result

    def test_handles_non_serializable_objects(self):
        """Test processor handles non-serializable objects"""
        processor = SerializationFallbackProcessor()

        # Create a non-serializable object
        class NonSerializable:
            def __repr__(self):
                return "NonSerializable(test_data)"

        event_dict = {"message": "Test", "obj": NonSerializable(), "normal_field": "normal_value"}

        # Execute
        result = processor(None, None, event_dict)

        # Assert
        assert result["obj"] == "NonSerializable(test_data)"
        assert result["normal_field"] == "normal_value"
        assert result["serialization_fallback"] is True

    def test_handles_mixed_serializable_and_non_serializable(self):
        """Test processor handles mixed object types"""
        processor = SerializationFallbackProcessor()

        # Create mixed objects
        class NonSerializable:
            def __repr__(self):
                return "NonSerializable()"

        event_dict = {
            "good": "serializable",
            "bad": NonSerializable(),
            "also_good": 123,
            "also_bad": lambda x: x,  # Functions are not JSON serializable
        }

        # Execute
        result = processor(None, None, event_dict)

        # Assert
        assert result["good"] == "serializable"
        assert result["also_good"] == 123
        assert result["bad"] == "NonSerializable()"
        assert "lambda" in result["also_bad"]  # Lambda should be converted to string
        assert result["serialization_fallback"] is True

    def test_preserves_original_dict_reference(self):
        """Test processor modifies the original event dict"""
        processor = SerializationFallbackProcessor()

        class NonSerializable:
            def __repr__(self):
                return "test"

        event_dict = {"obj": NonSerializable()}

        # Execute
        result = processor(None, None, event_dict)

        # Assert - should be the same dict reference
        assert result is event_dict
        assert event_dict["obj"] == "test"
        assert event_dict["serialization_fallback"] is True


class TestStandardFieldsProcessor:
    """Test standard fields processor"""

    def test_does_not_modify_event_dict_by_default(self):
        """Test that standard fields processor doesn't modify event dict by default"""
        processor = StandardFieldsProcessor()

        event_dict = {"message": "Test message", "component": "api", "state": "starting"}

        # Execute
        result = processor(None, None, event_dict)

        # Assert - should preserve all existing fields
        assert result["message"] == "Test message"
        assert result["component"] == "api"
        assert result["state"] == "starting"

        # Should not add any new fields by default
        assert len(result) == len(event_dict)

    def test_returns_same_dict_reference(self):
        """Test processor returns the same dict reference"""
        processor = StandardFieldsProcessor()

        event_dict = {"test": "value"}

        # Execute
        result = processor(None, None, event_dict)

        # Assert
        assert result is event_dict


class TestErrorType:
    """Test ErrorType enumeration"""

    def test_error_type_values(self):
        """Test that error type has expected values"""
        assert ErrorType.TIMEOUT.value == "timeout"
        assert ErrorType.CONNECTION_ERROR.value == "connection_error"
        assert ErrorType.CONFIG_ERROR.value == "config_error"
        assert ErrorType.DEPENDENCY_ERROR.value == "dependency_error"
        assert ErrorType.VALIDATION_ERROR.value == "validation_error"
        assert ErrorType.STARTUP_ERROR.value == "startup_error"
        assert ErrorType.SHUTDOWN_ERROR.value == "shutdown_error"

    def test_error_type_enum_membership(self):
        """Test error type enumeration membership"""
        all_error_types = list(ErrorType)

        expected_types = [
            ErrorType.TIMEOUT,
            ErrorType.CONNECTION_ERROR,
            ErrorType.CONFIG_ERROR,
            ErrorType.DEPENDENCY_ERROR,
            ErrorType.VALIDATION_ERROR,
            ErrorType.STARTUP_ERROR,
            ErrorType.SHUTDOWN_ERROR,
        ]

        assert len(all_error_types) == len(expected_types)
        for error_type in expected_types:
            assert error_type in all_error_types
