"""
Round query service for conversation operations.

Handles read operations for conversation rounds with caching optimization.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.common.repositories.conversation import ConversationRoundRepository, SqlAlchemyConversationRoundRepository
from src.common.services.conversation.conversation_access_control import ConversationAccessControl
from src.common.services.conversation.conversation_cache import ConversationCacheManager
from src.common.services.conversation.conversation_error_handler import ConversationErrorHandler
from src.common.services.conversation.conversation_serializers import ConversationSerializer
from src.schemas.novel.dialogue import DialogueRole

logger = logging.getLogger(__name__)


class ConversationRoundQueryService:
    """Service for conversation round query operations."""

    def __init__(
        self,
        cache: ConversationCacheManager | None = None,
        access_control: ConversationAccessControl | None = None,
        serializer: ConversationSerializer | None = None,
        repository: ConversationRoundRepository | None = None,
    ) -> None:
        self.cache = cache or ConversationCacheManager()
        self.access_control = access_control or ConversationAccessControl()
        self.serializer = serializer or ConversationSerializer()
        self.repository = repository

    async def list_rounds(
        self,
        db: AsyncSession,
        user_id: int,
        session_id: UUID,
        *,
        after: str | None = None,
        limit: int = 50,
        order: str = "asc",
        role: DialogueRole | None = None,
    ) -> dict[str, Any]:
        """
        List conversation rounds for a session.

        Args:
            db: Database session
            user_id: User ID for ownership verification
            session_id: Session ID to list rounds for
            after: Cursor for pagination (ISO timestamp string)
            limit: Maximum number of rounds to return
            order: Sort order ('asc' or 'desc')
            role: Filter by dialogue role (optional)

        Returns:
            Dict with success status and rounds list or error details
        """
        try:
            # Verify session access
            access_result = await self.access_control.verify_session_access(db, user_id, session_id)
            if not access_result["success"]:
                return access_result

            # Initialize repository if not provided
            repository = self.repository or SqlAlchemyConversationRoundRepository(db)

            # Handle complex cursor pagination if needed
            processed_after = after
            if after:
                try:
                    import re

                    # Check if after looks like a round_path (numbers with optional dots)
                    if re.match(r"^\d+(\.\d+)*$", after):
                        # It's a round_path, find the corresponding round to get timestamp
                        round_obj = await repository.find_by_session_and_path(session_id, after)
                        if round_obj:
                            processed_after = round_obj.created_at.isoformat()
                            logger.debug(f"Using round_path cursor: {after} -> {processed_after}")
                        else:
                            processed_after = None
                    else:
                        # Assume it's already an ISO timestamp
                        logger.debug(f"Using timestamp cursor: {after}")
                        processed_after = after

                except (ValueError, AttributeError) as e:
                    # Invalid cursor format, ignore and log warning
                    logger.warning(f"Invalid cursor format '{after}': {e}")
                    processed_after = None

            # Use repository to get rounds
            rounds = await repository.list_by_session(
                session_id=session_id, after=processed_after, limit=limit, order=order, role=role
            )

            # Serialize ORM objects to dict at service boundary
            serialized_rounds = [self.serializer.serialize_round(rnd) for rnd in rounds]
            return ConversationErrorHandler.success_response({"rounds": serialized_rounds})

        except Exception as e:
            return ConversationErrorHandler.internal_error(
                "Failed to list rounds", logger_instance=logger, context="List rounds error", exception=e
            )

    async def get_round(self, db: AsyncSession, user_id: int, session_id: UUID, round_path: str) -> dict[str, Any]:
        """
        Get a specific conversation round.

        Args:
            db: Database session
            user_id: User ID for ownership verification
            session_id: Session ID
            round_path: Round path identifier

        Returns:
            Dict with success status and round or error details
        """
        try:
            # Verify session access
            access_result = await self.access_control.verify_session_access(db, user_id, session_id)
            if not access_result["success"]:
                return access_result

            # Try cache first
            cached = await self.cache.get_round(str(session_id), round_path)
            if cached:
                # Cache already contains serialized dict
                return ConversationErrorHandler.success_response({"round": cached, "cached": True})

            # Initialize repository if not provided
            repository = self.repository or SqlAlchemyConversationRoundRepository(db)

            # Get from repository
            rnd = await repository.find_by_session_and_path(session_id, round_path)

            if not rnd:
                return ConversationErrorHandler.not_found_error(
                    "Round", logger_instance=logger, context="Get round error"
                )

            # Serialize ORM object to dict at service boundary
            serialized_round = self.serializer.serialize_round(rnd)

            # Cache for future use (best effort) - already serialized
            try:
                await self.cache.cache_round(str(session_id), round_path, serialized_round)
                logger.debug(f"Cached round {session_id}:{round_path}")
            except Exception as cache_error:
                # Cache failure should not affect main business flow
                logger.warning(
                    f"Failed to cache round {session_id}:{round_path}: {cache_error}",
                    extra={"session_id": str(session_id), "round_path": round_path},
                )

            return ConversationErrorHandler.success_response({"round": serialized_round})

        except Exception as e:
            return ConversationErrorHandler.internal_error(
                "Failed to get round", logger_instance=logger, context="Get round error", exception=e
            )
