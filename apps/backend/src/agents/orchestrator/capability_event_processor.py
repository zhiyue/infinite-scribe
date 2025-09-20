"""Capability Event Processing Module

Handles capability event processing for the orchestrator.
Extracts event data, tries different handlers, and prepares actions for execution.
"""

from __future__ import annotations

from typing import Any

from src.agents.orchestrator.event_handlers import CapabilityEventHandlers, EventAction


class EventDataExtractor:
    """Extracts and normalizes data from capability events."""

    @staticmethod
    def extract_event_data(message: dict[str, Any]) -> dict[str, Any]:
        """Extract data from message, preferring 'data' field but falling back to message itself."""
        return message.get("data") or message

    @staticmethod
    def extract_session_and_scope(data: dict[str, Any], context: dict[str, Any]) -> tuple[str, dict[str, str]]:
        """Extract session ID and scope information from data and context."""
        session_id = str(data.get("session_id") or data.get("aggregate_id") or "")
        topic = context.get("topic") or ""

        # Infer scope from topic prefix (e.g., genesis.outline.events)
        scope_prefix = topic.split(".", 1)[0].upper() if "." in topic else "GENESIS"
        scope_type = scope_prefix

        scope_info = {
            "topic": topic,
            "scope_prefix": scope_prefix,
            "scope_type": scope_type,
        }

        return session_id, scope_info

    @staticmethod
    def extract_correlation_id(context: dict[str, Any], data: dict[str, Any]) -> str | None:
        """Extract correlation_id, preferring context['meta'] but falling back to data."""
        return context.get("meta", {}).get("correlation_id") or data.get("correlation_id")

    @staticmethod
    def extract_causation_id(context: dict[str, Any], data: dict[str, Any]) -> str | None:
        """Extract causation_id (capability event's event_id for downstream domain events)."""
        return context.get("meta", {}).get("event_id") or data.get("event_id")


class EventHandlerMatcher:
    """Matches events to appropriate handlers and executes them."""

    def __init__(self, logger):
        self.log = logger

    def find_matching_handler(
        self,
        msg_type: str,
        session_id: str,
        data: dict[str, Any],
        correlation_id: str | None,
        scope_info: dict[str, str],
        causation_id: str | None,
    ) -> EventAction | None:
        """Try different event handlers in sequence until one matches."""
        scope_type = scope_info["scope_type"]
        scope_prefix = scope_info["scope_prefix"]

        # Define handlers to try in sequence
        handlers = [
            lambda: CapabilityEventHandlers.handle_generation_completed(
                msg_type, session_id, data, correlation_id, scope_type, scope_prefix, causation_id
            ),
            lambda: CapabilityEventHandlers.handle_quality_review_result(
                msg_type, session_id, data, correlation_id, scope_type, scope_prefix, causation_id
            ),
            lambda: CapabilityEventHandlers.handle_consistency_check_result(
                msg_type, session_id, data, correlation_id, scope_type, causation_id
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
                return action

        self.log.debug(
            "orchestrator_no_handler_matched",
            msg_type=msg_type,
            session_id=session_id,
            handlers_tried=len(handlers),
        )
        return None


class CapabilityEventProcessor:
    """Main capability event processing orchestrator."""

    def __init__(self, logger):
        self.log = logger
        self.data_extractor = EventDataExtractor()
        self.handler_matcher = EventHandlerMatcher(logger)

    async def handle_capability_event(
        self, msg_type: str, message: dict[str, Any], context: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Handle capability event processing with orchestration."""
        # Extract event data and context
        data = self.data_extractor.extract_event_data(message)
        session_id, scope_info = self.data_extractor.extract_session_and_scope(data, context)
        correlation_id = self.data_extractor.extract_correlation_id(context, data)
        causation_id = self.data_extractor.extract_causation_id(context, data)

        self.log.info(
            "orchestrator_capability_event_details",
            msg_type=msg_type,
            session_id=session_id,
            topic=scope_info["topic"],
            scope_prefix=scope_info["scope_prefix"],
            scope_type=scope_info["scope_type"],
            correlation_id=correlation_id,
            data_keys=list(data.keys()) if data else [],
        )

        # Find matching handler
        action = self.handler_matcher.find_matching_handler(
            msg_type, session_id, data, correlation_id, scope_info, causation_id
        )

        if not action:
            return None

        # Return action for execution by the main orchestrator
        return {
            "action": action,
            "msg_type": msg_type,
            "session_id": session_id,
            "correlation_id": correlation_id,
        }
