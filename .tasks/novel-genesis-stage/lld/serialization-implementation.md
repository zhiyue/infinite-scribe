# 序列化实现

本文档定义了命令和事件的序列化实现，包括Python枚举定义、序列化器和工具函数。

## 枚举定义

### 命令类型枚举

```python
from enum import Enum
from typing import Optional

class CommandType(Enum):
    """命令类型枚举，value使用点式命名"""

    # Stage 0 - 创意种子
    SESSION_START = "Command.Genesis.Session.Start"
    SEED_REQUEST = "Command.Genesis.Session.Seed.Request"
    CONCEPT_CONFIRM = "Command.Genesis.Session.Concept.Confirm"
    STAGE_COMPLETE = "Command.Genesis.Session.Stage.Complete"

    # Stage 1 - 立意主题
    THEME_REQUEST = "Command.Genesis.Session.Theme.Request"
    THEME_REVISE = "Command.Genesis.Session.Theme.Revise"
    THEME_CONFIRM = "Command.Genesis.Session.Theme.Confirm"

    # Stage 2 - 世界观
    WORLD_REQUEST = "Command.Genesis.Session.World.Request"
    WORLD_UPDATE = "Command.Genesis.Session.World.Update"
    WORLD_CONFIRM = "Command.Genesis.Session.World.Confirm"

    # Stage 3 - 人物
    CHARACTER_REQUEST = "Command.Genesis.Session.Character.Request"
    CHARACTER_UPDATE = "Command.Genesis.Session.Character.Update"
    CHARACTER_CONFIRM = "Command.Genesis.Session.Character.Confirm"
    CHARACTER_NETWORK_CREATE = "Command.Genesis.Session.CharacterNetwork.Create"

    # Stage 4 - 情节
    PLOT_REQUEST = "Command.Genesis.Session.Plot.Request"
    PLOT_UPDATE = "Command.Genesis.Session.Plot.Update"
    PLOT_CONFIRM = "Command.Genesis.Session.Plot.Confirm"

    # Stage 5 - 细节
    DETAILS_REQUEST = "Command.Genesis.Session.Details.Request"
    DETAILS_CONFIRM = "Command.Genesis.Session.Details.Confirm"

    # 通用命令
    SESSION_FINISH = "Command.Genesis.Session.Finish"
    SESSION_FAIL = "Command.Genesis.Session.Fail"
    BRANCH_CREATE = "Command.Genesis.Session.Branch.Create"

    @classmethod
    def from_string(cls, value: str) -> 'CommandType':
        """从字符串获取枚举值"""
        for item in cls:
            if item.value == value:
                return item
        raise ValueError(f"Unknown CommandType value: {value}")

    @classmethod
    def get_stage_commands(cls, stage: str) -> list['CommandType']:
        """获取指定阶段的命令类型"""
        stage_mapping = {
            "Stage_0": [cls.SESSION_START, cls.SEED_REQUEST, cls.CONCEPT_CONFIRM, cls.STAGE_COMPLETE],
            "Stage_1": [cls.THEME_REQUEST, cls.THEME_REVISE, cls.THEME_CONFIRM],
            "Stage_2": [cls.WORLD_REQUEST, cls.WORLD_UPDATE, cls.WORLD_CONFIRM],
            "Stage_3": [cls.CHARACTER_REQUEST, cls.CHARACTER_UPDATE, cls.CHARACTER_CONFIRM, cls.CHARACTER_NETWORK_CREATE],
            "Stage_4": [cls.PLOT_REQUEST, cls.PLOT_UPDATE, cls.PLOT_CONFIRM],
            "Stage_5": [cls.DETAILS_REQUEST, cls.DETAILS_CONFIRM]
        }
        return stage_mapping.get(stage, [])

    def get_expected_result_event(self) -> Optional['GenesisEventType']:
        """获取该命令预期产生的结果事件"""
        from .event_types import GenesisEventType, COMMAND_EVENT_MAPPING
        event_type_str = COMMAND_EVENT_MAPPING.get(self.value)
        if event_type_str:
            return GenesisEventType.from_string(event_type_str)
        return None
```

### 事件类型枚举

```python
class GenesisEventType(Enum):
    """创世事件类型枚举，value使用点式命名"""

    # Stage 0 - 创意种子
    SESSION_STARTED = "Genesis.Session.Started"
    SEED_REQUESTED = "Genesis.Session.SeedRequested"
    CONCEPT_PROPOSED = "Genesis.Session.ConceptProposed"
    CONCEPT_CONFIRMED = "Genesis.Session.ConceptConfirmed"
    STAGE_COMPLETED = "Genesis.Session.StageCompleted"

    # Stage 1 - 立意主题
    THEME_REQUESTED = "Genesis.Session.Theme.Requested"
    THEME_PROPOSED = "Genesis.Session.Theme.Proposed"
    THEME_REVISED = "Genesis.Session.Theme.Revised"
    THEME_CONFIRMED = "Genesis.Session.Theme.Confirmed"

    # Stage 2 - 世界观
    WORLD_REQUESTED = "Genesis.Session.World.Requested"
    WORLD_PROPOSED = "Genesis.Session.World.Proposed"
    WORLD_UPDATED = "Genesis.Session.World.Updated"
    WORLD_CONFIRMED = "Genesis.Session.World.Confirmed"

    # Stage 3 - 人物
    CHARACTER_REQUESTED = "Genesis.Session.Character.Requested"
    CHARACTER_PROPOSED = "Genesis.Session.Character.Proposed"
    CHARACTER_UPDATED = "Genesis.Session.Character.Updated"
    CHARACTER_CONFIRMED = "Genesis.Session.Character.Confirmed"
    CHARACTER_NETWORK_CREATED = "Genesis.Session.CharacterNetwork.Created"

    # Stage 4 - 情节
    PLOT_REQUESTED = "Genesis.Session.Plot.Requested"
    PLOT_PROPOSED = "Genesis.Session.Plot.Proposed"
    PLOT_UPDATED = "Genesis.Session.Plot.Updated"
    PLOT_CONFIRMED = "Genesis.Session.Plot.Confirmed"

    # Stage 5 - 细节
    DETAILS_REQUESTED = "Genesis.Session.Details.Requested"
    DETAILS_GENERATED = "Genesis.Session.Details.Generated"
    DETAILS_CONFIRMED = "Genesis.Session.Details.Confirmed"

    # 通用事件
    SESSION_FINISHED = "Genesis.Session.Finished"
    SESSION_FAILED = "Genesis.Session.Failed"
    BRANCH_CREATED = "Genesis.Session.BranchCreated"

    @classmethod
    def from_string(cls, value: str) -> 'GenesisEventType':
        """从字符串获取枚举值"""
        for item in cls:
            if item.value == value:
                return item
        raise ValueError(f"Unknown GenesisEventType value: {value}")

    @classmethod
    def get_stage_events(cls, stage: str) -> list['GenesisEventType']:
        """获取指定阶段的事件类型"""
        stage_mapping = {
            "Stage_0": [cls.SESSION_STARTED, cls.SEED_REQUESTED, cls.CONCEPT_PROPOSED, cls.CONCEPT_CONFIRMED, cls.STAGE_COMPLETED],
            "Stage_1": [cls.THEME_REQUESTED, cls.THEME_PROPOSED, cls.THEME_REVISED, cls.THEME_CONFIRMED],
            "Stage_2": [cls.WORLD_REQUESTED, cls.WORLD_PROPOSED, cls.WORLD_UPDATED, cls.WORLD_CONFIRMED],
            "Stage_3": [cls.CHARACTER_REQUESTED, cls.CHARACTER_PROPOSED, cls.CHARACTER_UPDATED, cls.CHARACTER_CONFIRMED, cls.CHARACTER_NETWORK_CREATED],
            "Stage_4": [cls.PLOT_REQUESTED, cls.PLOT_PROPOSED, cls.PLOT_UPDATED, cls.PLOT_CONFIRMED],
            "Stage_5": [cls.DETAILS_REQUESTED, cls.DETAILS_GENERATED, cls.DETAILS_CONFIRMED]
        }
        return stage_mapping.get(stage, [])

    def is_request_event(self) -> bool:
        """判断是否为请求类事件"""
        return self.value.endswith('.Requested')

    def is_proposal_event(self) -> bool:
        """判断是否为提议类事件"""
        return self.value.endswith('.Proposed')

    def is_confirmation_event(self) -> bool:
        """判断是否为确认类事件"""
        return self.value.endswith('.Confirmed')

    def get_stage(self) -> Optional[str]:
        """获取事件所属阶段"""
        if 'Theme' in self.value:
            return 'Stage_1'
        elif 'World' in self.value:
            return 'Stage_2'
        elif 'Character' in self.value:
            return 'Stage_3'
        elif 'Plot' in self.value:
            return 'Stage_4'
        elif 'Details' in self.value:
            return 'Stage_5'
        elif self in [self.SESSION_STARTED, self.SEED_REQUESTED, self.CONCEPT_PROPOSED, self.CONCEPT_CONFIRMED]:
            return 'Stage_0'
        return None
```

### 命令事件映射

```python
# 完整的命令→事件映射表
COMMAND_EVENT_MAPPING = {
    # Stage 0 - 创意种子
    "Command.Genesis.Session.Start": "Genesis.Session.Started",
    "Command.Genesis.Session.Seed.Request": "Genesis.Session.SeedRequested",
    "Command.Genesis.Session.Concept.Confirm": "Genesis.Session.ConceptConfirmed",
    "Command.Genesis.Session.Stage.Complete": "Genesis.Session.StageCompleted",

    # Stage 1 - 立意主题
    "Command.Genesis.Session.Theme.Request": "Genesis.Session.Theme.Requested",
    "Command.Genesis.Session.Theme.Revise": "Genesis.Session.Theme.Revised",
    "Command.Genesis.Session.Theme.Confirm": "Genesis.Session.Theme.Confirmed",

    # Stage 2 - 世界观
    "Command.Genesis.Session.World.Request": "Genesis.Session.World.Requested",
    "Command.Genesis.Session.World.Update": "Genesis.Session.World.Updated",
    "Command.Genesis.Session.World.Confirm": "Genesis.Session.World.Confirmed",

    # Stage 3 - 人物
    "Command.Genesis.Session.Character.Request": "Genesis.Session.Character.Requested",
    "Command.Genesis.Session.Character.Update": "Genesis.Session.Character.Updated",
    "Command.Genesis.Session.Character.Confirm": "Genesis.Session.Character.Confirmed",
    "Command.Genesis.Session.CharacterNetwork.Create": "Genesis.Session.CharacterNetwork.Created",

    # Stage 4 - 情节
    "Command.Genesis.Session.Plot.Request": "Genesis.Session.Plot.Requested",
    "Command.Genesis.Session.Plot.Update": "Genesis.Session.Plot.Updated",
    "Command.Genesis.Session.Plot.Confirm": "Genesis.Session.Plot.Confirmed",

    # Stage 5 - 细节
    "Command.Genesis.Session.Details.Request": "Genesis.Session.Details.Requested",
    "Command.Genesis.Session.Details.Confirm": "Genesis.Session.Details.Confirmed",

    # 通用映射
    "Command.Genesis.Session.Finish": "Genesis.Session.Finished",
    "Command.Genesis.Session.Fail": "Genesis.Session.Failed",
    "Command.Genesis.Session.Branch.Create": "Genesis.Session.BranchCreated"
}

def get_result_event_type(command_type: str) -> Optional[str]:
    """根据命令类型获取对应的结果事件类型"""
    return COMMAND_EVENT_MAPPING.get(command_type)

def get_command_for_event(event_type: str) -> Optional[str]:
    """根据事件类型获取对应的命令类型（反向查找）"""
    for cmd_type, evt_type in COMMAND_EVENT_MAPPING.items():
        if evt_type == event_type:
            return cmd_type
    return None
```

## 领域对象定义

### 命令对象

```python
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, Optional
import uuid

@dataclass
class DomainCommand:
    """领域命令基类"""
    command_id: str
    command_type: CommandType
    aggregate_id: str
    aggregate_type: str
    payload: Dict[str, Any]
    user_id: str
    correlation_id: Optional[str] = None
    causation_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None

    def __post_init__(self):
        if not self.command_id:
            self.command_id = str(uuid.uuid4())
        if not self.created_at:
            self.created_at = datetime.utcnow()
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "command_id": self.command_id,
            "command_type": self.command_type.value,
            "aggregate_id": self.aggregate_id,
            "aggregate_type": self.aggregate_type,
            "payload": self.payload,
            "user_id": self.user_id,
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DomainCommand':
        """从字典创建命令对象"""
        return cls(
            command_id=data["command_id"],
            command_type=CommandType.from_string(data["command_type"]),
            aggregate_id=data["aggregate_id"],
            aggregate_type=data["aggregate_type"],
            payload=data["payload"],
            user_id=data["user_id"],
            correlation_id=data.get("correlation_id"),
            causation_id=data.get("causation_id"),
            metadata=data.get("metadata", {}),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None
        )
```

### 事件对象

```python
@dataclass
class DomainEvent:
    """领域事件基类"""
    event_id: str
    event_type: GenesisEventType
    aggregate_id: str
    aggregate_type: str
    aggregate_version: int
    payload: Dict[str, Any]
    user_id: Optional[str] = None
    correlation_id: Optional[str] = None
    causation_id: Optional[str] = None
    occurred_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if not self.event_id:
            self.event_id = str(uuid.uuid4())
        if not self.occurred_at:
            self.occurred_at = datetime.utcnow()
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "aggregate_id": self.aggregate_id,
            "aggregate_type": self.aggregate_type,
            "aggregate_version": self.aggregate_version,
            "payload": self.payload,
            "user_id": self.user_id,
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id,
            "occurred_at": self.occurred_at.isoformat() if self.occurred_at else None,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DomainEvent':
        """从字典创建事件对象"""
        return cls(
            event_id=data["event_id"],
            event_type=GenesisEventType.from_string(data["event_type"]),
            aggregate_id=data["aggregate_id"],
            aggregate_type=data["aggregate_type"],
            aggregate_version=data["aggregate_version"],
            payload=data["payload"],
            user_id=data.get("user_id"),
            correlation_id=data.get("correlation_id"),
            causation_id=data.get("causation_id"),
            occurred_at=datetime.fromisoformat(data["occurred_at"]) if data.get("occurred_at") else None,
            metadata=data.get("metadata", {})
        )
```

## 序列化器实现

### 命令序列化器

```python
from typing import Union, Dict, Any
import json
from datetime import datetime

class CommandSerializer:
    """命令序列化器"""

    @staticmethod
    def serialize_for_storage(command: DomainCommand) -> Dict[str, Any]:
        """序列化命令到数据库存储格式"""
        return {
            "command_id": command.command_id,
            "command_type": command.command_type.value,  # 点式字符串
            "aggregate_id": command.aggregate_id,
            "aggregate_type": command.aggregate_type,
            "payload": command.payload,
            "correlation_id": command.correlation_id,
            "causation_id": command.causation_id,
            "user_id": command.user_id,
            "metadata": command.metadata or {}
        }

    @staticmethod
    def deserialize_from_storage(data: Dict[str, Any]) -> DomainCommand:
        """从数据库存储格式反序列化命令"""
        return DomainCommand(
            command_id=data["command_id"],
            command_type=CommandType.from_string(data["command_type"]),
            aggregate_id=data["aggregate_id"],
            aggregate_type=data["aggregate_type"],
            payload=data["payload"],
            user_id=data["user_id"],
            correlation_id=data.get("correlation_id"),
            causation_id=data.get("causation_id"),
            metadata=data.get("metadata", {})
        )

    @staticmethod
    def serialize_for_api(command: DomainCommand) -> Dict[str, Any]:
        """序列化命令到API响应格式"""
        result = CommandSerializer.serialize_for_storage(command)
        result["created_at"] = command.created_at.isoformat() if command.created_at else None
        return result

    @staticmethod
    def validate_payload(command_type: CommandType, payload: Dict[str, Any]) -> bool:
        """验证命令负载的格式是否正确"""
        # 根据命令类型验证必需字段
        required_fields = {
            CommandType.SESSION_START: ["user_id", "initial_input"],
            CommandType.SEED_REQUEST: ["session_id", "user_id", "user_input"],
            CommandType.CONCEPT_CONFIRM: ["session_id", "novel_id", "concept_id"],
            CommandType.THEME_REQUEST: ["session_id", "novel_id", "concept_context"],
            # 添加其他命令类型的验证规则...
        }

        required = required_fields.get(command_type, [])
        return all(field in payload for field in required)
```

### 事件序列化器

```python
class EventSerializer:
    """事件序列化器"""

    @staticmethod
    def serialize_for_storage(event: DomainEvent) -> Dict[str, Any]:
        """序列化事件到数据库存储格式"""
        return {
            "event_id": event.event_id,
            "event_type": event.event_type.value,  # 点式字符串
            "aggregate_id": event.aggregate_id,
            "aggregate_type": event.aggregate_type,
            "aggregate_version": event.aggregate_version,
            "payload": event.payload,
            "correlation_id": event.correlation_id,
            "causation_id": event.causation_id,
            "user_id": event.user_id,
            "metadata": event.metadata or {}
        }

    @staticmethod
    def deserialize_from_storage(data: Dict[str, Any]) -> DomainEvent:
        """从数据库存储格式反序列化事件"""
        return DomainEvent(
            event_id=data["event_id"],
            event_type=GenesisEventType.from_string(data["event_type"]),
            aggregate_id=data["aggregate_id"],
            aggregate_type=data["aggregate_type"],
            aggregate_version=data["aggregate_version"],
            payload=data["payload"],
            user_id=data.get("user_id"),
            correlation_id=data.get("correlation_id"),
            causation_id=data.get("causation_id"),
            metadata=data.get("metadata", {})
        )

    @staticmethod
    def serialize_for_kafka(event: DomainEvent, topic: str, partition_key: str) -> Dict[str, Any]:
        """序列化事件到Kafka Outbox格式"""
        # Headers 包含路由和元数据信息
        headers = {
            "event_type": event.event_type.value,
            "content_type": "application/json",
            "correlation_id": event.correlation_id,
            "causation_id": event.causation_id,
            "aggregate_id": event.aggregate_id,
            "aggregate_type": event.aggregate_type,
            "user_id": event.user_id,
            "source": event.metadata.get("source", "unknown"),
            "trace_id": event.metadata.get("trace_id"),
            "timestamp": event.occurred_at.isoformat() if event.occurred_at else None,
            "schema_version": "1.0"
        }

        # Payload 包含完整的领域事件数据
        payload = EventSerializer.serialize_for_storage(event)
        payload["occurred_at"] = event.occurred_at.isoformat() if event.occurred_at else None

        return {
            "event_id": event.event_id,
            "topic": topic,
            "partition_key": partition_key,
            "headers": headers,
            "payload": payload
        }

    @staticmethod
    def serialize_for_sse(event: DomainEvent) -> Dict[str, Any]:
        """序列化事件到SSE格式"""
        return {
            "id": event.event_id,
            "event": event.event_type.value,
            "data": {
                "aggregate_id": event.aggregate_id,
                "payload": event.payload,
                "timestamp": event.occurred_at.isoformat() if event.occurred_at else None,
                "correlation_id": event.correlation_id
            }
        }
```

## 工具函数

### 类型转换工具

```python
class TypeConverter:
    """类型转换工具"""

    @staticmethod
    def string_to_uuid(value: str) -> str:
        """验证并返回UUID字符串"""
        try:
            uuid.UUID(value)  # 验证格式
            return value
        except ValueError:
            raise ValueError(f"Invalid UUID format: {value}")

    @staticmethod
    def ensure_string(value: Any) -> str:
        """确保值为字符串类型"""
        if isinstance(value, str):
            return value
        return str(value)

    @staticmethod
    def safe_json_loads(value: str) -> Dict[str, Any]:
        """安全的JSON解析"""
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return {}

    @staticmethod
    def safe_json_dumps(value: Any) -> str:
        """安全的JSON序列化"""
        try:
            return json.dumps(value, ensure_ascii=False, default=str)
        except (TypeError, ValueError):
            return "{}"
```

### 验证工具

```python
class ValidationUtils:
    """验证工具"""

    @staticmethod
    def validate_command_structure(data: Dict[str, Any]) -> bool:
        """验证命令数据结构"""
        required_fields = ["command_id", "command_type", "aggregate_id", "aggregate_type", "payload", "user_id"]
        return all(field in data for field in required_fields)

    @staticmethod
    def validate_event_structure(data: Dict[str, Any]) -> bool:
        """验证事件数据结构"""
        required_fields = ["event_id", "event_type", "aggregate_id", "aggregate_type", "aggregate_version", "payload"]
        return all(field in data for field in required_fields)

    @staticmethod
    def validate_genesis_stage(stage: str) -> bool:
        """验证创世阶段值"""
        valid_stages = ["Stage_0", "Stage_1", "Stage_2", "Stage_3", "Stage_4", "Stage_5"]
        return stage in valid_stages

    @staticmethod
    def validate_correlation_chain(commands: list, events: list) -> bool:
        """验证命令事件链的一致性"""
        # 检查 correlation_id 是否一致
        correlation_ids = set()
        for cmd in commands:
            if cmd.get("correlation_id"):
                correlation_ids.add(cmd["correlation_id"])
        for evt in events:
            if evt.get("correlation_id"):
                correlation_ids.add(evt["correlation_id"])

        return len(correlation_ids) <= 1  # 应该只有一个或零个correlation_id
```

## 使用示例

### 创建和序列化命令

```python
# 创建开始会话命令
command = DomainCommand(
    command_id=str(uuid.uuid4()),
    command_type=CommandType.SESSION_START,
    aggregate_id="session-456",
    aggregate_type="GenesisSession",
    payload={
        "user_id": "user-789",
        "initial_input": "我想写一个关于时间旅行的科幻小说",
        "preferences": {"genre": "sci-fi", "length": "medium"}
    },
    user_id="user-789",
    correlation_id="flow-001"
)

# 序列化到数据库
db_data = CommandSerializer.serialize_for_storage(command)

# 从数据库反序列化
restored_command = CommandSerializer.deserialize_from_storage(db_data)
```

### 创建和序列化事件

```python
# 创建会话开始事件
event = DomainEvent(
    event_id=str(uuid.uuid4()),
    event_type=GenesisEventType.SESSION_STARTED,
    aggregate_id="session-456",
    aggregate_type="GenesisSession",
    aggregate_version=1,
    payload={
        "session_id": "session-456",
        "novel_id": "novel-789",
        "stage": "Stage_0",
        "user_id": "user-789",
        "content": {"initial_input": "我想写一个关于时间旅行的科幻小说"}
    },
    user_id="user-789",
    correlation_id="flow-001",
    causation_id="cmd-123"
)

# 序列化到Kafka
kafka_data = EventSerializer.serialize_for_kafka(event, "genesis.session.events", "session-456")

# 序列化到SSE
sse_data = EventSerializer.serialize_for_sse(event)
```

这套序列化实现确保了命令和事件在不同存储和传输层之间的一致性和正确性。