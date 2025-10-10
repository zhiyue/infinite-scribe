"""
Session access control operations helper for conversation services.

Handles access control verification patterns with consistent error handling.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.common.services.conversation.conversation_access_control import ConversationAccessControl

logger = logging.getLogger(__name__)


class ConversationSessionAccessOperations:
    """Helper for conversation session access control operations."""

    def __init__(self, access_control: ConversationAccessControl) -> None:
        self.access_control = access_control

    async def verify_scope_access_for_creation(
        self, db: AsyncSession, user_id: int, scope_type_str: str, scope_id: str
    ) -> dict[str, Any]:
        """
        Verify access to scope for session creation.

        Args:
            db: Database session
            user_id: User ID
            scope_type_str: Scope type string
            scope_id: Scope ID

        Returns:
            Access result dict
        """
        logger.debug(f"Verifying access to scope: {scope_type_str}, {scope_id}")
        novel_result = await self.access_control.get_novel_for_scope(db, user_id, scope_type_str, scope_id)
        logger.debug(f"Access control result: {novel_result}")
        if not novel_result["success"]:
            logger.warning(f"Access denied: {novel_result}")
        return novel_result

    async def verify_session_access(
        self, db: AsyncSession, user_id: int, session: Any, operation: str = "session access"
    ) -> dict[str, Any]:
        """
        Verify access to existing session.

        Args:
            db: Database session
            user_id: User ID
            session: Session object or dict with scope info
            operation: Operation name for logging

        Returns:
            Access result dict
        """
        if hasattr(session, "scope_type"):
            # ORM object
            session_data = {"scope_type": session.scope_type, "scope_id": session.scope_id, "status": session.status}
        else:
            # Dict object
            session_data = session

        access_result = await self.access_control.verify_cached_session_access(db, user_id, session_data)
        if not access_result["success"]:
            logger.debug(f"Access denied for {operation}: {access_result}")
        return access_result

    async def verify_cached_session_access(
        self, db: AsyncSession, user_id: int, cached_session: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Verify access to cached session data.

        Args:
            db: Database session
            user_id: User ID
            cached_session: Cached session data

        Returns:
            Access result dict
        """
        return await self.access_control.verify_cached_session_access(db, user_id, cached_session)

    async def verify_scope_access(
        self, db: AsyncSession, user_id: int, scope_type: str, scope_id: str
    ) -> dict[str, Any]:
        """
        Verify user has access to scope for listing operations.

        Args:
            db: Database session
            user_id: User ID
            scope_type: Scope type
            scope_id: Scope ID

        Returns:
            Access result dict
        """
        return await self.access_control.verify_scope_access(db, user_id, scope_type, scope_id)
