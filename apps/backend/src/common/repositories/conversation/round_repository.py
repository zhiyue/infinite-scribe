"""Repository for conversation round data access."""

from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID

from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.conversation import ConversationRound
from src.schemas.novel.dialogue import DialogueRole


class ConversationRoundRepository(ABC):
    """Abstract repository interface for conversation rounds."""

    @abstractmethod
    async def find_by_session_and_path(self, session_id: UUID, round_path: str) -> ConversationRound | None:
        """Find a conversation round by session ID and round path."""
        pass

    @abstractmethod
    async def find_by_correlation_id(self, session_id: UUID, correlation_id: UUID) -> ConversationRound | None:
        """Find a conversation round by correlation ID within a session."""
        pass

    @abstractmethod
    async def list_by_session(
        self,
        session_id: UUID,
        after: str | None = None,
        limit: int = 50,
        order: str = "asc",
        role: DialogueRole | None = None,
    ) -> list[ConversationRound]:
        """List conversation rounds for a session with filtering and pagination."""
        pass

    @abstractmethod
    async def count_by_session(self, session_id: UUID) -> int:
        """Count the total number of rounds in a session."""
        pass

    @abstractmethod
    async def create(
        self,
        session_id: UUID,
        round_path: str,
        role: str | DialogueRole,
        input: dict[str, Any] | None = None,
        output: dict[str, Any] | None = None,
        model: str | None = None,
        correlation_id: str | None = None,
    ) -> ConversationRound:
        """Create a new conversation round."""
        pass


class SqlAlchemyConversationRoundRepository(ConversationRoundRepository):
    """SQLAlchemy implementation of ConversationRoundRepository."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def find_by_session_and_path(self, session_id: UUID, round_path: str) -> ConversationRound | None:
        """Find a conversation round by session ID and round path."""
        return await self.db.scalar(
            select(ConversationRound).where(
                and_(
                    ConversationRound.session_id == session_id,
                    ConversationRound.round_path == round_path,
                )
            )
        )

    async def find_by_correlation_id(self, session_id: UUID, correlation_id: UUID) -> ConversationRound | None:
        """Find a conversation round by correlation ID within a session."""
        return await self.db.scalar(
            select(ConversationRound).where(
                and_(
                    ConversationRound.session_id == session_id,
                    ConversationRound.correlation_id == str(correlation_id),
                )
            )
        )

    async def list_by_session(
        self,
        session_id: UUID,
        after: str | None = None,
        limit: int = 50,
        order: str = "asc",
        role: DialogueRole | None = None,
    ) -> list[ConversationRound]:
        """List conversation rounds for a session with filtering and pagination."""
        query = select(ConversationRound).where(ConversationRound.session_id == session_id)

        # Add role filter if specified
        if role is not None:
            query = query.where(ConversationRound.role == role.value)

        # Add pagination (after cursor)
        if after:
            if order == "desc":
                query = query.where(ConversationRound.round_path < after)
            else:
                query = query.where(ConversationRound.round_path > after)

        # Add ordering
        if order == "desc":
            query = query.order_by(desc(ConversationRound.round_path))
        else:
            query = query.order_by(ConversationRound.round_path)

        # Add limit
        query = query.limit(limit)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def count_by_session(self, session_id: UUID) -> int:
        """Count the total number of rounds in a session."""
        result = await self.db.execute(select(func.count()).where(ConversationRound.session_id == session_id))
        return result.scalar() or 0

    async def create(
        self,
        session_id: UUID,
        round_path: str,
        role: str | DialogueRole,
        input: dict[str, Any] | None = None,  # Changed from input_data to input
        output: dict[str, Any] | None = None,  # Changed from output_data to output
        model: str | None = None,
        correlation_id: str | None = None,
    ) -> ConversationRound:
        """Create a new conversation round."""
        # Handle enum conversion
        role_value = role.value if isinstance(role, DialogueRole) else role

        round_obj = ConversationRound(
            session_id=session_id,
            round_path=round_path,
            role=role_value,
            input=input or {},
            output=output or {},
            model=model,
            correlation_id=correlation_id,
        )

        self.db.add(round_obj)
        # Note: ConversationRound uses composite primary key (session_id, round_path)
        # so no need to flush for ID generation, and refresh() can cause issues with composite keys
        await self.db.flush()  # Flush to ensure the object is persisted and constraints are checked

        return round_obj
