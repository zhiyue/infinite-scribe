"""
Round creation service for conversation operations.

Handles round creation with domain events, idempotency, and atomic operations.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.repositories.conversation import ConversationRoundRepository, SqlAlchemyConversationRoundRepository
from src.common.services.conversation.conversation_access_control import ConversationAccessControl
from src.common.services.conversation.conversation_cache import ConversationCacheManager
from src.common.services.conversation.conversation_error_handler import ConversationErrorHandler
from src.common.services.conversation.conversation_event_handler import ConversationEventHandler
from src.common.services.conversation.conversation_serializers import ConversationSerializer
from src.db.sql.session import transactional
from src.models.conversation import ConversationRound, ConversationSession
from src.schemas.novel.dialogue import DialogueRole

logger = logging.getLogger(__name__)


class ConversationRoundCreationService:
    """Service for conversation round creation operations."""

    def __init__(
        self,
        cache: ConversationCacheManager | None = None,
        access_control: ConversationAccessControl | None = None,
        serializer: ConversationSerializer | None = None,
        event_handler: ConversationEventHandler | None = None,
        repository: ConversationRoundRepository | None = None,
        repository_factory: Callable[[AsyncSession], ConversationRoundRepository] | None = None,
    ) -> None:
        self.cache = cache or ConversationCacheManager()
        self.access_control = access_control or ConversationAccessControl()
        self.serializer = serializer or ConversationSerializer()
        self.event_handler = event_handler or ConversationEventHandler()

        # Repository factory pattern - prioritize factory > instance > default
        if repository_factory:
            self._repo_factory = repository_factory
        elif repository:
            self._repo_factory = lambda _: repository  # Convert instance to factory
        else:
            self._repo_factory = SqlAlchemyConversationRoundRepository

    async def create_round(
        self,
        db: AsyncSession,
        user_id: int,
        session_id: UUID,
        *,
        role: DialogueRole,
        input_data: dict[str, Any],
        model: str | None = None,
        correlation_id: str | None = None,
        parent_round_path: str | None = None,
    ) -> dict[str, Any]:
        """
        Create a new conversation round with domain events and idempotency.

        Args:
            db: Database session
            user_id: User ID for ownership verification
            session_id: Session ID
            role: Dialogue role for the round
            input_data: Input data for the round
            model: Model name (optional)
            correlation_id: Correlation ID for idempotency (optional)
            parent_round_path: Parent round path for branching (optional)

        Returns:
            Dict with success status and round or error details
        """
        try:
            # Verify session access
            access_result = await self.access_control.verify_session_access(db, user_id, session_id)
            if not access_result["success"]:
                return access_result

            session = access_result["session"]

            # Parse correlation UUID for domain event idempotency
            corr_uuid: UUID | None = None
            if correlation_id:
                try:
                    corr_uuid = UUID(str(correlation_id))
                except Exception:
                    corr_uuid = None

            # Atomic operation: round + domain_event + outbox
            created_round = await self._create_round_atomic(
                db, session, role, input_data, model, correlation_id, corr_uuid, parent_round_path
            )

            if not created_round:
                return ConversationErrorHandler.internal_error(
                    "Failed to create round", logger_instance=logger, context="Create round error"
                )

            # Serialize ORM object to dict at service boundary
            serialized_round = self.serializer.serialize_round(created_round)

            # Update cache (best effort) - already serialized
            try:
                await self.cache.cache_round(str(session_id), created_round.round_path, serialized_round)
                logger.debug(f"Cached round {session_id}:{created_round.round_path}")
            except Exception as cache_error:
                # Cache failure should not affect main business flow
                logger.warning(
                    f"Failed to cache round {session_id}:{created_round.round_path}: {cache_error}",
                    extra={"session_id": str(session_id), "round_path": created_round.round_path},
                )

            return ConversationErrorHandler.success_response({"round": serialized_round})

        except Exception as e:
            return ConversationErrorHandler.internal_error(
                "Failed to create round", logger_instance=logger, context="Create round error", exception=e
            )

    async def _create_round_atomic(
        self,
        db: AsyncSession,
        session: ConversationSession,
        role: DialogueRole,
        input_data: dict[str, Any],
        model: str | None,
        correlation_id: str | None,
        corr_uuid: UUID | None,
        parent_round_path: str | None = None,
    ) -> ConversationRound | None:
        """
        Create round atomically with domain events and outbox pattern.

        Args:
            db: Database session
            session: ConversationSession instance
            role: Dialogue role
            input_data: Input data
            model: Model name
            correlation_id: Correlation ID string
            corr_uuid: Parsed correlation UUID

        Returns:
            Created ConversationRound or None if failed
        """
        try:
            # Get repository from factory
            repository = self._repo_factory(db)

            async with transactional(db):
                created_round = None

                # Check for idempotent creation via correlation_id
                if correlation_id:
                    try:
                        existing = await repository.find_by_correlation_id(session.id, UUID(correlation_id))
                        if existing:
                            # Ensure domain event and outbox exist
                            await self.event_handler.ensure_round_events(db, session, existing, corr_uuid)
                            created_round = existing
                    except (ValueError, TypeError):
                        # Invalid correlation_id format, skip idempotent check
                        pass

                # Create new round if no idempotent hit
                if created_round is None:
                    created_round = await self._create_new_round(
                        db, session, role, input_data, model, correlation_id, corr_uuid, parent_round_path
                    )

                return created_round

        except Exception as e:
            logger.error(f"Atomic round creation error: {e}")
            return None

    async def _create_new_round(
        self,
        db: AsyncSession,
        session: ConversationSession,
        role: DialogueRole,
        input_data: dict[str, Any],
        model: str | None,
        correlation_id: str | None,
        corr_uuid: UUID | None,
        parent_round_path: str | None = None,
    ) -> ConversationRound:
        """Create a new round with events using atomic sequence generation."""
        from sqlalchemy import func, update

        if parent_round_path is None:
            # Top-level round: use session's round_sequence
            update_stmt = (
                update(ConversationSession)
                .where(ConversationSession.id == session.id)
                .values(round_sequence=ConversationSession.round_sequence + 1)
                .returning(ConversationSession.round_sequence)
            )
            result = await db.execute(update_stmt)
            new_sequence = result.scalar_one()
            round_path = str(new_sequence)
        else:
            # Branch round: find max child sequence under parent
            parent_pattern = f"{parent_round_path}.%"
            max_child_query = select(
                func.coalesce(
                    func.max(
                        func.cast(
                            func.split_part(ConversationRound.round_path, ".", len(parent_round_path.split(".")) + 1),
                            Integer,
                        )
                    ),
                    0,
                )
            ).where(
                and_(
                    ConversationRound.session_id == session.id,
                    ConversationRound.round_path.like(parent_pattern),
                    # Ensure exact depth match (no deeper children)
                    func.array_length(func.string_to_array(ConversationRound.round_path, "."), 1)
                    == len(parent_round_path.split(".")) + 1,
                )
            )

            max_child_result = await db.execute(max_child_query)
            max_child_sequence = max_child_result.scalar_one()
            new_child_sequence = max_child_sequence + 1
            round_path = f"{parent_round_path}.{new_child_sequence}"

        # Get repository from factory
        repository = self.repository or SqlAlchemyConversationRoundRepository(db)

        # Create round with atomically generated round_path using repository
        rnd = await repository.create(
            session_id=session.id,
            round_path=round_path,
            role=role.value,
            input=input_data,
            output=None,
            model=model,
            correlation_id=correlation_id,
        )

        # Create domain event and outbox (low-level helper)
        await self.event_handler.create_round_support_events(db, session, rnd, corr_uuid)

        return rnd
