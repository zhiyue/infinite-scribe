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
    def __init__(self, name: str, consume_topics: list[str], produce_topics: list[str] | None = None) -> None:
        super().__init__(name=name, consume_topics=consume_topics, produce_topics=produce_topics)

    async def process_message(
        self, message: dict[str, Any], context: dict[str, Any] | None = None
    ) -> dict[str, Any] | None:
        # Two possible shapes:
        # 1) DomainEvent envelope (from outbox relay)
        #    { event_type, aggregate_type, aggregate_id, payload, metadata, ... }
        # 2) Capability Envelope (agent bus) via BaseAgent: { id, ts, type, data:{...} }

        self.log.info(
            "orchestrator_message_received",
            message_keys=list(message.keys()),
            has_context=context is not None,
            context_keys=list(context.keys()) if context else [],
        )

        # Domain event shape
        if "event_type" in message and "aggregate_id" in message:
            self.log.info(
                "orchestrator_processing_domain_event",
                event_type=message.get("event_type"),
                aggregate_id=message.get("aggregate_id"),
                has_payload=bool(message.get("payload")),
            )
            # 传入 context 以便在 handler 内部解析 headers 中的 correlation_id
            return await self._handle_domain_event(message, context or {})

        # Capability event envelope - 从context中获取type而非message
        msg_type = (context or {}).get("meta", {}).get("type") or message.get("type")
        if msg_type:
            self.log.info(
                "orchestrator_processing_capability_event",
                msg_type=msg_type,
                topic=context.get("topic") if context else None,
                has_data=bool(message.get("data")),
            )
            return await self._handle_capability_event(msg_type, message, context or {})

        self.log.debug("orchestrator_ignored_message", reason="unknown_shape")
        return None

    async def _handle_domain_event(self, evt: dict[str, Any], context: dict[str, Any] | None = None) -> dict[str, Any] | None:
        event_type = str(evt.get("event_type"))
        aggregate_id = str(evt.get("aggregate_id"))
        payload = evt.get("payload") or {}
        metadata = evt.get("metadata") or {}
        # 优先从 context.meta 或 headers 提取 correlation_id，其次才从事件本体中获取
        correlation_id: str | None = None
        try:
            if context:
                meta = (context or {}).get("meta") or {}
                if isinstance(meta, dict):
                    correlation_id = correlation_id or meta.get("correlation_id")
                headers = (context or {}).get("headers")
                # headers 可能是 dict 或 list[tuple[str, bytes]]
                if isinstance(headers, dict):
                    correlation_id = correlation_id or headers.get("correlation_id") or headers.get("correlation-id")
                elif isinstance(headers, list):
                    for k, v in headers:
                        if str(k).lower().replace("_", "-") in {"correlation-id", "correlation_id"}:
                            try:
                                correlation_id = correlation_id or (
                                    v.decode("utf-8") if isinstance(v, (bytes, bytearray)) else str(v)
                                )
                            except Exception:
                                correlation_id = correlation_id or (str(v) if v is not None else None)
                            break
        except Exception:
            # 解析失败不影响后续逻辑，按原有回退策略
            pass
        correlation_id = correlation_id or metadata.get("correlation_id") or evt.get("correlation_id")

        self.log.info(
            "orchestrator_domain_event_details",
            event_type=event_type,
            aggregate_id=aggregate_id,
            correlation_id=correlation_id,
            payload_keys=list(payload.keys()) if payload else [],
            metadata_keys=list(metadata.keys()) if metadata else [],
        )

        # Only react to trigger-class events (commands/user actions)
        if not event_type.endswith("Command.Received"):
            self.log.debug(
                "orchestrator_domain_event_ignored",
                event_type=event_type,
                reason="not_command_received",
            )
            return None

        cmd_type = (payload or {}).get("command_type")
        if not cmd_type:
            self.log.warning(
                "orchestrator_domain_event_missing_command_type",
                event_type=event_type,
                aggregate_id=aggregate_id,
                payload_keys=list(payload.keys()) if payload else [],
            )
            return None

        scope_prefix = event_type.split(".", 1)[0] if "." in event_type else "Genesis"
        scope_type = scope_prefix.upper()  # e.g., GENESIS

        self.log.info(
            "orchestrator_processing_command",
            cmd_type=cmd_type,
            scope_type=scope_type,
            scope_prefix=scope_prefix,
            aggregate_id=aggregate_id,
        )

        # Map command to domain requested + capability task
        mapping = command_registry.process_command(
            cmd_type=cmd_type,
            scope_type=scope_type,
            scope_prefix=scope_prefix,
            aggregate_id=aggregate_id,
            payload=payload,
        )

        if not mapping:
            self.log.warning(
                "orchestrator_command_mapping_failed",
                cmd_type=cmd_type,
                scope_type=scope_type,
                aggregate_id=aggregate_id,
                reason="no_mapping_found",
            )
            return None

        self.log.info(
            "orchestrator_command_mapped",
            cmd_type=cmd_type,
            requested_action=mapping.requested_action,
            capability_type=mapping.capability_message.get("type"),
            has_capability_input=bool(mapping.capability_message.get("input")),
        )

        # 1) Project to domain facts (*Requested) via DB Outbox
        try:
            # Propagate context (user_id/timestamp) for SSE routing downstream
            enriched_payload = {
                "session_id": aggregate_id,
                "input": (payload or {}).get("payload", {}),
            }
            if (payload or {}).get("user_id"):
                enriched_payload["user_id"] = (payload or {}).get("user_id")
            if evt.get("created_at"):
                enriched_payload["timestamp"] = evt.get("created_at")

            await self._persist_domain_event(
                scope_type=scope_type,
                session_id=aggregate_id,
                event_action=mapping.requested_action,
                payload=enriched_payload,
                correlation_id=correlation_id,
            )
            self.log.info(
                "orchestrator_domain_event_persisted",
                scope_type=scope_type,
                event_action=mapping.requested_action,
                aggregate_id=aggregate_id,
            )
        except Exception as e:
            self.log.error(
                "orchestrator_domain_event_persist_failed",
                scope_type=scope_type,
                event_action=mapping.requested_action,
                aggregate_id=aggregate_id,
                error=str(e),
                exc_info=True,
            )
            raise

        # 2) Emit capability task (agent bus) and create AsyncTask for tracking
        try:
            await self._create_async_task(
                correlation_id=correlation_id,
                session_id=aggregate_id,
                task_type=normalize_task_type(mapping.capability_message.get("type", "")),
                input_data=mapping.capability_message.get("input") or {},
            )
            self.log.info(
                "orchestrator_async_task_created",
                correlation_id=correlation_id,
                task_type=normalize_task_type(mapping.capability_message.get("type", "")),
                aggregate_id=aggregate_id,
            )
        except Exception as e:
            self.log.warning(
                "async_task_create_failed",
                correlation_id=correlation_id,
                task=mapping.capability_message.get("type"),
                error=str(e),
                exc_info=True,
            )

        self.log.info(
            "orchestrator_domain_event_processed",
            cmd_type=cmd_type,
            scope_type=scope_type,
            aggregate_id=aggregate_id,
            correlation_id=correlation_id,
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

        self.log.info(
            "orchestrator_capability_event_details",
            msg_type=msg_type,
            session_id=session_id,
            topic=topic,
            scope_prefix=scope_prefix,
            scope_type=scope_type,
            correlation_id=correlation_id,
            data_keys=list(data.keys()) if data else [],
        )

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

        for i, handler in enumerate(handlers):
            self.log.debug(
                "orchestrator_trying_handler",
                handler_index=i,
                msg_type=msg_type,
                session_id=session_id,
            )

            action = handler()
            if action:
                self.log.info(
                    "orchestrator_handler_matched",
                    handler_index=i,
                    msg_type=msg_type,
                    session_id=session_id,
                    has_domain_event=bool(action.domain_event),
                    has_task_completion=bool(action.task_completion),
                    has_capability_message=bool(action.capability_message),
                )
                return await self._execute_event_action(action)

        self.log.debug(
            "orchestrator_no_handler_matched",
            msg_type=msg_type,
            session_id=session_id,
            handlers_tried=len(handlers),
        )
        return None

    async def _execute_event_action(self, action) -> dict[str, Any] | None:
        """Execute the actions specified by an event handler."""
        self.log.info(
            "orchestrator_executing_event_action",
            has_domain_event=bool(action.domain_event),
            has_task_completion=bool(action.task_completion),
            has_capability_message=bool(action.capability_message),
        )

        # Persist domain event if specified
        if action.domain_event:
            try:
                self.log.info("orchestrator_persisting_domain_event", **action.domain_event)
                await self._persist_domain_event(**action.domain_event)
                self.log.info(
                    "orchestrator_domain_event_persisted_success",
                    event_action=action.domain_event.get("event_action"),
                    scope_type=action.domain_event.get("scope_type"),
                )
            except Exception as e:
                self.log.error(
                    "orchestrator_domain_event_persist_failed",
                    error=str(e),
                    domain_event_params=action.domain_event,
                    exc_info=True,
                )
                raise

        # Complete async task if specified
        if action.task_completion:
            try:
                self.log.info("orchestrator_completing_async_task", **action.task_completion)
                await self._complete_async_task(**action.task_completion)
                self.log.info(
                    "orchestrator_async_task_completed_success",
                    correlation_id=action.task_completion.get("correlation_id"),
                    expect_task_prefix=action.task_completion.get("expect_task_prefix"),
                )
            except Exception as e:
                self.log.error(
                    "orchestrator_async_task_complete_failed",
                    error=str(e),
                    task_completion_params=action.task_completion,
                    exc_info=True,
                )
                # 不抛出异常，任务完成失败不应该阻止消息返回

        # Return capability message for further processing
        if action.capability_message:
            self.log.info(
                "orchestrator_returning_capability_message",
                message_type=action.capability_message.get("type"),
                has_input=bool(action.capability_message.get("input")),
            )

        return action.capability_message

    async def _create_async_task(
        self, *, correlation_id: str | None, session_id: str, task_type: str, input_data: dict[str, Any]
    ) -> None:
        """Create an AsyncTask row to track capability execution with idempotency protection."""
        from datetime import UTC, datetime

        self.log.info(
            "orchestrator_creating_async_task",
            correlation_id=correlation_id,
            session_id=session_id,
            task_type=task_type,
            input_data_keys=list(input_data.keys()) if input_data else [],
        )

        if not task_type:
            self.log.warning(
                "orchestrator_async_task_skipped",
                reason="empty_task_type",
                correlation_id=correlation_id,
                session_id=session_id,
            )
            return

        trig_cmd_id = None
        if correlation_id:
            try:
                trig_cmd_id = UUID(str(correlation_id))
                self.log.debug(
                    "orchestrator_async_task_correlation_parsed",
                    correlation_id=correlation_id,
                    trig_cmd_id=str(trig_cmd_id),
                )
            except Exception as e:
                self.log.warning(
                    "orchestrator_async_task_correlation_parse_failed",
                    correlation_id=correlation_id,
                    error=str(e),
                )
                trig_cmd_id = None

        async with create_sql_session() as db:
            # Check for existing RUNNING/PENDING task to prevent duplicates
            if trig_cmd_id:
                self.log.debug(
                    "orchestrator_checking_existing_task",
                    trig_cmd_id=str(trig_cmd_id),
                    task_type=task_type,
                )

                existing_stmt = select(AsyncTask).where(
                    and_(
                        AsyncTask.triggered_by_command_id == trig_cmd_id,
                        AsyncTask.task_type == task_type,
                        AsyncTask.status.in_([TaskStatus.RUNNING, TaskStatus.PENDING]),
                    )
                )
                existing_task = await db.scalar(existing_stmt)
                if existing_task:
                    self.log.info(
                        "async_task_already_exists",
                        correlation_id=correlation_id,
                        task_type=task_type,
                        existing_task_id=str(existing_task.id),
                        existing_status=existing_task.status.value
                        if hasattr(existing_task.status, "value")
                        else str(existing_task.status),
                    )
                    return

            self.log.info(
                "orchestrator_creating_new_async_task",
                task_type=task_type,
                trig_cmd_id=str(trig_cmd_id) if trig_cmd_id else None,
                session_id=session_id,
            )

            task = AsyncTask(
                task_type=task_type,
                triggered_by_command_id=trig_cmd_id,
                status=TaskStatus.RUNNING,
                started_at=datetime.now(UTC),
                input_data={"session_id": session_id, **(input_data or {})},
            )
            db.add(task)
            await db.flush()

            self.log.info(
                "orchestrator_async_task_created_success",
                task_id=str(task.id),
                task_type=task_type,
                status=task.status.value if hasattr(task.status, "value") else str(task.status),
                correlation_id=correlation_id,
                session_id=session_id,
            )

    async def _complete_async_task(
        self, *, correlation_id: str | None, expect_task_prefix: str, result_data: dict[str, Any]
    ) -> None:
        """Mark latest RUNNING/PENDING AsyncTask (by correlation) as COMPLETED.

        Args:
            correlation_id: UUID string from envelope meta
            expect_task_prefix: Prefix of task_type to match (e.g., "Character.Design.Generation")
        """
        from src.common.utils.datetime_utils import utc_now

        self.log.info(
            "orchestrator_completing_async_task",
            correlation_id=correlation_id,
            expect_task_prefix=expect_task_prefix,
            result_data_keys=list(result_data.keys()) if result_data else [],
        )

        if not correlation_id:
            self.log.warning(
                "orchestrator_async_task_complete_skipped",
                reason="no_correlation_id",
                expect_task_prefix=expect_task_prefix,
            )
            return

        try:
            trig_cmd_id = UUID(str(correlation_id))
            self.log.debug(
                "orchestrator_async_task_complete_correlation_parsed",
                correlation_id=correlation_id,
                trig_cmd_id=str(trig_cmd_id),
            )
        except Exception as e:
            self.log.warning(
                "orchestrator_async_task_complete_correlation_parse_failed",
                correlation_id=correlation_id,
                error=str(e),
            )
            return

        async with create_sql_session() as db:
            self.log.debug(
                "orchestrator_searching_async_task_to_complete",
                trig_cmd_id=str(trig_cmd_id),
                expect_task_prefix=expect_task_prefix,
            )

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
                self.log.warning(
                    "orchestrator_async_task_not_found_for_completion",
                    correlation_id=correlation_id,
                    expect_task_prefix=expect_task_prefix,
                    trig_cmd_id=str(trig_cmd_id),
                )
                return

            self.log.info(
                "orchestrator_async_task_found_for_completion",
                task_id=str(task.id),
                task_type=task.task_type,
                current_status=task.status.value if hasattr(task.status, "value") else str(task.status),
                created_at=str(task.created_at),
            )

            task.status = TaskStatus.COMPLETED
            task.completed_at = utc_now()
            task.result_data = result_data or {}
            db.add(task)

            self.log.info(
                "orchestrator_async_task_completed_success",
                task_id=str(task.id),
                task_type=task.task_type,
                correlation_id=correlation_id,
                result_data_size=len(str(result_data)) if result_data else 0,
            )

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

        self.log.info(
            "orchestrator_persisting_domain_event",
            scope_type=scope_type,
            session_id=session_id,
            event_action=event_action,
            correlation_id=correlation_id,
            evt_type=evt_type,
            aggregate_type=aggregate_type,
            topic=topic,
            payload_keys=list(payload.keys()) if payload else [],
        )

        async with create_sql_session() as db:
            # Idempotency: check existing DomainEvent by (correlation_id, event_type)
            existing = None
            if correlation_id:
                try:
                    self.log.debug(
                        "orchestrator_checking_existing_domain_event",
                        correlation_id=correlation_id,
                        evt_type=evt_type,
                    )

                    existing = await db.scalar(
                        select(DomainEvent).where(
                            and_(
                                DomainEvent.correlation_id == UUID(str(correlation_id)),
                                DomainEvent.event_type == evt_type,
                            )
                        )
                    )

                    if existing:
                        self.log.info(
                            "orchestrator_domain_event_already_exists",
                            correlation_id=correlation_id,
                            evt_type=evt_type,
                            existing_event_id=str(existing.event_id),
                            existing_aggregate_id=existing.aggregate_id,
                        )
                    else:
                        self.log.debug(
                            "orchestrator_no_existing_domain_event_found",
                            correlation_id=correlation_id,
                            evt_type=evt_type,
                        )
                except Exception as e:
                    self.log.warning(
                        "orchestrator_existing_domain_event_check_failed",
                        correlation_id=correlation_id,
                        evt_type=evt_type,
                        error=str(e),
                    )
                    existing = None

            if existing is None:
                self.log.info(
                    "orchestrator_creating_new_domain_event",
                    evt_type=evt_type,
                    aggregate_type=aggregate_type,
                    aggregate_id=session_id,
                    correlation_id=correlation_id,
                )

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

                self.log.info(
                    "orchestrator_domain_event_created",
                    event_id=str(dom_evt.event_id),
                    evt_type=evt_type,
                    aggregate_id=session_id,
                )
            else:
                dom_evt = existing
                self.log.debug(
                    "orchestrator_using_existing_domain_event",
                    event_id=str(dom_evt.event_id),
                    evt_type=evt_type,
                )

            # Upsert Outbox by id=domain_event.event_id
            self.log.debug(
                "orchestrator_checking_outbox_entry",
                domain_event_id=str(dom_evt.event_id),
            )

            out = await db.scalar(select(EventOutbox).where(EventOutbox.id == dom_evt.event_id))
            if out is None:
                self.log.info(
                    "orchestrator_creating_outbox_entry",
                    event_id=str(dom_evt.event_id),
                    topic=topic,
                    key=session_id,
                )

                # Fix: Flatten the payload structure to avoid double nesting
                outbox_payload = {
                    "event_id": str(dom_evt.event_id),
                    "event_type": dom_evt.event_type,
                    "aggregate_type": dom_evt.aggregate_type,
                    "aggregate_id": dom_evt.aggregate_id,
                    "metadata": dom_evt.event_metadata or {},
                }
                # Merge domain event payload directly instead of nesting under "payload" key
                outbox_payload.update(dom_evt.payload or {})
                # Add created_at for downstream timestamp fallback
                try:
                    if getattr(dom_evt, "created_at", None):
                        outbox_payload["created_at"] = dom_evt.created_at.isoformat()  # type: ignore[attr-defined]
                except Exception:
                    pass

                out = EventOutbox(
                    id=dom_evt.event_id,
                    topic=topic,
                    key=str(session_id),
                    partition_key=str(session_id),
                    payload=outbox_payload,
                    headers={
                        "event_type": dom_evt.event_type,
                        "version": 1,
                        "correlation_id": str(correlation_id) if correlation_id else None,
                    },
                    status=OutboxStatus.PENDING,
                )
                db.add(out)

                self.log.info(
                    "orchestrator_outbox_entry_created",
                    event_id=str(dom_evt.event_id),
                    topic=topic,
                    status=out.status.value if hasattr(out.status, "value") else str(out.status),
                )
            else:
                self.log.debug(
                    "orchestrator_outbox_entry_already_exists",
                    event_id=str(dom_evt.event_id),
                    existing_status=out.status.value if hasattr(out.status, "value") else str(out.status),
                )

        self.log.info(
            "orchestrator_domain_event_persist_completed",
            evt_type=evt_type,
            event_id=str(dom_evt.event_id),
            session_id=session_id,
            correlation_id=correlation_id,
        )
        # commit via context manager
