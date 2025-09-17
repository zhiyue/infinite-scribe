"""Service for Genesis stage session association operations."""

import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.common.repositories.conversation import SqlAlchemyConversationSessionRepository
from src.common.repositories.genesis import (
    GenesisStageSessionRepository,
    SqlAlchemyGenesisStageSessionRepository,
)
from src.models.genesis_flows import GenesisStageSession
from src.schemas.enums import StageSessionStatus

logger = logging.getLogger(__name__)


class GenesisStageSessionService:
    """Service for Genesis stage session association operations."""

    def __init__(self, repository: GenesisStageSessionRepository | None = None) -> None:
        self._repository = repository

    def _get_repository(self, db: AsyncSession) -> GenesisStageSessionRepository:
        """Get repository instance."""
        if self._repository:
            return self._repository
        return SqlAlchemyGenesisStageSessionRepository(db)

    async def create_and_bind_session(
        self,
        db: AsyncSession,
        stage_id: UUID,
        novel_id: UUID,
        is_primary: bool = False,
        session_kind: str | None = None,
    ) -> tuple[UUID, GenesisStageSession]:
        """
        Create a new conversation session and bind it to a Genesis stage.

        Args:
            db: Database session
            stage_id: Stage record ID
            novel_id: Novel ID (for session scope validation)
            is_primary: Whether this should be the primary session for the stage
            session_kind: Session classification (e.g., user_interaction, review, etc.)

        Returns:
            Tuple of (session_id, stage_session_association)
        """
        # Create conversation session
        conversation_repo = SqlAlchemyConversationSessionRepository(db)
        conversation_session = await conversation_repo.create(
            scope_type="GENESIS",
            scope_id=str(novel_id),
            status="ACTIVE",
        )

        # Create stage-session association
        repo = self._get_repository(db)
        stage_session = await repo.create(
            stage_id=stage_id,
            session_id=conversation_session.id,
            status=StageSessionStatus.ACTIVE,
            is_primary=is_primary,
            session_kind=session_kind,
        )

        await db.commit()
        logger.info(
            f"Created and bound conversation session {conversation_session.id} to stage {stage_id}"
        )

        return conversation_session.id, stage_session

    async def bind_existing_session(
        self,
        db: AsyncSession,
        stage_id: UUID,
        session_id: UUID,
        novel_id: UUID,
        is_primary: bool = False,
        session_kind: str | None = None,
    ) -> GenesisStageSession | None:
        """
        Bind an existing conversation session to a Genesis stage.

        Args:
            db: Database session
            stage_id: Stage record ID
            session_id: Existing conversation session ID
            novel_id: Novel ID (for scope validation)
            is_primary: Whether this should be the primary session for the stage
            session_kind: Session classification

        Returns:
            The stage-session association if successful, None if validation fails
        """
        # Validate that the session exists and has correct scope
        conversation_repo = SqlAlchemyConversationSessionRepository(db)
        session = await conversation_repo.find_by_id(session_id)

        if not session:
            logger.warning(f"Session {session_id} not found for binding to stage {stage_id}")
            return None

        if session.scope_type != "GENESIS" or session.scope_id != str(novel_id):
            logger.warning(
                f"Session {session_id} has invalid scope ({session.scope_type}, {session.scope_id}) "
                f"for novel {novel_id}"
            )
            return None

        # Create stage-session association
        repo = self._get_repository(db)
        stage_session = await repo.create(
            stage_id=stage_id,
            session_id=session_id,
            status=StageSessionStatus.ACTIVE,
            is_primary=is_primary,
            session_kind=session_kind,
        )

        await db.commit()
        logger.info(f"Bound existing conversation session {session_id} to stage {stage_id}")

        return stage_session

    async def get_association(
        self, db: AsyncSession, association_id: UUID
    ) -> GenesisStageSession | None:
        """Get a stage-session association by ID."""
        repo = self._get_repository(db)
        return await repo.find_by_id(association_id)

    async def get_association_by_stage_and_session(
        self, db: AsyncSession, stage_id: UUID, session_id: UUID
    ) -> GenesisStageSession | None:
        """Get association by stage ID and session ID."""
        repo = self._get_repository(db)
        return await repo.find_by_stage_and_session(stage_id, session_id)

    async def list_stage_sessions(
        self,
        db: AsyncSession,
        stage_id: UUID,
        status: StageSessionStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[GenesisStageSession]:
        """List all sessions associated with a stage."""
        repo = self._get_repository(db)
        return await repo.list_by_stage_id(stage_id, status=status, limit=limit, offset=offset)

    async def list_session_stages(
        self,
        db: AsyncSession,
        session_id: UUID,
        status: StageSessionStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[GenesisStageSession]:
        """List all stages associated with a session."""
        repo = self._get_repository(db)
        return await repo.list_by_session_id(session_id, status=status, limit=limit, offset=offset)

    async def get_primary_session(
        self, db: AsyncSession, stage_id: UUID
    ) -> GenesisStageSession | None:
        """Get the primary session for a stage."""
        repo = self._get_repository(db)
        return await repo.find_primary_session_for_stage(stage_id)

    async def set_primary_session(
        self, db: AsyncSession, stage_id: UUID, session_id: UUID
    ) -> GenesisStageSession | None:
        """
        Set a session as primary for a stage.

        This will clear the primary flag from all other sessions for this stage.

        Args:
            db: Database session
            stage_id: Stage record ID
            session_id: Session ID to set as primary

        Returns:
            Updated primary association if successful, None if not found
        """
        repo = self._get_repository(db)

        logger.info(f"Setting session {session_id} as primary for stage {stage_id}")
        updated_association = await repo.set_primary_session(stage_id, session_id)

        if updated_association:
            await db.commit()
            logger.info(f"Successfully set session {session_id} as primary for stage {stage_id}")
        else:
            logger.warning(f"Failed to set primary session: stage {stage_id} or session {session_id} not found")

        return updated_association

    async def archive_session(
        self, db: AsyncSession, association_id: UUID
    ) -> GenesisStageSession | None:
        """
        Archive a stage-session association.

        Args:
            db: Database session
            association_id: Association ID

        Returns:
            Updated association if successful, None if not found
        """
        repo = self._get_repository(db)

        logger.info(f"Archiving stage-session association {association_id}")
        updated_association = await repo.update(
            association_id=association_id,
            status=StageSessionStatus.ARCHIVED,
        )

        if updated_association:
            await db.commit()
            logger.info(f"Successfully archived association {association_id}")
        else:
            logger.warning(f"Failed to archive association {association_id}: not found")

        return updated_association

    async def close_session(
        self, db: AsyncSession, association_id: UUID
    ) -> GenesisStageSession | None:
        """
        Close a stage-session association.

        Args:
            db: Database session
            association_id: Association ID

        Returns:
            Updated association if successful, None if not found
        """
        repo = self._get_repository(db)

        logger.info(f"Closing stage-session association {association_id}")
        updated_association = await repo.update(
            association_id=association_id,
            status=StageSessionStatus.CLOSED,
        )

        if updated_association:
            await db.commit()
            logger.info(f"Successfully closed association {association_id}")
        else:
            logger.warning(f"Failed to close association {association_id}: not found")

        return updated_association

    async def update_session_kind(
        self, db: AsyncSession, association_id: UUID, session_kind: str
    ) -> GenesisStageSession | None:
        """
        Update the session kind for an association.

        Args:
            db: Database session
            association_id: Association ID
            session_kind: New session kind

        Returns:
            Updated association if successful, None if not found
        """
        repo = self._get_repository(db)

        logger.info(f"Updating session kind for association {association_id} to {session_kind}")
        updated_association = await repo.update(
            association_id=association_id,
            session_kind=session_kind,
        )

        if updated_association:
            await db.commit()
            logger.info(f"Successfully updated session kind for association {association_id}")
        else:
            logger.warning(f"Failed to update session kind for association {association_id}: not found")

        return updated_association

    async def delete_association(self, db: AsyncSession, association_id: UUID) -> bool:
        """
        Delete a stage-session association.

        Args:
            db: Database session
            association_id: Association ID

        Returns:
            True if deleted, False if not found
        """
        repo = self._get_repository(db)

        logger.info(f"Deleting stage-session association {association_id}")
        deleted = await repo.delete(association_id)

        if deleted:
            await db.commit()
            logger.info(f"Successfully deleted association {association_id}")
        else:
            logger.warning(f"Failed to delete association {association_id}: not found")

        return deleted