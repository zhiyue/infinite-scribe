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
from src.agents.orchestrator.workflows import EventAction, EventActionBuilder, EventHandlerConfig


class EventCommand(ABC):
    """Abstract base class for event command handlers."""

    def __init__(self, config: EventHandlerConfig | None = None):
        self.config = config or EventHandlerConfig.for_genesis_workflow()

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
        return msg_type in {
            "Character.Design.Generated",
            "Character.Generated",
            "Outliner.Theme.Generated",
            "Theme.Generated",
        }

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

        target_type = self.config.EVENT_TARGET_MAPPING.get(msg_type)
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
        return msg_type in {"Review.Quality.Evaluated", "Review.Quality.Result"}

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

        score = float(data.score or data.quality_score or 0.0)
        attempts = int(data.attempts or 0)
        max_attempts = int(data.max_attempts or self.config.MAX_ATTEMPTS)
        threshold = float(data.threshold or self.config.QUALITY_THRESHOLD)
        target_type = str(data.target_type or data.entity or "content").lower()

        builder = EventActionBuilder()

        # Add task completion (common for all paths) - use config
        task_prefix = self.config.TASK_PREFIX_MAPPING.get("quality_review", "Review.Quality.Evaluation")
        builder.with_task_completion(
            correlation_id=correlation_id,
            expect_task_prefix=task_prefix,
            result_data=data.model_dump(),
        )

        # Quality passed - confirm the content
        if score >= threshold:
            action = self.config.TARGET_CONFIRMATION_ACTIONS.get(target_type, "Stage.Confirmed")
            builder.with_domain_event(
                scope_type=scope_type,
                session_id=session_id,
                event_action=action,
                payload={"session_id": session_id, "score": score},
                correlation_id=correlation_id,
                causation_id=causation_id,
            )
            return builder.build()

        # Max attempts reached - mark as failed
        if attempts + 1 >= max_attempts:
            action = self.config.TARGET_FAILURE_ACTIONS.get(target_type, "Stage.Failed")
            builder.with_domain_event(
                scope_type=scope_type,
                session_id=session_id,
                event_action=action,
                payload={"session_id": session_id, "score": score, "attempts": attempts + 1},
                correlation_id=correlation_id,
                causation_id=causation_id,
            )
            return builder.build()

        # Quality not met, but attempts remaining - trigger regeneration
        regen_action = self.config.TARGET_REGENERATION_ACTIONS.get(target_type, "Stage.RegenerationRequested")
        builder.with_domain_event(
            scope_type=scope_type,
            session_id=session_id,
            event_action=regen_action,
            payload={"session_id": session_id, "score": score, "attempts": attempts + 1},
            correlation_id=correlation_id,
            causation_id=causation_id,
        )

        # Add regeneration capability message
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

        # Support three types of judgments: boolean ok/passed; or numeric score >= threshold
        ok = bool(data.ok or data.passed)
        if not ok:
            score = data.score or 0.0
            threshold = data.threshold or 1.0
            try:
                ok = float(score) >= float(threshold)
            except Exception:
                ok = False

        builder = EventActionBuilder()

        # Add task completion - use config
        task_prefix = self.config.TASK_PREFIX_MAPPING.get("consistency_check", "Review.Consistency.Check")
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

    def __init__(self, config: EventHandlerConfig | None = None):
        self.config = config or EventHandlerConfig.for_genesis_workflow()
        self._commands = [
            GenerationCompletedCommand(self.config),
            QualityReviewCommand(self.config),
            ConsistencyCheckCommand(self.config),
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
        config: EventHandlerConfig | None = None,
        factory: EventCommandFactory | None = None,
    ) -> None:
        self.config = config or EventHandlerConfig.for_genesis_workflow()
        self.factory = factory or EventCommandFactory(self.config)

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
        self, config: EventHandlerConfig | None = None, orchestrator: WorkflowOrchestrator | None = None
    ) -> None:
        self.orchestrator = orchestrator or WorkflowOrchestrator(config=config)

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
