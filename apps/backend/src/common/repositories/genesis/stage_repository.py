"""Repository for Genesis stage record data access."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy import update as sql_update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.genesis_flows import GenesisStageRecord
from src.schemas.enums import GenesisStage, StageStatus


class GenesisStageRepository(ABC):
    """Abstract repository interface for Genesis stage records."""

    @abstractmethod
    async def find_by_id(self, stage_id: UUID) -> GenesisStageRecord | None:
        """Find a Genesis stage record by ID."""
        pass

    @abstractmethod
    async def find_by_flow_and_stage(self, flow_id: UUID, stage: GenesisStage) -> GenesisStageRecord | None:
        """Find the latest stage record for a specific flow and stage."""
        pass

    @abstractmethod
    async def list_by_flow_id(
        self,
        flow_id: UUID,
        status: StageStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[GenesisStageRecord]:
        """List stage records by flow ID with optional status filtering."""
        pass

    @abstractmethod
    async def list_by_stage(
        self,
        stage: GenesisStage,
        status: StageStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[GenesisStageRecord]:
        """List stage records by stage type with optional status filtering."""
        pass

    @abstractmethod
    async def create(
        self,
        flow_id: UUID,
        stage: GenesisStage,
        status: StageStatus = StageStatus.RUNNING,
        config: dict[str, Any] | None = None,
        result: dict[str, Any] | None = None,
        iteration_count: int = 0,
        metrics: dict[str, Any] | None = None,
    ) -> GenesisStageRecord:
        """Create a new Genesis stage record."""
        pass

    @abstractmethod
    async def update(
        self,
        stage_id: UUID,
        status: StageStatus | None = None,
        config: dict[str, Any] | None = None,
        result: dict[str, Any] | None = None,
        iteration_count: int | None = None,
        metrics: dict[str, Any] | None = None,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
    ) -> GenesisStageRecord | None:
        """
        Update a Genesis stage record.

        Returns:
            Updated stage record if successful, None if not found
        """
        pass

    @abstractmethod
    async def delete(self, stage_id: UUID) -> bool:
        """
        Delete a Genesis stage record.

        Returns:
            True if deleted, False if not found
        """
        pass


class SqlAlchemyGenesisStageRepository(GenesisStageRepository):
    """SQLAlchemy implementation of GenesisStageRepository."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def find_by_id(self, stage_id: UUID) -> GenesisStageRecord | None:
        """Find a Genesis stage record by ID."""
        return await self.db.scalar(
            select(GenesisStageRecord)
            .options(selectinload(GenesisStageRecord.stage_sessions))
            .where(GenesisStageRecord.id == stage_id)
        )

    async def find_by_flow_and_stage(self, flow_id: UUID, stage: GenesisStage) -> GenesisStageRecord | None:
        """Find the latest stage record for a specific flow and stage."""
        return await self.db.scalar(
            select(GenesisStageRecord)
            .options(selectinload(GenesisStageRecord.stage_sessions))
            .where(
                and_(
                    GenesisStageRecord.flow_id == flow_id,
                    GenesisStageRecord.stage == stage,
                )
            )
            .order_by(GenesisStageRecord.created_at.desc())
        )

    async def list_by_flow_id(
        self,
        flow_id: UUID,
        status: StageStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[GenesisStageRecord]:
        """List stage records by flow ID with optional status filtering."""
        query = (
            select(GenesisStageRecord)
            .options(selectinload(GenesisStageRecord.stage_sessions))
            .where(GenesisStageRecord.flow_id == flow_id)
        )

        # Add status filter if provided
        if status is not None:
            query = query.where(GenesisStageRecord.status == status)

        # Add pagination and ordering
        query = query.order_by(GenesisStageRecord.created_at.desc()).offset(offset).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def list_by_stage(
        self,
        stage: GenesisStage,
        status: StageStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[GenesisStageRecord]:
        """List stage records by stage type with optional status filtering."""
        query = (
            select(GenesisStageRecord)
            .options(selectinload(GenesisStageRecord.stage_sessions))
            .where(GenesisStageRecord.stage == stage)
        )

        # Add status filter if provided
        if status is not None:
            query = query.where(GenesisStageRecord.status == status)

        # Add pagination and ordering
        query = query.order_by(GenesisStageRecord.created_at.desc()).offset(offset).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def create(
        self,
        flow_id: UUID,
        stage: GenesisStage,
        status: StageStatus = StageStatus.RUNNING,
        config: dict[str, Any] | None = None,
        result: dict[str, Any] | None = None,
        iteration_count: int = 0,
        metrics: dict[str, Any] | None = None,
    ) -> GenesisStageRecord:
        """Create a new Genesis stage record."""
        stage_record = GenesisStageRecord(
            flow_id=flow_id,
            stage=stage,
            status=status,
            config=config or {},
            result=result or {},
            iteration_count=iteration_count,
            metrics=metrics or {},
        )

        self.db.add(stage_record)
        await self.db.flush()  # Flush to get generated ID
        await self.db.refresh(stage_record)

        return stage_record

    async def update(
        self,
        stage_id: UUID,
        status: StageStatus | None = None,
        config: dict[str, Any] | None = None,
        result: dict[str, Any] | None = None,
        iteration_count: int | None = None,
        metrics: dict[str, Any] | None = None,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
    ) -> GenesisStageRecord | None:
        """Update a Genesis stage record."""
        # Build update values, only including non-None values
        update_values: dict[str, Any] = {}

        if status is not None:
            update_values["status"] = status
        if config is not None:
            update_values["config"] = config
        if result is not None:
            update_values["result"] = result
        if iteration_count is not None:
            update_values["iteration_count"] = iteration_count
        if metrics is not None:
            update_values["metrics"] = metrics
        if started_at is not None:
            update_values["started_at"] = started_at
        if completed_at is not None:
            update_values["completed_at"] = completed_at

        # Execute update
        update_result = await self.db.execute(
            sql_update(GenesisStageRecord)
            .where(GenesisStageRecord.id == stage_id)
            .values(**update_values)
            .returning(GenesisStageRecord)
        )

        updated_record = update_result.scalar_one_or_none()

        if updated_record:
            # Refresh to load relationships
            await self.db.refresh(updated_record, ["stage_sessions"])

        return updated_record

    async def delete(self, stage_id: UUID) -> bool:
        """Delete a Genesis stage record."""
        stage_record = await self.find_by_id(stage_id)
        if not stage_record:
            return False

        await self.db.delete(stage_record)
        return True
