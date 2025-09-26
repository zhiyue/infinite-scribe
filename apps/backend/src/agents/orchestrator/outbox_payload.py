"""Outbox Payload Builder模块

实现LLD规范的命名空间隔离构建器，确保系统元数据与业务数据完全分离。
"""

from __future__ import annotations

from typing import Any, NotRequired, TypedDict

from src.models.event import DomainEvent


class SystemMetadata(TypedDict):
    """系统元数据类型定义"""

    event_id: str
    event_type: str
    aggregate_type: str
    aggregate_id: str
    metadata: dict[str, Any]
    correlation_id: NotRequired[str]
    causation_id: NotRequired[str]
    created_at: NotRequired[str]
    event_version: NotRequired[int]


class OutboxPayloadEnvelope(TypedDict):
    """Outbox有效负载信封结构定义"""

    system: SystemMetadata
    data: dict[str, Any]
    schema_version: str


class OutboxPayloadBuilder:
    """类型安全的outbox payload构建器

    优势：
    - 彻底消除字段冲突风险
    - 为后续演进（版本升级）提供明确边界
    - 保持结构清晰：system层专注元数据，data层专注业务负载
    """

    RESERVED_TOP_LEVEL_FIELDS = {"system", "data", "schema_version"}

    def __init__(self):
        self._system_metadata: dict[str, Any] = {}
        self._business_data: dict[str, Any] = {}
        self._schema_version: str = "v1"

    def with_domain_event(self, event: DomainEvent) -> OutboxPayloadBuilder:
        """从领域事件提取系统元数据"""
        self._system_metadata = {
            "event_id": str(event.event_id),
            "event_type": event.event_type,
            "aggregate_type": event.aggregate_type,
            "aggregate_id": event.aggregate_id,
            "metadata": event.event_metadata or {},
        }

        # 添加可选字段
        if hasattr(event, "correlation_id") and event.correlation_id:
            self._system_metadata["correlation_id"] = str(event.correlation_id)

        if hasattr(event, "causation_id") and event.causation_id:
            self._system_metadata["causation_id"] = str(event.causation_id)

        if hasattr(event, "created_at") and event.created_at:
            try:
                self._system_metadata["created_at"] = event.created_at.isoformat()
            except Exception:
                # 静默处理时间格式化异常
                pass

        # 添加event_version支持
        if hasattr(event, "event_version") and event.event_version is not None:
            self._system_metadata["event_version"] = event.event_version

        return self

    def with_business_data(self, data: dict[str, Any]) -> OutboxPayloadBuilder:
        """设置业务数据，防御性检查顶层保留字段冲突"""
        if not data:
            return self

        # 检查业务数据是否包含顶层保留字段
        conflicts = set(data.keys()) & self.RESERVED_TOP_LEVEL_FIELDS
        if conflicts:
            raise ValueError(
                f"Business data contains reserved top-level fields: {conflicts}. "
                f"These fields conflict with the envelope structure."
            )

        self._business_data = data
        return self

    def with_schema_version(self, version: str) -> OutboxPayloadBuilder:
        """设置Schema版本（支持灰度迁移）"""
        self._schema_version = version
        return self

    def build(self) -> OutboxPayloadEnvelope:
        """构建最终的outbox payload"""
        # 完整性校验：必需的系统字段
        required_fields = ["event_id", "event_type", "aggregate_type", "aggregate_id"]
        missing_fields = [field for field in required_fields if field not in self._system_metadata]

        if missing_fields:
            raise ValueError(f"Missing required system metadata fields: {missing_fields}")

        return {"system": self._system_metadata, "data": self._business_data, "schema_version": self._schema_version}

    @classmethod
    def from_domain_event(cls, domain_event: DomainEvent) -> OutboxPayloadBuilder:
        """便捷工厂方法"""
        return cls().with_domain_event(domain_event).with_business_data(domain_event.payload or {})
