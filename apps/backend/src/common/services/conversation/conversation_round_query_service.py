"""
Round query service for conversation operations.

Handles read operations for conversation rounds with caching optimization.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from sqlalchemy import and_, asc, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.services.conversation.conversation_access_control import ConversationAccessControl
from src.common.services.conversation.conversation_cache import ConversationCacheManager
from src.common.services.conversation.conversation_error_handler import ConversationErrorHandler
from src.common.services.conversation.conversation_serializers import ConversationSerializer
from src.models.conversation import ConversationRound
from src.schemas.novel.dialogue import DialogueRole

logger = logging.getLogger(__name__)


class ConversationRoundQueryService:
    """Service for conversation round query operations."""

    def __init__(
        self,
        cache: ConversationCacheManager | None = None,
        access_control: ConversationAccessControl | None = None,
        serializer: ConversationSerializer | None = None,
    ) -> None:
        self.cache = cache or ConversationCacheManager()
        self.access_control = access_control or ConversationAccessControl()
        self.serializer = serializer or ConversationSerializer()

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

            # Build query - use created_at for proper chronological ordering
            q = select(ConversationRound).where(ConversationRound.session_id == session_id)

            if role is not None:
                q = q.where(ConversationRound.role == role.value)

            # Cursor pagination with dual format support
            if after:
                after_dt = None
                try:
                    from datetime import datetime
                    import re
                    
                    # Check if after looks like a round_path (numbers with optional dots)
                    if re.match(r'^\d+(\.\d+)*$', after):
                        # It's a round_path, find the corresponding round's created_at
                        round_result = await db.scalar(
                            select(ConversationRound.created_at).where(
                                and_(
                                    ConversationRound.session_id == session_id,
                                    ConversationRound.round_path == after
                                )
                            )
                        )
                        if round_result:
                            after_dt = round_result
                            logger.debug(f"Using round_path cursor: {after} -> {after_dt}")
                    else:
                        # Assume it's an ISO timestamp
                        after_dt = datetime.fromisoformat(after.replace("Z", "+00:00"))
                        logger.debug(f"Using timestamp cursor: {after}")

                    if after_dt:
                        if order == "asc":
                            q = q.where(ConversationRound.created_at > after_dt)
                        else:  # desc
                            q = q.where(ConversationRound.created_at < after_dt)
                            
                except (ValueError, AttributeError) as e:
                    # Invalid cursor format, ignore and log warning
                    logger.warning(f"Invalid cursor format '{after}': {e}")
                    pass

            # Use created_at for reliable chronological ordering
            q = q.order_by(
                asc(ConversationRound.created_at) if order == "asc" else desc(ConversationRound.created_at)
            ).limit(limit)

            result = await db.execute(q)
            rounds = result.scalars().all()

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

            # Get from database
            rnd = await db.scalar(
                select(ConversationRound).where(
                    and_(ConversationRound.session_id == session_id, ConversationRound.round_path == round_path)
                )
            )

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
                    extra={"session_id": str(session_id), "round_path": round_path}
                )

            return ConversationErrorHandler.success_response({"round": serialized_round})

        except Exception as e:
            return ConversationErrorHandler.internal_error(
                "Failed to get round", logger_instance=logger, context="Get round error", exception=e
            )
