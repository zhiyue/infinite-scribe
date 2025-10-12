"""领域事件信封和构建器。

提供领域事件的标准化消息格式，支持事件溯源（Event Sourcing）和 CQRS 架构。
这些类可以在整个系统中复用，用于：
- 领域事件的持久化和发布
- 与 Agent 消息格式的互操作
- 事件总线和事件处理

核心组件：
- SystemMetadata: 领域事件的系统级元数据
- DomainEventEnvelope: 领域事件的标准信封格式
- DomainEventBuilder: 构建领域事件信封的 Builder 模式实现
"""

from __future__ import annotations

import contextlib
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from src.models.event import DomainEvent


class SystemMetadata(BaseModel):
    """领域事件的系统级元数据。

    包含事件溯源和 CQRS 所需的核心系统信息：
    - 事件标识（event_id, event_type）
    - 聚合根信息（aggregate_type, aggregate_id）
    - 因果追踪（correlation_id, causation_id）
    - 版本管理（event_version）
    """

    event_id: str = Field(description="事件唯一标识符")
    event_type: str = Field(description="事件类型（如 Genesis.Session.Started）")
    aggregate_type: str = Field(description="聚合根类型（如 GenesisFlow）")
    aggregate_id: str = Field(description="聚合根实例标识符")
    metadata: dict[str, Any] = Field(default_factory=dict, description="额外的元数据字段")
    correlation_id: str | None = Field(default=None, description="关联ID，用于追踪事件链")
    causation_id: str | None = Field(default=None, description="因果ID，记录触发此事件的原始事件")
    created_at: str | None = Field(default=None, description="事件创建时间（ISO格式）")
    event_version: int | None = Field(default=None, description="事件版本号")

    model_config = ConfigDict(extra="forbid")


class DomainEventEnvelope(BaseModel):
    """领域事件的标准消息封装。

    用于领域事件（Event Sourcing）的结构化消息格式，与 Agent 通信的 Envelope 格式互补。

    设计理念：
    - 分离系统元数据（system）和业务数据（data），支持事件溯源
    - 包含聚合根信息（aggregate_type, aggregate_id）用于事件重放
    - 支持因果追踪（causation_id, correlation_id）构建事件链
    - 提供类型安全的转换方法以实现与 Envelope 格式的互操作

    使用场景：
    - 领域事件持久化到 domain_events 表
    - 通过 EventOutbox 发布到事件总线
    - 事件溯源和 CQRS 架构
    - 跨服务的事件通知
    """

    system: SystemMetadata = Field(description="系统级元数据")
    data: dict[str, Any] = Field(default_factory=dict, description="业务数据负载")
    schema_version: str = Field(default="v1", description="信封格式版本")

    model_config = ConfigDict(extra="forbid")

    def to_envelope_meta(self) -> dict[str, Any]:
        """将 DomainEventEnvelope 转换为 Envelope 兼容的元数据格式。

        这个方法提供了从领域事件格式到 Agent 消息格式的类型安全转换，
        使得下游代码可以统一处理两种消息格式。

        映射关系：
            - system.event_id -> id/message_id
            - system.event_type -> type
            - system.correlation_id -> correlation_id
            - system.metadata.source -> agent
            - schema_version -> version

        Returns:
            包含 Envelope 兼容元数据字段的字典
        """
        # 提取 source 信息作为 agent 字段
        agent_source = None
        if isinstance(self.system.metadata, dict):
            agent_source = self.system.metadata.get("source")

        return {
            "id": self.system.event_id,
            "message_id": self.system.event_id,
            "type": self.system.event_type,
            "version": self.schema_version,
            "correlation_id": self.system.correlation_id,
            "agent": agent_source,
            "retries": None,  # 领域事件不包含重试信息
            "status": None,  # 领域事件不包含状态信息
            # 保留领域事件特有的额外字段
            "aggregate_id": self.system.aggregate_id,
            "aggregate_type": self.system.aggregate_type,
            "causation_id": self.system.causation_id,
            "event_id": self.system.event_id,
        }


class DomainEventBuilder:
    """领域事件信封构建器。

    使用 Builder 模式构建 DomainEventEnvelope，确保：
    - 系统元数据和业务数据的分离
    - 字段验证和冲突检查
    - 从 SQLAlchemy DomainEvent 模型的便捷转换

    使用示例：
        ```python
        # 从 DomainEvent 模型构建
        envelope = DomainEventBuilder.from_domain_event(domain_event).build()

        # 手动构建
        envelope = (
            DomainEventBuilder()
            .with_domain_event(domain_event)
            .with_business_data({"key": "value"})
            .build()
        )
        ```
    """

    RESERVED_TOP_LEVEL_FIELDS = {"system", "data", "schema_version"}

    def __init__(self) -> None:
        """初始化构建器，设置默认值。"""
        self._system_metadata: dict[str, Any] = {}
        self._business_data: dict[str, Any] = {}
        self._schema_version: str = "v1"

    def with_domain_event(self, event: DomainEvent) -> DomainEventBuilder:
        """从 SQLAlchemy DomainEvent 实例填充系统元数据。

        Args:
            event: DomainEvent 模型实例

        Returns:
            self，支持链式调用
        """
        raw_metadata = event.event_metadata or {}
        if isinstance(raw_metadata, dict):
            cleaned_metadata = {k: v for k, v in raw_metadata.items() if v is not None}
        else:
            cleaned_metadata = {}

        # 移除空的嵌套 metadata 字段
        nested = cleaned_metadata.get("metadata")
        if isinstance(nested, dict) and not nested:
            cleaned_metadata.pop("metadata")

        self._system_metadata = {
            "event_id": str(event.event_id),
            "event_type": event.event_type,
            "aggregate_type": event.aggregate_type,
            "aggregate_id": event.aggregate_id,
            "metadata": cleaned_metadata,
        }

        # 添加可选字段
        if getattr(event, "correlation_id", None):
            self._system_metadata["correlation_id"] = str(event.correlation_id)
        if getattr(event, "causation_id", None):
            self._system_metadata["causation_id"] = str(event.causation_id)
        if getattr(event, "created_at", None):
            with contextlib.suppress(Exception):
                self._system_metadata["created_at"] = event.created_at.isoformat()  # type: ignore[attr-defined]
        if getattr(event, "event_version", None) is not None:
            self._system_metadata["event_version"] = event.event_version

        return self

    def with_business_data(self, data: dict[str, Any]) -> DomainEventBuilder:
        """附加业务数据负载，并验证保留字段冲突。

        Args:
            data: 业务数据字典

        Returns:
            self，支持链式调用

        Raises:
            ValueError: 如果业务数据包含保留的顶层字段
        """
        if not data:
            return self

        conflicts = set(data.keys()) & self.RESERVED_TOP_LEVEL_FIELDS
        if conflicts:
            raise ValueError(
                f"Business data contains reserved top-level fields: {conflicts}. "
                "These fields conflict with the envelope structure."
            )

        self._business_data = data
        return self

    def with_schema_version(self, version: str) -> DomainEventBuilder:
        """覆盖默认的 schema 版本，用于渐进式迁移。

        Args:
            version: schema 版本字符串

        Returns:
            self，支持链式调用
        """
        self._schema_version = version
        return self

    def build(self) -> DomainEventEnvelope:
        """构建最终的 DomainEventEnvelope 实例。

        Returns:
            构建好的 DomainEventEnvelope 实例

        Raises:
            ValueError: 如果缺少必需的系统元数据字段
        """
        required_fields = ["event_id", "event_type", "aggregate_type", "aggregate_id"]
        missing = [field for field in required_fields if field not in self._system_metadata]
        if missing:
            raise ValueError(f"Missing required system metadata fields: {missing}")

        return DomainEventEnvelope(
            system=SystemMetadata(**self._system_metadata),
            data=self._business_data,
            schema_version=self._schema_version,
        )

    @classmethod
    def from_domain_event(cls, domain_event: DomainEvent) -> DomainEventBuilder:
        """便捷构造方法，从 DomainEvent 模型创建 Builder。

        Args:
            domain_event: DomainEvent 模型实例

        Returns:
            预填充了事件数据的 Builder 实例

        使用示例：
            ```python
            envelope = DomainEventBuilder.from_domain_event(event).build()
            ```
        """
        return cls().with_domain_event(domain_event).with_business_data(domain_event.payload or {})
