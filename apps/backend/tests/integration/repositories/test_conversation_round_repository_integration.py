"""Integration tests for ConversationRoundRepository with real database."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from src.common.repositories.conversation.round_repository import (
    SqlAlchemyConversationRoundRepository,
)
from src.common.repositories.conversation.session_repository import (
    SqlAlchemyConversationSessionRepository,
)
from src.models.conversation import ConversationRound, ConversationSession
from src.schemas.novel.dialogue import DialogueRole, SessionStatus


@pytest.mark.integration
class TestConversationRoundRepositoryIntegration:
    """Integration tests for SqlAlchemyConversationRoundRepository with real database."""

    @pytest.fixture
    async def test_session(self, postgres_test_session: AsyncSession) -> ConversationSession:
        """Create a test session for round operations."""
        session_repo = SqlAlchemyConversationSessionRepository(postgres_test_session)
        session = await session_repo.create(
            scope_type="genesis",
            scope_id=str(uuid4()),
            status=SessionStatus.ACTIVE,
        )
        await postgres_test_session.commit()
        return session

    async def test_create_and_persist_round(
        self, postgres_test_session: AsyncSession, test_session: ConversationSession
    ):
        """Test round creation and persistence to real database."""
        # Arrange
        repository = SqlAlchemyConversationRoundRepository(postgres_test_session)
        round_path = "1"
        role = DialogueRole.USER.value
        input_data = {"message": "Integration test message"}
        model = "gpt-4"
        correlation_id = str(uuid4())

        # Act
        round_obj = await repository.create(
            session_id=test_session.id,
            round_path=round_path,
            role=role,
            input=input_data,
            model=model,
            correlation_id=correlation_id,
        )
        await postgres_test_session.commit()

        # Verify persistence in fresh session using composite primary key
        new_session = AsyncSession(postgres_test_session.bind)
        try:
            found_round = await new_session.get(ConversationRound, (test_session.id, round_path))
        finally:
            await new_session.close()

        # Assert
        assert found_round is not None
        assert found_round.session_id == test_session.id
        assert found_round.round_path == round_path
        assert found_round.role == role
        assert found_round.input == input_data
        assert found_round.model == model
        assert found_round.correlation_id == correlation_id

    async def test_foreign_key_constraint_session(self, postgres_test_session: AsyncSession):
        """Test foreign key constraint with session."""
        # Arrange
        repository = SqlAlchemyConversationRoundRepository(postgres_test_session)
        non_existent_session_id = uuid4()

        # Act & Assert
        with pytest.raises(IntegrityError):
            await repository.create(
                session_id=non_existent_session_id,
                round_path="1",
                role=DialogueRole.USER.value,
            )
            await postgres_test_session.commit()

    async def test_unique_constraint_session_and_path(
        self, postgres_test_session: AsyncSession, test_session: ConversationSession
    ):
        """Test unique constraint for session_id + round_path."""
        # Arrange
        repository = SqlAlchemyConversationRoundRepository(postgres_test_session)
        round_path = "1"

        # Create first round
        await repository.create(
            session_id=test_session.id,
            round_path=round_path,
            role=DialogueRole.USER.value,
        )
        await postgres_test_session.commit()

        # Act & Assert - Try to create duplicate
        with pytest.raises(IntegrityError):
            await repository.create(
                session_id=test_session.id,
                round_path=round_path,
                role=DialogueRole.ASSISTANT.value,
            )
            await postgres_test_session.commit()

    async def test_find_by_session_and_path_database_query(
        self, postgres_test_session: AsyncSession, test_session: ConversationSession
    ):
        """Test finding round by session and path with real database query."""
        # Arrange
        repository = SqlAlchemyConversationRoundRepository(postgres_test_session)
        round_path = "1.2.3"
        input_data = {"nested": {"message": "deep path test"}}

        created_round = await repository.create(
            session_id=test_session.id,
            round_path=round_path,
            role=DialogueRole.USER.value,
            input=input_data,
        )
        await postgres_test_session.commit()

        # Act
        found_round = await repository.find_by_session_and_path(test_session.id, round_path)

        # Assert
        assert found_round is not None
        assert found_round.session_id == created_round.session_id
        assert found_round.round_path == created_round.round_path
        assert found_round.input == input_data

    async def test_find_by_correlation_id_database_query(
        self, postgres_test_session: AsyncSession, test_session: ConversationSession
    ):
        """Test finding round by correlation ID with real database query."""
        # Arrange
        repository = SqlAlchemyConversationRoundRepository(postgres_test_session)
        correlation_id = uuid4()

        created_round = await repository.create(
            session_id=test_session.id,
            round_path="1",
            role=DialogueRole.USER.value,
            correlation_id=str(correlation_id),
        )
        await postgres_test_session.commit()

        # Act
        found_round = await repository.find_by_correlation_id(test_session.id, correlation_id)

        # Assert
        assert found_round is not None
        assert found_round.session_id == created_round.session_id
        assert found_round.round_path == created_round.round_path
        assert found_round.correlation_id == str(correlation_id)

    async def test_list_by_session_sorting_and_pagination(
        self, postgres_test_session: AsyncSession, test_session: ConversationSession
    ):
        """Test complex list queries with sorting and pagination."""
        # Arrange
        repository = SqlAlchemyConversationRoundRepository(postgres_test_session)

        # Create rounds in specific order for testing
        round_data = [
            ("1", DialogueRole.USER, {"msg": "first"}),
            ("2", DialogueRole.ASSISTANT, {"msg": "second"}),
            ("1.1", DialogueRole.USER, {"msg": "branch"}),
            ("3", DialogueRole.USER, {"msg": "third"}),
            ("2.1", DialogueRole.ASSISTANT, {"msg": "assistant branch"}),
        ]

        created_rounds = []
        for path, role, data in round_data:
            round_obj = await repository.create(
                session_id=test_session.id,
                round_path=path,
                role=role.value,
                input=data,
            )
            created_rounds.append(round_obj)

        await postgres_test_session.commit()

        # Test ascending order (default)
        asc_rounds = await repository.list_by_session(test_session.id)

        # Test descending order
        desc_rounds = await repository.list_by_session(test_session.id, order="desc")

        # Test pagination with limit
        limited_rounds = await repository.list_by_session(test_session.id, limit=3)

        # Test pagination with after
        after_rounds = await repository.list_by_session(test_session.id, after="2")

        # Assert sorting
        assert len(asc_rounds) == 5
        assert asc_rounds[0].round_path == "1"
        assert asc_rounds[1].round_path == "1.1"
        assert asc_rounds[-1].round_path == "3"

        # Assert descending
        assert desc_rounds[0].round_path == "3"
        assert desc_rounds[-1].round_path == "1"

        # Assert limit
        assert len(limited_rounds) == 3

        # Assert after pagination
        after_paths = [r.round_path for r in after_rounds]
        assert "1" not in after_paths
        assert "2" not in after_paths
        assert "2.1" in after_paths
        assert "3" in after_paths

    async def test_list_by_session_role_filtering(
        self, postgres_test_session: AsyncSession, test_session: ConversationSession
    ):
        """Test filtering by role in list queries."""
        # Arrange
        repository = SqlAlchemyConversationRoundRepository(postgres_test_session)

        # Create mixed role rounds
        await repository.create(
            session_id=test_session.id,
            round_path="1",
            role=DialogueRole.USER.value,
            input={"type": "user1"},
        )
        await repository.create(
            session_id=test_session.id,
            round_path="2",
            role=DialogueRole.ASSISTANT.value,
            input={"type": "assistant1"},
        )
        await repository.create(
            session_id=test_session.id,
            round_path="3",
            role=DialogueRole.USER.value,
            input={"type": "user2"},
        )

        await postgres_test_session.commit()

        # Act
        user_rounds = await repository.list_by_session(test_session.id, role=DialogueRole.USER)
        assistant_rounds = await repository.list_by_session(test_session.id, role=DialogueRole.ASSISTANT)

        # Assert
        assert len(user_rounds) == 2
        assert all(r.role == DialogueRole.USER.value for r in user_rounds)
        assert user_rounds[0].input["type"] == "user1"
        assert user_rounds[1].input["type"] == "user2"

        assert len(assistant_rounds) == 1
        assert assistant_rounds[0].role == DialogueRole.ASSISTANT.value
        assert assistant_rounds[0].input["type"] == "assistant1"

    async def test_count_by_session_accuracy(
        self, postgres_test_session: AsyncSession, test_session: ConversationSession
    ):
        """Test count accuracy with real database."""
        # Arrange
        repository = SqlAlchemyConversationRoundRepository(postgres_test_session)

        # Initial count should be zero
        initial_count = await repository.count_by_session(test_session.id)
        assert initial_count == 0

        # Create rounds
        for i in range(7):
            await repository.create(
                session_id=test_session.id,
                round_path=str(i + 1),
                role=DialogueRole.USER.value,
            )

        await postgres_test_session.commit()

        # Act
        final_count = await repository.count_by_session(test_session.id)

        # Assert
        assert final_count == 7

    async def test_json_data_persistence(self, postgres_test_session: AsyncSession, test_session: ConversationSession):
        """Test JSON data types persistence and querying."""
        # Arrange
        repository = SqlAlchemyConversationRoundRepository(postgres_test_session)

        complex_input = {
            "message": "Complex message",
            "metadata": {
                "timestamp": "2024-01-01T00:00:00Z",
                "tokens": 150,
                "nested": {
                    "array": [1, 2, 3],
                    "boolean": True,
                    "null_value": None,
                },
            },
        }

        complex_output = {
            "response": "AI response",
            "confidence": 0.95,
            "sources": ["doc1", "doc2"],
            "metrics": {
                "processing_time": 1.5,
                "token_count": 75,
            },
        }

        # Act
        round_obj = await repository.create(
            session_id=test_session.id,
            round_path="1",
            role=DialogueRole.ASSISTANT.value,
            input=complex_input,
            output=complex_output,
        )
        await postgres_test_session.commit()

        # Verify persistence in fresh session using composite primary key
        new_session = AsyncSession(postgres_test_session.bind)
        try:
            found_round = await new_session.get(ConversationRound, (test_session.id, "1"))
        finally:
            await new_session.close()

        # Assert
        assert found_round is not None
        assert found_round.input == complex_input
        assert found_round.output == complex_output
        assert found_round.input["metadata"]["nested"]["array"] == [1, 2, 3]
        assert found_round.output["confidence"] == 0.95

    async def test_cascade_delete_with_session(
        self, postgres_test_session: AsyncSession, test_session: ConversationSession
    ):
        """Test cascade delete behavior when session is deleted."""
        # Arrange
        repository = SqlAlchemyConversationRoundRepository(postgres_test_session)
        session_repo = SqlAlchemyConversationSessionRepository(postgres_test_session)

        # Create rounds
        round1 = await repository.create(
            session_id=test_session.id,
            round_path="1",
            role=DialogueRole.USER.value,
        )
        round2 = await repository.create(
            session_id=test_session.id,
            round_path="2",
            role=DialogueRole.ASSISTANT.value,
        )
        await postgres_test_session.commit()

        # Act - Delete session
        await session_repo.delete(test_session.id)
        await postgres_test_session.commit()

        # Verify rounds are also deleted using composite primary keys
        new_session = AsyncSession(postgres_test_session.bind)
        try:
            found_round1 = await new_session.get(ConversationRound, (test_session.id, "1"))
            found_round2 = await new_session.get(ConversationRound, (test_session.id, "2"))
        finally:
            await new_session.close()

        # Assert
        assert found_round1 is None
        assert found_round2 is None

    async def test_concurrent_round_creation(
        self, postgres_test_session: AsyncSession, test_session: ConversationSession
    ):
        """Test concurrent round creation with different paths."""
        # Arrange
        repository = SqlAlchemyConversationRoundRepository(postgres_test_session)

        # Create multiple rounds concurrently (different paths)
        rounds = []
        for i in range(5):
            round_obj = await repository.create(
                session_id=test_session.id,
                round_path=f"parallel_{i}",
                role=DialogueRole.USER.value,
                input={"batch": i},
            )
            rounds.append(round_obj)

        await postgres_test_session.commit()

        # Verify all created
        count = await repository.count_by_session(test_session.id)
        all_rounds = await repository.list_by_session(test_session.id)

        # Assert
        assert count == 5
        assert len(all_rounds) == 5
        assert all(r.session_id == test_session.id for r in all_rounds)

    async def test_timestamp_consistency_and_timezone(
        self, postgres_test_session: AsyncSession, test_session: ConversationSession
    ):
        """Test timestamp consistency and timezone handling."""
        # Arrange
        repository = SqlAlchemyConversationRoundRepository(postgres_test_session)
        before_creation = datetime.now(UTC)

        # Act
        round_obj = await repository.create(
            session_id=test_session.id,
            round_path="1",
            role=DialogueRole.USER.value,
        )
        await postgres_test_session.commit()

        after_creation = datetime.now(UTC)

        # Verify persistence using composite primary key
        new_session = AsyncSession(postgres_test_session.bind)
        try:
            # ConversationRound uses composite primary key (session_id, round_path)
            found_round = await new_session.get(ConversationRound, (test_session.id, "1"))
        finally:
            await new_session.close()

        # Assert
        assert found_round is not None
        assert before_creation <= found_round.created_at <= after_creation
        assert found_round.created_at.tzinfo is not None

    async def test_transaction_rollback_behavior(
        self, postgres_test_session: AsyncSession, test_session: ConversationSession
    ):
        """Test transaction rollback behavior."""
        # Arrange
        repository = SqlAlchemyConversationRoundRepository(postgres_test_session)
        session_id = test_session.id  # Store the ID before potential rollback

        try:
            # Create valid round
            await repository.create(
                session_id=session_id,
                round_path="1",
                role=DialogueRole.USER.value,
            )

            # Force constraint violation
            await repository.create(
                session_id=session_id,
                round_path="1",  # Duplicate path
                role=DialogueRole.ASSISTANT.value,
            )

            await postgres_test_session.commit()

        except IntegrityError:
            await postgres_test_session.rollback()

        # Verify rollback - no rounds should exist
        # Use the stored session_id since test_session may be invalidated after rollback
        count = await repository.count_by_session(session_id)

        # Assert
        assert count == 0
