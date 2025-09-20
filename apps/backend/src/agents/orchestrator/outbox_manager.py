"""Outbox Management Module

Handles domain event persistence and capability task enqueueing for the orchestrator.
Provides idempotent operations for domain events and outbox entries.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import and_, select

from src.agents.message import encode_message
from src.common.events.config import build_event_type, get_aggregate_type, get_domain_topic
from src.db.sql.session import create_sql_session
from src.models.event import DomainEvent
from src.models.workflow import EventOutbox
from src.schemas.enums import OutboxStatus


class DomainEventIdempotencyChecker:
    """Handles domain event idempotency validation."""

    @staticmethod
    async def check_existing_domain_event(correlation_id: str, evt_type: str, db_session) -> DomainEvent | None:
        """Check if domain event already exists by correlation_id and event_type."""
        try:
            return await db_session.scalar(
                select(DomainEvent).where(
                    and_(
                        DomainEvent.correlation_id == UUID(str(correlation_id)),
                        DomainEvent.event_type == evt_type,
                    )
                )
            )
        except Exception:
            # If correlation_id is invalid UUID or other error, treat as no existing event
            return None


class DomainEventCreator:
    """Handles domain event creation."""

    def __init__(self, logger):
        self.log = logger
        self.idempotency_checker = DomainEventIdempotencyChecker()

    async def create_or_get_domain_event(
        self,
        scope_type: str,
        session_id: str,
        event_action: str,
        payload: dict[str, Any],
        correlation_id: str | None,
        causation_id: str | None,
        db_session,
    ) -> DomainEvent:
        """Create new domain event or return existing one if found by correlation_id + event_type."""
        evt_type = build_event_type(scope_type, event_action)
        aggregate_type = get_aggregate_type(scope_type)

        # Check for existing domain event (idempotency)
        existing = None
        if correlation_id:
            self.log.debug(
                "orchestrator_checking_existing_domain_event",
                correlation_id=correlation_id,
                evt_type=evt_type,
            )

            existing = await self.idempotency_checker.check_existing_domain_event(correlation_id, evt_type, db_session)

            if existing:
                self.log.info(
                    "orchestrator_domain_event_already_exists",
                    correlation_id=correlation_id,
                    evt_type=evt_type,
                    existing_event_id=str(existing.event_id),
                    existing_aggregate_id=existing.aggregate_id,
                )
                return existing
            else:
                self.log.debug(
                    "orchestrator_no_existing_domain_event_found",
                    correlation_id=correlation_id,
                    evt_type=evt_type,
                )

        # Create new domain event
        self.log.info(
            "orchestrator_creating_new_domain_event",
            evt_type=evt_type,
            aggregate_type=aggregate_type,
            aggregate_id=session_id,
            correlation_id=correlation_id,
        )

        domain_event = DomainEvent(
            event_type=evt_type,
            aggregate_type=aggregate_type,
            aggregate_id=str(session_id),
            payload=payload,
            correlation_id=UUID(str(correlation_id)) if correlation_id else None,
            causation_id=UUID(str(causation_id)) if causation_id else None,
            event_metadata={"source": "orchestrator"},
        )
        db_session.add(domain_event)
        await db_session.flush()

        self.log.info(
            "orchestrator_domain_event_created",
            event_id=str(domain_event.event_id),
            evt_type=evt_type,
            aggregate_id=session_id,
        )

        return domain_event


class OutboxEntryCreator:
    """Handles outbox entry creation."""

    def __init__(self, logger):
        self.log = logger

    async def create_or_get_outbox_entry(
        self,
        domain_event: DomainEvent,
        scope_type: str,
        session_id: str,
        correlation_id: str | None,
        db_session,
    ) -> EventOutbox:
        """Create outbox entry or return existing one if found by domain event id."""
        topic = get_domain_topic(scope_type)

        # Check for existing outbox entry (idempotency by domain event id)
        self.log.debug(
            "orchestrator_checking_outbox_entry",
            domain_event_id=str(domain_event.event_id),
        )

        existing_outbox = await self._check_existing_outbox(domain_event.event_id, db_session)
        if existing_outbox:
            self.log.debug(
                "orchestrator_outbox_entry_already_exists",
                event_id=str(domain_event.event_id),
                existing_status=existing_outbox.status.value
                if hasattr(existing_outbox.status, "value")
                else str(existing_outbox.status),
            )
            return existing_outbox

        # Create new outbox entry
        self.log.info(
            "orchestrator_creating_outbox_entry",
            event_id=str(domain_event.event_id),
            topic=topic,
            key=session_id,
        )

        outbox_payload = self._build_outbox_payload(domain_event)

        outbox_entry = EventOutbox(
            id=domain_event.event_id,
            topic=topic,
            key=str(session_id),
            partition_key=str(session_id),
            payload=outbox_payload,
            headers={
                "event_type": domain_event.event_type,
                "version": 1,
                "correlation_id": str(correlation_id) if correlation_id else None,
            },
            status=OutboxStatus.PENDING,
        )
        db_session.add(outbox_entry)

        self.log.info(
            "orchestrator_outbox_entry_created",
            event_id=str(domain_event.event_id),
            topic=topic,
            status=outbox_entry.status.value if hasattr(outbox_entry.status, "value") else str(outbox_entry.status),
        )

        return outbox_entry

    async def _check_existing_outbox(self, event_id: UUID, db_session) -> EventOutbox | None:
        """Check if outbox entry already exists for the given event_id."""
        return await db_session.scalar(select(EventOutbox).where(EventOutbox.id == event_id))

    def _build_outbox_payload(self, domain_event: DomainEvent) -> dict:
        """Build outbox payload from domain event."""
        # Flatten the payload structure to avoid double nesting
        outbox_payload = {
            "event_id": str(domain_event.event_id),
            "event_type": domain_event.event_type,
            "aggregate_type": domain_event.aggregate_type,
            "aggregate_id": domain_event.aggregate_id,
            "metadata": domain_event.event_metadata or {},
        }
        # Merge domain event payload directly instead of nesting under "payload" key
        outbox_payload.update(domain_event.payload or {})

        # Add created_at for downstream timestamp fallback
        try:
            if getattr(domain_event, "created_at", None):
                outbox_payload["created_at"] = domain_event.created_at.isoformat()  # type: ignore[attr-defined]
        except Exception:
            pass

        return outbox_payload


class CapabilityTaskEnqueuer:
    """Handles capability task enqueueing."""

    def __init__(self, logger, agent_name: str):
        self.log = logger
        self.agent_name = agent_name

    async def enqueue_capability_task(self, capability_message: dict[str, Any], correlation_id: str | None) -> None:
        """Enqueue capability task to EventOutbox for relay to publish to Kafka."""
        # Extract routing
        topic = capability_message.get("_topic")
        key = capability_message.get("_key") or capability_message.get("session_id")

        if not topic:
            self.log.warning("capability_task_enqueue_skipped", reason="missing_topic", msg=capability_message)
            return

        # Build envelope payload (strip routing keys)
        result_payload = {k: v for k, v in capability_message.items() if k not in {"_topic", "_key"}}
        envelope = encode_message(self.agent_name, result_payload, correlation_id=correlation_id, retries=0)

        await self._create_outbox_entry(envelope, correlation_id, topic, key)

    async def _create_outbox_entry(
        self,
        envelope: dict,
        correlation_id: str | None,
        topic: str,
        key: Any,
    ) -> None:
        """Create outbox entry for capability task."""
        async with create_sql_session() as db:
            outbox_entry = EventOutbox(
                topic=topic,
                key=str(key) if key is not None else None,
                partition_key=str(key) if key is not None else None,
                payload=envelope,
                headers={
                    "type": envelope.get("type"),
                    "version": envelope.get("version"),
                    "correlation_id": correlation_id,
                    "agent": self.agent_name,
                },
                status=OutboxStatus.PENDING,
            )
            db.add(outbox_entry)
            # flush for log id
            await db.flush()

            self.log.debug(
                "capability_task_outbox_created",
                outbox_id=str(outbox_entry.id),
                topic=topic,
                key=key,
            )


class OutboxManager:
    """Unified outbox management interface."""

    def __init__(self, logger, agent_name: str):
        self.log = logger
        self.domain_event_creator = DomainEventCreator(logger)
        self.outbox_entry_creator = OutboxEntryCreator(logger)
        self.capability_enqueuer = CapabilityTaskEnqueuer(logger, agent_name)

    async def persist_domain_event(
        self,
        *,
        scope_type: str,
        session_id: str,
        event_action: str,
        payload: dict[str, Any],
        correlation_id: str | None,
        causation_id: str | None = None,
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
            # Create or get domain event (idempotent)
            domain_event = await self.domain_event_creator.create_or_get_domain_event(
                scope_type, session_id, event_action, payload, correlation_id, causation_id, db
            )

            # Create or get outbox entry (idempotent)
            await self.outbox_entry_creator.create_or_get_outbox_entry(
                domain_event, scope_type, session_id, correlation_id, db
            )

        self.log.info(
            "orchestrator_domain_event_persist_completed",
            evt_type=evt_type,
            event_id=str(domain_event.event_id),
            session_id=session_id,
            correlation_id=correlation_id,
        )

    async def enqueue_capability_task(self, *, capability_message: dict[str, Any], correlation_id: str | None) -> None:
        """Enqueue capability task to outbox for relay to publish to Kafka."""
        await self.capability_enqueuer.enqueue_capability_task(capability_message, correlation_id)
