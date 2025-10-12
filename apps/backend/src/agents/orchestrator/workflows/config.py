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
        """根据配置源类型选择加载方式

        统一的配置加载入口,根据参数类型路由到具体的加载方法。

        Args:
            config_source: 配置源,可以是文件路径或None(使用默认配置)

        Returns:
            完整的工作流配置对象
        """
        if isinstance(config_source, str | Path):
            # 从指定文件路径加载配置
            return cls._load_from_file(Path(config_source))
        # 使用默认配置(带缓存机制)
        return cls._get_default_config()

    @classmethod
    def _get_default_config(cls) -> WorkflowConfig:
        """加载并缓存默认配置(线程安全)

        使用双检锁模式确保默认配置只被初始化一次,同时保证多线程环境下的安全性。
        返回深拷贝以防止不同实例间的意外修改影响缓存。

        线程安全策略:
        - 第一次检查:避免每次都获取锁,提升性能
        - 加锁:确保只有一个线程执行初始化
        - 第二次检查:防止其他等待线程重复初始化

        Returns:
            默认配置的深拷贝副本,确保每个调用者获得独立的配置对象
        """
        if cls._cached_default_config is None:
            with cls._config_lock:
                # 双检锁模式:第二次检查确保初始化唯一性
                if cls._cached_default_config is None:
                    cls._cached_default_config = cls._create_builtin_default_config()
        # 返回深拷贝防止跨实例的意外修改影响缓存
        return copy.deepcopy(cls._cached_default_config)

    @classmethod
    def _create_builtin_default_config(cls) -> WorkflowConfig:
        """创建内置的Genesis工作流默认配置

        构建系统默认的Genesis阶段工作流配置,包含标准的阈值设置和事件路由规则。
        这些默认值基于实际生产环境的最佳实践调优,平衡了内容质量和生成效率。

        配置设计考虑:
        - 质量阈值7.5:在10分制下,既保证内容质量又避免过度严格导致频繁重试
        - 最大重试3次:防止无限循环消耗资源,同时给予合理的重试机会
        - 完整的领域覆盖:支持角色(character)、主题(theme)、世界(world)、询问(inquiry)

        Returns:
            完整配置的内置默认实例,适用于Genesis工作流的所有标准场景
        """
        # 阈值配置:控制质量评估和重试策略
        thresholds = WorkflowThresholds(
            quality_threshold=7.5,  # 7.5分以上才通过审核,平衡质量和效率
            max_attempts=3,  # 最多重试3次,防止资源浪费
            consistency_threshold=1.0,  # 完全一致性要求,确保设定连贯
        )

        # 路由配置:定义事件到领域的映射和后续动作
        routing = WorkflowRouting(
            # 事件到目标领域的映射:决定哪个领域处理此事件
            event_target_mapping={
                "Genesis.Character.Command.Received": "character",  # 角色创建命令
                "Genesis.Theme.Command.Received": "theme",  # 主题设定命令
                "Genesis.World.Command.Received": "world",  # 世界构建命令
                "Character.Design.Generated": "character",  # 角色设计生成完成
                "Character.Generated": "character",  # 角色生成完成
                "Outliner.Theme.Generated": "theme",  # 大纲主题生成完成
                "Theme.Generated": "theme",  # 主题生成完成
                "Inquiry.Response.Generated": "inquiry",  # 询问响应生成完成
            },
            # 确认动作:质量审核通过后触发的确认事件
            target_confirmation_actions={
                "character": "Character.Confirmed",
                "theme": "Theme.Confirmed",
                "world": "Stage.Confirmed",  # 世界相关事件使用Stage前缀
                "inquiry": "Inquiry.Confirmed",
            },
            # 失败动作:达到最大重试次数后触发的失败通知
            target_failure_actions={
                "character": "Character.Failed",
                "theme": "Theme.Failed",
                "world": "Stage.Failed",
                "inquiry": "Inquiry.Failed",
            },
            # 重新生成动作:质量不达标时触发的重试请求
            target_regeneration_actions={
                "character": "Character.RegenerationRequested",
                "theme": "Theme.RegenerationRequested",
                "world": "Stage.RegenerationRequested",
                "inquiry": "Inquiry.RegenerationRequested",
            },
            # 任务前缀映射:标准化任务命名,便于监控和日志追踪
            task_prefix_mapping={
                "Character.Design": "Character.Design",
                "Theme.Creation": "Theme.Creation",
                "World.Building": "World.Building",
                "quality_review": "Review.Quality.Evaluation",  # 质量审核任务
                "consistency_check": "Review.Consistency.Check",  # 一致性检查任务
            },
        )

        # 返回完整配置:包含名称、版本、阈值、路由和元数据
        return WorkflowConfig(
            name="genesis-workflow",
            description="Genesis stage workflow configuration",
            version="1.0.0",
            thresholds=thresholds,
            routing=routing,
            metadata={
                "created_by": "system",  # 系统内置配置
                "environment": "builtin",  # 标记为内置环境
            },
        )

    @classmethod
    def _load_from_file(cls, file_path: Path) -> WorkflowConfig:
        """从JSON文件加载工作流配置

        读取并解析JSON格式的工作流配置文件,验证必需字段并构建配置对象。
        采用快速失败策略:文件不存在或格式错误时立即抛出异常。

        Args:
            file_path: 配置文件的绝对路径

        Returns:
            解析后的完整工作流配置对象

        Raises:
            WorkflowConfigError: 文件不存在、格式错误或缺少必需字段时抛出
        """
        if not file_path.exists():
            # 快速失败:配置文件不存在是严重错误,无法继续
            raise WorkflowConfigError(f"Workflow config file not found: {file_path}")

        # 使用UTF-8编码读取JSON文件,支持中文配置内容
        with file_path.open(encoding="utf-8") as f:
            config_data = json.load(f)

        try:
            # 提取必需的配置段落,缺少任一段落都无法正常工作
            thresholds_data = config_data["thresholds"]
            routing_data = config_data["routing"]
        except KeyError as exc:  # pragma: no cover - 防御性保护,JSON已版本化
            # 快速失败:缺少必需字段说明配置文件不完整
            raise WorkflowConfigError(f"Missing required workflow section: {exc}") from exc

        # 构建完整配置对象,可选字段使用默认值或空值
        return WorkflowConfig(
            name=config_data.get("name", cls.DEFAULT_WORKFLOW_FILENAME.rsplit(".", 1)[0]),
            description=config_data.get("description"),
            version=config_data.get("version"),
            thresholds=WorkflowThresholds(**thresholds_data),  # 解包字典创建阈值对象
            routing=WorkflowRouting(**routing_data),  # 解包字典创建路由对象
            metadata=config_data.get("metadata", {}),  # 元数据可选,默认空字典
        )

    # ---------------------------------------------------------------------
    # 替代构造器:提供语义化的工厂方法,让调用者明确配置来源
    # ---------------------------------------------------------------------
    @classmethod
    def from_file(cls, config_file: str | Path) -> EventHandlerConfig:
        """从指定文件路径创建配置实例

        工厂方法:明确表示配置来自用户指定的文件。

        Args:
            config_file: 配置文件路径,支持相对路径和绝对路径

        Returns:
            从文件加载的配置实例
        """
        return cls(Path(config_file))

    @classmethod
    def from_config(cls, config: WorkflowConfig) -> EventHandlerConfig:
        """从预构建的配置对象创建实例

        工厂方法:适用于程序化构建配置或测试场景。

        Args:
            config: 已构建的完整配置对象

        Returns:
            包装了指定配置对象的实例
        """
        return cls(config)

    @classmethod
    def for_genesis_workflow(cls) -> EventHandlerConfig:
        """创建标准Genesis工作流配置实例

        工厂方法:返回绑定到标准Genesis工作流的配置,使用系统内置的默认值。
        这是生产环境推荐的创建方式。

        Returns:
            使用默认Genesis配置的实例
        """
        return cls(cls._get_default_config())

    @classmethod
    def for_testing(cls, **overrides: Any) -> EventHandlerConfig:
        """创建用于测试的配置实例,支持轻量级参数覆盖

        工厂方法:基于默认配置创建测试实例,允许通过关键字参数覆盖特定配置项。
        避免在测试中重复构建完整配置,提升测试代码的可读性和维护性。

        Args:
            **overrides: 要覆盖的配置参数,支持以下键:
                        - quality_threshold: 覆盖质量阈值
                        - max_attempts: 覆盖最大重试次数
                        - consistency_threshold: 覆盖一致性阈值
                        - event_target_mapping: 覆盖事件目标映射
                        - target_confirmation_actions: 覆盖确认动作
                        - target_failure_actions: 覆盖失败动作
                        - target_regeneration_actions: 覆盖重新生成动作
                        - task_prefix_mapping: 覆盖任务前缀

        Returns:
            应用了覆盖参数的测试配置实例
        """
        # 获取默认配置作为基准
        config = cls._get_default_config()

        if overrides:
            # 存在覆盖参数时,构建新的配置对象
            # 阈值覆盖:支持单独调整质量标准和重试策略
            thresholds = WorkflowThresholds(
                quality_threshold=overrides.get("quality_threshold", config.thresholds.quality_threshold),
                max_attempts=overrides.get("max_attempts", config.thresholds.max_attempts),
                consistency_threshold=overrides.get("consistency_threshold", config.thresholds.consistency_threshold),
            )
            # 路由覆盖:支持自定义事件映射和动作,深拷贝防止修改默认配置
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
            # 重建配置对象,保留元数据但应用新的阈值和路由
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
    # 便捷访问器:为事件命令处理器提供简化的配置访问接口
    # 使用全大写命名遵循常量访问习惯,提升代码可读性
    # ---------------------------------------------------------------------
    @property
    def QUALITY_THRESHOLD(self) -> float:  # noqa: N802
        """质量评分阈值

        生成内容的质量分数需达到此值才能通过审核,低于此值将触发重新生成。
        典型值为7.5(满分10分),平衡内容质量和生成效率。
        """
        return self._config.thresholds.quality_threshold

    @property
    def MAX_ATTEMPTS(self) -> int:  # noqa: N802
        """最大重试次数

        单个任务失败后允许的最大重新生成次数,超过此次数后任务将被标记为最终失败。
        防止无限重试消耗系统资源,同时给予合理的改进机会。
        """
        return self._config.thresholds.max_attempts

    @property
    def CONSISTENCY_THRESHOLD(self) -> float:  # noqa: N802
        """一致性检查阈值

        用于评估生成内容与现有世界观设定的一致性程度,默认值1.0表示要求完全一致。
        确保角色、情节、世界观等元素在整个作品中保持连贯。
        """
        return self._config.thresholds.consistency_threshold

    @property
    def EVENT_TARGET_MAPPING(self) -> dict[str, str]:  # noqa: N802
        """事件到目标领域的映射关系

        定义每个事件应该由哪个领域(character/theme/world/inquiry)处理。
        用于事件路由决策,确保事件被正确的处理器接收。
        """
        return self._config.routing.event_target_mapping

    @property
    def TARGET_CONFIRMATION_ACTIONS(self) -> dict[str, str]:  # noqa: N802
        """目标确认动作映射

        当内容通过质量审核时,根据目标领域触发相应的确认事件。
        例如:character领域触发"Character.Confirmed"事件。
        """
        return self._config.routing.target_confirmation_actions

    @property
    def TARGET_FAILURE_ACTIONS(self) -> dict[str, str]:  # noqa: N802
        """目标失败动作映射

        当任务达到最大重试次数仍失败时,根据目标领域触发相应的失败通知事件。
        用于通知下游系统任务最终失败,触发降级或补偿逻辑。
        """
        return self._config.routing.target_failure_actions

    @property
    def TARGET_REGENERATION_ACTIONS(self) -> dict[str, str]:  # noqa: N802
        """目标重新生成动作映射

        当内容质量不达标时,根据目标领域触发相应的重新生成请求事件。
        驱动自动重试机制,给予系统改进输出的机会。
        """
        return self._config.routing.target_regeneration_actions

    @property
    def TASK_PREFIX_MAPPING(self) -> dict[str, str]:  # noqa: N802
        """任务前缀映射

        将任务类型映射到标准化的事件前缀,用于任务跟踪、审计和监控。
        统一的命名规范便于日志分析和问题排查。
        """
        return self._config.routing.task_prefix_mapping

    @property
    def METADATA(self) -> dict[str, Any]:  # noqa: N802
        """配置元数据

        存储配置的附加信息,如创建者、环境、时间戳等上下文数据。
        不影响核心业务逻辑,用于配置管理和追溯。
        """
        return self._config.metadata

    def to_dict(self) -> dict[str, Any]:
        """导出配置为可序列化的字典格式

        将配置对象转换为标准的Python字典,便于JSON序列化、日志记录和调试。
        主要用于测试断言、配置导出和问题排查场景。

        设计考虑:
        - 使用深拷贝防止返回的字典被修改影响原配置
        - 保持与JSON配置文件格式一致,支持配置导出和导入
        - 包含所有配置项,提供完整的配置视图

        Returns:
            包含完整配置信息的字典,结构与JSON配置文件一致
        """
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
                # 深拷贝所有字典类型配置,防止外部修改
                "event_target_mapping": copy.deepcopy(self.EVENT_TARGET_MAPPING),
                "target_confirmation_actions": copy.deepcopy(self.TARGET_CONFIRMATION_ACTIONS),
                "target_failure_actions": copy.deepcopy(self.TARGET_FAILURE_ACTIONS),
                "target_regeneration_actions": copy.deepcopy(self.TARGET_REGENERATION_ACTIONS),
                "task_prefix_mapping": copy.deepcopy(self.TASK_PREFIX_MAPPING),
            },
            "metadata": copy.deepcopy(self.METADATA),
        }
