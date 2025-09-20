# Event Mapping Unification Analysis

## 概述

本文档分析当前系统中事件相关映射的分布情况，评估将这些映射统一组织的可行性，并提供具体的重构建议。

## 当前事件映射架构分析

### 1. 已实现的统一化组件

#### 1.1 集中配置映射 (`apps/backend/src/common/events/config.py`)

**功能**: 提供作用域到事件前缀、聚合类型、域主题的映射

```python
# 核心映射表
SCOPE_EVENT_PREFIX: Final[dict[str, str]] = {
    ScopeType.GENESIS.value: "Genesis.Session",
    ScopeType.CHAPTER.value: "Chapter.Session",
    # ...
}

SCOPE_AGGREGATE_TYPE: Final[dict[str, str]] = {
    ScopeType.GENESIS.value: "GenesisFlow",
    ScopeType.CHAPTER.value: "ChapterSession",
    # ...
}

SCOPE_DOMAIN_TOPIC: Final[dict[str, str]] = {
    ScopeType.GENESIS.value: "genesis.session.events",
    ScopeType.CHAPTER.value: "chapter.session.events",
    # ...
}
```

**设计亮点**:

- 🎯 **单一事实来源**: 避免硬编码
- 🔧 **可扩展性**: 支持新的作用域类型
- 📝 **标准化命名**: 统一的点号标记法

#### 1.2 统一序列化工具 (`apps/backend/src/schemas/genesis_events.py`)

**功能**: 提供事件序列化/反序列化和事件创建的统一接口

```python
class EventSerializationUtils:
    @staticmethod
    def deserialize_payload(event_type: GenesisEventType, payload_data: dict[str, Any]):
        """基于事件类型的智能反序列化"""
        payload_map = {
            GenesisEventType.STAGE_ENTERED: StageEnteredPayload,
            GenesisEventType.STAGE_COMPLETED: StageCompletedPayload,
            # ...
        }

    @staticmethod
    def create_genesis_event(...) -> GenesisEventCreate:
        """统一的事件创建工厂方法"""
```

**设计亮点**:

- ⚡ **类型安全**: 基于枚举的映射防止错误
- 🏭 **工厂模式**: 统一事件创建逻辑
- 🔄 **优雅降级**: 反序列化失败时的兜底机制

#### 1.3 命令策略注册 (`apps/backend/src/agents/orchestrator/command_strategies.py`)

**功能**: 提供命令到事件映射的策略模式实现

```python
class CommandStrategyRegistry:
    def process_command(self, cmd_type: str, scope_type: str, scope_prefix: str,
                       aggregate_id: str, payload: dict[str, Any]) -> CommandMapping | None:
        """基于策略的命令处理"""
        strategy = self._strategies.get(cmd_type)
        return strategy.process(...) if strategy else None

class CharacterRequestStrategy(CommandStrategy):
    def process(self, ...) -> CommandMapping:
        return CommandMapping(
            requested_action="Character.Requested",
            capability_message={
                "type": "Character.Design.GenerationRequested",
                # ...
            }
        )
```

**设计亮点**:

- 🎭 **策略模式**: 可插拔的命令处理逻辑
- 🔧 **自动注册**: 构造器中自动注册默认策略
- 🎯 **双向映射**: 命令 → 域事实 + 能力任务

#### 1.4 能力任务路由工厂 (`apps/backend/src/agents/orchestrator/message_factory.py`)

**功能**: 提供统一的能力任务消息创建和路由规范

```python
class MessageFactory:
    @staticmethod
    def create_capability_message(task_type: str, session_id: str, input_data: dict,
                                 topic: str = None) -> dict[str, Any]:
        """统一的能力任务消息创建"""
        return {
            "type": task_type,
            "session_id": session_id,
            "input": input_data,
            "_topic": topic,
            "_key": session_id,
        }

    @staticmethod
    def normalize_task_type(raw_type: str) -> str:
        """后缀归一化 (GenerationRequested → Generation)"""
        return raw_type.replace("Requested", "").replace("Started", "")
```

**设计亮点**:

- 🏭 **工厂模式**: 统一能力任务消息结构
- 📐 **命名规范**: 任务类型后缀归一化
- 🎯 **路由一致**: 统一的主题和分区键策略

### 2. 分布式组件

#### 2.1 事件类型定义 (`apps/backend/src/schemas/enums.py:84-118`)

```python
class GenesisEventType(str, Enum):
    """创世流程领域事件类型枚举"""

    # Session lifecycle events
    GENESIS_SESSION_STARTED = "GENESIS_SESSION_STARTED"
    GENESIS_SESSION_COMPLETED = "GENESIS_SESSION_COMPLETED"

    # Stage progression events
    STAGE_ENTERED = "STAGE_ENTERED"
    STAGE_COMPLETED = "STAGE_COMPLETED"

    # Content generation events
    INSPIRATION_GENERATED = "INSPIRATION_GENERATED"
    CONCEPT_SELECTED = "CONCEPT_SELECTED"
    # ...
```

#### 2.2 事件负载模型 (`apps/backend/src/schemas/genesis_events.py`)

```python
# 各种特定负载类
class StageEnteredPayload(GenesisEventPayload): ...
class StageCompletedPayload(GenesisEventPayload): ...
class ConceptSelectedPayload(GenesisEventPayload): ...
# ...

# 联合类型
GenesisEventPayloadUnion = Union[
    StageEnteredPayload,
    StageCompletedPayload,
    ConceptSelectedPayload,
    # ...
]
```

#### 2.3 基础事件模型 (`apps/backend/src/schemas/events.py`)

```python
class BaseEvent(BaseModel):
    """事件模型基类"""
    event_id: UUID
    event_type: str
    timestamp: datetime
    source_agent: str
    novel_id: UUID
    correlation_id: UUID | None
```

## 统一化评估

### ✅ 优势分析

#### 1. **类型安全保障**

- 使用 Python 枚举防止无效事件类型
- 编译时类型检查减少运行时错误
- IDE 智能提示提高开发效率

#### 2. **中心化配置管理**

- 单一事实来源避免重复定义
- 配置变更影响范围可控
- 便于维护和版本管理

#### 3. **标准化命名约定**

- 点号标记法确保一致性 (`Domain.Entity.Action`)
- 分层命名空间便于理解和管理
- 支持工具化处理

#### 4. **清晰的架构分离**

- 域事件vs能力事件职责明确
- 公共接口vs内部实现边界清楚
- 便于独立演进和测试

#### 5. **良好的可扩展性**

- 策略模式支持新业务场景
- 注册机制支持动态扩展
- 配置驱动的行为定制

#### 6. **完整的可追溯性**

- correlation_id → causation_id 链路追踪
- 事件溯源支持审计需求
- 便于问题诊断和性能分析

### ⚠️ 当前限制

#### 1. **映射逻辑分散**

- 事件-负载映射在 `EventSerializationUtils`
- 命令-事件映射在 `CommandStrategyRegistry`
- 作用域映射在 `common/events/config.py`

#### 2. **缺少全局视图**

- 没有统一的事件映射注册表
- 难以快速了解系统中所有事件类型
- 新增事件需要修改多个文件

#### 3. **发现机制不够直观**

- 需要查看多个文件才能理解完整映射关系
- 缺少自动化的映射验证工具
- 重构时容易遗漏相关映射

## 重构建议与实施方案

### 🎯 目标

1. **集中管理**: 所有事件映射关系在一处定义
2. **类型安全**: 保持现有的类型检查能力
3. **向后兼容**: 不破坏现有代码结构
4. **易于维护**: 简化新增事件的工作流程

### 📋 方案对比

#### 方案一：创建统一事件映射注册表 (革命式)

**实现方式**:

```python
# apps/backend/src/common/events/registry.py
from typing import Dict, Type, Set
from dataclasses import dataclass

@dataclass
class EventMapping:
    event_type: str
    payload_class: Type
    domain_topic: str
    aggregate_type: str
    command_aliases: Set[str] = None

class EventMappingRegistry:
    """统一事件映射注册表"""

    def __init__(self):
        self._mappings: Dict[str, EventMapping] = {}
        self._command_to_event: Dict[str, str] = {}
        self._auto_register()

    def register_event(self, mapping: EventMapping):
        """注册事件映射"""
        self._mappings[mapping.event_type] = mapping

        # 注册命令别名
        if mapping.command_aliases:
            for alias in mapping.command_aliases:
                self._command_to_event[alias] = mapping.event_type

    def get_event_mapping(self, event_type: str) -> EventMapping:
        """获取事件映射"""
        return self._mappings.get(event_type)

    def get_event_by_command(self, command: str) -> str:
        """通过命令获取事件类型"""
        return self._command_to_event.get(command)

    def list_all_events(self) -> List[str]:
        """列出所有注册的事件类型"""
        return list(self._mappings.keys())

    def validate_mappings(self) -> List[str]:
        """验证映射完整性，返回错误列表"""
        errors = []
        # 验证逻辑...
        return errors

    def _auto_register(self):
        """自动注册现有事件"""
        # 从现有枚举和配置自动发现并注册
        pass

# 全局实例
event_registry = EventMappingRegistry()
```

**优势**:

- 📊 **完整视图**: 所有映射关系一目了然
- 🔧 **工具化**: 支持验证、文档生成等工具
- 🚀 **高度灵活**: 支持复杂的映射逻辑

**劣势**:

- ⚠️ **风险较高**: 需要大幅重构现有代码
- 📈 **复杂度增加**: 引入新的抽象层
- 🕐 **开发周期长**: 需要完整的测试覆盖

#### 方案二：增强现有配置文件 (渐进式) ⭐**推荐**

**实现方式**:

```python
# 新增 apps/backend/src/common/events/mapping.py

# 事件-负载类映射表
EVENT_PAYLOAD_MAPPING: Final[Dict[str, Type]] = {
    "STAGE_ENTERED": StageEnteredPayload,
    "STAGE_COMPLETED": StageCompletedPayload,
    "CONCEPT_SELECTED": ConceptSelectedPayload,
    "INSPIRATION_GENERATED": InspirationGeneratedPayload,
    "FEEDBACK_PROVIDED": FeedbackProvidedPayload,
    "AI_GENERATION_STARTED": AIGenerationStartedPayload,
    "AI_GENERATION_COMPLETED": AIGenerationCompletedPayload,
    "NOVEL_CREATED_FROM_GENESIS": NovelCreatedFromGenesisPayload,
}

# 命令-事件映射表
COMMAND_EVENT_MAPPING: Final[Dict[str, str]] = {
    "Character.Request": "Character.Requested",
    "Character.Requested": "Character.Requested",
    "CHARACTER_REQUEST": "Character.Requested",
    "Theme.Request": "Theme.Requested",
    "Stage.Validate": "Stage.ValidationRequested",
    "Stage.Lock": "Stage.LockRequested",
}

# 事件类别映射表 (用于主题路由)
EVENT_CATEGORY_MAPPING: Final[Dict[str, str]] = {
    "STAGE_ENTERED": "stage_lifecycle",
    "STAGE_COMPLETED": "stage_lifecycle",
    "CONCEPT_SELECTED": "content_generation",
    "INSPIRATION_GENERATED": "content_generation",
    "AI_GENERATION_STARTED": "ai_interaction",
    "AI_GENERATION_COMPLETED": "ai_interaction",
}

def get_event_payload_class(event_type: str | GenesisEventType) -> Type:
    """获取事件负载类"""
    key = event_type.value if isinstance(event_type, GenesisEventType) else str(event_type)
    return EVENT_PAYLOAD_MAPPING.get(key, GenesisEventPayload)

def get_event_by_command(command: str) -> str:
    """通过命令获取事件类型"""
    return COMMAND_EVENT_MAPPING.get(command)

def get_event_category(event_type: str | GenesisEventType) -> str:
    """获取事件类别"""
    key = event_type.value if isinstance(event_type, GenesisEventType) else str(event_type)
    return EVENT_CATEGORY_MAPPING.get(key, "general")

def list_events_by_category(category: str) -> List[str]:
    """按类别列出事件"""
    return [event for event, cat in EVENT_CATEGORY_MAPPING.items() if cat == category]

def validate_event_mappings() -> Dict[str, List[str]]:
    """验证映射完整性"""
    issues = {
        "missing_payload_mapping": [],
        "missing_command_mapping": [],
        "orphaned_mappings": []
    }

    # 检查所有GenesisEventType是否都有负载映射
    for event_type in GenesisEventType:
        if event_type.value not in EVENT_PAYLOAD_MAPPING:
            issues["missing_payload_mapping"].append(event_type.value)

    # 检查是否有多余的映射
    valid_events = {event.value for event in GenesisEventType}
    for mapped_event in EVENT_PAYLOAD_MAPPING.keys():
        if mapped_event not in valid_events:
            issues["orphaned_mappings"].append(mapped_event)

    return {k: v for k, v in issues.items() if v}
```

**更新使用方**:

```python
# 更新 EventSerializationUtils
class EventSerializationUtils:
    @staticmethod
    def deserialize_payload(event_type: GenesisEventType, payload_data: dict[str, Any]):
        """使用统一配置的反序列化"""
        payload_class = get_event_payload_class(event_type)
        try:
            return payload_class(**payload_data)
        except Exception:
            return GenesisEventPayload(**payload_data)

# 更新 CommandStrategyRegistry
class CommandStrategyRegistry:
    def process_command(self, cmd_type: str, ...):
        """优先使用配置映射，回退到策略"""
        # 先尝试配置映射
        event_type = get_event_by_command(cmd_type)
        if event_type:
            return self._create_mapping_from_config(event_type, ...)

        # 回退到策略模式
        strategy = self._strategies.get(cmd_type)
        return strategy.process(...) if strategy else None
```

**优势**:

- ✅ **风险最低**: 基于现有良好架构
- 🎯 **收益明显**: 解决映射分散问题
- 🔄 **向后兼容**: 不破坏现有代码
- 📏 **符合设计**: 与现有中心化理念一致

**劣势**:

- 📝 **模块耦合**: 新增mapping.py引入schema类依赖
- 🔍 **发现能力有限**: 相比注册表方案功能较少

### 🚀 推荐实施路径

#### 第一阶段：配置增强 (低风险，高收益)

**目标**: 统一事件-负载映射，优化现有工具

**任务清单**:

1. ✅ 新增 `common/events/mapping.py` 专门处理事件映射表
2. ✅ 更新 `EventSerializationUtils` 使用统一映射
3. ✅ 在 `CommandStrategyRegistry` 中集成配置映射
4. ✅ 添加映射验证工具函数
5. ✅ 编写单元测试验证映射正确性

**验收标准**:

- 高频事件有专属payload映射，其他事件明确回退到generic payload
- EventSerializationUtils 使用统一映射配置
- 映射验证工具能检测不一致问题和孤儿项
- 现有功能测试全部通过，新增参数化反序列化测试

#### 第二阶段：策略整合 (中等风险)

**目标**: 简化命令策略，减少重复代码

**任务清单**:

1. 📋 分析现有策略的共性逻辑
2. 🔧 创建通用策略基于配置映射
3. 🧹 重构特殊策略，保留必要的定制逻辑
4. 📊 添加策略性能监控
5. ✅ 完善集成测试

#### 第三阶段：工具增强 (可选，长期)

**目标**: 提供更好的开发体验

**任务清单**:

1. 🔍 创建事件映射可视化工具
2. 📖 自动生成事件文档
3. 🚨 添加映射一致性检查到CI
4. 📈 提供事件使用统计分析
5. 🛠️ 开发事件调试辅助工具

### 📏 成功指标

#### 短期指标 (第一阶段)

- ✅ **代码重复度减少**: 映射逻辑不再重复定义
- ✅ **维护效率提升**: 新增事件只需修改一处配置
- ✅ **错误率降低**: 类型安全和验证工具减少错误

#### 长期指标 (全部阶段)

- 📊 **开发效率**: 新功能开发时间减少20%
- 🔧 **维护成本**: 事件相关bug数量减少50%
- 📖 **代码可读性**: 新开发者理解时间减少30%

## 风险评估与缓解策略

### 🚨 潜在风险

#### 1. **模块依赖耦合**

- **风险**: mapping.py引入schema类增加模块间耦合
- **缓解**: 仅导入必要类型，使用懒加载避免循环依赖

#### 2. **性能影响**

- **风险**: 运行时查找映射可能影响性能
- **缓解**: 使用缓存，性能关键路径预编译

#### 3. **向后兼容性**

- **风险**: 现有代码依赖可能被破坏
- **缓解**: 渐进式迁移，保留兼容接口

### 🛡️ 缓解措施

1. **分阶段实施**: 每个阶段都有独立价值和回退方案
2. **充分测试**: 每次变更都有完整的测试覆盖
3. **监控机制**: 添加性能和错误监控
4. **文档同步**: 及时更新开发文档和最佳实践

## 结论

### 📊 总体评估

当前 InfiniteScribe 系统在事件映射方面**已经具备了相当成熟的统一化架构**，主要体现在：

1. **中心化配置**: `common/events/config.py` 提供了核心映射
2. **类型安全**: 基于枚举的事件类型定义
3. **标准化**: 一致的命名约定和序列化机制
4. **可扩展**: 策略模式支持灵活的业务逻辑

### 🎯 推荐行动

**建议采用渐进式增强方案**，原因如下：

1. ✅ **风险可控**: 基于现有良好架构，风险最小
2. 📈 **收益明显**: 能解决当前主要痛点
3. 🔄 **平滑演进**: 不破坏现有投资和团队习惯
4. 🎯 **目标明确**: 每个阶段都有清晰的价值产出

### 🚀 后续步骤

1. **立即执行**: 第一阶段配置增强 (预计1-2天)
2. **规划评估**: 第二阶段策略整合 (预计1周)
3. **长期考虑**: 第三阶段工具增强 (按需实施)

这种方式能够在最小化风险的前提下，最大化事件映射统一化带来的收益，为系统的长期演进奠定坚实的基础。

## 具体实施建议

### 📁 文件结构调整

```
apps/backend/src/common/events/
├── config.py              # 保持现有：作用域→前缀/聚合/主题映射
├── mapping.py             # 新增：事件映射和验证工具
└── __init__.py            # 统一导出接口
```

### 🔧 核心实现要点

#### 1. 新增映射模块 (`common/events/mapping.py`)

```python
from typing import Dict, Type, List, Final
from src.schemas.enums import GenesisEventType
from src.schemas.genesis_events import (
    GenesisEventPayload, StageEnteredPayload, StageCompletedPayload,
    ConceptSelectedPayload, InspirationGeneratedPayload,
    # ... 其他payload类
)

# 事件-负载类映射表 (仅覆盖高频事件)
EVENT_PAYLOAD_MAPPING: Final[Dict[str, Type]] = {
    "STAGE_ENTERED": StageEnteredPayload,
    "STAGE_COMPLETED": StageCompletedPayload,
    "CONCEPT_SELECTED": ConceptSelectedPayload,
    "INSPIRATION_GENERATED": InspirationGeneratedPayload,
    "FEEDBACK_PROVIDED": FeedbackProvidedPayload,
    "AI_GENERATION_STARTED": AIGenerationStartedPayload,
    "AI_GENERATION_COMPLETED": AIGenerationCompletedPayload,
    "NOVEL_CREATED_FROM_GENESIS": NovelCreatedFromGenesisPayload,
}

# 命令-事件映射表
COMMAND_EVENT_MAPPING: Final[Dict[str, str]] = {
    "Character.Request": "Character.Requested",
    "CHARACTER_REQUEST": "Character.Requested",
    "Theme.Request": "Theme.Requested",
    "Stage.Validate": "Stage.ValidationRequested",
    "Stage.Lock": "Stage.LockRequested",
}

def get_event_payload_class(event_type: str | GenesisEventType) -> Type:
    """获取事件负载类，未映射时回退到通用负载"""
    key = event_type.value if isinstance(event_type, GenesisEventType) else str(event_type)
    return EVENT_PAYLOAD_MAPPING.get(key, GenesisEventPayload)

def get_event_by_command(command: str) -> str | None:
    """通过命令获取事件类型"""
    return COMMAND_EVENT_MAPPING.get(command)

def validate_event_mappings() -> Dict[str, List[str]]:
    """验证映射完整性，返回问题列表"""
    issues = {
        "missing_high_frequency_mapping": [],
        "orphaned_mappings": []
    }

    # 检查高频事件是否有映射 (按需定义高频事件列表)
    high_frequency_events = [
        "STAGE_ENTERED", "STAGE_COMPLETED", "AI_GENERATION_STARTED",
        "AI_GENERATION_COMPLETED", "CONCEPT_SELECTED"
    ]

    for event in high_frequency_events:
        if event not in EVENT_PAYLOAD_MAPPING:
            issues["missing_high_frequency_mapping"].append(event)

    # 检查孤儿映射
    valid_events = {event.value for event in GenesisEventType}
    for mapped_event in EVENT_PAYLOAD_MAPPING.keys():
        if mapped_event not in valid_events:
            issues["orphaned_mappings"].append(mapped_event)

    return {k: v for k, v in issues.items() if v}
```

#### 2. 更新使用方

**EventSerializationUtils** (`schemas/genesis_events.py`):
```python
from src.common.events.mapping import get_event_payload_class

class EventSerializationUtils:
    @staticmethod
    def deserialize_payload(event_type: GenesisEventType, payload_data: dict[str, Any]):
        """使用统一映射配置的反序列化"""
        payload_class = get_event_payload_class(event_type)
        try:
            return payload_class(**payload_data)
        except Exception:
            # 保持现有的优雅降级机制
            return GenesisEventPayload(**payload_data)
```

**CommandStrategyRegistry** (`agents/orchestrator/command_strategies.py`):
```python
from src.common.events.mapping import get_event_by_command

class CommandStrategyRegistry:
    def process_command(self, cmd_type: str, scope_type: str, scope_prefix: str,
                       aggregate_id: str, payload: dict[str, Any]) -> CommandMapping | None:
        """优先使用配置映射，回退到策略"""
        # 尝试配置映射
        event_type = get_event_by_command(cmd_type)
        if event_type:
            return self._create_mapping_from_config(event_type, scope_type, scope_prefix,
                                                   aggregate_id, payload)

        # 回退到策略模式 (保持现有逻辑)
        strategy = self._strategies.get(cmd_type)
        return strategy.process(scope_type, scope_prefix, aggregate_id, payload) if strategy else None

    def _create_mapping_from_config(self, event_type: str, scope_type: str,
                                   scope_prefix: str, aggregate_id: str,
                                   payload: dict[str, Any]) -> CommandMapping:
        """基于配置创建标准映射"""
        return CommandMapping(
            requested_action=event_type,
            capability_message={
                "type": f"{event_type.replace('.', '.')}.GenerationRequested",
                "session_id": aggregate_id,
                "input": payload.get("payload", {}),
                "_topic": self._build_topic_from_scope(scope_type, scope_prefix),
                "_key": aggregate_id,
            }
        )
```

### 🧪 测试策略

#### 1. 映射验证测试
```python
# tests/unit/common/events/test_event_mapping.py
def test_validate_event_mappings():
    """验证映射完整性"""
    issues = validate_event_mappings()
    assert not issues.get("orphaned_mappings", []), f"发现孤儿映射: {issues['orphaned_mappings']}"
    # 允许missing_high_frequency_mapping，但记录警告

def test_event_payload_mapping_coverage():
    """测试高频事件映射覆盖"""
    high_freq_events = ["STAGE_ENTERED", "STAGE_COMPLETED", "AI_GENERATION_STARTED"]
    for event in high_freq_events:
        payload_class = get_event_payload_class(event)
        assert payload_class != GenesisEventPayload, f"高频事件 {event} 应有专属payload类"

@pytest.mark.parametrize("event_type,expected_class", [
    (GenesisEventType.STAGE_ENTERED, StageEnteredPayload),
    (GenesisEventType.CONCEPT_SELECTED, ConceptSelectedPayload),
    ("UNKNOWN_EVENT", GenesisEventPayload),  # 回退测试
])
def test_get_event_payload_class(event_type, expected_class):
    """参数化测试反序列化类型正确性"""
    result = get_event_payload_class(event_type)
    assert result == expected_class
```

#### 2. 集成测试
```python
# tests/integration/agents/test_orchestrator_mapping.py
def test_command_strategy_registry_with_config_mapping():
    """验证配置映射与策略回退的集成"""
    registry = CommandStrategyRegistry()

    # 测试配置映射路径
    result = registry.process_command("Character.Request", "GENESIS", "Genesis", "session-123", {})
    assert result.requested_action == "Character.Requested"

    # 测试策略回退路径
    result = registry.process_command("ComplexCustomCommand", "GENESIS", "Genesis", "session-123", {})
    # 应该走策略路径或返回None
```

### 📊 迁移检查清单

#### 阶段一完成标准
- [ ] `common/events/mapping.py` 创建并包含核心映射表
- [ ] `EventSerializationUtils.deserialize_payload` 使用统一映射
- [ ] `CommandStrategyRegistry.process_command` 集成配置映射
- [ ] 映射验证工具 `validate_event_mappings()` 可用
- [ ] 参数化反序列化测试覆盖已映射事件
- [ ] 现有功能测试全部通过
- [ ] 新增 `events:lint` 脚本并集成CI

#### 质量门禁
- **代码覆盖率**: 新增映射逻辑100%覆盖
- **性能回归**: 反序列化性能不劣化超过5%
- **兼容性**: 现有API行为完全一致
- **文档同步**: 更新开发文档说明新的映射机制

这样的实施方案既解决了映射分散的问题，又保持了架构的清晰性和可维护性。
