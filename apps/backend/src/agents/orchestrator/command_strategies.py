"""命令处理策略模块

使用策略模式(Strategy Pattern)结合数据驱动配置,提高系统的可维护性和扩展性。
所有策略配置通过 events/config.py 中的集中映射进行管理,避免硬编码。

核心设计理念:
- 策略模式: 将不同命令类型的处理逻辑封装为独立策略,支持运行时切换
- 数据驱动: 通过配置文件定义命令到事件的映射关系,无需修改代码即可扩展
- 自动发现: 注册表自动加载所有配置的策略,简化新策略的添加流程
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, NamedTuple

from src.common.events.config import (
    get_strategy_config,
    get_strategy_keys,
    is_state_change_event,
)
from src.common.events.mapping import (
    build_topic_name,
    extract_strategy_key_from_event_type,
    get_command_aliases_for_action,
)


class CommandMapping(NamedTuple):
    """命令映射结果的数据传输对象

    封装命令处理后的结果,包含请求的动作类型和可选的能力消息。

    Attributes:
        requested_action: 请求执行的动作类型(事件类型),如 "CHARACTER_REQUESTED"
        capability_message: 发送给能力代理的消息载荷,None表示仅状态变更无需执行任务

    设计说明:
        使用 NamedTuple 而非普通类是因为:
        1. 不可变性确保数据在传递过程中不会被意外修改
        2. 自动生成 __repr__ 和 __eq__ 方法便于调试和测试
        3. 内存占用更小,性能更优
    """

    requested_action: str
    capability_message: dict[str, Any] | None


class CommandStrategy(ABC):
    """命令处理策略的抽象基类

    定义了所有具体命令策略必须实现的接口,遵循策略模式(Strategy Pattern)。
    每个具体策略负责处理一类相关的命令类型,并生成对应的能力消息。

    设计模式说明:
        策略模式允许在运行时动态选择算法(处理逻辑),而不是在编译时硬编码。
        这使得添加新的命令类型只需实现新的策略类,无需修改现有代码。

    子类必须实现:
        - get_aliases: 返回该策略处理的命令类型别名集合
        - process: 执行具体的命令处理逻辑并返回映射结果
    """

    @abstractmethod
    def get_aliases(self) -> set[str]:
        """获取该策略处理的命令类型别名集合

        Returns:
            包含所有命令别名的集合,如 {"create_character", "character_create"}

        设计说明:
            使用集合(set)而非列表是为了 O(1) 的查找效率
        """
        pass

    @abstractmethod
    def process(self, scope_type: str, scope_prefix: str, aggregate_id: str, payload: dict[str, Any]) -> CommandMapping:
        """处理命令并生成命令映射结果

        Args:
            scope_type: 作用域类型,如 "user" 或 "global"
            scope_prefix: 作用域前缀,用于构建主题名称
            aggregate_id: 聚合根ID,通常是会话ID或实体ID
            payload: 命令的载荷数据,包含业务参数

        Returns:
            CommandMapping 对象,包含请求动作和能力消息

        设计说明:
            scope_type 和 scope_prefix 用于实现多租户隔离,
            确保不同用户或租户的消息发送到不同的主题
        """
        pass

    def _build_topic(self, base_topic: str, scope_type: str, scope_prefix: str) -> str:
        """根据作用域构建完整的主题名称

        Args:
            base_topic: 基础主题名称,如 "character.requests"
            scope_type: 作用域类型
            scope_prefix: 作用域前缀

        Returns:
            完整的主题名称,如 "user.alice.character.requests"

        设计说明:
            委托给 build_topic_name 函数以保持主题命名的一致性
        """
        return build_topic_name(base_topic, scope_type, scope_prefix)


class GenericRequestStrategy(CommandStrategy):
    """通用的数据驱动命令处理策略

    这是一个通用策略实现,通过外部配置驱动其行为,避免为每种命令类型编写专门的策略类。
    所有配置数据来自 events/config.py 中的 STRATEGY_CONFIG 字典。

    核心优势:
        - 数据驱动: 通过配置文件定义策略行为,无需修改代码即可添加新命令类型
        - 可扩展: 新增命令类型只需在配置文件中添加条目,无需编写新的策略类
        - 统一逻辑: 所有相似的请求类命令共享相同的处理逻辑,减少代码重复

    配置示例:
        {
            "character": {
                "requested_action": "CHARACTER_REQUESTED",
                "capability_type": "CHARACTER_REQUEST",
                "base_topic": "character.requests"
            }
        }
    """

    def __init__(self, strategy_key: str) -> None:
        """初始化策略并加载配置

        Args:
            strategy_key: 策略配置键,对应 STRATEGY_CONFIG 中的键名,如 "character"、"theme"

        Raises:
            ValueError: 当策略键不存在于配置中时抛出

        设计说明:
            在初始化时立即验证配置存在性,确保后续处理不会因配置缺失而失败
        """
        self.strategy_key = strategy_key
        self.config = get_strategy_config(strategy_key)
        if self.config is None:
            raise ValueError(f"Unknown strategy key: {strategy_key}")

    def get_aliases(self) -> set[str]:
        """获取该策略处理的命令别名集合

        从配置中的 requested_action 查询对应的命令别名。
        例如: "CHARACTER_REQUESTED" -> {"create_character", "character_create"}

        Returns:
            命令别名集合,如果配置无效则返回空集合

        设计说明:
            使用反向映射从事件类型获取命令别名,支持多对一的命令到事件映射
        """
        if not self.config or "requested_action" not in self.config:
            return set()
        requested_action = self.config["requested_action"]
        return get_command_aliases_for_action(requested_action)

    def process(self, scope_type: str, scope_prefix: str, aggregate_id: str, payload: dict[str, Any]) -> CommandMapping:
        """使用配置数据处理命令

        根据配置生成标准化的能力消息,发送给对应的能力代理执行实际任务。

        Args:
            scope_type: 作用域类型
            scope_prefix: 作用域前缀
            aggregate_id: 聚合根ID,用作会话ID和消息键
            payload: 命令载荷数据

        Returns:
            包含请求动作和能力消息的 CommandMapping 对象

        Raises:
            ValueError: 当配置无效时抛出

        能力消息结构说明:
            - type: 能力消息类型,标识要执行的任务类型
            - session_id: 会话标识符,用于关联请求和响应
            - input: 业务输入数据,传递给能力代理
            - _topic: 消息发送的目标主题,用于路由
            - _key: 消息分区键,确保相同会话的消息发送到同一分区保证顺序
        """
        if not self.config:
            raise ValueError(f"Cannot process with invalid config for strategy: {self.strategy_key}")
        return CommandMapping(
            requested_action=self.config["requested_action"],
            capability_message={
                "type": self.config["capability_type"],
                "session_id": aggregate_id,
                "input": payload,
                "_topic": self._build_topic(self.config["base_topic"], scope_type, scope_prefix),
                "_key": aggregate_id,
            },
        )


class CommandStrategyRegistry:
    """命令策略注册表

    管理所有命令处理策略的注册和查找,支持自动发现和动态注册。
    注册表在初始化时自动加载所有配置的策略,无需手动注册。

    核心功能:
        - 自动发现: 初始化时自动加载所有配置的策略
        - 别名映射: 将命令别名映射到对应的策略实例
        - 容错处理: 单个策略注册失败不影响其他策略
        - 统一入口: 提供统一的命令处理接口

    设计模式:
        使用注册表模式(Registry Pattern)集中管理策略实例,
        避免在业务代码中直接创建和管理策略对象。
    """

    def __init__(self) -> None:
        """初始化注册表并自动注册所有默认策略"""
        self._strategies: dict[str, CommandStrategy] = {}
        self._register_default_strategies()

    def _register_default_strategies(self) -> None:
        """注册所有默认策略

        遍历配置中的所有策略键,为每个键创建对应的策略实例并注册。
        如果某个策略注册失败,记录警告日志但继续处理其他策略。

        容错设计说明:
            单个策略注册失败不应导致整个注册表不可用,
            因此捕获异常并记录日志,确保其他策略能够正常注册。
            这种设计遵循"fail gracefully"原则,提高系统鲁棒性。
        """
        # 为所有配置的策略键创建通用策略实例
        for strategy_key in get_strategy_keys():
            try:
                strategy = GenericRequestStrategy(strategy_key)
                self.register(strategy)
            except ValueError as e:
                # 记录错误但继续处理其他策略
                # 防止单个错误配置导致整个注册表初始化失败
                import logging

                logging.warning(f"Failed to register strategy '{strategy_key}': {e}")

    def register(self, strategy: CommandStrategy) -> None:
        """注册策略及其所有命令别名

        将策略实例注册到注册表中,建立命令别名到策略的映射关系。
        一个策略可以处理多个命令别名,每个别名都会映射到同一个策略实例。

        Args:
            strategy: 要注册的策略实例

        设计说明:
            同一个策略实例被多个别名引用,而不是为每个别名创建新实例,
            这样可以节省内存并确保所有别名共享相同的状态和配置。
        """
        for alias in strategy.get_aliases():
            self._strategies[alias] = strategy

    def process_command(
        self, cmd_type: str, scope_type: str, scope_prefix: str, aggregate_id: str, payload: dict[str, Any]
    ) -> CommandMapping | None:
        """处理命令并生成命令映射结果

        使用统一的映射配置和策略回退机制处理命令。处理流程分为三个层次:
        1. 配置映射优先: 首先查找命令到事件的映射配置
        2. 状态变更检查: 判断是否为纯状态变更(无需执行任务)
        3. 策略回退: 如果配置映射失败,尝试使用注册的策略处理

        Args:
            cmd_type: 命令类型,如 "create_character"
            scope_type: 作用域类型
            scope_prefix: 作用域前缀
            aggregate_id: 聚合根ID
            payload: 命令载荷数据

        Returns:
            CommandMapping 对象,如果命令无法处理则返回 None

        处理流程说明:
            1. 优先使用配置映射查找对应的事件类型
            2. 如果是纯状态变更事件,直接返回无能力消息的映射
            3. 如果需要执行任务,查找或创建对应的策略
            4. 如果策略处理失败,回退为纯状态变更
            5. 最后尝试使用已注册的策略直接处理(兼容旧行为)

        设计理念:
            采用"配置优先、策略回退"的双层机制,确保:
            - 新增命令可通过配置快速支持
            - 旧的策略注册方式仍然可用
            - 即使策略创建失败也能完成状态变更
        """
        from src.common.events.mapping import get_event_by_command

        # 第一步: 尝试从配置映射获取事件类型
        event_type = get_event_by_command(cmd_type)
        if event_type:
            # 第二步: 检查是否为纯状态变更事件(不需要执行能力任务)
            if is_state_change_event(event_type):
                return CommandMapping(requested_action=event_type, capability_message=None)

            # 第三步: 对于需要能力任务的事件,查找合适的策略
            strategy = self._strategies.get(cmd_type)
            if not strategy:
                # 尝试根据事件类型前缀动态创建策略
                # 例如: "CHARACTER_REQUESTED" -> "character"
                strategy_key = extract_strategy_key_from_event_type(event_type)
                if strategy_key and strategy_key in get_strategy_keys():
                    try:
                        strategy = GenericRequestStrategy(strategy_key)
                    except ValueError:
                        # 策略创建失败,回退为纯状态变更
                        return CommandMapping(requested_action=event_type, capability_message=None)

            if strategy:
                result = strategy.process(scope_type, scope_prefix, aggregate_id, payload)
                if result and result.capability_message:
                    # 使用配置中的事件类型保持一致性
                    return CommandMapping(requested_action=event_type, capability_message=result.capability_message)
                else:
                    # 策略存在但无法处理,回退为纯状态变更
                    return CommandMapping(requested_action=event_type, capability_message=None)

        # 第四步: 纯策略回退(保持与现有行为兼容,用于未映射的命令)
        strategy = self._strategies.get(cmd_type)
        if strategy:
            return strategy.process(scope_type, scope_prefix, aggregate_id, payload)

        # 命令无法识别或处理
        return None


# 全局命令策略注册表实例
# 在模块加载时自动初始化,确保所有策略在应用启动时就已就绪
# 使用单例模式避免重复初始化,所有命令处理都使用这个全局实例
command_registry = CommandStrategyRegistry()
