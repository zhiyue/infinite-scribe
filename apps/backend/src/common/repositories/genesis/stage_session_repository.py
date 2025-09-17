"""Repository for Genesis stage session association data access."""

from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy import update as sql_update
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.genesis_flows import GenesisStageSession
from src.schemas.enums import StageSessionStatus


class GenesisStageSessionRepository(ABC):
    """Abstract repository interface for Genesis stage session associations."""

    @abstractmethod
    async def find_by_id(self, association_id: UUID) -> GenesisStageSession | None:
        """Find a stage session association by ID."""
        pass

    @abstractmethod
    async def find_by_stage_and_session(self, stage_id: UUID, session_id: UUID) -> GenesisStageSession | None:
        """Find association by stage ID and session ID."""
        pass

    @abstractmethod
    async def list_by_stage_id(
        self,
        stage_id: UUID,
        status: StageSessionStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[GenesisStageSession]:
        """List associations by stage ID with optional status filtering."""
        pass

    @abstractmethod
    async def list_by_session_id(
        self,
        session_id: UUID,
        status: StageSessionStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[GenesisStageSession]:
        """List associations by session ID with optional status filtering."""
        pass

    @abstractmethod
    async def find_primary_session_for_stage(self, stage_id: UUID) -> GenesisStageSession | None:
        """Find the primary session association for a stage."""
        pass

    @abstractmethod
    async def create(
        self,
        stage_id: UUID,
        session_id: UUID,
        status: StageSessionStatus = StageSessionStatus.ACTIVE,
        is_primary: bool = False,
        session_kind: str | None = None,
    ) -> GenesisStageSession:
        """Create a new stage session association."""
        pass

    @abstractmethod
    async def update(
        self,
        association_id: UUID,
        status: StageSessionStatus | None = None,
        is_primary: bool | None = None,
        session_kind: str | None = None,
    ) -> GenesisStageSession | None:
        """
        Update a stage session association.

        Returns:
            Updated association if successful, None if not found
        """
        pass

    @abstractmethod
    async def set_primary_session(self, stage_id: UUID, session_id: UUID) -> GenesisStageSession | None:
        """
        Set a session as primary for a stage, clearing other primary flags.

        Returns:
            Updated primary association if successful, None if not found
        """
        pass

    @abstractmethod
    async def delete(self, association_id: UUID) -> bool:
        """
        Delete a stage session association.

        Returns:
            True if deleted, False if not found
        """
        pass


class SqlAlchemyGenesisStageSessionRepository(GenesisStageSessionRepository):
    """SQLAlchemy implementation of GenesisStageSessionRepository."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def find_by_id(self, association_id: UUID) -> GenesisStageSession | None:
        """Find a stage session association by ID."""
        return await self.db.scalar(select(GenesisStageSession).where(GenesisStageSession.id == association_id))

    async def find_by_stage_and_session(self, stage_id: UUID, session_id: UUID) -> GenesisStageSession | None:
        """Find association by stage ID and session ID."""
        return await self.db.scalar(
            select(GenesisStageSession).where(
                and_(
                    GenesisStageSession.stage_id == stage_id,
                    GenesisStageSession.session_id == session_id,
                )
            )
        )

    async def list_by_stage_id(
        self,
        stage_id: UUID,
        status: StageSessionStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[GenesisStageSession]:
        """List associations by stage ID with optional status filtering."""
        query = select(GenesisStageSession).where(GenesisStageSession.stage_id == stage_id)

        # Add status filter if provided
        if status is not None:
            query = query.where(GenesisStageSession.status == status)

        # Add pagination and ordering
        query = query.order_by(GenesisStageSession.created_at.desc()).offset(offset).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def list_by_session_id(
        self,
        session_id: UUID,
        status: StageSessionStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[GenesisStageSession]:
        """List associations by session ID with optional status filtering."""
        query = select(GenesisStageSession).where(GenesisStageSession.session_id == session_id)

        # Add status filter if provided
        if status is not None:
            query = query.where(GenesisStageSession.status == status)

        # Add pagination and ordering
        query = query.order_by(GenesisStageSession.created_at.desc()).offset(offset).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def find_primary_session_for_stage(self, stage_id: UUID) -> GenesisStageSession | None:
        """Find the primary session association for a stage."""
        return await self.db.scalar(
            select(GenesisStageSession).where(
                and_(
                    GenesisStageSession.stage_id == stage_id,
                    GenesisStageSession.is_primary == True,
                    GenesisStageSession.status == StageSessionStatus.ACTIVE,
                )
            )
        )

    async def create(
        self,
        stage_id: UUID,
        session_id: UUID,
        status: StageSessionStatus = StageSessionStatus.ACTIVE,
        is_primary: bool = False,
        session_kind: str | None = None,
    ) -> GenesisStageSession:
        """Create a new stage session association."""
        association = GenesisStageSession(
            stage_id=stage_id,
            session_id=session_id,
            status=status,
            is_primary=is_primary,
            session_kind=session_kind,
        )

        self.db.add(association)
        await self.db.flush()  # Flush to get generated ID
        await self.db.refresh(association)

        return association

    async def update(
        self,
        association_id: UUID,
        status: StageSessionStatus | None = None,
        is_primary: bool | None = None,
        session_kind: str | None = None,
    ) -> GenesisStageSession | None:
        """Update a stage session association."""
        # Build update values, only including non-None values
        update_values: dict[str, Any] = {}

        if status is not None:
            update_values["status"] = status
        if is_primary is not None:
            update_values["is_primary"] = is_primary
        if session_kind is not None:
            update_values["session_kind"] = session_kind

        # Execute update
        result = await self.db.execute(
            sql_update(GenesisStageSession)
            .where(GenesisStageSession.id == association_id)
            .values(**update_values)
            .returning(GenesisStageSession)
        )

        return result.scalar_one_or_none()

    async def set_primary_session(self, stage_id: UUID, session_id: UUID) -> GenesisStageSession | None:
        """Set a session as primary for a stage, clearing other primary flags."""
        # First, clear all primary flags for this stage
        await self.db.execute(
            sql_update(GenesisStageSession).where(GenesisStageSession.stage_id == stage_id).values(is_primary=False)
        )

        # Then set the specified session as primary
        result = await self.db.execute(
            sql_update(GenesisStageSession)
            .where(
                and_(
                    GenesisStageSession.stage_id == stage_id,
                    GenesisStageSession.session_id == session_id,
                )
            )
            .values(is_primary=True)
            .returning(GenesisStageSession)
        )

        return result.scalar_one_or_none()

    async def delete(self, association_id: UUID) -> bool:
        """Delete a stage session association."""
        association = await self.find_by_id(association_id)
        if not association:
            return False

        await self.db.delete(association)
        return True
