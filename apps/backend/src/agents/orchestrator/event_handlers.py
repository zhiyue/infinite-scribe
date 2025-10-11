"""Event Handlers for Capability Events

Contains focused handler functions for different types of capability events,
extracted from the main orchestrator to improve readability and maintainability.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any

from src.agents.orchestrator.message_factory import MessageFactory
from src.agents.orchestrator.types import GenerationData
from src.agents.orchestrator.workflow_rules import ConfigBasedWorkflowRules, IWorkflowRules
from src.agents.orchestrator.workflows import EventAction, EventActionBuilder, EventHandlerConfig


class EventCommand(ABC):
    """Abstract base class for event command handlers."""

    def __init__(self, workflow_rules: IWorkflowRules | None = None, config: EventHandlerConfig | None = None):
        # Support both new rules interface and legacy config for migration
        if workflow_rules:
            self.workflow_rules = workflow_rules
        else:
            # Backward compatibility: create rules from config
            config = config or EventHandlerConfig.for_genesis_workflow()
            self.workflow_rules = ConfigBasedWorkflowRules(config)
            self.config = config  # Keep for legacy code that still needs it

    @abstractmethod
    def can_handle(self, msg_type: str) -> bool:
        """Check if this command can handle the given message type."""
        pass

    @abstractmethod
    def execute(
        self,
        msg_type: str,
        session_id: str,
        data: Any,
        correlation_id: str | None,
        scope_type: str,
        scope_prefix: str = "",
        causation_id: str | None = None,
    ) -> EventAction | None:
        """Execute the command and return an EventAction."""
        pass


class GenerationCompletedCommand(EventCommand):
    """Command for handling generation completion events."""

    def can_handle(self, msg_type: str) -> bool:
        """Check if this is a generation completion event."""
        from src.common.events.mapping import is_generation_completed_event

        return is_generation_completed_event(msg_type)

    def execute(
        self,
        msg_type: str,
        session_id: str,
        data: Any,
        correlation_id: str | None,
        scope_type: str,
        scope_prefix: str = "",
        causation_id: str | None = None,
    ) -> EventAction | None:
        """Handle generation completion events."""
        if not (self.can_handle(msg_type) and session_id):
            return None

        target_type = self.workflow_rules.get_target_for_event(msg_type)
        if not target_type:
            return None

        # Get task prefix using existing mapping utility
        from src.common.events.mapping import normalize_task_type

        task_prefix = normalize_task_type(msg_type)

        # Build event action using builder pattern
        builder = EventActionBuilder()

        # Add domain event
        builder.with_domain_event(
            scope_type=scope_type,
            session_id=session_id,
            event_action=f"{target_type.capitalize()}.Proposed",
            payload={"session_id": session_id, "content": data.model_dump()},
            correlation_id=correlation_id,
            causation_id=causation_id,
        )

        # Add task completion
        builder.with_task_completion(
            correlation_id=correlation_id,
            expect_task_prefix=task_prefix,
            result_data=data.model_dump(),
        )

        # Add capability message
        capability_message = MessageFactory.create_quality_review_message(
            session_id=session_id, target_type=target_type, content=data.model_dump(), scope_prefix=scope_prefix
        )
        builder.with_capability_message(capability_message)

        return builder.build()


class EventCommandFactory:
    """Factory for creating event command handlers."""

    def __init__(self, workflow_rules: IWorkflowRules | None = None, config: EventHandlerConfig | None = None):
        # Support both new rules interface and legacy config for migration
        if workflow_rules:
            self.workflow_rules = workflow_rules
        else:
            # Backward compatibility: create rules from config
            config = config or EventHandlerConfig.for_genesis_workflow()
            self.workflow_rules = ConfigBasedWorkflowRules(config)

        self._commands = [
            GenerationCompletedCommand(workflow_rules=self.workflow_rules),
        ]

    def get_command(self, msg_type: str) -> EventCommand | None:
        """Get the appropriate command handler for a message type."""
        for command in self._commands:
            if command.can_handle(msg_type):
                return command
        return None

    def handle_event(
        self,
        msg_type: str,
        session_id: str,
        data: Any,
        correlation_id: str | None,
        scope_type: str,
        scope_prefix: str = "",
        causation_id: str | None = None,
    ) -> EventAction | None:
        """Handle an event using the appropriate command."""
        command = self.get_command(msg_type)
        if command:
            return command.execute(
                msg_type=msg_type,
                session_id=session_id,
                data=data,
                correlation_id=correlation_id,
                scope_type=scope_type,
                scope_prefix=scope_prefix,
                causation_id=causation_id,
            )
        return None


class WorkflowOrchestrator:
    """Core workflow orchestrator responsible for routing events to commands."""

    def __init__(
        self,
        workflow_rules: IWorkflowRules | None = None,
        config: EventHandlerConfig | None = None,
        factory: EventCommandFactory | None = None,
    ) -> None:
        # Support both new rules interface and legacy config for migration
        if workflow_rules:
            self.workflow_rules = workflow_rules
        elif config:
            self.workflow_rules = ConfigBasedWorkflowRules(config)
        else:
            # Default backward compatibility
            config = EventHandlerConfig.for_genesis_workflow()
            self.workflow_rules = ConfigBasedWorkflowRules(config)

        self.factory = factory or EventCommandFactory(workflow_rules=self.workflow_rules)

    def orchestrate_generation(
        self,
        msg_type: str,
        session_id: str,
        data: GenerationData,
        correlation_id: str | None,
        scope_type: str,
        scope_prefix: str,
        causation_id: str | None = None,
    ) -> EventAction | None:
        return self.orchestrate(
            msg_type=msg_type,
            session_id=session_id,
            data=data,
            correlation_id=correlation_id,
            scope_type=scope_type,
            scope_prefix=scope_prefix,
            causation_id=causation_id,
        )

    def orchestrate(
        self,
        *,
        msg_type: str,
        session_id: str,
        data: Any,
        correlation_id: str | None,
        scope_type: str,
        scope_prefix: str = "",
        causation_id: str | None = None,
    ) -> EventAction | None:
        return self.factory.handle_event(
            msg_type=msg_type,
            session_id=session_id,
            data=data,
            correlation_id=correlation_id,
            scope_type=scope_type,
            scope_prefix=scope_prefix,
            causation_id=causation_id,
        )


class CapabilityEventHandlers:
    """Backward-compatible facade exposing workflow orchestration entry points."""

    _default_orchestrator: WorkflowOrchestrator | None = None

    def __init__(
        self,
        workflow_rules: IWorkflowRules | None = None,
        config: EventHandlerConfig | None = None,
        orchestrator: WorkflowOrchestrator | None = None,
    ) -> None:
        if orchestrator:
            self.orchestrator = orchestrator
        elif workflow_rules:
            self.orchestrator = WorkflowOrchestrator(workflow_rules=workflow_rules)
        else:
            # Backward compatibility
            self.orchestrator = WorkflowOrchestrator(config=config)

    # ------------------------------------------------------------------
    # Instance-based API
    # ------------------------------------------------------------------
    def handle_generation_event(
        self,
        msg_type: str,
        session_id: str,
        data: GenerationData,
        correlation_id: str | None,
        scope_type: str,
        scope_prefix: str,
        causation_id: str | None = None,
    ) -> EventAction | None:
        return self.orchestrator.orchestrate_generation(
            msg_type=msg_type,
            session_id=session_id,
            data=data,
            correlation_id=correlation_id,
            scope_type=scope_type,
            scope_prefix=scope_prefix,
            causation_id=causation_id,
        )

    def handle_event(
        self,
        msg_type: str,
        session_id: str,
        data: Any,
        correlation_id: str | None,
        scope_type: str,
        scope_prefix: str = "",
        causation_id: str | None = None,
    ) -> EventAction | None:
        return self.orchestrator.orchestrate(
            msg_type=msg_type,
            session_id=session_id,
            data=data,
            correlation_id=correlation_id,
            scope_type=scope_type,
            scope_prefix=scope_prefix,
            causation_id=causation_id,
        )

    # ------------------------------------------------------------------
    # Class-level helpers to preserve historical static API
    # ------------------------------------------------------------------
    @classmethod
    def _default(cls) -> WorkflowOrchestrator:
        if cls._default_orchestrator is None:
            cls._default_orchestrator = WorkflowOrchestrator()
        return cls._default_orchestrator

    @classmethod
    def handle_generation_completed(
        cls,
        msg_type: str,
        session_id: str,
        data: GenerationData,
        correlation_id: str | None,
        scope_type: str,
        scope_prefix: str,
        causation_id: str | None = None,
    ) -> EventAction | None:
        return cls._default().orchestrate_generation(
            msg_type=msg_type,
            session_id=session_id,
            data=data,
            correlation_id=correlation_id,
            scope_type=scope_type,
            scope_prefix=scope_prefix,
            causation_id=causation_id,
        )


# ==============================================================================
# Dynamic Handler Dispatch Registry
# ==============================================================================

# Type alias for handler functions
HandlerFunction = Callable[..., EventAction | None]

# Core registry: maps data types to their corresponding handler functions
HANDLER_REGISTRY: dict[type, HandlerFunction] = {
    GenerationData: CapabilityEventHandlers.handle_generation_completed,
}
