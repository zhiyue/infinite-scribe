"""
Conversation service (persistent) for Genesis conversation flows.

Implements CRUD for conversation sessions and rounds with:
- PostgreSQL persistence via SQLAlchemy ORM
- Write-through cache to Redis (DialogueCacheManager)
- Optimistic concurrency control using version column
- Idempotency for rounds via correlation_id and for commands via idempotency_key
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import and_, asc, desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.events.config import build_event_type, get_aggregate_type, get_domain_topic
from src.db.redis.dialogue_cache import DialogueCacheManager
from src.models.conversation import ConversationRound, ConversationSession
from src.models.event import DomainEvent
from src.models.novel import Novel
from src.models.workflow import CommandInbox, EventOutbox
from src.schemas.enums import CommandStatus, OutboxStatus
from src.schemas.novel.dialogue import DialogueRole, ScopeType, SessionStatus

logger = logging.getLogger(__name__)


class ConversationService:
    """Service for conversation sessions and rounds."""

    def __init__(self) -> None:
        self.cache = DialogueCacheManager()

    # ---------- Session ----------

    async def create_session(
        self,
        db: AsyncSession,
        user_id: int,
        scope_type: ScopeType,
        scope_id: str,
        stage: str | None = None,
        initial_state: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        try:
            if scope_type != ScopeType.GENESIS:
                return {"success": False, "error": "Only GENESIS scope is supported"}

            # Ownership check: for GENESIS, scope_id is novel_id
            try:
                novel_uuid = UUID(str(scope_id))
            except Exception:
                return {"success": False, "error": "Invalid novel id", "code": 422}
            novel = await db.scalar(select(Novel).where(and_(Novel.id == novel_uuid, Novel.user_id == user_id)))
            if not novel:
                return {"success": False, "error": "Novel not found or access denied", "code": 403}

            # Optional: disallow multiple ACTIVE sessions for same novel
            existing = await db.scalar(
                select(ConversationSession).where(
                    and_(
                        ConversationSession.scope_type == ScopeType.GENESIS.value,
                        ConversationSession.scope_id == str(scope_id),
                        ConversationSession.status == SessionStatus.ACTIVE.value,
                    )
                )
            )
            if existing:
                return {"success": False, "error": "An active session already exists for this novel", "code": 409}

            session = ConversationSession(
                scope_type=scope_type.value,
                scope_id=str(scope_id),
                status=SessionStatus.ACTIVE.value,
                stage=stage,
                state=initial_state or {},
                version=1,
            )
            db.add(session)
            await db.commit()
            await db.refresh(session)

            # Cache write-through (best-effort)
            await self.cache.cache_session(str(session.id), self._serialize_session(session))

            return {"success": True, "session": session}

        except Exception as e:
            await db.rollback()
            logger.error(f"Create session error: {e}")
            return {"success": False, "error": "Failed to create session"}

    async def get_session(self, db: AsyncSession, user_id: int, session_id: UUID) -> dict[str, Any]:
        try:
            # Try cache first
            cached = await self.cache.get_session(str(session_id))
            if cached:
                # Perform ownership verification via scope if possible
                scope_type = cached.get("scope_type")
                scope_id = cached.get("scope_id")
                if scope_type == ScopeType.GENESIS.value and scope_id:
                    try:
                        novel_uuid = UUID(str(scope_id))
                    except Exception:
                        return {"success": False, "error": "Invalid novel id", "code": 422}
                    novel_exists = await db.scalar(
                        select(Novel.id).where(and_(Novel.id == novel_uuid, Novel.user_id == user_id))
                    )
                    if not novel_exists:
                        return {"success": False, "error": "Access denied", "code": 403}
                return {"success": True, "session": cached, "cached": True}

            # Fallback to DB
            session = await db.scalar(select(ConversationSession).where(ConversationSession.id == session_id))
            if not session:
                return {"success": False, "error": "Session not found", "code": 404}

            # Ownership: resolve to novel
            if session.scope_type == ScopeType.GENESIS.value:
                try:
                    novel_uuid = UUID(str(session.scope_id))
                except Exception:
                    return {"success": False, "error": "Invalid novel id", "code": 422}
                novel = await db.scalar(select(Novel).where(and_(Novel.id == novel_uuid, Novel.user_id == user_id)))
                if not novel:
                    return {"success": False, "error": "Access denied", "code": 403}

            await self.cache.cache_session(str(session.id), self._serialize_session(session))
            return {"success": True, "session": session}

        except Exception as e:
            logger.error(f"Get session error: {e}")
            return {"success": False, "error": "Failed to get session"}

    async def update_session(
        self,
        db: AsyncSession,
        user_id: int,
        session_id: UUID,
        *,
        status: SessionStatus | None = None,
        stage: str | None = None,
        state: dict[str, Any] | None = None,
        expected_version: int | None = None,
    ) -> dict[str, Any]:
        try:
            # Ownership check via join on loaded entity
            session = await db.scalar(select(ConversationSession).where(ConversationSession.id == session_id))
            if not session:
                return {"success": False, "error": "Session not found", "code": 404}

            if session.scope_type == ScopeType.GENESIS.value:
                try:
                    novel_uuid = UUID(str(session.scope_id))
                except Exception:
                    return {"success": False, "error": "Invalid novel id", "code": 422}
                novel = await db.scalar(select(Novel.id).where(and_(Novel.id == novel_uuid, Novel.user_id == user_id)))
                if not novel:
                    return {"success": False, "error": "Access denied", "code": 403}

            # OCC via single UPDATE ... WHERE version=expected
            new_values: dict[str, Any] = {}
            if status is not None:
                new_values["status"] = status.value if isinstance(status, SessionStatus) else status
            if stage is not None:
                new_values["stage"] = stage
            if state is not None:
                new_values["state"] = state

            if not new_values:
                # nothing to update
                return {"success": True, "session": session}

            stmt = (
                update(ConversationSession)
                .where(ConversationSession.id == session_id)
                .values(**new_values, version=ConversationSession.version + 1, updated_at=datetime.now(tz=UTC))
                .returning(ConversationSession)
            )

            if expected_version is not None:
                stmt = stmt.where(ConversationSession.version == expected_version)

            result = await db.execute(stmt)
            updated = result.scalar_one_or_none()
            if not updated:
                await db.rollback()
                return {"success": False, "error": "Version mismatch or conflict", "code": 412}

            await db.commit()

            # Cache write-through
            await self.cache.cache_session(str(updated.id), self._serialize_session(updated))

            return {"success": True, "session": updated}

        except Exception as e:
            await db.rollback()
            logger.error(f"Update session error: {e}")
            return {"success": False, "error": "Failed to update session"}

    async def delete_session(self, db: AsyncSession, user_id: int, session_id: UUID) -> dict[str, Any]:
        try:
            session = await db.scalar(select(ConversationSession).where(ConversationSession.id == session_id))
            if not session:
                return {"success": False, "error": "Session not found", "code": 404}

            if session.scope_type == ScopeType.GENESIS.value:
                try:
                    novel_uuid = UUID(str(session.scope_id))
                except Exception:
                    return {"success": False, "error": "Invalid novel id", "code": 422}
                novel = await db.scalar(select(Novel.id).where(and_(Novel.id == novel_uuid, Novel.user_id == user_id)))
                if not novel:
                    return {"success": False, "error": "Access denied", "code": 403}

            await db.delete(session)
            await db.commit()

            # Invalidate cache best-effort
            await self.cache.clear_session(str(session_id))
            return {"success": True}

        except Exception as e:
            await db.rollback()
            logger.error(f"Delete session error: {e}")
            return {"success": False, "error": "Failed to delete session"}

    # ---------- Rounds ----------

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
        try:
            # Ownership check via session
            session = await db.scalar(select(ConversationSession).where(ConversationSession.id == session_id))
            if not session:
                return {"success": False, "error": "Session not found", "code": 404}
            if session.scope_type == ScopeType.GENESIS.value:
                try:
                    novel_uuid = UUID(str(session.scope_id))
                except Exception:
                    return {"success": False, "error": "Invalid novel id", "code": 422}
                novel = await db.scalar(select(Novel.id).where(and_(Novel.id == novel_uuid, Novel.user_id == user_id)))
                if not novel:
                    return {"success": False, "error": "Access denied", "code": 403}

            q = select(ConversationRound).where(ConversationRound.session_id == session_id)
            if role is not None:
                q = q.where(ConversationRound.role == role.value)
            if after:
                # Simple cursor by round_path string
                q = q.where(ConversationRound.round_path > after)
            q = q.order_by(
                asc(ConversationRound.round_path) if order == "asc" else desc(ConversationRound.round_path)
            ).limit(limit)

            res = await db.execute(q)
            rounds = res.scalars().all()
            return {"success": True, "rounds": rounds}
        except Exception as e:
            logger.error(f"List rounds error: {e}")
            return {"success": False, "error": "Failed to list rounds"}

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
    ) -> dict[str, Any]:
        try:
            session = await db.scalar(select(ConversationSession).where(ConversationSession.id == session_id))
            if not session:
                return {"success": False, "error": "Session not found", "code": 404}
            if session.scope_type == ScopeType.GENESIS.value:
                try:
                    novel_uuid = UUID(str(session.scope_id))
                except Exception:
                    return {"success": False, "error": "Invalid novel id", "code": 422}
                novel = await db.scalar(select(Novel.id).where(and_(Novel.id == novel_uuid, Novel.user_id == user_id)))
                if not novel:
                    return {"success": False, "error": "Access denied", "code": 403}

            # Parse correlation UUID for domain event idempotency
            corr_uuid: UUID | None = None
            if correlation_id:
                try:
                    corr_uuid = UUID(str(correlation_id))
                except Exception:
                    corr_uuid = None

            # Atomic unit: round + domain_event + outbox
            async with db.begin():
                created_round = None
                # Idempotency path: existing round by correlation_id
                if correlation_id:
                    existing = await db.scalar(
                        select(ConversationRound).where(
                            and_(
                                ConversationRound.session_id == session_id,
                                ConversationRound.correlation_id == correlation_id,
                            )
                        )
                    )
                    if existing:
                        # Ensure event/outbox exist for this correlation
                        event_type = build_event_type(session.scope_type, "Round.Created")
                        dom_evt = None
                        if corr_uuid is not None:
                            dom_evt = await db.scalar(
                                select(DomainEvent).where(
                                    and_(
                                        DomainEvent.correlation_id == corr_uuid,
                                        DomainEvent.event_type == event_type,
                                    )
                                )
                            )
                        if not dom_evt:
                            dom_evt = DomainEvent(
                                event_type=event_type,
                                aggregate_type=get_aggregate_type(session.scope_type),
                                aggregate_id=str(session_id),
                                payload={
                                    "session_id": str(session_id),
                                    "round_path": existing.round_path,
                                    "role": existing.role,
                                    "model": existing.model,
                                },
                                correlation_id=corr_uuid,
                                causation_id=None,
                                event_metadata={"source": "api-gateway"},
                            )
                            db.add(dom_evt)
                            await db.flush()

                        # Upsert outbox by dom_evt.event_id
                        existing_out = await db.scalar(select(EventOutbox).where(EventOutbox.id == dom_evt.event_id))
                        if not existing_out:
                            out = EventOutbox(
                                id=dom_evt.event_id,
                                topic=get_domain_topic(session.scope_type),
                                key=str(session_id),
                                partition_key=str(session_id),
                                payload={
                                    "event_id": str(dom_evt.event_id),
                                    "event_type": dom_evt.event_type,
                                    "aggregate_type": dom_evt.aggregate_type,
                                    "aggregate_id": dom_evt.aggregate_id,
                                    "payload": dom_evt.payload or {},
                                    "metadata": dom_evt.event_metadata or {},
                                },
                                headers={
                                    "event_type": dom_evt.event_type,
                                    "version": 1,
                                    "correlation_id": str(corr_uuid) if corr_uuid else None,
                                },
                                status=OutboxStatus.PENDING,
                            )
                            db.add(out)

                        # End atomic path, return existing
                        rnd = existing
                        # No need to refresh inside transaction
                        pass
                        # Transaction will commit
                        # Fall through to cache and return outside with rnd
                        # Using outer scope variable
                        created_round = rnd
                        # Exit transaction block
                        # Note: using block variable; after block commit

                # Non-idempotent: create new round when no idempotent hit
                if created_round is None:
                    # Compute next round_path (naive: count + 1)
                    count_stmt = (
                        select(func.count())
                        .select_from(ConversationRound)
                        .where(ConversationRound.session_id == session_id)
                    )
                    total = (await db.execute(count_stmt)).scalar() or 0
                    next_index = total + 1
                    round_path = str(next_index)

                    rnd = ConversationRound(
                        session_id=session_id,
                        round_path=round_path,
                        role=role.value,
                        input=input_data,
                        output=None,
                        tool_calls=None,
                        model=model,
                        correlation_id=correlation_id,
                    )
                    db.add(rnd)
                    await db.flush()

                    # Create domain event + outbox
                    event_type = build_event_type(session.scope_type, "Round.Created")
                    dom_evt = DomainEvent(
                        event_type=event_type,
                        aggregate_type=get_aggregate_type(session.scope_type),
                        aggregate_id=str(session_id),
                        payload={
                            "session_id": str(session_id),
                            "round_path": round_path,
                            "role": role.value,
                            "model": model,
                        },
                        correlation_id=corr_uuid,
                        causation_id=None,
                        event_metadata={"source": "api-gateway"},
                    )
                    db.add(dom_evt)
                    await db.flush()

                    out = EventOutbox(
                        id=dom_evt.event_id,
                        topic=get_domain_topic(session.scope_type),
                        key=str(session_id),
                        partition_key=str(session_id),
                        payload={
                            "event_id": str(dom_evt.event_id),
                            "event_type": dom_evt.event_type,
                            "aggregate_type": dom_evt.aggregate_type,
                            "aggregate_id": dom_evt.aggregate_id,
                            "payload": dom_evt.payload or {},
                            "metadata": dom_evt.event_metadata or {},
                        },
                        headers={
                            "event_type": dom_evt.event_type,
                            "version": 1,
                            "correlation_id": str(corr_uuid) if corr_uuid else None,
                        },
                        status=OutboxStatus.PENDING,
                    )
                    db.add(out)

                    created_round = rnd

            # After atomic commit, update cache (best effort)
            await self.cache.cache_round(
                str(session_id), created_round.round_path, self._serialize_round(created_round)
            )

            return {"success": True, "round": created_round}
        except Exception as e:
            logger.error(f"Create round error: {e}")
            return {"success": False, "error": "Failed to create round"}

    async def get_round(self, db: AsyncSession, user_id: int, session_id: UUID, round_path: str) -> dict[str, Any]:
        try:
            # Ownership check
            session = await db.scalar(select(ConversationSession).where(ConversationSession.id == session_id))
            if not session:
                return {"success": False, "error": "Session not found", "code": 404}
            if session.scope_type == ScopeType.GENESIS.value:
                novel = await db.scalar(
                    select(Novel.id).where(and_(Novel.id == session.scope_id, Novel.user_id == user_id))
                )
                if not novel:
                    return {"success": False, "error": "Access denied", "code": 403}

            # Try cache
            cached = await self.cache.get_round(str(session_id), round_path)
            if cached:
                return {"success": True, "round": cached, "cached": True}

            rnd = await db.scalar(
                select(ConversationRound).where(
                    and_(ConversationRound.session_id == session_id, ConversationRound.round_path == round_path)
                )
            )
            if not rnd:
                return {"success": False, "error": "Round not found", "code": 404}

            await self.cache.cache_round(str(session_id), round_path, self._serialize_round(rnd))
            return {"success": True, "round": rnd}
        except Exception as e:
            logger.error(f"Get round error: {e}")
            return {"success": False, "error": "Failed to get round"}

    # ---------- Commands ----------

    async def enqueue_command(
        self,
        db: AsyncSession,
        user_id: int,
        session_id: UUID,
        *,
        command_type: str,
        payload: dict[str, Any] | None,
        idempotency_key: str | None,
    ) -> dict[str, Any]:
        try:
            # Access via session
            session = await db.scalar(select(ConversationSession).where(ConversationSession.id == session_id))
            if not session:
                return {"success": False, "error": "Session not found", "code": 404}
            if session.scope_type == ScopeType.GENESIS.value:
                try:
                    novel_uuid = UUID(str(session.scope_id))
                except Exception:
                    return {"success": False, "error": "Invalid novel id", "code": 422}
                novel = await db.scalar(select(Novel.id).where(and_(Novel.id == novel_uuid, Novel.user_id == user_id)))
                if not novel:
                    return {"success": False, "error": "Access denied", "code": 403}

            # Atomic unit (Outbox pattern): command_inbox + domain_events + event_outbox
            async with db.begin():
                # 1) Idempotent fetch-or-create CommandInbox
                cmd: CommandInbox | None = None
                if idempotency_key:
                    cmd = await db.scalar(select(CommandInbox).where(CommandInbox.idempotency_key == idempotency_key))
                if not cmd:
                    cmd = CommandInbox(
                        session_id=session_id,
                        command_type=command_type,
                        idempotency_key=idempotency_key or f"cmd-{uuid4()}",
                        payload=payload or {},
                        status=CommandStatus.RECEIVED,
                    )
                    db.add(cmd)
                    # flush to get cmd.id
                    await db.flush()

                # 2) Upsert DomainEvent by correlation_id (cmd.id) + event_type
                event_type = build_event_type(session.scope_type, "Command.Received")
                dom_evt = await db.scalar(
                    select(DomainEvent).where(
                        and_(DomainEvent.correlation_id == cmd.id, DomainEvent.event_type == event_type)
                    )
                )
                if not dom_evt:
                    dom_evt = DomainEvent(
                        event_type=event_type,
                        aggregate_type=get_aggregate_type(session.scope_type),
                        aggregate_id=str(session_id),
                        payload={"command_type": command_type, "payload": payload or {}},
                        correlation_id=cmd.id,
                        causation_id=None,
                        event_metadata={"source": "api-gateway"},
                    )
                    db.add(dom_evt)
                    await db.flush()  # get event_id

                # 3) Insert EventOutbox with id = domain_event.event_id for idempotency
                existing_out = await db.scalar(select(EventOutbox).where(EventOutbox.id == dom_evt.event_id))
                if not existing_out:
                    out = EventOutbox(
                        id=dom_evt.event_id,
                        topic=get_domain_topic(session.scope_type),
                        key=str(session_id),
                        partition_key=str(session_id),
                        payload={
                            "event_id": str(dom_evt.event_id),
                            "event_type": dom_evt.event_type,
                            "aggregate_type": dom_evt.aggregate_type,
                            "aggregate_id": dom_evt.aggregate_id,
                            "payload": dom_evt.payload or {},
                            "metadata": dom_evt.event_metadata or {},
                            "created_at": getattr(dom_evt.created_at, "isoformat", lambda: str(dom_evt.created_at))()
                            if getattr(dom_evt, "created_at", None)
                            else None,
                        },
                        headers={
                            "event_type": dom_evt.event_type,
                            "version": 1,
                            "correlation_id": str(cmd.id),
                        },
                        status=OutboxStatus.PENDING,
                    )
                    db.add(out)
                # end unit

            # NOTE: db.begin() commits here atomically
            return {"success": True, "command": cmd}

        except Exception as e:
            logger.error(f"Enqueue command error: {e}")
            return {"success": False, "error": "Failed to enqueue command"}

    # ---------- Serialization helpers ----------

    @staticmethod
    def _serialize_session(session: ConversationSession | dict[str, Any]) -> dict[str, Any]:
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
    def _serialize_round(rnd: ConversationRound | dict[str, Any]) -> dict[str, Any]:
        if isinstance(rnd, dict):
            return rnd
        return {
            "session_id": str(rnd.session_id),
            "round_path": rnd.round_path,
            "role": rnd.role,
            "input": rnd.input or {},
            "output": rnd.output,
            "model": rnd.model,
            "correlation_id": rnd.correlation_id,
            "created_at": getattr(rnd.created_at, "isoformat", lambda: str(rnd.created_at))()
            if hasattr(rnd, "created_at")
            else None,
        }


conversation_service = ConversationService()

__all__ = ["conversation_service", "ConversationService"]
