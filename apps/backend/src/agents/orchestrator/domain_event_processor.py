"""领域事件处理模块

处理编排器的领域事件处理功能。
提取correlation_id，验证事件，映射命令，并编排响应。
"""

from __future__ import annotations

from typing import Any, NamedTuple

from src.agents.orchestrator.intent_classifier import IntentClassification, IntentClassifier
from src.common.events.config import (
    DEFAULT_VALUES,
    get_message_type,
    get_strategy_config,
    is_command_received_event,
    is_state_change_event,
    infer_scope_from_topic,
)
from src.common.events.mapping import build_topic_name, extract_strategy_key_from_event_type, get_event_by_command
from src.common.utils.datetime_utils import utc_now


class CorrelationIdExtractor:
    """关联ID提取器，负责从各种数据源中提取correlation_id。

    correlation_id用于追踪跨服务的请求链路，对于分布式系统的可观测性至关重要。
    由于不同来源（HTTP请求、消息队列、内部事件）的数据结构差异，需要支持多种提取策略。
    """

    @staticmethod
    def extract_correlation_id(evt: dict[str, Any], context: dict[str, Any] | None) -> str | None:
        """从context.meta、headers或事件元数据中提取correlation_id。

        使用新嵌套结构：system.correlation_id

        提取优先级：
        1. context.meta（显式上下文传递）
        2. context.headers（HTTP请求头）
        3. evt.system.correlation_id（事件元数据）
        4. evt.system.metadata.correlation_id（备用元数据位置）

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
                # meta通常由内部服务显式设置，优先级最高，用于服务间直接调用场景
                meta = (context or {}).get("meta") or {}
                if isinstance(meta, dict):
                    # 使用 or 运算符保留已找到的值，避免None覆盖已有的correlation_id
                    correlation_id = correlation_id or meta.get("correlation_id")

                # 尝试从headers获取（可能是字典或元组列表）
                # headers来源于HTTP请求，格式因网关/框架而异（FastAPI/ASGI规范）
                headers = (context or {}).get("headers")
                if isinstance(headers, dict):
                    # 标准字典格式：支持下划线和连字符两种命名风格
                    # 兼容不同的HTTP客户端和代理服务器的命名习惯
                    correlation_id = correlation_id or headers.get("correlation_id") or headers.get("correlation-id")
                elif isinstance(headers, list):
                    # 元组列表格式：常见于ASGI原始headers或消息队列传递场景
                    # 格式为 [(b"header-name", b"value"), ...] 或 [("header-name", "value"), ...]
                    for k, v in headers:
                        # 规范化header名称，统一处理下划线和连字符，忽略大小写
                        if str(k).lower().replace("_", "-") in {"correlation-id", "correlation_id"}:
                            try:
                                # 处理字节类型的header值（常见于底层网络协议和消息队列）
                                # bytes/bytearray需要解码为UTF-8字符串
                                correlation_id = correlation_id or (
                                    v.decode("utf-8") if isinstance(v, bytes | bytearray) else str(v)
                                )
                            except Exception:
                                # 解码失败时降级为字符串转换，确保即使编码异常也能获取部分信息
                                # 这种容错机制避免因header格式问题导致整个请求追踪链路中断
                                correlation_id = correlation_id or (str(v) if v is not None else None)
                            break
        except Exception:
            # 解析context失败不影响下游逻辑，使用回退策略
            # 允许系统在上下文不完整或格式异常时继续运行，体现容错设计
            # 即使context解析失败，仍可从事件本身的system层提取correlation_id
            pass

        # 回退到事件元数据 - 新嵌套结构
        # 如果从context提取失败，尝试从事件本身提取，确保correlation_id的可用性
        # 这是最后的回退机制，适用于内部事件或未携带context的场景
        system = evt.get("system", {})
        correlation_id = correlation_id or system.get("correlation_id")

        # 也检查system.metadata中是否有correlation_id
        # 兼容旧版事件结构或特殊场景的嵌套元数据（历史遗留或特定业务需求）
        if not correlation_id and isinstance(system.get("metadata"), dict):
            correlation_id = system["metadata"].get("correlation_id")

        return correlation_id


class EventValidator:
    """领域事件验证器，验证领域事件是否可以被处理。

    编排器需要过滤掉不相关的事件（如内部状态变更、通知等），只处理需要编排的命令接收事件。
    这样可以提高处理效率，避免无效的业务逻辑执行。
    """

    @staticmethod
    def is_command_received_event(event_type: str) -> bool:
        """检查事件是否为应该被处理的命令接收事件。

        编排器只关心Command.Received类型的事件，这些事件表示用户发起的业务操作请求。
        其他类型的事件（如领域事件、系统事件）由各自的处理器负责，不需要编排器介入。

        Args:
            event_type: 事件类型字符串

        Returns:
            如果是命令接收事件则返回True， 否则返回False
        """
        return is_command_received_event(event_type)

    @staticmethod
    def extract_command_type(evt: dict[str, Any]) -> str | None:
        """从事件data中提取command_type。

        使用新嵌套结构：data.command_type

        命令类型决定了后续的路由策略和能力任务分配，是编排逻辑的核心依据。

        Args:
            evt: 事件字典（新嵌套结构）

        Returns:
            提取到的命令类型字符串或None
        """
        # 从新嵌套结构的data字段中获取
        data = evt.get("data") or {}
        return data.get("command_type")

    @staticmethod
    def extract_scope_info(event_type: str, context: dict[str, Any] | None = None) -> tuple[str, str]:
        """从事件类型中提取作用域前缀和作用域类型。

        作用域信息用于确定事件的业务上下文（如genesis、worldbuild等），
        影响消息主题构建和能力任务的路由目标。

        事件类型格式约定：scope_prefix.Entity.Action
        示例：genesis.Command.Received、worldbuild.WorldConcept.Created

        Args:
            event_type: 事件类型字符串（格式：scope_prefix.Entity.Action）

        Returns:
            (作用域前缀, 作用域类型) 元组，例如：("genesis", "GENESIS")
        """
        # 优先使用 topic → scope 的集中推断
        topic = (context or {}).get("topic") if isinstance(context, dict) else None
        if topic:
            return infer_scope_from_topic(topic)

        # 回退：从事件类型前缀推断
        scope_prefix = event_type.split(".", 1)[0] if "." in event_type else DEFAULT_VALUES["scope_prefix"]
        scope_type = scope_prefix.upper()
        return scope_prefix, scope_type


class CommandMapping(NamedTuple):
    """命令映射结果：请求动作 + 能力消息。"""

    requested_action: str
    capability_message: dict[str, Any] | None


class CommandMapper:
    """命令映射器，将命令映射到领域事件和能力任务。

    使用策略模式的命令注册表，根据命令类型和作用域动态路由到相应的处理器。
    这种设计支持灵活的命令扩展，无需修改核心编排逻辑。
    """

    @staticmethod
    def map_command(
        cmd_type: str, scope_type: str, scope_prefix: str, aggregate_id: str, payload: dict[str, Any]
    ) -> CommandMapping | None:
        """数据驱动的直接映射：命令 → 请求动作 + 能力消息。

        - 通过配置 `get_event_by_command` 翻译命令 → 请求动作
        - 纯状态变更（如 *.Confirmed）不生成能力消息
        - 依据请求动作推断策略键，查 `get_strategy_config` 构造能力消息
        """
        event_action = get_event_by_command(cmd_type)
        if not event_action:
            return None

        if is_state_change_event(event_action):
            return CommandMapping(requested_action=event_action, capability_message=None)

        strategy_key = CommandMapper._strategy_for_action(event_action)
        cfg = get_strategy_config(strategy_key) if strategy_key else None
        if not cfg:
            return CommandMapping(requested_action=event_action, capability_message=None)

        capability_message = {
            "type": cfg["capability_type"],
            "session_id": aggregate_id,
            "input": payload or {},
            "_topic": build_topic_name(cfg["base_topic"], scope_type, scope_prefix),
            "_key": aggregate_id,
        }
        return CommandMapping(requested_action=event_action, capability_message=capability_message)

    @staticmethod
    def _strategy_for_action(event_action: str) -> str | None:
        # 特例映射：Stage.*
        if event_action.endswith("ValidationRequested"):
            return "stage_validation"
        if event_action.endswith("LockRequested"):
            return "stage_lock"
        # 通用映射：取前缀
        return extract_strategy_key_from_event_type(event_action)


class PayloadEnricher:
    """有效负载丰富器，用上下文信息丰富有效负载。

    在分布式系统中，需要确保关键上下文信息（如用户ID、时间戳）在整个处理链路中传播。
    这对于日志追踪、权限验证、SSE事件推送等功能至关重要。
    """

    @staticmethod
    def enrich_domain_payload(evt: dict[str, Any], aggregate_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        """用会话上下文丰富有效负载，并传播user_id/timestamp用于SSE路由。

        丰富策略：
        1. 添加session_id以关联会话上下文
        2. 保留原始payload作为input字段
        3. 传播user_id用于SSE路由和权限验证
        4. 传播timestamp用于事件排序和超时检测

        设计目的：
        - 确保下游Agent能够访问完整的业务上下文（会话、用户、时间）
        - 支持SSE实时推送（通过user_id匹配WebSocket连接）
        - 保持原始payload不变，避免污染业务数据

        Args:
            evt: 原始事件字典（包含user_id、created_at等顶层字段）
            aggregate_id: 聚合ID（会话标识符，用于关联同一会话的所有操作）
            payload: 原始有效负载（命令参数，纯业务数据）

        Returns:
            丰富后的有效负载字典，包含会话和路由信息
            结构：{session_id, input, user_id?, timestamp?}
        """
        # 构建基础的丰富payload结构
        enriched_payload = {
            "session_id": aggregate_id,  # 会话标识符，下游Agent用于检索会话状态和历史
            "input": payload,  # 原始业务payload，保持不变以确保下游处理逻辑正确
        }

        # 传播上下文信息（user_id/timestamp）用于下游SSE路由和业务逻辑
        # user_id是SSE推送的关键字段，EventBridge通过它匹配WebSocket连接
        user_id = evt.get("user_id")
        if user_id:
            # 只在user_id存在时添加，避免None值干扰下游逻辑
            enriched_payload["user_id"] = user_id

        # 时间戳用于事件顺序保证和超时处理
        # 从事件顶层的created_at字段提取（事件生产者设置的创建时间）
        created_at = evt.get("created_at")
        if created_at:
            # 使用timestamp字段名，与下游Agent的约定保持一致
            enriched_payload["timestamp"] = created_at

        return enriched_payload


class DomainEventProcessor:
    """主要的领域事件处理编排器，负责协调整个领域事件的处理流程。

    采用职责链模式组织处理流程：
    1. 关联ID提取 - 追踪请求链路
    2. 事件验证 - 过滤不相关事件
    3. 意图分类 - 区分查询和生成意图
    4. 命令映射 - 路由到对应的能力任务
    5. 负载丰富 - 传播上下文信息

    通过组合各个处理组件，实现松耦合的事件编排架构。
    """

    def __init__(self, logger: Any, intent_classifier: IntentClassifier | None = None) -> None:
        """初始化领域事件处理器。

        采用依赖注入模式，允许外部传入intent_classifier以支持测试和灵活配置。

        Args:
            logger: 日志记录器实例（结构化日志）
            intent_classifier: 意图分类器实例（可选，默认创建新实例）
        """
        self.log = logger
        # 组装处理组件，每个组件负责特定的职责
        self.correlation_extractor = CorrelationIdExtractor()
        self.event_validator = EventValidator()
        self.command_mapper = CommandMapper()
        self.payload_enricher = PayloadEnricher()
        # 意图分类器支持依赖注入，便于测试和配置
        self.intent_classifier = intent_classifier or IntentClassifier(logger=self.log)

    async def handle_domain_event(
        self, evt: dict[str, Any], context: dict[str, Any] | None = None
    ) -> dict[str, Any] | None:
        """处理领域事件，进行完整的编排流程。

        使用新的嵌套payload结构：
        - system: {event_type, aggregate_id, ...}
        - data: {...}
        - schema_version

        处理流程：
        1. 验证事件结构（system层必须存在）
        2. 提取事件元数据和有效负载
        3. 关联ID提取（用于链路追踪）
        4. 事件类型验证（只处理Command.Received）
        5. 意图分类（区分查询和生成意图）
        6. 根据意图路由到相应的处理器
        7. 丰富有效负载并构建处理指令

        Args:
            evt: 领域事件字典（标准化的嵌套结构）
            context: 可选的上下文信息字典（来自消息队列或HTTP请求）

        Returns:
            包含处理指令的结果字典，如果无法处理则返回None
            返回结构：{correlation_id, scope_type, aggregate_id, mapping, enriched_payload, metadata}
        """
        # 提取新嵌套结构的字段
        # system层包含事件的系统元数据（事件类型、聚合ID、时间戳等），是事件处理的基础
        # 没有system层的事件是不完整的，可能来自错误的事件生产者或格式转换问题
        system = evt.get("system")
        if not isinstance(system, dict):
            # 缺少system层表明事件结构不符合规范，无法安全处理
            # 记录警告并返回None，让编排器跳过此事件，避免下游处理错误
            self.log.warning(
                "orchestrator_domain_event_missing_system_layer",
                evt_keys=list(evt.keys()),
            )
            return None

        # 提取核心事件元数据
        # event_type确定事件的业务类型（如genesis.Command.Received）
        event_type = str(system.get("event_type") or "")
        # aggregate_id标识聚合根实例（通常是session_id），用于关联业务上下文
        aggregate_id = str(system.get("aggregate_id") or "")
        # metadata包含额外的上下文信息（user_id、novel_id、source等）
        metadata = system.get("metadata") or {}
        # event_id用于事件溯源和因果关系追踪（causation chain）
        event_id = system.get("event_id")

        # 提取业务数据层
        # data层包含命令的业务参数和payload，与system层的元数据分离
        # 这种分层设计便于事件路由、过滤和审计，符合CQRS和事件溯源的最佳实践
        data_layer = evt.get("data")
        if isinstance(data_layer, dict):
            raw_payload = data_layer.get("payload")
            if isinstance(raw_payload, dict):
                # 标准的嵌套payload结构：data.payload包含实际的业务参数
                # 这是推荐的结构，清晰地分离元数据和业务数据
                payload = raw_payload
            else:
                # 兼容未显式嵌套payload的情况（历史遗留或特定场景）
                # 移除command_type等命令元数据，只保留业务参数
                # 避免将元数据混入业务payload，确保下游处理的数据纯净性
                payload = {k: v for k, v in data_layer.items() if k != "command_type"}
        else:
            # data层缺失或格式错误时使用空字典，保证后续处理不会因payload为None而异常
            payload = {}

        # 从各种来源提取correlation_id
        # correlation_id是分布式追踪的关键，用于关联整个请求链路
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
        # 编排器的职责是处理用户发起的业务命令，其他类型的事件由专门的处理器负责
        if not self.event_validator.is_command_received_event(event_type):
            self.log.debug(
                "orchestrator_domain_event_ignored",
                event_type=event_type,
                reason="not_command_received",
            )
            return None

        # 提取命令类型
        # 命令类型决定了后续的路由策略，是编排逻辑的核心依据
        cmd_type = self.event_validator.extract_command_type(evt)
        if not cmd_type:
            # 缺少命令类型的事件无法路由，记录警告便于排查配置问题
            self.log.warning(
                "orchestrator_domain_event_missing_command_type",
                event_type=event_type,
                aggregate_id=aggregate_id,
                payload_keys=list(payload.keys()) if payload else [],
                evt_keys=list(evt.keys()),
            )
            return None

        # 提取作用域信息
        # 作用域确定了业务上下文（如genesis、worldbuild），影响消息路由和能力任务分配
        scope_prefix, scope_type = self.event_validator.extract_scope_info(event_type, context)

        self.log.info(
            "orchestrator_processing_command",
            cmd_type=cmd_type,
            scope_type=scope_type,
            scope_prefix=scope_prefix,
            aggregate_id=aggregate_id,
        )

        # 对所有 Command.Received 事件进行意图分类
        # 意图分类用于区分查询（inquiry）和生成（generation）两类不同的业务场景
        # 查询意图：用户询问现有信息，需要路由到InquiryAgent进行知识检索
        # 生成意图：用户请求创建新内容，需要路由到相应的生成Agent（WorldsmithAgent等）
        # 这个分类决策是编排器的核心职责之一，直接影响后续的处理流程和用户体验
        self.log.info(
            "orchestrator_calling_intent_classifier",
            cmd_type=cmd_type,
            payload_keys=list(payload.keys()) if payload else [],
        )

        intent_result: IntentClassification | None = None
        try:
            # 调用意图分类器（可能使用LLM进行语义分析或规则引擎进行模式匹配）
            # 分类器会分析命令类型和payload内容，返回意图分类结果及置信度
            intent_result = await self.intent_classifier.classify(command_type=cmd_type, payload=payload)
            self.log.info(
                "orchestrator_intent_classifier_returned",
                has_result=intent_result is not None,
                intent=intent_result.intent if intent_result else None,
                confidence=intent_result.confidence if intent_result else None,
            )
        except Exception as exc:
            # 意图分类失败不应阻塞整个处理流程（容错设计原则）
            # 降级为默认的生成意图处理，确保系统可用性优先于分类准确性
            # 这种设计避免了因意图分类器故障（如LLM服务不可用）导致整个系统无法工作
            self.log.warning("orchestrator_intent_classification_failed", error=str(exc), exc_info=True)
            intent_result = None

        if intent_result:
            # 成功获得意图分类结果，记录完整的分类信息用于监控和调试
            # 置信度和来源信息帮助评估分类质量和优化分类器
            self.log.info(
                "orchestrator_command_intent_classified",
                cmd_type=cmd_type,
                intent=intent_result.intent,
                confidence=intent_result.confidence,
                source=intent_result.source,
            )
        else:
            # 未获得意图分类结果（分类器返回None或发生异常）
            # 记录原因便于追踪是分类器逻辑问题还是系统故障
            self.log.info(
                "orchestrator_no_intent_result",
                cmd_type=cmd_type,
                reason="intent_classifier returned None",
            )

        # 根据意图决定路由 - 这是核心的路由决策点
        # 这个if-else分支决定了命令的后续处理路径，是编排器的关键职责
        if intent_result and intent_result.intent == "inquiry":
            # 查询意图路由 - 路由到InquiryAgent
            # InquiryAgent专门处理用户的查询请求，如"告诉我当前故事的设定"、"世界观中有哪些势力"
            # 查询不修改状态，主要从知识库（向量数据库、图数据库）检索信息
            mapping = self._create_inquiry_mapping(
                scope_type=scope_type, scope_prefix=scope_prefix, aggregate_id=aggregate_id, payload=payload
            )
        else:
            # 生成意图或无意图分类 - 使用标准的命令映射流程
            # 生成意图如"创建新的世界观"、"生成下一章节"会路由到相应的生成Agent
            # 无意图分类时默认按生成处理，保证系统的基本可用性（优雅降级）
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
            capability_type=(mapping.capability_message or {}).get("type"),
            has_capability_input=bool((mapping.capability_message or {}).get("input")),
        )

        # 针对“反馈生成”意图：将能力消息改路由到质量评审(review)
        # 并在输入中附带意图相关元信息
        if mapping and mapping.capability_message and intent_result and intent_result.intent == "feedback_generation":
            review_cfg = get_strategy_config("stage_validation")
            if review_cfg:
                mapping.capability_message["type"] = get_message_type("quality_review")
                mapping.capability_message["_topic"] = build_topic_name(
                    review_cfg["base_topic"], scope_type, scope_prefix
                )
                review_input = mapping.capability_message.get("input") or {}
                review_input = dict(review_input)
                review_input.update(
                    {
                        "intent": intent_result.intent,
                        "intent_confidence": intent_result.confidence,
                        "intent_source": intent_result.source,
                    }
                )
                mapping.capability_message["input"] = review_input

        # 丰富有效负载，添加会话上下文和路由信息
        # PayloadEnricher会添加session_id、user_id、timestamp等核心字段
        # 这些字段对于SSE推送、权限验证、事件排序等功能至关重要
        enriched_payload = self.payload_enricher.enrich_domain_payload(evt, aggregate_id, payload)

        # 如果有意图分类结果，添加到payload中
        # 意图信息对于下游的调试、监控和审计非常重要，帮助追踪路由决策的依据
        if intent_result:
            # 意图类型（inquiry/generation）决定了后续的处理路径
            enriched_payload["intent"] = intent_result.intent
            if intent_result.confidence is not None:
                # 置信度帮助下游判断分类结果的可靠性，低置信度时可能需要人工介入或额外验证
                enriched_payload["intent_confidence"] = intent_result.confidence
            # 记录分类来源（LLM、规则引擎等），便于评估不同分类器的性能和准确性
            enriched_payload["intent_source"] = intent_result.source
            if intent_result.reasoning:
                # 推理过程有助于理解分类决策（特别是LLM分类时的思考过程）
                # 便于调试分类错误和优化提示词
                enriched_payload["intent_reasoning"] = intent_result.reasoning

        # 确保downstream payload包含核心字段，避免EventBridge过滤掉事件
        # EventBridge可能根据这些字段进行路由和过滤（如基于user_id的SSE推送）
        # 使用setdefault而非直接赋值，避免覆盖已经在enrich_domain_payload中设置的值
        user_id = metadata.get("user_id")
        if user_id:
            # user_id用于：1) SSE推送时匹配客户端连接 2) 权限验证 3) 用户行为追踪
            enriched_payload.setdefault("user_id", user_id)

        novel_id = metadata.get("novel_id")
        if novel_id:
            # novel_id用于：1) 业务数据隔离 2) 多租户权限验证 3) 数据查询过滤
            enriched_payload.setdefault("novel_id", novel_id)

        # 时间戳的多级回退策略，确保始终有有效的时间信息
        # 时间戳用于：1) 事件排序和因果关系推断 2) 超时检测 3) 审计日志
        # 优先级：enriched_payload.timestamp > metadata.timestamp > system.created_at > 当前时间
        timestamp = enriched_payload.get("timestamp") or metadata.get("timestamp") or system.get("created_at")
        if not timestamp:
            # 最后的回退：使用当前UTC时间（避免时区问题）
            # 这种情况表明事件来源没有正确设置时间戳，可能需要排查事件生产者
            timestamp = utc_now().isoformat()
        enriched_payload.setdefault("timestamp", timestamp)

        # 构建派生元数据，用于事件追踪和路由
        # 这些字段会被EventBridge、监控系统和日志聚合服务使用，需要在事件顶层可见
        # 与enriched_payload中的字段部分重复，但用途不同：
        # - enriched_payload：传递给下游Agent的业务数据
        # - derived_metadata：用于事件路由和过滤的元数据
        derived_metadata = {
            key: value
            for key, value in {
                "user_id": enriched_payload.get("user_id"),
                "novel_id": enriched_payload.get("novel_id"),
                "timestamp": enriched_payload.get("timestamp"),
                "session_id": aggregate_id,  # session_id用于关联同一会话的所有事件
            }.items()
            if value is not None  # 只保留非空值，减少元数据冗余，避免None值干扰过滤逻辑
        }
        # 传播source字段（事件来源标识）
        # source用于区分事件来源（如"api"表示用户请求、"scheduler"表示定时任务）
        # 便于监控、日志分析和问题追踪
        source_value = metadata.get("source")
        if source_value is not None:
            derived_metadata["source"] = source_value

        # 返回处理指令供主编排器使用
        # 返回字典而非直接发送事件，保持编排器的控制权和可测试性
        # 这种设计允许主编排器决定是否发送事件、发送到哪里、如何处理失败等
        return {
            # 用于分布式追踪，关联整个请求链路（从用户请求到最终响应）
            "correlation_id": correlation_id,
            # 业务作用域类型（GENESIS、WORLDBUILD等），决定事件路由和处理策略
            "scope_type": scope_type,
            # 聚合根标识符（通常是session_id），用于关联同一业务实体的所有事件
            "aggregate_id": aggregate_id,
            # 命令映射结果（包含requested_action和capability_message）
            # requested_action：领域请求的事件类型（如WorldConcept.Create.Requested）
            # capability_message：发送给能力Agent的消息（包含type、input、_topic、_key）
            "mapping": mapping,
            # 丰富后的业务数据（包含session_id、user_id、timestamp、intent等）
            # 传递给下游Agent的完整上下文信息
            "enriched_payload": enriched_payload,
            # 派生元数据（用于EventBridge过滤和路由）
            # 包含user_id、novel_id、timestamp、session_id、source等关键路由字段
            "metadata": derived_metadata,
            # 因果关系ID（causation chain），用于事件溯源和调试
            # 记录当前处理是由哪个事件触发的，形成完整的因果链
            "causation_id": event_id,
        }

    def _create_inquiry_mapping(
        self, scope_type: str, scope_prefix: str, aggregate_id: str, payload: dict[str, Any]
    ) -> CommandMapping:
        """创建查询意图的映射，路由到InquiryAgent。

        InquiryAgent是处理用户查询请求的专门Agent，与生成类Agent（WorldsmithAgent等）的处理流程不同。
        查询请求不需要修改状态，主要从现有知识库和上下文中检索信息。

        设计原因：
        - 查询和生成是两种不同的业务模式，需要不同的Agent处理
        - 查询请求访问只读数据源（向量数据库、图数据库），不涉及状态变更
        - 查询Agent可以优化缓存策略，提高响应速度

        Args:
            scope_type: 作用域类型（大写，如GENESIS），用于主题构建
            scope_prefix: 作用域前缀（小写，如genesis），用于主题构建
            aggregate_id: 聚合ID（会话标识符），用于关联会话上下文和分区键
            payload: 有效负载（查询参数，包含用户问题、过滤条件等）

        Returns:
            命令映射对象，包含查询意图的路由信息和能力消息
        """
        # 构建InquiryAgent的能力消息
        # 注意：使用 "type" 字段而不是 "event_type"，因为下游Agent代码期待 "type"
        # 这是Agent消息协议的约定（历史原因），保持与现有Agent框架的兼容性
        # 未来可能会统一使用"event_type"，但需要同步修改所有Agent的消息处理逻辑
        capability_message = {
            "type": "Inquiry.Query.Requested",  # Agent消息类型，InquiryAgent会根据此字段分发到对应的处理器
            "session_id": aggregate_id,  # 关联会话上下文，用于检索会话历史和状态
            "input": payload,  # 查询参数（用户问题、过滤条件、检索偏好等）
            "_topic": build_topic_name("inquiry", scope_type, scope_prefix),  # 路由主题，如"genesis.inquiry.tasks"
            "_key": aggregate_id,  # Kafka分区键，确保同一会话的消息有序处理（同一分区保证顺序）
        }

        # 返回映射对象，包含两部分信息：
        # 1. requested_action：用于编排器的日志、监控和审计
        # 2. capability_message：实际发送给InquiryAgent的消息内容
        return CommandMapping(requested_action="Inquiry.Requested", capability_message=capability_message)
