"""Domain Event Processing Module

Handles domain event processing for the orchestrator.
Extracts correlation IDs, validates events, maps commands, and orchestrates responses.
"""

from __future__ import annotations

from typing import Any

from src.agents.orchestrator.command_strategies import command_registry


class CorrelationIdExtractor:
    """Handles correlation ID extraction from various sources."""

    @staticmethod
    def extract_correlation_id(evt: dict[str, Any], context: dict[str, Any] | None) -> str | None:
        """Extract correlation_id from context.meta, headers, or event metadata."""
        correlation_id: str | None = None

        try:
            if context:
                # Try context.meta first
                meta = (context or {}).get("meta") or {}
                if isinstance(meta, dict):
                    correlation_id = correlation_id or meta.get("correlation_id")

                # Try headers (can be dict or list of tuples)
                headers = (context or {}).get("headers")
                if isinstance(headers, dict):
                    correlation_id = correlation_id or headers.get("correlation_id") or headers.get("correlation-id")
                elif isinstance(headers, list):
                    for k, v in headers:
                        if str(k).lower().replace("_", "-") in {"correlation-id", "correlation_id"}:
                            try:
                                correlation_id = correlation_id or (
                                    v.decode("utf-8") if isinstance(v, bytes | bytearray) else str(v)
                                )
                            except Exception:
                                correlation_id = correlation_id or (str(v) if v is not None else None)
                            break
        except Exception:
            # Parse failure doesn't affect downstream logic, use fallback strategy
            pass

        # Fallback to event metadata or direct event field
        correlation_id = correlation_id or evt.get("metadata", {}).get("correlation_id") or evt.get("correlation_id")

        return correlation_id


class EventValidator:
    """Validates domain events for processing."""

    @staticmethod
    def is_command_received_event(event_type: str) -> bool:
        """Check if event is a command received event that should be processed."""
        return event_type.endswith("Command.Received")

    @staticmethod
    def extract_command_type(evt: dict[str, Any]) -> str | None:
        """Extract command_type from event root level."""
        return evt.get("command_type")

    @staticmethod
    def extract_scope_info(event_type: str) -> tuple[str, str]:
        """Extract scope prefix and scope type from event type."""
        scope_prefix = event_type.split(".", 1)[0] if "." in event_type else "Genesis"
        scope_type = scope_prefix.upper()  # e.g., GENESIS
        return scope_prefix, scope_type


class CommandMapper:
    """Maps commands to domain events and capability tasks."""

    @staticmethod
    def map_command(
        cmd_type: str, scope_type: str, scope_prefix: str, aggregate_id: str, payload: dict
    ) -> Any:  # Returns CommandMapping from command_registry
        """Map command to domain requested + capability task using command registry."""
        return command_registry.process_command(
            cmd_type=cmd_type,
            scope_type=scope_type,
            scope_prefix=scope_prefix,
            aggregate_id=aggregate_id,
            payload=payload,
        )


class PayloadEnricher:
    """Enriches payloads with context information."""

    @staticmethod
    def enrich_domain_payload(evt: dict[str, Any], aggregate_id: str, payload: dict) -> dict[str, Any]:
        """Enrich payload with session context and propagate user_id/timestamp for SSE routing."""
        enriched_payload = {
            "session_id": aggregate_id,
            "input": payload,  # payload is already the nested command data
        }

        # Propagate context (user_id/timestamp) for SSE routing downstream
        if evt.get("user_id"):
            enriched_payload["user_id"] = evt.get("user_id")
        if evt.get("created_at"):
            enriched_payload["timestamp"] = evt.get("created_at")

        return enriched_payload


class DomainEventProcessor:
    """Main domain event processing orchestrator."""

    def __init__(self, logger):
        self.log = logger
        self.correlation_extractor = CorrelationIdExtractor()
        self.event_validator = EventValidator()
        self.command_mapper = CommandMapper()
        self.payload_enricher = PayloadEnricher()

    async def handle_domain_event(
        self, evt: dict[str, Any], context: dict[str, Any] | None = None
    ) -> dict[str, Any] | None:
        """Handle domain event processing with orchestration."""
        # Extract basic event information
        event_type = str(evt.get("event_type"))
        aggregate_id = str(evt.get("aggregate_id"))
        payload = evt.get("payload") or {}
        metadata = evt.get("metadata") or {}

        # Extract correlation ID from various sources
        correlation_id = self.correlation_extractor.extract_correlation_id(evt, context)

        self.log.info(
            "orchestrator_domain_event_details",
            event_type=event_type,
            aggregate_id=aggregate_id,
            correlation_id=correlation_id,
            payload_keys=list(payload.keys()) if payload else [],
            metadata_keys=list(metadata.keys()) if metadata else [],
        )

        # Validate event type - only process command received events
        if not self.event_validator.is_command_received_event(event_type):
            self.log.debug(
                "orchestrator_domain_event_ignored",
                event_type=event_type,
                reason="not_command_received",
            )
            return None

        # Extract command type
        cmd_type = self.event_validator.extract_command_type(evt)
        if not cmd_type:
            self.log.warning(
                "orchestrator_domain_event_missing_command_type",
                event_type=event_type,
                aggregate_id=aggregate_id,
                payload_keys=list(payload.keys()) if payload else [],
                evt_keys=list(evt.keys()),
            )
            return None

        # Extract scope information
        scope_prefix, scope_type = self.event_validator.extract_scope_info(event_type)

        self.log.info(
            "orchestrator_processing_command",
            cmd_type=cmd_type,
            scope_type=scope_type,
            scope_prefix=scope_prefix,
            aggregate_id=aggregate_id,
        )

        # Map command to domain event and capability task
        mapping = self.command_mapper.map_command(cmd_type, scope_type, scope_prefix, aggregate_id, payload)

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

        # Return processing instructions for the main orchestrator
        return {
            "correlation_id": correlation_id,
            "scope_type": scope_type,
            "aggregate_id": aggregate_id,
            "mapping": mapping,
            "enriched_payload": self.payload_enricher.enrich_domain_payload(evt, aggregate_id, payload),
            "causation_id": evt.get("event_id"),
        }