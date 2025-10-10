"""Workflow configuration management for the orchestrator."""

from __future__ import annotations

import copy
import json
import os
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, ClassVar


class WorkflowConfigError(RuntimeError):
    """Raised when workflow configuration cannot be loaded."""


@dataclass
class WorkflowThresholds:
    """Numeric thresholds that drive workflow decisions."""

    quality_threshold: float
    max_attempts: int
    consistency_threshold: float = 1.0


@dataclass
class WorkflowRouting:
    """Routing rules that determine downstream actions."""

    event_target_mapping: dict[str, str] = field(default_factory=dict)
    target_confirmation_actions: dict[str, str] = field(default_factory=dict)
    target_failure_actions: dict[str, str] = field(default_factory=dict)
    target_regeneration_actions: dict[str, str] = field(default_factory=dict)
    task_prefix_mapping: dict[str, str] = field(default_factory=dict)


@dataclass
class WorkflowConfig:
    """Complete workflow configuration payload."""

    name: str
    thresholds: WorkflowThresholds
    routing: WorkflowRouting
    metadata: dict[str, Any] = field(default_factory=dict)
    description: str | None = None
    version: str | None = None


class EventHandlerConfig:
    """Configuration facade used by the orchestrator event handlers."""

    DEFAULT_WORKFLOW_FILENAME = "genesis-workflow.json"
    ENV_WORKFLOW_PATH = "ORCHESTRATOR_WORKFLOW_CONFIG"

    _cached_default_config: ClassVar[WorkflowConfig | None] = None
    _config_lock: ClassVar[threading.Lock] = threading.Lock()

    def __init__(self, config_source: str | Path | WorkflowConfig | None = None) -> None:
        if isinstance(config_source, WorkflowConfig):
            self._config = config_source
        else:
            self._config = self._load_config_from_source(config_source)

    # ---------------------------------------------------------------------
    # Configuration loading helpers
    # ---------------------------------------------------------------------
    @classmethod
    def workflows_dir(cls) -> Path:
        """Return directory where workflow configuration files are stored."""
        return Path(__file__).resolve().parent

    @classmethod
    def default_config_path(cls) -> Path:
        """Determine the default configuration path with environment override."""
        env_override = os.getenv(cls.ENV_WORKFLOW_PATH)
        if env_override:
            return Path(env_override).expanduser().resolve()
        return cls.workflows_dir() / cls.DEFAULT_WORKFLOW_FILENAME

    @classmethod
    def _load_config_from_source(cls, config_source: str | Path | None) -> WorkflowConfig:
        if isinstance(config_source, str | Path):
            return cls._load_from_file(Path(config_source))
        return cls._get_default_config()

    @classmethod
    def _get_default_config(cls) -> WorkflowConfig:
        """Load (and cache) the default workflow configuration with thread safety."""
        if cls._cached_default_config is None:
            with cls._config_lock:
                # Double-checked locking pattern
                if cls._cached_default_config is None:
                    cls._cached_default_config = cls._create_builtin_default_config()
        # Return a deep copy to avoid accidental mutations across instances
        return copy.deepcopy(cls._cached_default_config)

    @classmethod
    def _create_builtin_default_config(cls) -> WorkflowConfig:
        """Create the built-in default genesis workflow configuration."""
        thresholds = WorkflowThresholds(
            quality_threshold=7.5,
            max_attempts=3,
            consistency_threshold=1.0,
        )

        routing = WorkflowRouting(
            event_target_mapping={
                "Genesis.Character.Command.Received": "character",
                "Genesis.Theme.Command.Received": "theme",
                "Genesis.World.Command.Received": "world",
                "Character.Design.Generated": "character",
                "Character.Generated": "character",
                "Outliner.Theme.Generated": "theme",
                "Theme.Generated": "theme",
            },
            target_confirmation_actions={
                "character": "Character.Confirmed",
                "theme": "Theme.Confirmed",
                "world": "Stage.Confirmed",
            },
            target_failure_actions={
                "character": "Character.Failed",
                "theme": "Theme.Failed",
                "world": "Stage.Failed",
            },
            target_regeneration_actions={
                "character": "Character.RegenerationRequested",
                "theme": "Theme.RegenerationRequested",
                "world": "Stage.RegenerationRequested",
            },
            task_prefix_mapping={
                "Character.Design": "Character.Design",
                "Theme.Creation": "Theme.Creation",
                "World.Building": "World.Building",
                "quality_review": "Review.Quality.Evaluation",
                "consistency_check": "Review.Consistency.Check",
            },
        )

        return WorkflowConfig(
            name="genesis-workflow",
            description="Genesis stage workflow configuration",
            version="1.0.0",
            thresholds=thresholds,
            routing=routing,
            metadata={
                "created_by": "system",
                "environment": "builtin",
            },
        )

    @classmethod
    def _load_from_file(cls, file_path: Path) -> WorkflowConfig:
        if not file_path.exists():
            raise WorkflowConfigError(f"Workflow config file not found: {file_path}")

        with file_path.open(encoding="utf-8") as f:
            config_data = json.load(f)

        try:
            thresholds_data = config_data["thresholds"]
            routing_data = config_data["routing"]
        except KeyError as exc:  # pragma: no cover - defensive guard, JSON is versioned
            raise WorkflowConfigError(f"Missing required workflow section: {exc}") from exc

        return WorkflowConfig(
            name=config_data.get("name", cls.DEFAULT_WORKFLOW_FILENAME.rsplit(".", 1)[0]),
            description=config_data.get("description"),
            version=config_data.get("version"),
            thresholds=WorkflowThresholds(**thresholds_data),
            routing=WorkflowRouting(**routing_data),
            metadata=config_data.get("metadata", {}),
        )

    # ---------------------------------------------------------------------
    # Alternate constructors
    # ---------------------------------------------------------------------
    @classmethod
    def from_file(cls, config_file: str | Path) -> EventHandlerConfig:
        """Instantiate configuration from a user-provided file path."""
        return cls(Path(config_file))

    @classmethod
    def from_config(cls, config: WorkflowConfig) -> EventHandlerConfig:
        """Instantiate configuration from a pre-built workflow config object."""
        return cls(config)

    @classmethod
    def for_genesis_workflow(cls) -> EventHandlerConfig:
        """Return configuration bound to the canonical genesis workflow."""
        return cls(cls._get_default_config())

    @classmethod
    def for_testing(cls, **overrides: Any) -> EventHandlerConfig:
        """Create a configuration tailored for tests with lightweight overrides."""
        config = cls._get_default_config()

        if overrides:
            thresholds = WorkflowThresholds(
                quality_threshold=overrides.get("quality_threshold", config.thresholds.quality_threshold),
                max_attempts=overrides.get("max_attempts", config.thresholds.max_attempts),
                consistency_threshold=overrides.get("consistency_threshold", config.thresholds.consistency_threshold),
            )
            routing = WorkflowRouting(
                event_target_mapping=overrides.get(
                    "event_target_mapping", copy.deepcopy(config.routing.event_target_mapping)
                ),
                target_confirmation_actions=overrides.get(
                    "target_confirmation_actions", copy.deepcopy(config.routing.target_confirmation_actions)
                ),
                target_failure_actions=overrides.get(
                    "target_failure_actions", copy.deepcopy(config.routing.target_failure_actions)
                ),
                target_regeneration_actions=overrides.get(
                    "target_regeneration_actions", copy.deepcopy(config.routing.target_regeneration_actions)
                ),
                task_prefix_mapping=overrides.get(
                    "task_prefix_mapping", copy.deepcopy(config.routing.task_prefix_mapping)
                ),
            )
            config = WorkflowConfig(
                name=config.name,
                description=config.description,
                version=config.version,
                metadata=copy.deepcopy(config.metadata),
                thresholds=thresholds,
                routing=routing,
            )

        return cls(config)

    # ---------------------------------------------------------------------
    # Convenience accessors used by event commands
    # ---------------------------------------------------------------------
    @property
    def QUALITY_THRESHOLD(self) -> float:  # noqa: N802
        return self._config.thresholds.quality_threshold

    @property
    def MAX_ATTEMPTS(self) -> int:  # noqa: N802
        return self._config.thresholds.max_attempts

    @property
    def CONSISTENCY_THRESHOLD(self) -> float:  # noqa: N802
        return self._config.thresholds.consistency_threshold

    @property
    def EVENT_TARGET_MAPPING(self) -> dict[str, str]:  # noqa: N802
        return self._config.routing.event_target_mapping

    @property
    def TARGET_CONFIRMATION_ACTIONS(self) -> dict[str, str]:  # noqa: N802
        return self._config.routing.target_confirmation_actions

    @property
    def TARGET_FAILURE_ACTIONS(self) -> dict[str, str]:  # noqa: N802
        return self._config.routing.target_failure_actions

    @property
    def TARGET_REGENERATION_ACTIONS(self) -> dict[str, str]:  # noqa: N802
        return self._config.routing.target_regeneration_actions

    @property
    def TASK_PREFIX_MAPPING(self) -> dict[str, str]:  # noqa: N802
        return self._config.routing.task_prefix_mapping

    @property
    def METADATA(self) -> dict[str, Any]:  # noqa: N802
        return self._config.metadata

    def to_dict(self) -> dict[str, Any]:
        """Export configuration as a serialisable dictionary (primarily used in tests/debugging)."""
        return {
            "name": self._config.name,
            "description": self._config.description,
            "version": self._config.version,
            "thresholds": {
                "quality_threshold": self.QUALITY_THRESHOLD,
                "max_attempts": self.MAX_ATTEMPTS,
                "consistency_threshold": self.CONSISTENCY_THRESHOLD,
            },
            "routing": {
                "event_target_mapping": copy.deepcopy(self.EVENT_TARGET_MAPPING),
                "target_confirmation_actions": copy.deepcopy(self.TARGET_CONFIRMATION_ACTIONS),
                "target_failure_actions": copy.deepcopy(self.TARGET_FAILURE_ACTIONS),
                "target_regeneration_actions": copy.deepcopy(self.TARGET_REGENERATION_ACTIONS),
                "task_prefix_mapping": copy.deepcopy(self.TASK_PREFIX_MAPPING),
            },
            "metadata": copy.deepcopy(self.METADATA),
        }
