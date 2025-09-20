"""Event Handlers for Capability Events

Contains focused handler functions for different types of capability events,
extracted from the main orchestrator to improve readability and maintainability.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, NamedTuple

from src.agents.orchestrator.message_factory import MessageFactory
from src.agents.orchestrator.types import (
    ConsistencyCheckData,
    GenerationData,
    QualityReviewData,
)


class EventAction(NamedTuple):
    """Represents an action to be taken after handling an event."""

    domain_event: dict[str, Any] | None = None  # 保持dict用于参数解包
    task_completion: dict[str, Any] | None = None  # 保持dict用于参数解包
    capability_message: dict[str, Any] | None = None  # 保持dict用于参数解包


import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class WorkflowThresholds:
    """工作流阈值配置"""

    quality_threshold: float
    max_attempts: int
    consistency_threshold: float = 1.0


@dataclass
class WorkflowRouting:
    """工作流路由规则配置"""

    event_target_mapping: dict[str, str]
    target_confirmation_actions: dict[str, str]
    target_failure_actions: dict[str, str]
    target_regeneration_actions: dict[str, str]
    task_prefix_mapping: dict[str, str]


@dataclass
class WorkflowConfig:
    """单个工作流完整配置"""

    name: str
    thresholds: WorkflowThresholds
    routing: WorkflowRouting
    metadata: dict[str, Any] = field(default_factory=dict)


class EventHandlerConfig:
    """工作流编排器配置管理器 - 真正的配置驱动"""

    def __init__(self, config_source: str | Path | WorkflowConfig | None = None):
        """初始化配置管理器

        Args:
            config_source: 配置来源，可以是:
                - 文件路径 (str/Path)
                - 配置对象 (WorkflowConfig)
                - None (使用默认配置)
        """
        if isinstance(config_source, (str, Path)):
            self._config = self._load_from_file(Path(config_source))
        elif isinstance(config_source, WorkflowConfig):
            self._config = config_source
        else:
            self._config = self._get_default_config()

    @property
    def QUALITY_THRESHOLD(self) -> float:
        return self._config.thresholds.quality_threshold

    @property
    def MAX_ATTEMPTS(self) -> int:
        return self._config.thresholds.max_attempts

    @property
    def EVENT_TARGET_MAPPING(self) -> dict[str, str]:
        return self._config.routing.event_target_mapping

    @property
    def TARGET_CONFIRMATION_ACTIONS(self) -> dict[str, str]:
        return self._config.routing.target_confirmation_actions

    @property
    def TARGET_FAILURE_ACTIONS(self) -> dict[str, str]:
        return self._config.routing.target_failure_actions

    @property
    def TARGET_REGENERATION_ACTIONS(self) -> dict[str, str]:
        return self._config.routing.target_regeneration_actions

    @property
    def TASK_PREFIX_MAPPING(self) -> dict[str, str]:
        return self._config.routing.task_prefix_mapping

    def _load_from_file(self, file_path: Path) -> WorkflowConfig:
        """从配置文件加载工作流配置"""
        if not file_path.exists():
            raise FileNotFoundError(f"Workflow config file not found: {file_path}")

        with open(file_path, encoding="utf-8") as f:
            config_data = json.load(f)

        return WorkflowConfig(
            name=config_data["name"],
            thresholds=WorkflowThresholds(**config_data["thresholds"]),
            routing=WorkflowRouting(**config_data["routing"]),
            metadata=config_data.get("metadata", {}),
        )

    def _get_default_config(self) -> WorkflowConfig:
        """获取默认配置 - 从配置文件加载，真正的单一来源"""
        # 尝试从配置文件加载
        config_file = Path(__file__).parent / "workflows" / "genesis-workflow.json"

        if config_file.exists():
            return self._load_from_file(config_file)

        # 仅在配置文件不存在时才使用硬编码兜底
        # 这种情况应该只在开发环境或配置文件缺失时发生
        import warnings

        warnings.warn(
            f"Workflow config file not found: {config_file}. "
            "Using hardcoded fallback configuration. "
            "This should not happen in production!",
            UserWarning,
        )

        return WorkflowConfig(
            name="fallback-hardcoded-config",
            thresholds=WorkflowThresholds(quality_threshold=7.5, max_attempts=3),
            routing=WorkflowRouting(
                event_target_mapping={
                    "Character.Design.Generated": "character",
                    "Character.Generated": "character",
                    "Outliner.Theme.Generated": "theme",
                    "Theme.Generated": "theme",
                },
                target_confirmation_actions={
                    "character": "Character.Confirmed",
                    "theme": "Theme.Confirmed",
                },
                target_failure_actions={
                    "character": "Character.Failed",
                    "theme": "Theme.Failed",
                },
                target_regeneration_actions={
                    "character": "Character.RegenerationRequested",
                    "theme": "Theme.RegenerationRequested",
                },
                task_prefix_mapping={
                    "quality_review": "Review.Quality.Evaluation",
                    "consistency_check": "Review.Consistency.Check",
                },
            ),
        )

    @classmethod
    def from_file(cls, config_file: str | Path) -> EventHandlerConfig:
        """从配置文件创建配置管理器"""
        return cls(config_file)

    @classmethod
    def from_config(cls, config: WorkflowConfig) -> EventHandlerConfig:
        """从配置对象创建配置管理器"""
        return cls(config)

    @classmethod
    def for_testing(cls, **overrides) -> EventHandlerConfig:
        """创建测试用配置"""
        default_config = cls()._get_default_config()

        # 应用覆盖
        if "quality_threshold" in overrides:
            default_config.thresholds.quality_threshold = overrides["quality_threshold"]
        if "max_attempts" in overrides:
            default_config.thresholds.max_attempts = overrides["max_attempts"]

        return cls.from_config(default_config)


class EventActionBuilder:
    """Builder for constructing EventAction objects."""

    def __init__(self):
        self._domain_event = None
        self._task_completion = None
        self._capability_message = None

    def with_domain_event(
        self,
        scope_type: str,
        session_id: str,
        event_action: str,
        payload: dict,
        correlation_id: str | None = None,
        causation_id: str | None = None,
    ) -> EventActionBuilder:
        """Add domain event to the action."""
        self._domain_event = {
            "scope_type": scope_type,
            "session_id": session_id,
            "event_action": event_action,
            "payload": payload,
            "correlation_id": correlation_id,
            "causation_id": causation_id,
        }
        return self

    def with_task_completion(
        self,
        correlation_id: str | None,
        expect_task_prefix: str,
        result_data: dict,
    ) -> EventActionBuilder:
        """Add task completion to the action."""
        self._task_completion = {
            "correlation_id": correlation_id,
            "expect_task_prefix": expect_task_prefix,
            "result_data": result_data,
        }
        return self

    def with_capability_message(self, message: dict) -> EventActionBuilder:
        """Add capability message to the action."""
        self._capability_message = message
        return self

    def build(self) -> EventAction:
        """Build the final EventAction."""
        return EventAction(
            domain_event=self._domain_event,
            task_completion=self._task_completion,
            capability_message=self._capability_message,
        )


class EventCommand(ABC):
    """Abstract base class for event command handlers."""

    def __init__(self, config: EventHandlerConfig = None):
        self.config = config or EventHandlerConfig()

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

    def __init__(self, config: EventHandlerConfig = None):
        self.config = config or EventHandlerConfig()
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


class CapabilityEventHandlers:
    """Handlers for different types of capability events (refactored with command pattern)."""

    def __init__(self, config: EventHandlerConfig = None):
        """Initialize with event command factory."""
        self.factory = EventCommandFactory(config)

    @staticmethod
    def handle_generation_completed(
        msg_type: str,
        session_id: str,
        data: GenerationData,
        correlation_id: str | None,
        scope_type: str,
        scope_prefix: str,
        causation_id: str | None = None,
    ) -> EventAction | None:
        """Handle generation completion events (legacy method - use factory for new code)."""
        factory = EventCommandFactory()
        return factory.handle_event(
            msg_type=msg_type,
            session_id=session_id,
            data=data,
            correlation_id=correlation_id,
            scope_type=scope_type,
            scope_prefix=scope_prefix,
            causation_id=causation_id,
        )

    @staticmethod
    def handle_quality_review_result(
        msg_type: str,
        session_id: str,
        data: QualityReviewData,
        correlation_id: str | None,
        scope_type: str,
        scope_prefix: str,
        causation_id: str | None = None,
    ) -> EventAction | None:
        """Handle quality review result events (legacy method - use factory for new code)."""
        factory = EventCommandFactory()
        return factory.handle_event(
            msg_type=msg_type,
            session_id=session_id,
            data=data,
            correlation_id=correlation_id,
            scope_type=scope_type,
            scope_prefix=scope_prefix,
            causation_id=causation_id,
        )

    @staticmethod
    def handle_consistency_check_result(
        msg_type: str,
        session_id: str,
        data: ConsistencyCheckData,
        correlation_id: str | None,
        scope_type: str,
        causation_id: str | None = None,
    ) -> EventAction | None:
        """Handle consistency check result events (legacy method - use factory for new code)."""
        factory = EventCommandFactory()
        return factory.handle_event(
            msg_type=msg_type,
            session_id=session_id,
            data=data,
            correlation_id=correlation_id,
            scope_type=scope_type,
            scope_prefix="",  # Default value for consistency check
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
        """Handle any event using the command pattern (recommended method)."""
        return self.factory.handle_event(
            msg_type=msg_type,
            session_id=session_id,
            data=data,
            correlation_id=correlation_id,
            scope_type=scope_type,
            scope_prefix=scope_prefix,
            causation_id=causation_id,
        )
