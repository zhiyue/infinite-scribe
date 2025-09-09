"""
Access control logic for conversation operations.

Handles ownership verification and permission checks for conversation sessions and rounds.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.conversation import ConversationSession
from src.models.novel import Novel
from src.schemas.novel.dialogue import ScopeType

logger = logging.getLogger(__name__)


class ConversationAccessControl:
    """Centralized access control for conversation operations."""

    @staticmethod
    async def verify_session_access(
        db: AsyncSession, user_id: int, session_or_id: UUID | ConversationSession
    ) -> dict[str, Any]:
        """Verify user has access to a session.

        Supports both a `session_id` (UUID) and a pre-fetched ConversationSession
        instance for backward-compatibility with older call sites/tests.

        Returns dict with success flag and `session` on success; otherwise
        includes `error` and `code`.
        """
        try:
            if isinstance(session_or_id, ConversationSession):
                session = session_or_id
            else:
                session = await db.scalar(select(ConversationSession).where(ConversationSession.id == session_or_id))
                if not session:
                    return {"success": False, "error": "Session not found", "code": 404}

            access_result = await ConversationAccessControl._verify_scope_access(
                db, user_id, session.scope_type, session.scope_id
            )
            if not access_result["success"]:
                return access_result

            return {"success": True, "session": session}

        except Exception as e:
            logger.error(f"Session access verification error: {e}")
            return {"success": False, "error": "Failed to verify session access"}

    @staticmethod
    async def verify_scope_access(db: AsyncSession, user_id: int, scope_type: str, scope_id: str) -> dict[str, Any]:
        """
        Verify user has access to a scope.

        Returns:
            dict with success and error/code if failed
        """
        return await ConversationAccessControl._verify_scope_access(db, user_id, scope_type, scope_id)

    @staticmethod
    async def verify_cached_session_access(
        db: AsyncSession, user_id: int, cached_session: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Verify user has access to a cached session by checking its scope.

        Returns:
            dict with success and error/code if failed
        """
        try:
            scope_type = cached_session.get("scope_type")
            scope_id = cached_session.get("scope_id")

            if not scope_type or not scope_id:
                return {"success": False, "error": "Invalid cached session data"}

            return await ConversationAccessControl._verify_scope_access(db, user_id, scope_type, scope_id)

        except Exception as e:
            logger.error(f"Cached session access verification error: {e}")
            return {"success": False, "error": "Failed to verify cached session access"}

    @staticmethod
    async def _verify_scope_access(db: AsyncSession, user_id: int, scope_type: str, scope_id: str) -> dict[str, Any]:
        """
        Internal method to verify access to a specific scope.

        Currently only supports GENESIS scope (novel-based access).
        """
        try:
            if scope_type != ScopeType.GENESIS.value:
                return {"success": False, "error": "Only GENESIS scope is supported"}

            # For GENESIS scope, scope_id is novel_id
            try:
                novel_uuid = UUID(str(scope_id))
            except Exception:
                return {"success": False, "error": "Invalid novel id", "code": 422}

            # Check if user owns the novel
            novel_exists = await db.scalar(
                select(Novel.id).where(and_(Novel.id == novel_uuid, Novel.user_id == user_id))
            )

            if not novel_exists:
                return {"success": False, "error": "Access denied", "code": 403}

            return {"success": True}

        except Exception as e:
            logger.error(f"Scope access verification error: {e}")
            return {"success": False, "error": "Failed to verify scope access"}

    @staticmethod
    async def get_novel_for_scope(db: AsyncSession, user_id: int, scope_type: str, scope_id: str) -> dict[str, Any]:
        """
        Get novel entity for GENESIS scope with ownership verification.

        Returns:
            dict with success, novel (if successful), error and code (if failed)
        """
        try:
            if scope_type != ScopeType.GENESIS.value:
                return {"success": False, "error": "Only GENESIS scope is supported"}

            try:
                novel_uuid = UUID(str(scope_id))
            except Exception:
                return {"success": False, "error": "Invalid novel id", "code": 422}

            novel = await db.scalar(select(Novel).where(and_(Novel.id == novel_uuid, Novel.user_id == user_id)))

            if not novel:
                return {"success": False, "error": "Novel not found or access denied", "code": 403}

            return {"success": True, "novel": novel}

        except Exception as e:
            logger.error(f"Get novel for scope error: {e}")
            return {"success": False, "error": "Failed to get novel for scope"}
