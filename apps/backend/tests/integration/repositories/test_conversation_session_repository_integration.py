"""Integration tests for ConversationSessionRepository with real database."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from src.common.repositories.conversation.session_repository import (
    SqlAlchemyConversationSessionRepository,
)
from src.models.conversation import ConversationSession
from src.schemas.novel.dialogue import SessionStatus


@pytest.mark.integration
class TestConversationSessionRepositoryIntegration:
    """Integration tests for SqlAlchemyConversationSessionRepository with real database."""

    async def test_create_and_persist_session(self, postgres_test_session: AsyncSession):
        """Test session creation and persistence to real database."""
        # Arrange
        repository = SqlAlchemyConversationSessionRepository(postgres_test_session)
        scope_type = "genesis"
        scope_id = str(uuid4())

        # Act
        session = await repository.create(
            scope_type=scope_type,
            scope_id=scope_id,
            status=SessionStatus.ACTIVE,
            state={"test": "integration"},
        )

        # Commit to database
        await postgres_test_session.commit()

        # Verify persistence by creating new session and querying
        new_session = AsyncSession(postgres_test_session.bind)
        found_session = await new_session.get(ConversationSession, session.id)
        await new_session.close()

        # Assert
        assert found_session is not None
        assert found_session.scope_type == scope_type
        assert found_session.scope_id == scope_id
        assert found_session.status == SessionStatus.ACTIVE.value
        assert found_session.state == {"test": "integration"}
        assert found_session.version == 1

    async def test_unique_constraint_active_session_per_scope(self, postgres_test_session: AsyncSession):
        """Test unique constraint for active sessions per scope."""
        # Arrange
        repository = SqlAlchemyConversationSessionRepository(postgres_test_session)
        scope_type = "genesis"
        scope_id = str(uuid4())

        # Create first active session
        await repository.create(
            scope_type=scope_type,
            scope_id=scope_id,
            status=SessionStatus.ACTIVE,
        )
        await postgres_test_session.commit()

        # Act & Assert
        with pytest.raises(IntegrityError):
            await repository.create(
                scope_type=scope_type,
                scope_id=scope_id,
                status=SessionStatus.ACTIVE,
            )
            await postgres_test_session.commit()

    async def test_multiple_inactive_sessions_allowed(self, postgres_test_session: AsyncSession):
        """Test that multiple inactive sessions are allowed for same scope."""
        # Arrange
        repository = SqlAlchemyConversationSessionRepository(postgres_test_session)
        scope_type = "genesis"
        scope_id = str(uuid4())

        # Act - Create multiple inactive sessions
        session1 = await repository.create(
            scope_type=scope_type,
            scope_id=scope_id,
            status=SessionStatus.COMPLETED,
        )
        await postgres_test_session.commit()

        session2 = await repository.create(
            scope_type=scope_type,
            scope_id=scope_id,
            status=SessionStatus.FAILED,
        )
        await postgres_test_session.commit()

        # Assert
        assert session1.id != session2.id
        assert session1.status == SessionStatus.COMPLETED.value
        assert session2.status == SessionStatus.FAILED.value

    async def test_update_with_version_control(self, postgres_test_session: AsyncSession):
        """Test optimistic locking with version control in real database."""
        # Arrange
        repository = SqlAlchemyConversationSessionRepository(postgres_test_session)
        session = await repository.create(
            scope_type="genesis",
            scope_id=str(uuid4()),
            status=SessionStatus.ACTIVE,
        )
        await postgres_test_session.commit()
        original_version = session.version

        # Act
        updated_session = await repository.update(
            session_id=session.id,
            version=original_version,
            status=SessionStatus.COMPLETED,
            state={"updated": True},
        )
        await postgres_test_session.commit()

        # Verify in fresh session
        new_session = AsyncSession(postgres_test_session.bind)
        found_session = await new_session.get(ConversationSession, session.id)
        await new_session.close()

        # Assert
        assert updated_session.version == original_version + 1
        assert found_session.version == original_version + 1
        assert found_session.status == SessionStatus.COMPLETED.value
        assert found_session.state == {"updated": True}

    async def test_concurrent_update_version_conflict(self, postgres_test_session: AsyncSession):
        """Test version conflict detection in concurrent updates."""
        # Arrange
        repository = SqlAlchemyConversationSessionRepository(postgres_test_session)
        session = await repository.create(
            scope_type="genesis",
            scope_id=str(uuid4()),
            status=SessionStatus.ACTIVE,
        )
        await postgres_test_session.commit()

        # First update
        await repository.update(
            session_id=session.id,
            version=session.version,
            status=SessionStatus.PROCESSING,
        )
        await postgres_test_session.commit()

        # Act & Assert - Second update with stale version
        with pytest.raises(ValueError, match="Version conflict"):
            await repository.update(
                session_id=session.id,
                version=session.version,  # Stale version
                status=SessionStatus.COMPLETED,
            )

    async def test_find_active_by_scope_with_database_query(self, postgres_test_session: AsyncSession):
        """Test finding active session by scope with real database query."""
        # Arrange
        repository = SqlAlchemyConversationSessionRepository(postgres_test_session)
        scope_type = "genesis"
        scope_id = str(uuid4())

        # Create inactive session first
        await repository.create(
            scope_type=scope_type,
            scope_id=scope_id,
            status=SessionStatus.COMPLETED,
        )

        # Create active session
        active_session = await repository.create(
            scope_type=scope_type,
            scope_id=scope_id,
            status=SessionStatus.ACTIVE,
        )
        await postgres_test_session.commit()

        # Act
        found_session = await repository.find_active_by_scope(scope_type, scope_id)

        # Assert
        assert found_session is not None
        assert found_session.id == active_session.id
        assert found_session.status == SessionStatus.ACTIVE.value

    async def test_delete_cascade_behavior(self, postgres_test_session: AsyncSession):
        """Test delete operation and cascade behavior."""
        # Arrange
        repository = SqlAlchemyConversationSessionRepository(postgres_test_session)
        session = await repository.create(
            scope_type="genesis",
            scope_id=str(uuid4()),
            status=SessionStatus.ACTIVE,
        )
        await postgres_test_session.commit()
        session_id = session.id

        # Act
        result = await repository.delete(session_id)
        await postgres_test_session.commit()

        # Verify deletion in fresh session
        new_session = AsyncSession(postgres_test_session.bind)
        found_session = await new_session.get(ConversationSession, session_id)
        await new_session.close()

        # Assert
        assert result is True
        assert found_session is None

    async def test_database_constraints_and_indexes(self, postgres_test_session: AsyncSession):
        """Test database constraints and index performance."""
        # Arrange
        repository = SqlAlchemyConversationSessionRepository(postgres_test_session)

        # Test scope_type and scope_id constraints
        scope_type = "genesis"
        scope_id = str(uuid4())

        # Act - Create multiple sessions quickly to test indexes
        sessions = []
        for i in range(10):
            if i == 0:
                # One active session
                status = SessionStatus.ACTIVE
            else:
                # Rest inactive
                status = SessionStatus.COMPLETED

            session = await repository.create(
                scope_type=scope_type,
                scope_id=f"{scope_id}_{i}",
                status=status,
                state={"batch": i},
            )
            sessions.append(session)

        await postgres_test_session.commit()

        # Test query performance with find_active_by_scope
        found_session = await repository.find_active_by_scope(scope_type, f"{scope_id}_0")

        # Assert
        assert found_session is not None
        assert found_session.state["batch"] == 0
        assert len(sessions) == 10

    async def test_timestamp_consistency(self, postgres_test_session: AsyncSession):
        """Test timestamp consistency and timezone handling."""
        # Arrange
        repository = SqlAlchemyConversationSessionRepository(postgres_test_session)
        before_creation = datetime.now(UTC)

        # Act
        session = await repository.create(
            scope_type="genesis",
            scope_id=str(uuid4()),
            status=SessionStatus.ACTIVE,
        )
        await postgres_test_session.commit()

        after_creation = datetime.now(UTC)

        # Verify persistence of timestamps
        new_session = AsyncSession(postgres_test_session.bind)
        found_session = await new_session.get(ConversationSession, session.id)
        await new_session.close()

        # Assert
        assert before_creation <= found_session.created_at <= after_creation
        assert before_creation <= found_session.updated_at <= after_creation
        assert found_session.created_at.tzinfo is not None  # Timezone aware
        assert found_session.updated_at.tzinfo is not None  # Timezone aware

    async def test_transaction_rollback_behavior(self, postgres_test_session: AsyncSession):
        """Test transaction rollback behavior."""
        # Arrange
        repository = SqlAlchemyConversationSessionRepository(postgres_test_session)
        scope_id = str(uuid4())

        try:
            # Create session
            session = await repository.create(
                scope_type="genesis",
                scope_id=scope_id,
                status=SessionStatus.ACTIVE,
            )

            # Force an error by violating unique constraint
            await repository.create(
                scope_type="genesis",
                scope_id=scope_id,
                status=SessionStatus.ACTIVE,
            )

            await postgres_test_session.commit()

        except IntegrityError:
            await postgres_test_session.rollback()

        # Verify rollback - session should not exist
        found_session = await repository.find_active_by_scope("genesis", scope_id)

        # Assert
        assert found_session is None
