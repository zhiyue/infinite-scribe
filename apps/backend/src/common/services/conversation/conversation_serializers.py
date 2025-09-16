"""
Serialization utilities for conversation objects.

Handles conversion of SQLAlchemy models to cacheable dictionary representations.
"""

from __future__ import annotations

from typing import Any

from src.models.conversation import ConversationRound, ConversationSession
from src.models.workflow import CommandInbox


class ConversationSerializer:
    """Utility class for serializing conversation objects."""

    @staticmethod
    def serialize_session(session: ConversationSession | dict[str, Any]) -> dict[str, Any]:
        """
        Serialize a ConversationSession to a dictionary format suitable for caching.

        Args:
            session: ConversationSession instance or dict

        Returns:
            Serialized session data
        """
        if isinstance(session, dict):
            return session

        return {
            "id": str(session.id),
            "scope_type": session.scope_type,
            "scope_id": session.scope_id,
            "status": session.status,
            "stage": session.stage,
            "state": session.state or {},
            "version": session.version,
            "created_at": getattr(session.created_at, "isoformat", lambda: str(session.created_at))()
            if hasattr(session, "created_at")
            else None,
            "updated_at": getattr(session.updated_at, "isoformat", lambda: str(session.updated_at))()
            if hasattr(session, "updated_at")
            else None,
        }

    @staticmethod
    def serialize_round(rnd: ConversationRound | dict[str, Any]) -> dict[str, Any]:
        """
        Serialize a ConversationRound to a dictionary format suitable for caching.

        Args:
            rnd: ConversationRound instance or dict

        Returns:
            Serialized round data
        """
        if isinstance(rnd, dict):
            return rnd

        return {
            "session_id": str(rnd.session_id),
            "round_path": rnd.round_path,
            "role": rnd.role,
            "input": rnd.input or {},
            "output": rnd.output or {},
            "model": rnd.model,
            "correlation_id": rnd.correlation_id,
            "created_at": getattr(rnd.created_at, "isoformat", lambda: str(rnd.created_at))()
            if hasattr(rnd, "created_at")
            else None,
        }

    @staticmethod
    def serialize_command(cmd: CommandInbox | dict[str, Any]) -> dict[str, Any]:
        """
        Serialize a CommandInbox to a dictionary format suitable for API responses.

        Args:
            cmd: CommandInbox instance or dict

        Returns:
            Serialized command data
        """
        if isinstance(cmd, dict):
            return cmd

        return {
            "id": str(cmd.id),
            "session_id": str(cmd.session_id),
            "command_type": cmd.command_type,
            "idempotency_key": cmd.idempotency_key,
            "payload": cmd.payload or {},
            "status": cmd.status.value if hasattr(cmd.status, 'value') else str(cmd.status),
            "error_message": cmd.error_message,
            "retry_count": cmd.retry_count,
            "created_at": getattr(cmd.created_at, "isoformat", lambda: str(cmd.created_at))()
            if hasattr(cmd, "created_at")
            else None,
            "updated_at": getattr(cmd.updated_at, "isoformat", lambda: str(cmd.updated_at))()
            if hasattr(cmd, "updated_at")
            else None,
        }
