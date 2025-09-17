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
    async def list_by_scope(
        self,
        scope_type: str,
        scope_id: str,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ConversationSession]:
        """List sessions for the given scope with optional filtering."""
        pass

    @abstractmethod
    async def create(
        self,
        scope_type: str,
        scope_id: str,
        status: str | SessionStatus = SessionStatus.ACTIVE,
        # stage and state parameters removed - moved to Genesis tables
        version: int = 0,
    ) -> ConversationSession:
        """Create a new conversation session."""
        pass

    @abstractmethod
    async def update(
        self,
        session_id: UUID,
        status: str | None = None,
        # stage and state parameters removed - moved to Genesis tables
        version: int | None = None,
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

    async def list_by_scope(
        self,
        scope_type: str,
        scope_id: str,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ConversationSession]:
        """List sessions for the given scope with optional filtering."""
        query = select(ConversationSession).where(
            and_(
                ConversationSession.scope_type == scope_type,
                ConversationSession.scope_id == scope_id,
            )
        )

        # Add status filter if provided
        if status is not None:
            query = query.where(ConversationSession.status == status)

        # Add pagination
        query = query.offset(offset).limit(limit)

        # Order by creation time, newest first
        query = query.order_by(ConversationSession.created_at.desc())

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def create(
        self,
        scope_type: str,
        scope_id: str,
        status: str | SessionStatus = SessionStatus.ACTIVE,
        # stage and state parameters removed - moved to Genesis tables
        version: int = 0,  # Changed default to 0 to match model default
    ) -> ConversationSession:
        """Create a new conversation session."""
        # Handle enum conversion
        status_value = status.value if isinstance(status, SessionStatus) else status

        session = ConversationSession(
            scope_type=scope_type,
            scope_id=scope_id,
            status=status_value,
            # stage and state fields removed
            version=version,
        )

        self.db.add(session)
        await self.db.flush()  # Flush to get generated ID
        await self.db.refresh(session)

        return session

    async def update(
        self,
        session_id: UUID,
        status: str | SessionStatus | None = None,
        # stage and state parameters removed - moved to Genesis tables
        version: int | None = None,  # Added version parameter for test compatibility
        expected_version: int | None = None,  # Keep for backward compatibility
    ) -> ConversationSession | None:
        """Update a conversation session with optimistic concurrency control."""
        # Handle both parameter names for backward compatibility
        version_to_check = version or expected_version

        # Handle enum conversion
        if isinstance(status, SessionStatus):
            status_value = status.value
        elif status is not None:
            status_value = status
        else:
            status_value = None

        # Build update values, only including non-None values
        update_values: dict[str, Any] = {}

        if status_value is not None:
            update_values["status"] = status_value
        # stage and state updates removed

        # Build where conditions
        conditions = [ConversationSession.id == session_id]
        if version_to_check is not None:
            conditions.append(ConversationSession.version == version_to_check)

        # Execute update with version check
        result = await self.db.execute(
            sql_update(ConversationSession)
            .where(and_(*conditions))
            .values(version=ConversationSession.version + 1, **update_values)
            .returning(ConversationSession)
        )

        updated_session = result.scalar_one_or_none()

        # Return None to indicate failure - let the service handle the error
        return updated_session

    async def delete(self, session_id: UUID) -> bool:
        """Delete a conversation session."""
        session = await self.find_by_id(session_id)
        if not session:
            return False

        await self.db.delete(session)
        return True
