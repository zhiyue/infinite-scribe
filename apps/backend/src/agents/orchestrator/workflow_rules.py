"""Business rules interface for workflow orchestration.

This module decouples business logic from JSON configuration by providing
a clean interface for workflow decision making.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any


class ReviewResult(Enum):
    """Result of quality or consistency review."""

    APPROVED = "approved"
    REJECTED_RETRY = "rejected_retry"
    REJECTED_FAILED = "rejected_failed"


@dataclass
class QualityReviewRequest:
    """Request for quality review decision."""

    score: float
    attempts: int
    max_attempts: int
    threshold: float
    target_type: str


@dataclass
class WorkflowDecision:
    """Decision result from workflow rules."""

    result: ReviewResult
    action: str
    reason: str | None = None


class IWorkflowRules(ABC):
    """Interface for workflow business rules.

    This interface abstracts workflow decisions from configuration details,
    allowing business logic to focus on behavior rather than data structure.
    """

    @abstractmethod
    def get_target_for_event(self, event_type: str) -> str | None:
        """Get target type for a generation event."""

    @abstractmethod
    def get_task_prefix(self, task_type: str) -> str:
        """Get task prefix for a given task type."""

    @abstractmethod
    def evaluate_quality_review(self, request: QualityReviewRequest) -> WorkflowDecision:
        """Evaluate quality review and return decision."""

    @abstractmethod
    def get_confirmation_action(self, target_type: str) -> str:
        """Get confirmation action for target type."""

    @abstractmethod
    def get_failure_action(self, target_type: str) -> str:
        """Get failure action for target type."""

    @abstractmethod
    def get_regeneration_action(self, target_type: str) -> str:
        """Get regeneration action for target type."""

    @abstractmethod
    def should_confirm_consistency(self, result_data: dict[str, Any]) -> bool:
        """Determine if consistency check result should be confirmed."""


class ConfigBasedWorkflowRules(IWorkflowRules):
    """Implementation of workflow rules based on configuration.

    This class bridges the gap between the new business rules interface
    and the existing configuration system during the migration period.
    """

    def __init__(self, config: Any) -> None:
        """Initialize with existing configuration object."""
        self._config = config

    def get_target_for_event(self, event_type: str) -> str | None:
        """Get target type for a generation event."""
        return self._config.EVENT_TARGET_MAPPING.get(event_type)

    def get_task_prefix(self, task_type: str) -> str:
        """Get task prefix for a given task type."""
        default_mapping = {
            "quality_review": "Review.Quality.Evaluation",
            "consistency_check": "Review.Consistency.Check",
        }
        return self._config.TASK_PREFIX_MAPPING.get(task_type, default_mapping.get(task_type, "Unknown"))

    def evaluate_quality_review(self, request: QualityReviewRequest) -> WorkflowDecision:
        """Evaluate quality review and return decision."""
        # Quality passed - confirm the content
        if request.score >= request.threshold:
            action = self.get_confirmation_action(request.target_type)
            return WorkflowDecision(
                result=ReviewResult.APPROVED,
                action=action,
                reason=f"Score {request.score} >= threshold {request.threshold}"
            )

        # Max attempts reached - mark as failed
        if request.attempts + 1 >= request.max_attempts:
            action = self.get_failure_action(request.target_type)
            return WorkflowDecision(
                result=ReviewResult.REJECTED_FAILED,
                action=action,
                reason=f"Max attempts ({request.max_attempts}) reached"
            )

        # Quality not met, but attempts remaining - trigger regeneration
        action = self.get_regeneration_action(request.target_type)
        return WorkflowDecision(
            result=ReviewResult.REJECTED_RETRY,
            action=action,
            reason=f"Score {request.score} < threshold {request.threshold}, attempts: {request.attempts + 1}"
        )

    def get_confirmation_action(self, target_type: str) -> str:
        """Get confirmation action for target type."""
        return self._config.TARGET_CONFIRMATION_ACTIONS.get(target_type, "Stage.Confirmed")

    def get_failure_action(self, target_type: str) -> str:
        """Get failure action for target type."""
        return self._config.TARGET_FAILURE_ACTIONS.get(target_type, "Stage.Failed")

    def get_regeneration_action(self, target_type: str) -> str:
        """Get regeneration action for target type."""
        return self._config.TARGET_REGENERATION_ACTIONS.get(target_type, "Stage.RegenerationRequested")

    def should_confirm_consistency(self, result_data: dict[str, Any]) -> bool:
        """Determine if consistency check result should be confirmed."""
        # Support three types of judgments: boolean ok/passed; or numeric score >= threshold
        ok = bool(result_data.get("ok") or result_data.get("passed"))
        if not ok:
            score = result_data.get("score", 0.0)
            threshold = result_data.get("threshold", 1.0)
            try:
                ok = float(score) >= float(threshold)
            except Exception:
                ok = False
        return ok


class StaticWorkflowRules(IWorkflowRules):
    """Static implementation of workflow rules without external configuration.

    This implementation embeds the business rules directly in code,
    eliminating the dependency on JSON configuration files.
    """

    # Event to target type mapping
    _EVENT_TARGET_MAPPING = {
        "Character.Design.Generated": "character",
        "Character.Generated": "character",
        "Outliner.Theme.Generated": "theme",
        "Theme.Generated": "theme",
    }

    # Task prefixes
    _TASK_PREFIXES = {
        "quality_review": "Review.Quality.Evaluation",
        "consistency_check": "Review.Consistency.Check",
    }

    # Actions for different target types
    _CONFIRMATION_ACTIONS = {
        "character": "Character.Confirmed",
        "theme": "Theme.Confirmed",
    }

    _FAILURE_ACTIONS = {
        "character": "Character.Failed",
        "theme": "Theme.Failed",
    }

    _REGENERATION_ACTIONS = {
        "character": "Character.RegenerationRequested",
        "theme": "Theme.RegenerationRequested",
    }

    # Default thresholds
    _QUALITY_THRESHOLD = 7.5
    _MAX_ATTEMPTS = 3
    _CONSISTENCY_THRESHOLD = 1.0

    def get_target_for_event(self, event_type: str) -> str | None:
        """Get target type for a generation event."""
        return self._EVENT_TARGET_MAPPING.get(event_type)

    def get_task_prefix(self, task_type: str) -> str:
        """Get task prefix for a given task type."""
        return self._TASK_PREFIXES.get(task_type, "Unknown")

    def evaluate_quality_review(self, request: QualityReviewRequest) -> WorkflowDecision:
        """Evaluate quality review and return decision."""
        # Use defaults if not provided
        threshold = request.threshold or self._QUALITY_THRESHOLD
        max_attempts = request.max_attempts or self._MAX_ATTEMPTS

        # Quality passed - confirm the content
        if request.score >= threshold:
            action = self.get_confirmation_action(request.target_type)
            return WorkflowDecision(
                result=ReviewResult.APPROVED,
                action=action,
                reason=f"Score {request.score} >= threshold {threshold}"
            )

        # Max attempts reached - mark as failed
        if request.attempts + 1 >= max_attempts:
            action = self.get_failure_action(request.target_type)
            return WorkflowDecision(
                result=ReviewResult.REJECTED_FAILED,
                action=action,
                reason=f"Max attempts ({max_attempts}) reached"
            )

        # Quality not met, but attempts remaining - trigger regeneration
        action = self.get_regeneration_action(request.target_type)
        return WorkflowDecision(
            result=ReviewResult.REJECTED_RETRY,
            action=action,
            reason=f"Score {request.score} < threshold {threshold}, attempts: {request.attempts + 1}"
        )

    def get_confirmation_action(self, target_type: str) -> str:
        """Get confirmation action for target type."""
        return self._CONFIRMATION_ACTIONS.get(target_type, "Stage.Confirmed")

    def get_failure_action(self, target_type: str) -> str:
        """Get failure action for target type."""
        return self._FAILURE_ACTIONS.get(target_type, "Stage.Failed")

    def get_regeneration_action(self, target_type: str) -> str:
        """Get regeneration action for target type."""
        return self._REGENERATION_ACTIONS.get(target_type, "Stage.RegenerationRequested")

    def should_confirm_consistency(self, result_data: dict[str, Any]) -> bool:
        """Determine if consistency check result should be confirmed."""
        # Support three types of judgments: boolean ok/passed; or numeric score >= threshold
        ok = bool(result_data.get("ok") or result_data.get("passed"))
        if not ok:
            score = result_data.get("score", 0.0)
            threshold = result_data.get("threshold", self._CONSISTENCY_THRESHOLD)
            try:
                ok = float(score) >= float(threshold)
            except Exception:
                ok = False
        return ok