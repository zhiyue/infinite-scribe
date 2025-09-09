"""Unit tests for conversation serializers."""

from datetime import UTC, datetime
from unittest.mock import Mock
from uuid import uuid4

from src.common.services.conversation.conversation_serializers import ConversationSerializer
from src.models.conversation import ConversationRound, ConversationSession
from src.schemas.novel.dialogue import SessionStatus


class TestConversationSerializer:
    """Test conversation serialization utilities."""

    def test_serialize_session_with_model(self):
        """Test serializing ConversationSession model instance."""
        # Arrange
        session_id = uuid4()
        created_at = datetime.now(UTC)
        updated_at = datetime.now(UTC)

        session = Mock(spec=ConversationSession)
        session.id = session_id
        session.scope_type = "genesis"
        session.scope_id = "novel-123"
        session.status = SessionStatus.ACTIVE.value
        session.stage = "worldbuilding"
        session.state = {"key": "value"}
        session.version = 2
        session.created_at = created_at
        session.updated_at = updated_at

        # Act
        result = ConversationSerializer.serialize_session(session)

        # Assert
        expected = {
            "id": str(session_id),
            "scope_type": "genesis",
            "scope_id": "novel-123",
            "status": SessionStatus.ACTIVE.value,
            "stage": "worldbuilding",
            "state": {"key": "value"},
            "version": 2,
            "created_at": created_at.isoformat(),
            "updated_at": updated_at.isoformat(),
        }
        assert result == expected

    def test_serialize_session_with_dict(self):
        """Test serializing session dictionary (pass-through)."""
        # Arrange
        session_dict = {
            "id": "123e4567-e89b-12d3-a456-426614174000",
            "scope_type": "genesis",
            "scope_id": "novel-456",
            "status": "active",
            "stage": "writing",
            "state": {},
            "version": 1,
        }

        # Act
        result = ConversationSerializer.serialize_session(session_dict)

        # Assert - should return the same dict
        assert result == session_dict

    def test_serialize_session_without_timestamps(self):
        """Test serializing session without created_at/updated_at."""

        # Arrange
        class MockSessionWithoutTimestamps:
            def __init__(self):
                self.id = uuid4()
                self.scope_type = "genesis"
                self.scope_id = "novel-789"
                self.status = "active"
                self.stage = None
                self.state = None
                self.version = 1
                # No created_at/updated_at attributes

        session = MockSessionWithoutTimestamps()

        # Act
        result = ConversationSerializer.serialize_session(session)

        # Assert
        assert result["created_at"] is None
        assert result["updated_at"] is None
        assert result["state"] == {}
        assert result["stage"] is None

    def test_serialize_round_with_model(self):
        """Test serializing ConversationRound model instance."""
        # Arrange
        session_id = uuid4()
        created_at = datetime.now(UTC)
        correlation_id = str(uuid4())

        round_model = Mock(spec=ConversationRound)
        round_model.session_id = session_id
        round_model.round_path = "1"
        round_model.role = "user"
        round_model.input = {"prompt": "Hello"}
        round_model.output = {"response": "Hi there"}
        round_model.model = "gpt-4"
        round_model.correlation_id = correlation_id
        round_model.created_at = created_at

        # Act
        result = ConversationSerializer.serialize_round(round_model)

        # Assert
        expected = {
            "session_id": str(session_id),
            "round_path": "1",
            "role": "user",
            "input": {"prompt": "Hello"},
            "output": {"response": "Hi there"},
            "model": "gpt-4",
            "correlation_id": correlation_id,
            "created_at": created_at.isoformat(),
        }
        assert result == expected

    def test_serialize_round_with_dict(self):
        """Test serializing round dictionary (pass-through)."""
        # Arrange
        round_dict = {
            "session_id": "123e4567-e89b-12d3-a456-426614174000",
            "round_path": "2",
            "role": "assistant",
            "input": {},
            "output": None,
            "model": None,
            "correlation_id": None,
        }

        # Act
        result = ConversationSerializer.serialize_round(round_dict)

        # Assert - should return the same dict
        assert result == round_dict

    def test_serialize_round_without_timestamps(self):
        """Test serializing round without created_at."""

        # Arrange
        class MockRoundWithoutTimestamps:
            def __init__(self):
                self.session_id = uuid4()
                self.round_path = "3"
                self.role = "user"
                self.input = None
                self.output = None
                self.model = None
                self.correlation_id = None
                # No created_at attribute

        round_model = MockRoundWithoutTimestamps()

        # Act
        result = ConversationSerializer.serialize_round(round_model)

        # Assert
        assert result["created_at"] is None
        assert result["input"] == {}

    def test_serialize_session_handles_isoformat_method(self):
        """Test that datetime objects with isoformat method are properly serialized."""
        # Arrange
        created_at = Mock()
        created_at.isoformat.return_value = "2023-12-01T10:00:00+00:00"

        session = Mock()
        session.id = uuid4()
        session.scope_type = "genesis"
        session.scope_id = "novel-test"
        session.status = "active"
        session.stage = "test"
        session.state = {}
        session.version = 1
        session.created_at = created_at
        session.updated_at = created_at

        # Act
        result = ConversationSerializer.serialize_session(session)

        # Assert
        assert result["created_at"] == "2023-12-01T10:00:00+00:00"
        assert result["updated_at"] == "2023-12-01T10:00:00+00:00"
        created_at.isoformat.assert_called()

    def test_serialize_round_handles_isoformat_method(self):
        """Test that datetime objects with isoformat method are properly serialized."""
        # Arrange
        created_at = Mock()
        created_at.isoformat.return_value = "2023-12-01T15:30:00+00:00"

        round_model = Mock()
        round_model.session_id = uuid4()
        round_model.round_path = "test"
        round_model.role = "user"
        round_model.input = {}
        round_model.output = None
        round_model.model = None
        round_model.correlation_id = None
        round_model.created_at = created_at

        # Act
        result = ConversationSerializer.serialize_round(round_model)

        # Assert
        assert result["created_at"] == "2023-12-01T15:30:00+00:00"
        created_at.isoformat.assert_called()

    def test_serialize_session_handles_string_conversion_fallback(self):
        """Test fallback to str() when isoformat is not available."""
        # Arrange
        created_at = "2023-12-01 10:00:00"  # String without isoformat method

        session = Mock()
        session.id = uuid4()
        session.scope_type = "genesis"
        session.scope_id = "novel-test"
        session.status = "active"
        session.stage = "test"
        session.state = {}
        session.version = 1
        session.created_at = created_at
        session.updated_at = created_at

        # Act
        result = ConversationSerializer.serialize_session(session)

        # Assert
        assert result["created_at"] == "2023-12-01 10:00:00"
        assert result["updated_at"] == "2023-12-01 10:00:00"
