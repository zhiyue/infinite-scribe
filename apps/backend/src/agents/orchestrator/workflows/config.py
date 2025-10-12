"""工作流配置管理模块

本模块负责编排器(orchestrator)的工作流配置加载、缓存和访问。
提供线程安全的配置管理,支持从文件加载、环境变量覆盖和内置默认配置。

核心设计决策:
- 使用双检锁模式实现线程安全的配置缓存
- 返回配置深拷贝防止意外修改
- 支持多种配置源(文件、对象、默认值)
- 配置分为阈值(thresholds)和路由(routing)两大类
"""

from __future__ import annotations

import copy
import json
import os
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, ClassVar


class WorkflowConfigError(RuntimeError):
    """工作流配置加载失败异常

    当配置文件不存在、格式错误或缺少必需字段时抛出。
    继承自RuntimeError表示这是一个严重的运行时错误,应该快速失败。
    """


@dataclass
class WorkflowThresholds:
    """工作流决策阈值配置

    定义驱动工作流自动决策的数值阈值,控制质量评估、重试策略和一致性检查。

    Attributes:
        quality_threshold: 质量评分阈值,生成内容的质量分数需达到此值才能通过审核
                          典型值为7.5(满分10分),低于此值将触发重新生成
        max_attempts: 最大重试次数,单个任务失败后允许的最大重新生成次数
                     超过此次数后任务将被标记为最终失败
        consistency_threshold: 一致性检查阈值,用于评估生成内容与现有设定的一致性
                              默认值1.0表示要求完全一致
    """

    quality_threshold: float  # 质量门槛,控制内容是否需要重新生成
    max_attempts: int  # 重试上限,防止无限重试消耗资源
    consistency_threshold: float = 1.0  # 一致性要求,确保世界观设定的连贯性


@dataclass
class WorkflowRouting:
    """工作流路由规则配置

    定义事件到下游动作的路由映射,控制不同领域对象(角色、主题、世界)的处理流程。
    采用基于目标(target)的路由策略,将事件名称映射到具体的领域标识。

    设计原则:
    - 事件驱动:通过事件名称确定处理目标
    - 领域隔离:不同领域(character/theme/world)有独立的确认和失败动作
    - 可扩展性:新增领域只需添加相应的映射关系

    Attributes:
        event_target_mapping: 事件到目标领域的映射
                            键为完整事件名(如"Genesis.Character.Command.Received")
                            值为目标标识(如"character","theme","world")
        target_confirmation_actions: 目标确认动作映射
                                    当内容通过审核时,根据目标触发对应的确认事件
        target_failure_actions: 目标失败动作映射
                              当任务达到最大重试次数仍失败时触发
        target_regeneration_actions: 目标重新生成动作映射
                                   当质量不达标时触发重新生成请求
        task_prefix_mapping: 任务前缀映射,用于将任务类型映射到标准化的事件前缀
                           支持任务跟踪和审计
    """

    # 事件路由:确定哪个领域应该处理此事件
    event_target_mapping: dict[str, str] = field(default_factory=dict)
    # 确认动作:质量审核通过后的后续事件
    target_confirmation_actions: dict[str, str] = field(default_factory=dict)
    # 失败动作:任务最终失败时的通知事件
    target_failure_actions: dict[str, str] = field(default_factory=dict)
    # 重新生成动作:质量不达标时的重试事件
    target_regeneration_actions: dict[str, str] = field(default_factory=dict)
    # 任务前缀:标准化任务命名,便于监控和追踪
    task_prefix_mapping: dict[str, str] = field(default_factory=dict)


@dataclass
class WorkflowConfig:
    """完整的工作流配置数据结构

    聚合了工作流所需的所有配置信息,包括阈值、路由规则和元数据。
    作为不可变的配置快照在系统中传递。

    Attributes:
        name: 工作流名称标识,用于区分不同的工作流配置
        thresholds: 决策阈值配置,控制质量评估和重试策略
        routing: 路由规则配置,定义事件到动作的映射关系
        metadata: 附加元数据,存储创建者、环境等上下文信息
        description: 工作流描述信息,便于理解配置用途
        version: 配置版本号,用于版本管理和兼容性检查
    """

    name: str  # 唯一标识,用于日志和监控
    thresholds: WorkflowThresholds  # 阈值配置,驱动自动决策
    routing: WorkflowRouting  # 路由配置,控制事件流转
    metadata: dict[str, Any] = field(default_factory=dict)  # 扩展信息,不影响核心逻辑
    description: str | None = None  # 可选描述,提升可维护性
    version: str | None = None  # 版本标识,支持配置演进


class EventHandlerConfig:
    """编排器事件处理器配置门面

    为事件处理器提供统一的配置访问接口,封装配置加载、缓存和访问逻辑。

    核心功能:
    1. 多源配置加载:支持文件、对象、默认配置三种来源
    2. 线程安全缓存:使用双检锁模式缓存默认配置,避免重复加载
    3. 防御式拷贝:返回配置深拷贝,防止跨实例的意外修改
    4. 环境变量覆盖:支持通过环境变量指定配置文件路径

    设计模式:
    - Facade模式:简化配置访问的复杂性
    - Singleton缓存:默认配置全局唯一且延迟初始化
    - Immutable对象:通过深拷贝确保配置不可变性
    """

    # 默认配置文件名,位于当前模块目录
    DEFAULT_WORKFLOW_FILENAME = "genesis-workflow.json"
    # 环境变量名,用于覆盖默认配置路径
    ENV_WORKFLOW_PATH = "ORCHESTRATOR_WORKFLOW_CONFIG"

    # 类级别的默认配置缓存,所有实例共享
    _cached_default_config: ClassVar[WorkflowConfig | None] = None
    # 线程锁,保护缓存初始化过程的线程安全
    _config_lock: ClassVar[threading.Lock] = threading.Lock()

    def __init__(self, config_source: str | Path | WorkflowConfig | None = None) -> None:
        """初始化配置门面

        Args:
            config_source: 配置来源,支持三种类型:
                          - WorkflowConfig对象: 直接使用
                          - str/Path: 从指定文件加载
                          - None: 使用默认配置
        """
        if isinstance(config_source, WorkflowConfig):
            # 直接使用已构建的配置对象,适用于测试和程序化配置
            self._config = config_source
        else:
            # 从文件或默认配置加载
            self._config = self._load_config_from_source(config_source)

    # ---------------------------------------------------------------------
    # 配置加载辅助方法
    # ---------------------------------------------------------------------
    @classmethod
    def workflows_dir(cls) -> Path:
        """获取工作流配置文件所在目录

        Returns:
            当前模块所在目录的绝对路径,配置文件默认存放于此
        """
        return Path(__file__).resolve().parent

    @classmethod
    def default_config_path(cls) -> Path:
        """确定默认配置文件路径,支持环境变量覆盖

        环境变量优先级高于默认路径,允许不同环境使用不同配置。

        Returns:
            配置文件的绝对路径
        """
        env_override = os.getenv(cls.ENV_WORKFLOW_PATH)
        if env_override:
            # 环境变量路径支持用户主目录展开(~)
            return Path(env_override).expanduser().resolve()
        # 默认使用模块目录下的标准配置文件
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
                "Inquiry.Response.Generated": "inquiry",
            },
            target_confirmation_actions={
                "character": "Character.Confirmed",
                "theme": "Theme.Confirmed",
                "world": "Stage.Confirmed",
                "inquiry": "Inquiry.Confirmed",
            },
            target_failure_actions={
                "character": "Character.Failed",
                "theme": "Theme.Failed",
                "world": "Stage.Failed",
                "inquiry": "Inquiry.Failed",
            },
            target_regeneration_actions={
                "character": "Character.RegenerationRequested",
                "theme": "Theme.RegenerationRequested",
                "world": "Stage.RegenerationRequested",
                "inquiry": "Inquiry.RegenerationRequested",
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
