"""Service for Genesis flow operations."""

import logging
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.common.repositories.genesis import GenesisFlowRepository, SqlAlchemyGenesisFlowRepository
from src.models.genesis_flows import GenesisFlow
from src.schemas.enums import GenesisStage, GenesisStatus

logger = logging.getLogger(__name__)


class GenesisFlowService:
    """Service for Genesis flow operations."""

    def __init__(self, repository: GenesisFlowRepository | None = None) -> None:
        self._repository = repository

    def _get_repository(self, db: AsyncSession) -> GenesisFlowRepository:
        """Get repository instance."""
        if self._repository:
            return self._repository
        return SqlAlchemyGenesisFlowRepository(db)

    async def ensure_flow(
        self,
        db: AsyncSession,
        novel_id: UUID,
        status: GenesisStatus = GenesisStatus.IN_PROGRESS,
        current_stage: GenesisStage | None = None,
    ) -> GenesisFlow:
        """
        Ensure a Genesis flow exists for the given novel.

        Creates a new flow if none exists, otherwise returns the existing flow.

        Args:
            db: Database session
            novel_id: Novel ID
            status: Initial status for new flows
            current_stage: Initial stage for new flows

        Returns:
            The existing or newly created Genesis flow
        """
        repo = self._get_repository(db)

        # Check if flow already exists
        existing_flow = await repo.find_by_novel_id(novel_id)
        if existing_flow:
            return existing_flow

        # Create new flow
        logger.info(f"Creating new Genesis flow for novel {novel_id}")
        new_flow = await repo.create(
            novel_id=novel_id,
            status=status,
            current_stage=current_stage,
        )

        await db.commit()
        return new_flow

    async def get_flow(self, db: AsyncSession, flow_id: UUID) -> GenesisFlow | None:
        """Get a Genesis flow by ID."""
        repo = self._get_repository(db)
        return await repo.find_by_id(flow_id)

    async def get_flow_by_novel(self, db: AsyncSession, novel_id: UUID) -> GenesisFlow | None:
        """Get a Genesis flow by novel ID."""
        repo = self._get_repository(db)
        return await repo.find_by_novel_id(novel_id)

    async def advance_stage(
        self,
        db: AsyncSession,
        flow_id: UUID,
        next_stage: GenesisStage,
        expected_version: int | None = None,
    ) -> GenesisFlow | None:
        """
        Advance a Genesis flow to the next stage.

        Args:
            db: Database session
            flow_id: Flow ID
            next_stage: The stage to advance to
            expected_version: Expected version for optimistic locking

        Returns:
            Updated flow if successful, None if version conflict or not found
        """
        repo = self._get_repository(db)

        logger.info(f"Advancing Genesis flow {flow_id} to stage {next_stage}")
        updated_flow = await repo.update(
            flow_id=flow_id,
            current_stage=next_stage,
            expected_version=expected_version,
        )

        if updated_flow:
            await db.commit()
            logger.info(f"Successfully advanced flow {flow_id} to stage {next_stage}")
        else:
            logger.warning(f"Failed to advance flow {flow_id}: version conflict or not found")

        return updated_flow

    async def complete_flow(
        self,
        db: AsyncSession,
        flow_id: UUID,
        expected_version: int | None = None,
    ) -> GenesisFlow | None:
        """
        Mark a Genesis flow as completed.

        Args:
            db: Database session
            flow_id: Flow ID
            expected_version: Expected version for optimistic locking

        Returns:
            Updated flow if successful, None if version conflict or not found
        """
        repo = self._get_repository(db)

        logger.info(f"Completing Genesis flow {flow_id}")
        updated_flow = await repo.update(
            flow_id=flow_id,
            status=GenesisStatus.COMPLETED,
            current_stage=GenesisStage.FINISHED,
            expected_version=expected_version,
        )

        if updated_flow:
            await db.commit()
            logger.info(f"Successfully completed flow {flow_id}")
        else:
            logger.warning(f"Failed to complete flow {flow_id}: version conflict or not found")

        return updated_flow

    async def update_flow_state(
        self,
        db: AsyncSession,
        flow_id: UUID,
        state: dict[str, Any],
        expected_version: int | None = None,
    ) -> GenesisFlow | None:
        """
        Update the global state of a Genesis flow.

        Args:
            db: Database session
            flow_id: Flow ID
            state: New state data
            expected_version: Expected version for optimistic locking

        Returns:
            Updated flow if successful, None if version conflict or not found
        """
        repo = self._get_repository(db)

        logger.info(f"Updating state for Genesis flow {flow_id}")
        updated_flow = await repo.update(
            flow_id=flow_id,
            state=state,
            expected_version=expected_version,
        )

        if updated_flow:
            await db.commit()
            logger.info(f"Successfully updated state for flow {flow_id}")
        else:
            logger.warning(f"Failed to update state for flow {flow_id}: version conflict or not found")

        return updated_flow

    async def list_flows_by_status(
        self,
        db: AsyncSession,
        status: GenesisStatus,
        limit: int = 50,
        offset: int = 0,
    ) -> list[GenesisFlow]:
        """List Genesis flows by status."""
        repo = self._get_repository(db)
        return await repo.list_by_status(status, limit=limit, offset=offset)

    async def delete_flow(self, db: AsyncSession, flow_id: UUID) -> bool:
        """
        Delete a Genesis flow.

        Args:
            db: Database session
            flow_id: Flow ID

        Returns:
            True if deleted, False if not found
        """
        repo = self._get_repository(db)

        logger.info(f"Deleting Genesis flow {flow_id}")
        deleted = await repo.delete(flow_id)

        if deleted:
            await db.commit()
            logger.info(f"Successfully deleted flow {flow_id}")
        else:
            logger.warning(f"Failed to delete flow {flow_id}: not found")

        return deleted