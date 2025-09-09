"""Unit tests for ConversationRoundRepository."""

from datetime import datetime
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from src.common.repositories.conversation import SqlAlchemyConversationRoundRepository
from src.models.conversation import ConversationSession
from src.schemas.novel.dialogue import DialogueRole, SessionStatus


@pytest.mark.asyncio
class TestSqlAlchemyConversationRoundRepository:
    """Test SqlAlchemyConversationRoundRepository implementation."""

    @pytest.fixture
    async def test_session(self, async_session: AsyncSession) -> ConversationSession:
        """Create a test session for round operations."""
        session = ConversationSession(
            scope_type="genesis",
            scope_id=str(uuid4()),
            status=SessionStatus.ACTIVE.value,
            version=1,
        )
        async_session.add(session)
        await async_session.commit()
        await async_session.refresh(session)
        return session

    async def test_create_round_success(self, async_session: AsyncSession, test_session: ConversationSession):
        """Test successful round creation."""
        # Arrange
        repository = SqlAlchemyConversationRoundRepository(async_session)
        round_path = "1"
        role = DialogueRole.USER.value
        input_data = {"message": "Hello world"}
        model = "gpt-4"
        correlation_id = str(uuid4())

        # Act
        round_obj = await repository.create(
            session_id=test_session.id,
            round_path=round_path,
            role=role,
            input_data=input_data,
            model=model,
            correlation_id=correlation_id,
        )

        # Assert
        assert round_obj is not None
        assert round_obj.session_id == test_session.id
        assert round_obj.round_path == round_path
        assert round_obj.role == role
        assert round_obj.input_data == input_data
        assert round_obj.model == model
        assert round_obj.correlation_id == correlation_id
        assert round_obj.id is not None
        assert isinstance(round_obj.created_at, datetime)
        assert isinstance(round_obj.updated_at, datetime)

    async def test_find_by_session_and_path_existing(
        self, async_session: AsyncSession, test_session: ConversationSession
    ):
        """Test finding round by session and path when it exists."""
        # Arrange
        repository = SqlAlchemyConversationRoundRepository(async_session)
        round_path = "1"

        # Create a round first
        created_round = await repository.create(
            session_id=test_session.id,
            round_path=round_path,
            role=DialogueRole.USER.value,
            input_data={"message": "test"},
        )

        # Act
        found_round = await repository.find_by_session_and_path(test_session.id, round_path)

        # Assert
        assert found_round is not None
        assert found_round.id == created_round.id
        assert found_round.session_id == test_session.id
        assert found_round.round_path == round_path

    async def test_find_by_session_and_path_not_existing(
        self, async_session: AsyncSession, test_session: ConversationSession
    ):
        """Test finding round by session and path when it doesn't exist."""
        # Arrange
        repository = SqlAlchemyConversationRoundRepository(async_session)
        non_existent_path = "999"

        # Act
        found_round = await repository.find_by_session_and_path(test_session.id, non_existent_path)

        # Assert
        assert found_round is None

    async def test_find_by_correlation_id_existing(
        self, async_session: AsyncSession, test_session: ConversationSession
    ):
        """Test finding round by correlation ID when it exists."""
        # Arrange
        repository = SqlAlchemyConversationRoundRepository(async_session)
        correlation_id = uuid4()

        # Create a round first
        created_round = await repository.create(
            session_id=test_session.id,
            round_path="1",
            role=DialogueRole.USER.value,
            input_data={"message": "test"},
            correlation_id=str(correlation_id),
        )

        # Act
        found_round = await repository.find_by_correlation_id(test_session.id, correlation_id)

        # Assert
        assert found_round is not None
        assert found_round.id == created_round.id
        assert found_round.correlation_id == str(correlation_id)

    async def test_find_by_correlation_id_not_existing(
        self, async_session: AsyncSession, test_session: ConversationSession
    ):
        """Test finding round by correlation ID when it doesn't exist."""
        # Arrange
        repository = SqlAlchemyConversationRoundRepository(async_session)
        non_existent_correlation_id = uuid4()

        # Act
        found_round = await repository.find_by_correlation_id(test_session.id, non_existent_correlation_id)

        # Assert
        assert found_round is None

    async def test_count_by_session(self, async_session: AsyncSession, test_session: ConversationSession):
        """Test counting rounds by session."""
        # Arrange
        repository = SqlAlchemyConversationRoundRepository(async_session)

        # Create multiple rounds
        await repository.create(
            session_id=test_session.id,
            round_path="1",
            role=DialogueRole.USER.value,
            input_data={"message": "first"},
        )
        await repository.create(
            session_id=test_session.id,
            round_path="2",
            role=DialogueRole.ASSISTANT.value,
            input_data={"message": "second"},
        )
        await repository.create(
            session_id=test_session.id,
            round_path="3",
            role=DialogueRole.USER.value,
            input_data={"message": "third"},
        )

        # Act
        count = await repository.count_by_session(test_session.id)

        # Assert
        assert count == 3

    async def test_count_by_session_empty(self, async_session: AsyncSession, test_session: ConversationSession):
        """Test counting rounds by session when no rounds exist."""
        # Arrange
        repository = SqlAlchemyConversationRoundRepository(async_session)

        # Act
        count = await repository.count_by_session(test_session.id)

        # Assert
        assert count == 0

    async def test_list_by_session_basic(self, async_session: AsyncSession, test_session: ConversationSession):
        """Test basic listing of rounds by session."""
        # Arrange
        repository = SqlAlchemyConversationRoundRepository(async_session)

        # Create rounds in specific order
        round1 = await repository.create(
            session_id=test_session.id,
            round_path="1",
            role=DialogueRole.USER.value,
            input_data={"message": "first"},
        )
        round2 = await repository.create(
            session_id=test_session.id,
            round_path="2",
            role=DialogueRole.ASSISTANT.value,
            input_data={"message": "second"},
        )
        round3 = await repository.create(
            session_id=test_session.id,
            round_path="3",
            role=DialogueRole.USER.value,
            input_data={"message": "third"},
        )

        # Act
        rounds = await repository.list_by_session(test_session.id)

        # Assert
        assert len(rounds) == 3
        # Should be in ascending order by round_path
        assert rounds[0].id == round1.id
        assert rounds[1].id == round2.id
        assert rounds[2].id == round3.id

    async def test_list_by_session_with_limit(self, async_session: AsyncSession, test_session: ConversationSession):
        """Test listing rounds with limit."""
        # Arrange
        repository = SqlAlchemyConversationRoundRepository(async_session)

        # Create 5 rounds
        for i in range(1, 6):
            await repository.create(
                session_id=test_session.id,
                round_path=str(i),
                role=DialogueRole.USER.value,
                input_data={"message": f"round {i}"},
            )

        # Act
        rounds = await repository.list_by_session(test_session.id, limit=3)

        # Assert
        assert len(rounds) == 3

    async def test_list_by_session_with_after(self, async_session: AsyncSession, test_session: ConversationSession):
        """Test listing rounds with after parameter for pagination."""
        # Arrange
        repository = SqlAlchemyConversationRoundRepository(async_session)

        # Create rounds
        for i in range(1, 6):
            await repository.create(
                session_id=test_session.id,
                round_path=str(i),
                role=DialogueRole.USER.value,
                input_data={"message": f"round {i}"},
            )

        # Act
        rounds = await repository.list_by_session(test_session.id, after="2")

        # Assert
        assert len(rounds) == 3  # rounds 3, 4, 5
        assert rounds[0].round_path == "3"
        assert rounds[1].round_path == "4"
        assert rounds[2].round_path == "5"

    async def test_list_by_session_descending_order(
        self, async_session: AsyncSession, test_session: ConversationSession
    ):
        """Test listing rounds in descending order."""
        # Arrange
        repository = SqlAlchemyConversationRoundRepository(async_session)

        # Create rounds
        for i in range(1, 4):
            await repository.create(
                session_id=test_session.id,
                round_path=str(i),
                role=DialogueRole.USER.value,
                input_data={"message": f"round {i}"},
            )

        # Act
        rounds = await repository.list_by_session(test_session.id, order="desc")

        # Assert
        assert len(rounds) == 3
        # Should be in descending order by round_path
        assert rounds[0].round_path == "3"
        assert rounds[1].round_path == "2"
        assert rounds[2].round_path == "1"

    async def test_list_by_session_filter_by_role(self, async_session: AsyncSession, test_session: ConversationSession):
        """Test listing rounds filtered by role."""
        # Arrange
        repository = SqlAlchemyConversationRoundRepository(async_session)

        # Create rounds with different roles
        await repository.create(
            session_id=test_session.id,
            round_path="1",
            role=DialogueRole.USER.value,
            input_data={"message": "user message 1"},
        )
        await repository.create(
            session_id=test_session.id,
            round_path="2",
            role=DialogueRole.ASSISTANT.value,
            input_data={"message": "assistant message"},
        )
        await repository.create(
            session_id=test_session.id,
            round_path="3",
            role=DialogueRole.USER.value,
            input_data={"message": "user message 2"},
        )

        # Act
        user_rounds = await repository.list_by_session(test_session.id, role=DialogueRole.USER)

        # Assert
        assert len(user_rounds) == 2
        assert all(r.role == DialogueRole.USER.value for r in user_rounds)
        assert user_rounds[0].round_path == "1"
        assert user_rounds[1].round_path == "3"

    async def test_list_by_session_empty(self, async_session: AsyncSession, test_session: ConversationSession):
        """Test listing rounds when no rounds exist."""
        # Arrange
        repository = SqlAlchemyConversationRoundRepository(async_session)

        # Act
        rounds = await repository.list_by_session(test_session.id)

        # Assert
        assert len(rounds) == 0

    async def test_create_round_with_defaults(self, async_session: AsyncSession, test_session: ConversationSession):
        """Test round creation with default values."""
        # Arrange
        repository = SqlAlchemyConversationRoundRepository(async_session)
        round_path = "1"
        role = DialogueRole.USER.value

        # Act
        round_obj = await repository.create(
            session_id=test_session.id,
            round_path=round_path,
            role=role,
        )

        # Assert
        assert round_obj is not None
        assert round_obj.session_id == test_session.id
        assert round_obj.round_path == round_path
        assert round_obj.role == role
        assert round_obj.input_data is None  # Default
        assert round_obj.output_data is None  # Default
        assert round_obj.model is None  # Default
        assert round_obj.correlation_id is None  # Default

    async def test_create_round_with_output_data(self, async_session: AsyncSession, test_session: ConversationSession):
        """Test round creation with output data."""
        # Arrange
        repository = SqlAlchemyConversationRoundRepository(async_session)
        input_data = {"message": "Hello"}
        output_data = {"response": "Hello back!"}

        # Act
        round_obj = await repository.create(
            session_id=test_session.id,
            round_path="1",
            role=DialogueRole.ASSISTANT.value,
            input_data=input_data,
            output_data=output_data,
        )

        # Assert
        assert round_obj is not None
        assert round_obj.input_data == input_data
        assert round_obj.output_data == output_data
