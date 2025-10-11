"""Workflow constants to avoid hardcoded values throughout the codebase."""

from typing import Final


class WorkflowDefaults:
    """Default values for workflow configuration."""

    # Quality thresholds
    QUALITY_THRESHOLD: Final[float] = 7.5
    MAX_ATTEMPTS: Final[int] = 3
    CONSISTENCY_THRESHOLD: Final[float] = 1.0

    # Task prefixes
    QUALITY_REVIEW_PREFIX: Final[str] = "Review.Quality.Evaluation"
    CONSISTENCY_CHECK_PREFIX: Final[str] = "Review.Consistency.Check"

    # Event mappings
    EVENT_TARGET_MAPPING: Final[dict[str, str]] = {
        "Character.Design.Generated": "character",
        "Character.Generated": "character",
        "Outliner.Theme.Generated": "theme",
        "Theme.Generated": "theme",
        "Inquiry.Response.Generated": "inquiry",
    }

    # Action mappings
    CONFIRMATION_ACTIONS: Final[dict[str, str]] = {
        "character": "Character.Confirmed",
        "theme": "Theme.Confirmed",
        "inquiry": "Inquiry.Confirmed",
    }

    FAILURE_ACTIONS: Final[dict[str, str]] = {
        "character": "Character.Failed",
        "theme": "Theme.Failed",
        "inquiry": "Inquiry.Failed",
    }

    REGENERATION_ACTIONS: Final[dict[str, str]] = {
        "character": "Character.RegenerationRequested",
        "theme": "Theme.RegenerationRequested",
        "inquiry": "Inquiry.RegenerationRequested",
    }


# Global constants instance
WORKFLOW_DEFAULTS = WorkflowDefaults()


class WorkflowValidationError(ValueError):
    """Raised when workflow configuration validation fails."""


def validate_quality_threshold(threshold: float) -> None:
    """Validate quality threshold value."""
    if not (0.0 <= threshold <= 10.0):
        raise WorkflowValidationError(f"Quality threshold must be between 0.0 and 10.0, got {threshold}")


def validate_max_attempts(attempts: int) -> None:
    """Validate max attempts value."""
    if attempts < 1:
        raise WorkflowValidationError(f"Max attempts must be positive, got {attempts}")


def validate_consistency_threshold(threshold: float) -> None:
    """Validate consistency threshold value."""
    if threshold < 0.0:
        raise WorkflowValidationError(f"Consistency threshold must be non-negative, got {threshold}")


def validate_workflow_thresholds(
    quality_threshold: float, max_attempts: int, consistency_threshold: float
) -> list[str]:
    """Validate all workflow threshold values and return list of errors."""
    errors = []

    try:
        validate_quality_threshold(quality_threshold)
    except WorkflowValidationError as e:
        errors.append(str(e))

    try:
        validate_max_attempts(max_attempts)
    except WorkflowValidationError as e:
        errors.append(str(e))

    try:
        validate_consistency_threshold(consistency_threshold)
    except WorkflowValidationError as e:
        errors.append(str(e))

    return errors
