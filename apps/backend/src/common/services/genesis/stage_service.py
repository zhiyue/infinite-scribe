"""Service for Genesis stage record operations."""

import logging
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.common.repositories.genesis import GenesisStageRepository, SqlAlchemyGenesisStageRepository
from src.models.genesis_flows import GenesisStageRecord
from src.schemas.enums import GenesisStage, StageStatus

logger = logging.getLogger(__name__)


class GenesisStageService:
    """Service for Genesis stage record operations."""

    def __init__(self, repository: GenesisStageRepository | None = None) -> None:
        self._repository = repository

    def _get_repository(self, db: AsyncSession) -> GenesisStageRepository:
        """Get repository instance."""
        if self._repository:
            return self._repository
        return SqlAlchemyGenesisStageRepository(db)

    async def create_stage(
        self,
        db: AsyncSession,
        flow_id: UUID,
        stage: GenesisStage,
        config: dict[str, Any] | None = None,
        iteration_count: int = 0,
    ) -> GenesisStageRecord:
        """
        Create a new Genesis stage record.

        Args:
            db: Database session
            flow_id: Genesis flow ID
            stage: Stage type
            config: Stage configuration
            iteration_count: Iteration count (for repeated stages)

        Returns:
            The newly created stage record
        """
        repo = self._get_repository(db)

        logger.info(f"Creating new stage {stage} for flow {flow_id}")
        stage_record = await repo.create(
            flow_id=flow_id,
            stage=stage,
            status=StageStatus.RUNNING,
            config=config or {},
            iteration_count=iteration_count,
        )

        await db.commit()
        logger.info(f"Successfully created stage record {stage_record.id}")
        return stage_record

    async def get_stage(self, db: AsyncSession, stage_id: UUID) -> GenesisStageRecord | None:
        """Get a Genesis stage record by ID."""
        repo = self._get_repository(db)
        return await repo.find_by_id(stage_id)

    async def get_stage_by_flow_and_stage(
        self, db: AsyncSession, flow_id: UUID, stage: GenesisStage
    ) -> GenesisStageRecord | None:
        """Get the latest stage record for a specific flow and stage."""
        repo = self._get_repository(db)
        return await repo.find_by_flow_and_stage(flow_id, stage)

    async def complete_stage(
        self,
        db: AsyncSession,
        stage_id: UUID,
        result: dict[str, Any] | None = None,
        metrics: dict[str, Any] | None = None,
    ) -> GenesisStageRecord | None:
        """
        Mark a Genesis stage as completed.

        Args:
            db: Database session
            stage_id: Stage record ID
            result: Stage result data
            metrics: Stage metrics (tokens, cost, latency, etc.)

        Returns:
            Updated stage record if successful, None if not found
        """
        repo = self._get_repository(db)

        logger.info(f"Completing Genesis stage {stage_id}")
        updated_stage = await repo.update(
            stage_id=stage_id,
            status=StageStatus.COMPLETED,
            result=result,
            metrics=metrics,
        )

        if updated_stage:
            await db.commit()
            logger.info(f"Successfully completed stage {stage_id}")
        else:
            logger.warning(f"Failed to complete stage {stage_id}: not found")

        return updated_stage

    async def fail_stage(
        self,
        db: AsyncSession,
        stage_id: UUID,
        error_info: dict[str, Any] | None = None,
    ) -> GenesisStageRecord | None:
        """
        Mark a Genesis stage as failed.

        Args:
            db: Database session
            stage_id: Stage record ID
            error_info: Error information to store in result

        Returns:
            Updated stage record if successful, None if not found
        """
        repo = self._get_repository(db)

        logger.info(f"Marking Genesis stage {stage_id} as failed")
        updated_stage = await repo.update(
            stage_id=stage_id,
            status=StageStatus.FAILED,
            result=error_info,
        )

        if updated_stage:
            await db.commit()
            logger.info(f"Successfully marked stage {stage_id} as failed")
        else:
            logger.warning(f"Failed to update stage {stage_id}: not found")

        return updated_stage

    async def update_stage_config(
        self,
        db: AsyncSession,
        stage_id: UUID,
        config: dict[str, Any],
    ) -> GenesisStageRecord | None:
        """
        Update the configuration of a Genesis stage.

        Args:
            db: Database session
            stage_id: Stage record ID
            config: New configuration data

        Returns:
            Updated stage record if successful, None if not found
        """
        repo = self._get_repository(db)

        logger.info(f"Updating config for Genesis stage {stage_id}")
        updated_stage = await repo.update(
            stage_id=stage_id,
            config=config,
        )

        if updated_stage:
            await db.commit()
            logger.info(f"Successfully updated config for stage {stage_id}")
        else:
            logger.warning(f"Failed to update config for stage {stage_id}: not found")

        return updated_stage

    async def increment_iteration(
        self,
        db: AsyncSession,
        stage_id: UUID,
    ) -> GenesisStageRecord | None:
        """
        Increment the iteration count for a Genesis stage.

        Args:
            db: Database session
            stage_id: Stage record ID

        Returns:
            Updated stage record if successful, None if not found
        """
        repo = self._get_repository(db)

        # First get the current stage to get its iteration count
        current_stage = await repo.find_by_id(stage_id)
        if not current_stage:
            logger.warning(f"Stage {stage_id} not found for iteration increment")
            return None

        new_iteration_count = current_stage.iteration_count + 1

        logger.info(f"Incrementing iteration count for Genesis stage {stage_id} to {new_iteration_count}")
        updated_stage = await repo.update(
            stage_id=stage_id,
            iteration_count=new_iteration_count,
        )

        if updated_stage:
            await db.commit()
            logger.info(f"Successfully incremented iteration for stage {stage_id}")
        else:
            logger.warning(f"Failed to increment iteration for stage {stage_id}")

        return updated_stage

    async def list_stages_by_flow(
        self,
        db: AsyncSession,
        flow_id: UUID,
        status: StageStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[GenesisStageRecord]:
        """List stage records for a Genesis flow."""
        repo = self._get_repository(db)
        return await repo.list_by_flow_id(flow_id, status=status, limit=limit, offset=offset)

    async def list_stages_by_type(
        self,
        db: AsyncSession,
        stage: GenesisStage,
        status: StageStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[GenesisStageRecord]:
        """List stage records by stage type."""
        repo = self._get_repository(db)
        return await repo.list_by_stage(stage, status=status, limit=limit, offset=offset)

    async def delete_stage(self, db: AsyncSession, stage_id: UUID) -> bool:
        """
        Delete a Genesis stage record.

        Args:
            db: Database session
            stage_id: Stage record ID

        Returns:
            True if deleted, False if not found
        """
        repo = self._get_repository(db)

        logger.info(f"Deleting Genesis stage {stage_id}")
        deleted = await repo.delete(stage_id)

        if deleted:
            await db.commit()
            logger.info(f"Successfully deleted stage {stage_id}")
        else:
            logger.warning(f"Failed to delete stage {stage_id}: not found")

        return deleted