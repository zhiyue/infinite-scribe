"""Repository for Genesis flow data access."""

from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy import update as sql_update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.genesis_flows import GenesisFlow
from src.schemas.enums import GenesisStage, GenesisStatus


class GenesisFlowRepository(ABC):
    """Abstract repository interface for Genesis flows."""

    @abstractmethod
    async def find_by_id(self, flow_id: UUID) -> GenesisFlow | None:
        """Find a Genesis flow by ID."""
        pass

    @abstractmethod
    async def find_by_novel_id(self, novel_id: UUID) -> GenesisFlow | None:
        """Find a Genesis flow by novel ID."""
        pass

    @abstractmethod
    async def list_by_status(
        self,
        status: GenesisStatus,
        limit: int = 50,
        offset: int = 0,
    ) -> list[GenesisFlow]:
        """List flows by status with pagination."""
        pass

    @abstractmethod
    async def create(
        self,
        novel_id: UUID,
        status: GenesisStatus = GenesisStatus.IN_PROGRESS,
        current_stage: GenesisStage | None = None,
        state: dict[str, Any] | None = None,
        version: int = 1,
    ) -> GenesisFlow:
        """Create a new Genesis flow."""
        pass

    @abstractmethod
    async def update(
        self,
        flow_id: UUID,
        status: GenesisStatus | None = None,
        current_stage: GenesisStage | None = None,
        state: dict[str, Any] | None = None,
        expected_version: int | None = None,
    ) -> GenesisFlow | None:
        """
        Update a Genesis flow with optimistic concurrency control.

        Returns:
            Updated flow if successful, None if version conflict or not found
        """
        pass

    @abstractmethod
    async def delete(self, flow_id: UUID) -> bool:
        """
        Delete a Genesis flow.

        Returns:
            True if deleted, False if not found
        """
        pass


class SqlAlchemyGenesisFlowRepository(GenesisFlowRepository):
    """SQLAlchemy implementation of GenesisFlowRepository."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def find_by_id(self, flow_id: UUID) -> GenesisFlow | None:
        """Find a Genesis flow by ID."""
        return await self.db.scalar(
            select(GenesisFlow).options(selectinload(GenesisFlow.stage_records)).where(GenesisFlow.id == flow_id)
        )

    async def find_by_novel_id(self, novel_id: UUID) -> GenesisFlow | None:
        """Find a Genesis flow by novel ID."""
        return await self.db.scalar(
            select(GenesisFlow).options(selectinload(GenesisFlow.stage_records)).where(GenesisFlow.novel_id == novel_id)
        )

    async def list_by_status(
        self,
        status: GenesisStatus,
        limit: int = 50,
        offset: int = 0,
    ) -> list[GenesisFlow]:
        """List flows by status with pagination."""
        query = (
            select(GenesisFlow)
            .options(selectinload(GenesisFlow.stage_records))
            .where(GenesisFlow.status == status)
            .order_by(GenesisFlow.created_at.desc())
            .offset(offset)
            .limit(limit)
        )

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def create(
        self,
        novel_id: UUID,
        status: GenesisStatus = GenesisStatus.IN_PROGRESS,
        current_stage: GenesisStage | None = None,
        state: dict[str, Any] | None = None,
        version: int = 1,
    ) -> GenesisFlow:
        """Create a new Genesis flow."""
        flow = GenesisFlow(
            novel_id=novel_id,
            status=status,
            current_stage=current_stage,
            state=state or {},
            version=version,
        )

        self.db.add(flow)
        await self.db.flush()  # Flush to get generated ID
        await self.db.refresh(flow)

        return flow

    async def update(
        self,
        flow_id: UUID,
        status: GenesisStatus | None = None,
        current_stage: GenesisStage | None = None,
        state: dict[str, Any] | None = None,
        expected_version: int | None = None,
    ) -> GenesisFlow | None:
        """Update a Genesis flow with optimistic concurrency control."""
        # Build update values, only including non-None values
        update_values: dict[str, Any] = {}

        if status is not None:
            update_values["status"] = status
        if current_stage is not None:
            update_values["current_stage"] = current_stage
        if state is not None:
            update_values["state"] = state

        # Build where conditions
        conditions = [GenesisFlow.id == flow_id]
        if expected_version is not None:
            conditions.append(GenesisFlow.version == expected_version)

        # Execute update with version check
        result = await self.db.execute(
            sql_update(GenesisFlow)
            .where(and_(*conditions))
            .values(version=GenesisFlow.version + 1, **update_values)
            .returning(GenesisFlow)
        )

        updated_flow = result.scalar_one_or_none()

        if updated_flow:
            # Refresh to load relationships
            await self.db.refresh(updated_flow, ["stage_records"])

        return updated_flow

    async def delete(self, flow_id: UUID) -> bool:
        """Delete a Genesis flow."""
        flow = await self.find_by_id(flow_id)
        if not flow:
            return False

        await self.db.delete(flow)
        return True
