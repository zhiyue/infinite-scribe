"""Domain Orchestrator Agent

Consumes domain bus + capability events and:
- Projects trigger-class domain events (Command.Received) into domain facts (*Requested)
- Emits capability tasks to corresponding capability topics
- Projects capability results into domain facts (e.g., *Proposed)

Notes:
- Domain facts are persisted via DomainEvent + EventOutbox (DB write-through),
  not directly produced to Kafka. Outbox relay will publish them.
- Capability tasks are sent to Kafka (agent bus) using BaseAgent producer.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import and_, select

from src.agents.agent_config import get_agent_topics
from src.agents.base import BaseAgent
from src.agents.orchestrator.command_strategies import command_registry
from src.agents.orchestrator.event_handlers import CapabilityEventHandlers
from src.common.events.config import build_event_type, get_aggregate_type, get_domain_topic
from src.common.events.mapping import normalize_task_type
from src.db.sql.session import create_sql_session
from src.models.event import DomainEvent
from src.models.workflow import AsyncTask, EventOutbox
from src.schemas.enums import OutboxStatus, TaskStatus


class OrchestratorAgent(BaseAgent):
    def __init__(self) -> None:
        consume_topics, produce_topics = get_agent_topics("orchestrator")
        super().__init__(name="orchestrator", consume_topics=consume_topics, produce_topics=produce_topics)

    async def process_message(
        self, message: dict[str, Any], context: dict[str, Any] | None = None
    ) -> dict[str, Any] | None:
        # Two possible shapes:
        # 1) DomainEvent envelope (from outbox relay)
        #    { event_type, aggregate_type, aggregate_id, payload, metadata, ... }
        # 2) Capability Envelope (agent bus) via BaseAgent: { id, ts, type, data:{...} }

        # Domain event shape
        if "event_type" in message and "aggregate_id" in message:
            return await self._handle_domain_event(message)

        # Capability event envelope - 从context中获取type而非message
        msg_type = (context or {}).get("meta", {}).get("type") or message.get("type")
        if msg_type:
            return await self._handle_capability_event(msg_type, message, context or {})

        self.log.debug("orchestrator_ignored_message", reason="unknown_shape")
        return None

    async def _handle_domain_event(self, evt: dict[str, Any]) -> dict[str, Any] | None:
        event_type = str(evt.get("event_type"))
        aggregate_id = str(evt.get("aggregate_id"))
        payload = evt.get("payload") or {}
        metadata = evt.get("metadata") or {}
        correlation_id = metadata.get("correlation_id") or evt.get("correlation_id")

        # Only react to trigger-class events (commands/user actions)
        if not event_type.endswith("Command.Received"):
            return None

        cmd_type = (payload or {}).get("command_type")
        if not cmd_type:
            return None

        scope_prefix = event_type.split(".", 1)[0] if "." in event_type else "Genesis"
        scope_type = scope_prefix.upper()  # e.g., GENESIS

        # Map command to domain requested + capability task
        mapping = command_registry.process_command(
            cmd_type=cmd_type,
            scope_type=scope_type,
            scope_prefix=scope_prefix,
            aggregate_id=aggregate_id,
            payload=payload,
        )

        if not mapping:
            return None

        # 1) Project to domain facts (*Requested) via DB Outbox
        await self._persist_domain_event(
            scope_type=scope_type,
            session_id=aggregate_id,
            event_action=mapping.requested_action,
            payload={"session_id": aggregate_id, "input": payload.get("payload", {})},
            correlation_id=correlation_id,
        )

        # 2) Emit capability task (agent bus) and create AsyncTask for tracking
        try:
            await self._create_async_task(
                correlation_id=correlation_id,
                session_id=aggregate_id,
                task_type=normalize_task_type(mapping.capability_message.get("type", "")),
                input_data=mapping.capability_message.get("input") or {},
            )
        except Exception:
            self.log.warning(
                "async_task_create_failed", correlation_id=correlation_id, task=mapping.capability_message.get("type")
            )

        return mapping.capability_message

    async def _handle_capability_event(
        self, msg_type: str, message: dict[str, Any], context: dict[str, Any]
    ) -> dict[str, Any] | None:
        data = message.get("data") or message  # 保持原有逻辑：优先从data字段获取，回退到message本身
        session_id = str(data.get("session_id") or data.get("aggregate_id") or "")
        topic = context.get("topic") or ""
        # infer scope from topic prefix (e.g., genesis.outline.events)
        scope_prefix = topic.split(".", 1)[0].upper() if "." in topic else "GENESIS"
        scope_type = scope_prefix
        # 优先从context['meta']读取correlation_id，回退到data
        correlation_id = context.get("meta", {}).get("correlation_id") or data.get("correlation_id")

        # Try different event handlers in sequence
        handlers = [
            lambda: CapabilityEventHandlers.handle_generation_completed(
                msg_type, session_id, data, correlation_id, scope_type, scope_prefix
            ),
            lambda: CapabilityEventHandlers.handle_quality_review_result(
                msg_type, session_id, data, correlation_id, scope_type, scope_prefix
            ),
            lambda: CapabilityEventHandlers.handle_consistency_check_result(
                msg_type, session_id, data, correlation_id, scope_type
            ),
        ]

        for handler in handlers:
            action = handler()
            if action:
                return await self._execute_event_action(action)

        return None

    async def _execute_event_action(self, action) -> dict[str, Any] | None:
        """Execute the actions specified by an event handler."""
        # Persist domain event if specified
        if action.domain_event:
            await self._persist_domain_event(**action.domain_event)

        # Complete async task if specified
        if action.task_completion:
            await self._complete_async_task(**action.task_completion)

        # Return capability message for further processing
        return action.capability_message

    async def _create_async_task(
        self, *, correlation_id: str | None, session_id: str, task_type: str, input_data: dict[str, Any]
    ) -> None:
        """Create an AsyncTask row to track capability execution with idempotency protection."""
        from datetime import UTC, datetime

        if not task_type:
            return
        trig_cmd_id = None
        if correlation_id:
            try:
                trig_cmd_id = UUID(str(correlation_id))
            except Exception:
                trig_cmd_id = None

        async with create_sql_session() as db:
            # Check for existing RUNNING/PENDING task to prevent duplicates
            if trig_cmd_id:
                existing_stmt = select(AsyncTask).where(
                    and_(
                        AsyncTask.triggered_by_command_id == trig_cmd_id,
                        AsyncTask.task_type == task_type,
                        AsyncTask.status.in_([TaskStatus.RUNNING, TaskStatus.PENDING]),
                    )
                )
                existing_task = await db.scalar(existing_stmt)
                if existing_task:
                    self.log.debug(
                        "async_task_already_exists",
                        correlation_id=correlation_id,
                        task_type=task_type,
                        existing_task_id=str(existing_task.id),
                    )
                    return

            task = AsyncTask(
                task_type=task_type,
                triggered_by_command_id=trig_cmd_id,
                status=TaskStatus.RUNNING,
                started_at=datetime.now(UTC),
                input_data={"session_id": session_id, **(input_data or {})},
            )
            db.add(task)
            await db.flush()

    async def _complete_async_task(
        self, *, correlation_id: str | None, expect_task_prefix: str, result_data: dict[str, Any]
    ) -> None:
        """Mark latest RUNNING/PENDING AsyncTask (by correlation) as COMPLETED.

        Args:
            correlation_id: UUID string from envelope meta
            expect_task_prefix: Prefix of task_type to match (e.g., "Character.Design.Generation")
        """
        from src.common.utils.datetime_utils import utc_now

        if not correlation_id:
            return
        try:
            trig_cmd_id = UUID(str(correlation_id))
        except Exception:
            return
        async with create_sql_session() as db:
            # pick most recent RUNNING/PENDING task with matching prefix
            stmt = (
                select(AsyncTask)
                .where(
                    and_(
                        AsyncTask.triggered_by_command_id == trig_cmd_id,
                        AsyncTask.status.in_([TaskStatus.RUNNING, TaskStatus.PENDING]),
                        AsyncTask.task_type.like(f"{expect_task_prefix}%"),
                    )
                )
                .order_by(AsyncTask.created_at.desc())
            )
            task = await db.scalar(stmt)
            if not task:
                return
            task.status = TaskStatus.COMPLETED
            task.completed_at = utc_now()
            task.result_data = result_data or {}
            db.add(task)

        return None

    # Removed: Task type normalization moved to unified mapping
    # Use src.common.events.mapping.normalize_task_type instead

    async def _persist_domain_event(
        self,
        *,
        scope_type: str,
        session_id: str,
        event_action: str,
        payload: dict[str, Any],
        correlation_id: str | None,
    ) -> None:
        """Persist domain event + outbox (idempotent by correlation_id + event_type)."""
        evt_type = build_event_type(scope_type, event_action)
        aggregate_type = get_aggregate_type(scope_type)
        topic = get_domain_topic(scope_type)

        async with create_sql_session() as db:
            # Idempotency: check existing DomainEvent by (correlation_id, event_type)
            existing = None
            if correlation_id:
                try:
                    existing = await db.scalar(
                        select(DomainEvent).where(
                            and_(
                                DomainEvent.correlation_id == UUID(str(correlation_id)),
                                DomainEvent.event_type == evt_type,
                            )
                        )
                    )
                except Exception:
                    existing = None

            if existing is None:
                dom_evt = DomainEvent(
                    event_type=evt_type,
                    aggregate_type=aggregate_type,
                    aggregate_id=str(session_id),
                    payload=payload,
                    correlation_id=UUID(str(correlation_id)) if correlation_id else None,
                    causation_id=None,
                    event_metadata={"source": "orchestrator"},
                )
                db.add(dom_evt)
                await db.flush()
            else:
                dom_evt = existing

            # Upsert Outbox by id=domain_event.event_id
            out = await db.scalar(select(EventOutbox).where(EventOutbox.id == dom_evt.event_id))
            if out is None:
                out = EventOutbox(
                    id=dom_evt.event_id,
                    topic=topic,
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
                        "correlation_id": str(correlation_id) if correlation_id else None,
                    },
                    status=OutboxStatus.PENDING,
                )
                db.add(out)
            # commit via context manager
