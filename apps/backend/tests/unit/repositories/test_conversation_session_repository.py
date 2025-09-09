"""Unit tests for ConversationSessionRepository."""

from datetime import datetime
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from src.common.repositories.conversation import SqlAlchemyConversationSessionRepository
from src.schemas.novel.dialogue import SessionStatus


@pytest.mark.asyncio
class TestSqlAlchemyConversationSessionRepository:
    """Test SqlAlchemyConversationSessionRepository implementation."""

    async def test_create_session_success(self, async_session: AsyncSession):
        """Test successful session creation."""
        # Arrange
        repository = SqlAlchemyConversationSessionRepository(async_session)
        scope_type = "genesis"
        scope_id = str(uuid4())
        stage = "worldbuilding"
        initial_state = {"key": "value"}

        # Act
        session = await repository.create(
            scope_type=scope_type,
            scope_id=scope_id,
            status=SessionStatus.ACTIVE.value,
            stage=stage,
            state=initial_state,
            version=1,
        )

        # Assert
        assert session is not None
        assert session.scope_type == scope_type
        assert session.scope_id == scope_id
        assert session.status == SessionStatus.ACTIVE.value
        assert session.stage == stage
        assert session.state == initial_state
        assert session.version == 1
        assert session.id is not None
        assert isinstance(session.created_at, datetime)
        assert isinstance(session.updated_at, datetime)

    async def test_find_by_id_existing(self, async_session: AsyncSession):
        """Test finding session by ID when it exists."""
        # Arrange
        repository = SqlAlchemyConversationSessionRepository(async_session)

        # Create a session first
        created_session = await repository.create(
            scope_type="genesis",
            scope_id=str(uuid4()),
            status=SessionStatus.ACTIVE.value,
        )

        # Act
        found_session = await repository.find_by_id(created_session.id)

        # Assert
        assert found_session is not None
        assert found_session.id == created_session.id
        assert found_session.scope_type == created_session.scope_type
        assert found_session.scope_id == created_session.scope_id
        assert found_session.status == created_session.status

    async def test_find_by_id_not_existing(self, async_session: AsyncSession):
        """Test finding session by ID when it doesn't exist."""
        # Arrange
        repository = SqlAlchemyConversationSessionRepository(async_session)
        non_existent_id = uuid4()

        # Act
        found_session = await repository.find_by_id(non_existent_id)

        # Assert
        assert found_session is None

    async def test_find_active_by_scope_existing(self, async_session: AsyncSession):
        """Test finding active session by scope when it exists."""
        # Arrange
        repository = SqlAlchemyConversationSessionRepository(async_session)
        scope_type = "genesis"
        scope_id = str(uuid4())

        # Create an active session
        created_session = await repository.create(
            scope_type=scope_type,
            scope_id=scope_id,
            status=SessionStatus.ACTIVE.value,
        )

        # Act
        found_session = await repository.find_active_by_scope(scope_type, scope_id)

        # Assert
        assert found_session is not None
        assert found_session.id == created_session.id
        assert found_session.scope_type == scope_type
        assert found_session.scope_id == scope_id
        assert found_session.status == SessionStatus.ACTIVE.value

    async def test_find_active_by_scope_inactive_exists(self, async_session: AsyncSession):
        """Test finding active session by scope when only inactive session exists."""
        # Arrange
        repository = SqlAlchemyConversationSessionRepository(async_session)
        scope_type = "genesis"
        scope_id = str(uuid4())

        # Create an inactive session
        await repository.create(
            scope_type=scope_type,
            scope_id=scope_id,
            status=SessionStatus.COMPLETED.value,
        )

        # Act
        found_session = await repository.find_active_by_scope(scope_type, scope_id)

        # Assert
        assert found_session is None

    async def test_find_active_by_scope_not_existing(self, async_session: AsyncSession):
        """Test finding active session by scope when it doesn't exist."""
        # Arrange
        repository = SqlAlchemyConversationSessionRepository(async_session)
        scope_type = "genesis"
        scope_id = str(uuid4())

        # Act
        found_session = await repository.find_active_by_scope(scope_type, scope_id)

        # Assert
        assert found_session is None

    async def test_update_session_success(self, async_session: AsyncSession):
        """Test successful session update."""
        # Arrange
        repository = SqlAlchemyConversationSessionRepository(async_session)

        # Create a session first
        created_session = await repository.create(
            scope_type="genesis",
            scope_id=str(uuid4()),
            status=SessionStatus.ACTIVE.value,
            stage="worldbuilding",
            state={"initial": True},
            version=1,
        )

        # Act
        updated_session = await repository.update(
            session_id=created_session.id,
            status=SessionStatus.COMPLETED.value,
            stage="finished",
            state={"completed": True},
            expected_version=1,
        )

        # Assert
        assert updated_session is not None
        assert updated_session.id == created_session.id
        assert updated_session.status == SessionStatus.COMPLETED.value
        assert updated_session.stage == "finished"
        assert updated_session.state == {"completed": True}
        assert updated_session.version == 2  # Version should be incremented
        assert updated_session.updated_at > created_session.updated_at

    async def test_update_session_version_conflict(self, async_session: AsyncSession):
        """Test session update with version conflict."""
        # Arrange
        repository = SqlAlchemyConversationSessionRepository(async_session)

        # Create a session first
        created_session = await repository.create(
            scope_type="genesis",
            scope_id=str(uuid4()),
            status=SessionStatus.ACTIVE.value,
            version=1,
        )

        # Act with wrong expected version
        updated_session = await repository.update(
            session_id=created_session.id,
            status=SessionStatus.COMPLETED.value,
            expected_version=999,  # Wrong version
        )

        # Assert
        assert updated_session is None

    async def test_update_session_not_found(self, async_session: AsyncSession):
        """Test updating session that doesn't exist."""
        # Arrange
        repository = SqlAlchemyConversationSessionRepository(async_session)
        non_existent_id = uuid4()

        # Act
        updated_session = await repository.update(
            session_id=non_existent_id,
            status=SessionStatus.COMPLETED.value,
        )

        # Assert
        assert updated_session is None

    async def test_update_session_partial_fields(self, async_session: AsyncSession):
        """Test updating only some fields."""
        # Arrange
        repository = SqlAlchemyConversationSessionRepository(async_session)

        # Create a session first
        created_session = await repository.create(
            scope_type="genesis",
            scope_id=str(uuid4()),
            status=SessionStatus.ACTIVE.value,
            stage="worldbuilding",
            state={"initial": True},
            version=1,
        )

        # Act - update only status
        updated_session = await repository.update(
            session_id=created_session.id,
            status=SessionStatus.COMPLETED.value,
        )

        # Assert
        assert updated_session is not None
        assert updated_session.status == SessionStatus.COMPLETED.value
        assert updated_session.stage == "worldbuilding"  # Should remain unchanged
        assert updated_session.state == {"initial": True}  # Should remain unchanged
        assert updated_session.version == 2

    async def test_delete_session_success(self, async_session: AsyncSession):
        """Test successful session deletion."""
        # Arrange
        repository = SqlAlchemyConversationSessionRepository(async_session)

        # Create a session first
        created_session = await repository.create(
            scope_type="genesis",
            scope_id=str(uuid4()),
            status=SessionStatus.ACTIVE.value,
        )

        # Act
        result = await repository.delete(created_session.id)

        # Assert
        assert result is True

        # Verify session is actually deleted
        found_session = await repository.find_by_id(created_session.id)
        assert found_session is None

    async def test_delete_session_not_found(self, async_session: AsyncSession):
        """Test deleting session that doesn't exist."""
        # Arrange
        repository = SqlAlchemyConversationSessionRepository(async_session)
        non_existent_id = uuid4()

        # Act
        result = await repository.delete(non_existent_id)

        # Assert
        assert result is False

    async def test_create_session_with_defaults(self, async_session: AsyncSession):
        """Test session creation with default values."""
        # Arrange
        repository = SqlAlchemyConversationSessionRepository(async_session)
        scope_type = "genesis"
        scope_id = str(uuid4())

        # Act
        session = await repository.create(
            scope_type=scope_type,
            scope_id=scope_id,
        )

        # Assert
        assert session is not None
        assert session.scope_type == scope_type
        assert session.scope_id == scope_id
        assert session.status == SessionStatus.ACTIVE.value  # Default
        assert session.stage is None
        assert session.state == {}  # Default empty dict
        assert session.version == 1  # Default
