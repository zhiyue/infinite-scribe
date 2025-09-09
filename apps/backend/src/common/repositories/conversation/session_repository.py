"""Repository for conversation session data access."""

from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy import update as sql_update
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.conversation import ConversationSession
from src.schemas.novel.dialogue import SessionStatus


class ConversationSessionRepository(ABC):
    """Abstract repository interface for conversation sessions."""

    @abstractmethod
    async def find_by_id(self, session_id: UUID) -> ConversationSession | None:
        """Find a conversation session by ID."""
        pass

    @abstractmethod
    async def find_active_by_scope(self, scope_type: str, scope_id: str) -> ConversationSession | None:
        """Find an active session for the given scope."""
        pass

    @abstractmethod
    async def create(
        self,
        scope_type: str,
        scope_id: str,
        status: str = SessionStatus.ACTIVE.value,
        stage: str | None = None,
        state: dict[str, Any] | None = None,
        version: int = 1,
    ) -> ConversationSession:
        """Create a new conversation session."""
        pass

    @abstractmethod
    async def update(
        self,
        session_id: UUID,
        status: str | None = None,
        stage: str | None = None,
        state: dict[str, Any] | None = None,
        expected_version: int | None = None,
    ) -> ConversationSession | None:
        """
        Update a conversation session with optimistic concurrency control.

        Returns:
            Updated session if successful, None if version conflict or not found
        """
        pass

    @abstractmethod
    async def delete(self, session_id: UUID) -> bool:
        """
        Delete a conversation session.

        Returns:
            True if deleted, False if not found
        """
        pass


class SqlAlchemyConversationSessionRepository(ConversationSessionRepository):
    """SQLAlchemy implementation of ConversationSessionRepository."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def find_by_id(self, session_id: UUID) -> ConversationSession | None:
        """Find a conversation session by ID."""
        return await self.db.scalar(select(ConversationSession).where(ConversationSession.id == session_id))

    async def find_active_by_scope(self, scope_type: str, scope_id: str) -> ConversationSession | None:
        """Find an active session for the given scope."""
        return await self.db.scalar(
            select(ConversationSession).where(
                and_(
                    ConversationSession.scope_type == scope_type,
                    ConversationSession.scope_id == scope_id,
                    ConversationSession.status == SessionStatus.ACTIVE.value,
                )
            )
        )

    async def create(
        self,
        scope_type: str,
        scope_id: str,
        status: str = SessionStatus.ACTIVE.value,
        stage: str | None = None,
        state: dict[str, Any] | None = None,
        version: int = 1,
    ) -> ConversationSession:
        """Create a new conversation session."""
        session = ConversationSession(
            scope_type=scope_type,
            scope_id=scope_id,
            status=status,
            stage=stage,
            state=state or {},
            version=version,
        )

        self.db.add(session)
        await self.db.flush()  # Flush to get generated ID
        await self.db.refresh(session)

        return session

    async def update(
        self,
        session_id: UUID,
        status: str | None = None,
        stage: str | None = None,
        state: dict[str, Any] | None = None,
        expected_version: int | None = None,
    ) -> ConversationSession | None:
        """Update a conversation session with optimistic concurrency control."""
        # Build update values, only including non-None values
        update_values = {"version": ConversationSession.version + 1}

        if status is not None:
            update_values["status"] = status
        if stage is not None:
            update_values["stage"] = stage
        if state is not None:
            update_values["state"] = state

        # Build where conditions
        conditions = [ConversationSession.id == session_id]
        if expected_version is not None:
            conditions.append(ConversationSession.version == expected_version)

        # Execute update with version check
        result = await self.db.execute(
            sql_update(ConversationSession)
            .where(and_(*conditions))
            .values(**update_values)
            .returning(ConversationSession)
        )

        return result.scalar_one_or_none()

    async def delete(self, session_id: UUID) -> bool:
        """Delete a conversation session."""
        session = await self.find_by_id(session_id)
        if not session:
            return False

        await self.db.delete(session)
        return True
