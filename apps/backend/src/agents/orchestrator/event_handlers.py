"""Event Handlers for Capability Events

Contains focused handler functions for different types of capability events,
extracted from the main orchestrator to improve readability and maintainability.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any

from src.agents.orchestrator.message_factory import MessageFactory
from src.agents.orchestrator.types import (
    ConsistencyCheckData,
    GenerationData,
    QualityReviewData,
)
from src.agents.orchestrator.workflow_constants import WORKFLOW_DEFAULTS
from src.agents.orchestrator.workflow_rules import (
    ConfigBasedWorkflowRules,
    IWorkflowRules,
    QualityReviewRequest,
    ReviewResult,
)
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


class QualityReviewCommand(EventCommand):
    """Command for handling quality review result events."""

    def can_handle(self, msg_type: str) -> bool:
        """Check if this is a quality review result event."""
        from src.common.events.mapping import is_quality_review_event
        return is_quality_review_event(msg_type)

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
        """Handle quality review result events."""
        if not (self.can_handle(msg_type) and session_id):
            return None

        # Extract data fields with safe type conversion
        def safe_float(value, default=0.0):
            """Safely convert value to float with fallback."""
            if value is None:
                return default
            try:
                return float(value)
            except (ValueError, TypeError):
                return default

        def safe_int(value, default=0):
            """Safely convert value to int with fallback."""
            if value is None:
                return default
            try:
                return int(value)
            except (ValueError, TypeError):
                return default

        score = safe_float(getattr(data, 'score', None) or getattr(data, 'quality_score', None))
        attempts = safe_int(getattr(data, 'attempts', None))
        max_attempts = safe_int(getattr(data, 'max_attempts', None), WORKFLOW_DEFAULTS.MAX_ATTEMPTS)
        threshold = safe_float(getattr(data, 'threshold', None), WORKFLOW_DEFAULTS.QUALITY_THRESHOLD)
        target_type = str(getattr(data, 'target_type', None) or getattr(data, 'entity', None) or "content").lower()

        # Create quality review request
        request = QualityReviewRequest(
            score=score,
            attempts=attempts,
            max_attempts=max_attempts,
            threshold=threshold,
            target_type=target_type
        )

        # Use business rules to make decision
        decision = self.workflow_rules.evaluate_quality_review(request)

        builder = EventActionBuilder()

        # Add task completion (common for all paths)
        task_prefix = self.workflow_rules.get_task_prefix("quality_review")
        builder.with_task_completion(
            correlation_id=correlation_id,
            expect_task_prefix=task_prefix,
            result_data=data.model_dump(),
        )

        # Add domain event based on decision
        payload_base = {"session_id": session_id, "score": score}
        if decision.result in [ReviewResult.REJECTED_RETRY, ReviewResult.REJECTED_FAILED]:
            payload_base["attempts"] = attempts + 1

        builder.with_domain_event(
            scope_type=scope_type,
            session_id=session_id,
            event_action=decision.action,
            payload=payload_base,
            correlation_id=correlation_id,
            causation_id=causation_id,
        )

        # Add regeneration capability message if needed
        if decision.result == ReviewResult.REJECTED_RETRY:
            capability_message = MessageFactory.create_regeneration_message(
                target_type=target_type, session_id=session_id, attempts=attempts, scope_prefix=scope_prefix
            )
            if capability_message:
                builder.with_capability_message(capability_message)

        return builder.build()


class ConsistencyCheckCommand(EventCommand):
    """Command for handling consistency check result events."""

    def can_handle(self, msg_type: str) -> bool:
        """Check if this is a consistency check result event."""
        return msg_type in {"Review.Consistency.Checked", "Consistency.Checked"}

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
        """Handle consistency check result events."""
        if not (self.can_handle(msg_type) and session_id):
            return None

        # Use business rules to determine consistency result
        ok = self.workflow_rules.should_confirm_consistency(data.model_dump())

        builder = EventActionBuilder()

        # Add task completion - use business rules
        task_prefix = self.workflow_rules.get_task_prefix("consistency_check")
        builder.with_task_completion(
            correlation_id=correlation_id,
            expect_task_prefix=task_prefix,
            result_data=data.model_dump(),
        )

        # Add domain event based on result
        event_action = "Stage.Confirmed" if ok else "Stage.Failed"
        builder.with_domain_event(
            scope_type=scope_type,
            session_id=session_id,
            event_action=event_action,
            payload={"session_id": session_id, "result": data.model_dump()},
            correlation_id=correlation_id,
            causation_id=causation_id,
        )

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
            QualityReviewCommand(workflow_rules=self.workflow_rules),
            ConsistencyCheckCommand(workflow_rules=self.workflow_rules),
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

    def orchestrate_quality_review(
        self,
        msg_type: str,
        session_id: str,
        data: QualityReviewData,
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

    def orchestrate_consistency_check(
        self,
        msg_type: str,
        session_id: str,
        data: ConsistencyCheckData,
        correlation_id: str | None,
        scope_type: str,
        scope_prefix: str = "",
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
        orchestrator: WorkflowOrchestrator | None = None
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

    def handle_quality_review_event(
        self,
        msg_type: str,
        session_id: str,
        data: QualityReviewData,
        correlation_id: str | None,
        scope_type: str,
        scope_prefix: str,
        causation_id: str | None = None,
    ) -> EventAction | None:
        return self.orchestrator.orchestrate_quality_review(
            msg_type=msg_type,
            session_id=session_id,
            data=data,
            correlation_id=correlation_id,
            scope_type=scope_type,
            scope_prefix=scope_prefix,
            causation_id=causation_id,
        )

    def handle_consistency_check_event(
        self,
        msg_type: str,
        session_id: str,
        data: ConsistencyCheckData,
        correlation_id: str | None,
        scope_type: str,
        scope_prefix: str,
        causation_id: str | None = None,
    ) -> EventAction | None:
        return self.orchestrator.orchestrate_consistency_check(
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

    @classmethod
    def handle_quality_review_result(
        cls,
        msg_type: str,
        session_id: str,
        data: QualityReviewData,
        correlation_id: str | None,
        scope_type: str,
        scope_prefix: str,
        causation_id: str | None = None,
    ) -> EventAction | None:
        return cls._default().orchestrate_quality_review(
            msg_type=msg_type,
            session_id=session_id,
            data=data,
            correlation_id=correlation_id,
            scope_type=scope_type,
            scope_prefix=scope_prefix,
            causation_id=causation_id,
        )

    @classmethod
    def handle_consistency_check_result(
        cls,
        msg_type: str,
        session_id: str,
        data: ConsistencyCheckData,
        correlation_id: str | None,
        scope_type: str,
        scope_prefix: str,
        causation_id: str | None = None,
    ) -> EventAction | None:
        return cls._default().orchestrate_consistency_check(
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
    QualityReviewData: CapabilityEventHandlers.handle_quality_review_result,
    ConsistencyCheckData: CapabilityEventHandlers.handle_consistency_check_result,
}
