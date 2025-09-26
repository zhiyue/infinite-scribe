"""领域事件处理模块

处理编排器的领域事件处理功能。
提取correlation_id，验证事件，映射命令，并编排响应。
"""

from __future__ import annotations

from typing import Any

from src.agents.orchestrator.command_strategies import command_registry


class CorrelationIdExtractor:
    """关联ID提取器，负责从各种数据源中提取correlation_id。"""

    @staticmethod
    def extract_correlation_id(evt: dict[str, Any], context: dict[str, Any] | None) -> str | None:
        """从context.meta、headers或事件元数据中提取correlation_id。

        使用新嵌套结构：system.correlation_id

        Args:
            evt: 事件字典（新嵌套结构）
            context: 可选的上下文信息字典

        Returns:
            提取到的correlation_id字符串或None
        """
        correlation_id: str | None = None

        try:
            if context:
                # 首先尝试从context.meta获取
                meta = (context or {}).get("meta") or {}
                if isinstance(meta, dict):
                    correlation_id = correlation_id or meta.get("correlation_id")

                # 尝试从headers获取（可能是字典或元组列表）
                headers = (context or {}).get("headers")
                if isinstance(headers, dict):
                    correlation_id = correlation_id or headers.get("correlation_id") or headers.get("correlation-id")
                elif isinstance(headers, list):
                    for k, v in headers:
                        if str(k).lower().replace("_", "-") in {"correlation-id", "correlation_id"}:
                            try:
                                correlation_id = correlation_id or (
                                    v.decode("utf-8") if isinstance(v, bytes | bytearray) else str(v)
                                )
                            except Exception:
                                correlation_id = correlation_id or (str(v) if v is not None else None)
                            break
        except Exception:
            # 解析失败不影响下游逻辑，使用回退策略
            pass

        # 回退到事件元数据 - 新嵌套结构
        system = evt.get("system", {})
        correlation_id = correlation_id or system.get("correlation_id")
        
        # 也检查system.metadata中是否有correlation_id
        if not correlation_id and isinstance(system.get("metadata"), dict):
            correlation_id = system["metadata"].get("correlation_id")

        return correlation_id


class EventValidator:
    """领域事件验证器，验证领域事件是否可以被处理。"""

    @staticmethod
    def is_command_received_event(event_type: str) -> bool:
        """检查事件是否为应该被处理的命令接收事件。

        Args:
            event_type: 事件类型字符串

        Returns:
            如果是命令接收事件则返回True， 否则返回False
        """
        from src.common.events.config import is_command_received_event

        return is_command_received_event(event_type)

    @staticmethod
    def extract_command_type(evt: dict[str, Any]) -> str | None:
        """从事件data中提取command_type。

        使用新嵌套结构：data.command_type

        Args:
            evt: 事件字典（新嵌套结构）

        Returns:
            提取到的命令类型字符串或None
        """
        # 从新嵌套结构的data字段中获取
        data = evt.get("data") or {}
        return data.get("command_type")

    @staticmethod
    def extract_scope_info(event_type: str) -> tuple[str, str]:
        """从事件类型中提取作用域前缀和作用域类型。

        Args:
            event_type: 事件类型字符串

        Returns:
            (作用域前缀, 作用域类型) 元组
        """
        from src.common.events.config import DEFAULT_VALUES

        scope_prefix = event_type.split(".", 1)[0] if "." in event_type else DEFAULT_VALUES["scope_prefix"]
        scope_type = scope_prefix.upper()  # 例如: GENESIS
        return scope_prefix, scope_type


class CommandMapper:
    """命令映射器，将命令映射到领域事件和能力任务。"""

    @staticmethod
    def map_command(
        cmd_type: str, scope_type: str, scope_prefix: str, aggregate_id: str, payload: dict[str, Any]
    ) -> Any:  # 返回来自command_registry的CommandMapping
        """使用命令注册表将命令映射到领域请求和能力任务。

        Args:
            cmd_type: 命令类型
            scope_type: 作用域类型
            scope_prefix: 作用域前缀
            aggregate_id: 聚合ID
            payload: 有效负载数据

        Returns:
            命令映射对象
        """
        return command_registry.process_command(
            cmd_type=cmd_type,
            scope_type=scope_type,
            scope_prefix=scope_prefix,
            aggregate_id=aggregate_id,
            payload=payload,
        )


class PayloadEnricher:
    """有效负载丰富器，用上下文信息丰富有效负载。"""

    @staticmethod
    def enrich_domain_payload(evt: dict[str, Any], aggregate_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        """用会话上下文丰富有效负载，并传播user_id/timestamp用于SSE路由。

        Args:
            evt: 原始事件字典
            aggregate_id: 聚合ID
            payload: 原始有效负载

        Returns:
            丰富后的有效负载字典
        """
        enriched_payload = {
            "session_id": aggregate_id,
            "input": payload,  # payload已经是嵌套的命令数据
        }

        # 传播上下文信息（user_id/timestamp）用于下游SSE路由
        user_id = evt.get("user_id")
        if user_id:
            enriched_payload["user_id"] = user_id
        created_at = evt.get("created_at")
        if created_at:
            enriched_payload["timestamp"] = created_at

        return enriched_payload


class DomainEventProcessor:
    """主要的领域事件处理编排器，负责协调整个领域事件的处理流程。"""

    def __init__(self, logger: Any) -> None:
        """初始化领域事件处理器。

        Args:
            logger: 日志记录器实例
        """
        self.log = logger
        self.correlation_extractor = CorrelationIdExtractor()
        self.event_validator = EventValidator()
        self.command_mapper = CommandMapper()
        self.payload_enricher = PayloadEnricher()

    async def handle_domain_event(
        self, evt: dict[str, Any], context: dict[str, Any] | None = None
    ) -> dict[str, Any] | None:
        """处理领域事件，进行完整的编排流程。

        使用新的嵌套payload结构：
        - system: {event_type, aggregate_id, ...}
        - data: {...}
        - schema_version

        Args:
            evt: 领域事件字典
            context: 可选的上下文信息字典

        Returns:
            包含处理指令的结果字典，如果无法处理则返回None
        """
        # 提取新嵌套结构的字段
        system = evt.get("system")
        if not isinstance(system, dict):
            self.log.warning(
                "orchestrator_domain_event_missing_system_layer",
                evt_keys=list(evt.keys()),
            )
            return None

        event_type = str(system.get("event_type") or "")
        aggregate_id = str(system.get("aggregate_id") or "")
        metadata = system.get("metadata") or {}
        event_id = system.get("event_id")

        data_layer = evt.get("data")
        if isinstance(data_layer, dict):
            raw_payload = data_layer.get("payload")
            if isinstance(raw_payload, dict):
                payload = raw_payload
            else:
                # 兼容未显式嵌套payload的情况，移除命令元数据
                payload = {k: v for k, v in data_layer.items() if k != "command_type"}
        else:
            payload = {}

        # 从各种来源提取correlation_id
        correlation_id = self.correlation_extractor.extract_correlation_id(evt, context)

        self.log.info(
            "orchestrator_domain_event_details",
            event_type=event_type,
            aggregate_id=aggregate_id,
            correlation_id=correlation_id,
            payload_keys=list(payload.keys()) if payload else [],
            metadata_keys=list(metadata.keys()) if metadata else [],
            schema_version=evt.get("schema_version"),
        )

        # 验证事件类型 - 只处理命令接收事件，过滤掉非命令事件以提高处理效率
        if not self.event_validator.is_command_received_event(event_type):
            self.log.debug(
                "orchestrator_domain_event_ignored",
                event_type=event_type,
                reason="not_command_received",
            )
            return None

        # 提取命令类型
        cmd_type = self.event_validator.extract_command_type(evt)
        if not cmd_type:
            self.log.warning(
                "orchestrator_domain_event_missing_command_type",
                event_type=event_type,
                aggregate_id=aggregate_id,
                payload_keys=list(payload.keys()) if payload else [],
                evt_keys=list(evt.keys()),
            )
            return None

        # 提取作用域信息
        scope_prefix, scope_type = self.event_validator.extract_scope_info(event_type)

        self.log.info(
            "orchestrator_processing_command",
            cmd_type=cmd_type,
            scope_type=scope_type,
            scope_prefix=scope_prefix,
            aggregate_id=aggregate_id,
        )

        # 将命令映射到领域事件和能力任务
        mapping = self.command_mapper.map_command(cmd_type, scope_type, scope_prefix, aggregate_id, payload)

        if not mapping:
            self.log.warning(
                "orchestrator_command_mapping_failed",
                cmd_type=cmd_type,
                scope_type=scope_type,
                aggregate_id=aggregate_id,
                reason="no_mapping_found",
            )
            return None

        self.log.info(
            "orchestrator_command_mapped",
            cmd_type=cmd_type,
            requested_action=mapping.requested_action,
            capability_type=mapping.capability_message.get("type"),
            has_capability_input=bool(mapping.capability_message.get("input")),
        )

        # 返回处理指令供主编排器使用
        return {
            "correlation_id": correlation_id,
            "scope_type": scope_type,
            "aggregate_id": aggregate_id,
            "mapping": mapping,
            "enriched_payload": self.payload_enricher.enrich_domain_payload(evt, aggregate_id, payload),
            "causation_id": event_id,
        }
