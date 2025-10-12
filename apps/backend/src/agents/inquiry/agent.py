#!/usr/bin/env python
"""
Inquiry Agent - 查询助手智能体

负责处理用户的各类查询和问题请求，是InfiniteScribe系统中的咨询服务组件。
采用事件驱动架构，通过Outbox模式保证消息投递的可靠性。

核心功能:
- 小说创作进度查询 (progress queries)
- 角色信息查询 (character information)
- 世界观设定查询 (world settings)
- 系统功能说明 (system functions)
- 创作状态查询 (creation status)

架构模式:
- Outbox模式: 通过OutboxEgress保证消息发布的可靠性和事务一致性
- Envelope标准: 遵循统一的消息封装格式，确保跨服务通信的一致性
- GenerationData约定: 响应数据遵循content/metadata结构，便于下游服务解析
"""

import logging
from typing import Any

from src.agents.base import BaseAgent
from src.agents.errors import NonRetriableError
from src.external.clients.llm import ChatMessage, LLMRequest
from src.services.llm import LLMService, LLMServiceFactory
from src.services.outbox.egress import OutboxEgress

logger = logging.getLogger(__name__)


class InquiryAgent(BaseAgent):
    """查询助手智能体 - 处理用户的各类查询请求

    职责:
    - 接收并解析用户查询消息
    - 根据查询类型路由到对应的处理器
    - 调用LLM生成自然语言响应
    - 通过Outbox模式可靠发布响应事件

    设计特点:
    - 策略模式: 使用query_handlers映射表动态路由不同类型的查询
    - 依赖注入: 通过构造器注入LLMService和OutboxEgress，便于测试
    - 异步处理: 所有IO操作均为异步，提高并发性能
    """

    def __init__(
        self,
        name: str | None = None,
        consume_topics: list[str] | None = None,
        produce_topics: list[str] | None = None,
        llm_service: LLMService | None = None,
        egress: OutboxEgress | None = None,
    ):
        """初始化InquiryAgent

        依赖注入设计: 所有依赖均可通过参数注入，便于单元测试和集成测试

        Args:
            name: 智能体名称，由launcher提供，默认为"inquiry"
            consume_topics: 订阅的Kafka主题列表，由launcher提供，回退到配置文件
            produce_topics: 发布的Kafka主题列表，由launcher提供，回退到配置文件
            llm_service: LLM服务实例，用于理解查询意图和生成自然语言响应
            egress: OutboxEgress实例，实现Outbox模式的可靠消息发布
                    - 保证消息投递的at-least-once语义
                    - 支持消息持久化和重试机制
                    - 避免双写问题(double-write problem)
        """
        # 从中心化配置读取主题映射 (单一数据源原则)
        # 确保主题配置在agent_config.py中统一管理，避免配置分散
        from src.agents.agent_config import get_agent_topics

        config_consume, config_produce = get_agent_topics("inquiry")
        # 优先使用launcher提供的主题配置，回退到配置文件
        # 这种设计允许运行时动态配置，同时保持配置文件作为默认值
        final_consume = consume_topics if consume_topics is not None else config_consume
        final_produce = produce_topics if produce_topics is not None else config_produce
        final_name = name or "inquiry"

        super().__init__(name=final_name, consume_topics=final_consume, produce_topics=final_produce)

        # 初始化LLM服务和Outbox出口
        # 使用工厂模式创建LLMService，支持不同的LLM提供商
        self.llm_service = llm_service or LLMServiceFactory().create_service()
        # OutboxEgress负责消息的可靠发布，实现Outbox模式
        self.egress = egress or OutboxEgress()

        # 查询处理器映射表 (策略模式)
        # 根据查询类型动态路由到对应的处理方法，便于扩展新的查询类型
        # 如需新增查询类型，只需添加handler方法并注册到此映射表
        self.query_handlers = {
            "progress": self._handle_progress_query,  # 创作进度查询
            "character": self._handle_character_query,  # 角色信息查询
            "world": self._handle_world_query,  # 世界观查询
            "system": self._handle_system_query,  # 系统功能查询
            "general": self._handle_general_query,  # 通用查询(默认)
        }

        logger.info("InquiryAgent initialized")

    async def process_message(
        self, message: dict[str, Any], context: dict[str, Any] | None = None
    ) -> dict[str, Any] | None:
        """处理查询消息并通过OutboxEgress发布响应

        采用Outbox模式的核心处理流程:
        1. 接收并解析查询消息
        2. 识别查询类型并路由到对应处理器
        3. 生成响应数据
        4. 通过OutboxEgress持久化并发布响应事件
        5. 返回None (异步发布模式，不直接返回结果)

        为什么返回None:
        - Outbox模式要求消息通过独立的发布机制投递，而非直接返回
        - 这样可以保证消息投递的可靠性和事务一致性
        - 调用方通过订阅响应主题来接收处理结果，实现解耦

        Args:
            message: 输入消息，包含查询内容和上下文信息
            context: 消息上下文，包含correlation_id等元数据用于追踪

        Returns:
            None - 响应通过OutboxEgress异步发布，不直接返回

        Raises:
            NonRetriableError: 当消息中缺少查询内容时抛出
        """
        # 记录消息结构用于调试
        # 帮助排查消息格式不一致的问题
        message_type = (context or {}).get("meta", {}).get("type") or message.get("type")
        logger.info(
            f"InquiryAgent processing message: {message_type}",
            extra={
                "message_keys": list(message.keys()),
                "context_keys": list(context.keys()) if context else [],
                "has_meta": "meta" in (context or {}),
                "meta_type": (context or {}).get("meta", {}).get("type") if context else None,
                "message_type": message.get("type"),
            },
        )

        # 提取查询内容
        # 支持多种消息格式，兼容不同来源的查询请求
        query = self._extract_query(message)
        if not query:
            # 查询内容缺失属于不可重试错误，应该立即失败
            raise NonRetriableError("No query content found in message")

        # 提取业务上下文信息
        # session_id用于消息分区，保证同一会话的消息有序处理
        session_id = message.get("session_id")
        # user_id优先从消息体获取，回退到context.meta.aggregate_id
        user_id = message.get("user_id") or (context.get("meta", {}).get("aggregate_id") if context else None)
        # novel_id用于关联具体的小说创作项目
        novel_id = message.get("novel_id")

        # 分析查询类型
        # 使用关键词匹配识别用户意图，未来可升级为LLM分类
        query_type = await self._analyze_query_type(query)
        logger.info(f"Query type identified: {query_type}")

        # 路由到对应的处理器 (策略模式)
        # 如果查询类型未注册，默认使用general处理器
        handler = self.query_handlers.get(query_type, self._handle_general_query)

        # 执行查询处理
        # 各handler负责具体的业务逻辑和数据查询
        response = await handler(
            query=query, session_id=session_id, user_id=user_id, novel_id=novel_id, context=context
        )

        # 从上下文提取correlation_id
        # correlation_id用于跨服务追踪请求链路，遵循agent架构模式
        correlation_id = (context or {}).get("meta", {}).get("correlation_id") if context else None

        # 通过OutboxEgress发布响应 (遵循Envelope + Outbox模式)
        #
        # Outbox模式优势:
        # 1. 消息持久化到数据库后再异步发送到Kafka，避免双写问题
        # 2. 保证消息投递的at-least-once语义
        # 3. 支持失败重试和监控
        #
        # Envelope标准封装:
        # - agent: 消息来源标识
        # - topic: 目标Kafka主题
        # - key: 分区键，用于消息有序性
        # - result: 消息负载，遵循GenerationData约定
        # - correlation_id: 链路追踪ID
        await self.egress.enqueue_capability_envelope(
            agent=self.name,  # 标识消息来源为inquiry智能体
            topic="genesis.inquiry.events",  # 标准的查询事件主题
            key=session_id,  # 使用session_id作为分区键，保证同一会话的消息顺序
            result={
                # 事件类型：遵循{Domain}.{Entity}.{Action}命名约定
                "type": "Inquiry.Response.Generated",

                # session_id是必需的，GenerationData提取器依赖此字段
                "session_id": session_id,

                # content字段遵循GenerationData/ContentData约定
                # 下游服务(如Orchestrator)通过标准化的content结构解析响应
                "content": {
                    "text": response.get("text", ""),  # 主要响应文本(必需)
                    "title": query_type,  # 查询类型作为标题
                    "metadata": {  # 额外的结构化元数据
                        "query_type": query_type,  # 查询分类
                        "confidence": response.get("confidence"),  # 置信度(如果有)
                        "data_summary": response.get("data", {}),  # 数据摘要
                    },
                },

                # 保留完整的原始数据供下游使用
                "query": query,  # 原始查询，便于审计和调试
                "answer": response,  # 完整的响应数据(更自然的结构)
                "query_type": query_type,  # 查询分类结果

                # 业务上下文
                "user_id": user_id,  # 用户标识
                "novel_id": novel_id,  # 小说项目标识
            },
            correlation_id=correlation_id,  # 链路追踪ID，用于跨服务日志关联
        )

        # 返回None：Outbox模式下消息通过独立机制投递，不直接返回
        # 调用方需订阅响应主题来接收处理结果
        return None

    def _extract_query(self, message: dict[str, Any]) -> str | None:
        """从消息中提取查询内容

        容错设计：支持多种消息格式以兼容不同来源
        - 直接查询字段: query, content, text
        - 嵌套查询字段: input.user_input, input.query
        - 备用字段: user_input

        这种设计是必要的，因为:
        1. 不同上游服务可能使用不同的字段名
        2. 消息格式可能随时间演进
        3. 提高系统的容错性和向后兼容性

        Returns:
            查询文本内容，如果未找到则返回None
        """
        # 候选字段列表，按优先级顺序尝试
        # 优先尝试标准字段，然后是嵌套字段，最后是备用字段
        candidates = [
            message.get("query"),  # 标准查询字段
            message.get("input", {}).get("user_input") if isinstance(message.get("input"), dict) else None,
            message.get("input", {}).get("query") if isinstance(message.get("input"), dict) else None,
            message.get("content"),  # 通用内容字段
            message.get("text"),  # 文本字段
            message.get("user_input"),  # 直接的用户输入字段
        ]

        # 记录提取尝试的调试信息
        # 帮助排查消息格式问题
        logger.debug(
            f"_extract_query: message_keys={list(message.keys())}, "
            f"has_input={'input' in message}, "
            f"input_keys={list(message.get('input', {}).keys()) if isinstance(message.get('input'), dict) else 'N/A'}"
        )

        # 遍历候选字段，返回第一个有效的非空字符串
        for idx, candidate in enumerate(candidates):
            if isinstance(candidate, str) and candidate.strip():
                logger.info(f"Query extracted from candidate[{idx}]: {candidate[:50]}...")
                return candidate.strip()

        # 所有候选字段均为空，记录警告并返回None
        logger.warning("No query content found in any candidate field")
        return None

    async def _analyze_query_type(self, query: str) -> str:
        """分析查询类型

        当前实现: 基于关键词匹配的简单分类器
        未来改进: 可升级为基于LLM的意图识别，提高准确率

        为什么现在使用简单匹配:
        1. 快速响应，无需额外的LLM调用
        2. 对于明确的查询类型已足够准确
        3. 降低成本和延迟
        4. 易于调试和维护

        Args:
            query: 用户查询文本

        Returns:
            查询类型: progress(进度)/character(角色)/world(世界观)/system(系统)/general(通用)
        """
        # 转小写便于关键词匹配，避免大小写敏感问题
        query_lower = query.lower()

        # 按优先级顺序匹配关键词
        # 使用any()提高可读性，易于添加新关键词
        if any(keyword in query_lower for keyword in ["progress", "status"]):
            return "progress"  # 进度查询
        elif any(keyword in query_lower for keyword in ["character", "protagonist", "hero"]):
            return "character"  # 角色查询
        elif any(keyword in query_lower for keyword in ["world", "setting", "universe"]):
            return "world"  # 世界观查询
        elif any(keyword in query_lower for keyword in ["system", "function", "how", "work"]):
            return "system"  # 系统功能查询
        else:
            return "general"  # 默认为通用查询

    async def _handle_progress_query(
        self,
        query: str,
        session_id: str | None,
        user_id: str | None,
        novel_id: str | None,
        context: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """处理创作进度查询

        职责: 查询并返回小说创作的当前进度信息

        当前状态: 返回模拟数据
        TODO: 需要集成数据库查询真实的创作进度
              - 从PostgreSQL查询小说基本信息和阶段
              - 从Redis查询缓存的进度统计
              - 从Neo4j查询角色和剧情节点数量

        Returns:
            包含进度信息的响应字典，包含type、text和data字段
        """
        # 使用LLM生成自然语言响应
        # 将结构化的进度数据转化为用户友好的文本描述
        response_text = await self._generate_response(
            query=query,
            query_type="progress",
            context_info={
                "session_id": session_id,
                "novel_id": novel_id,
                "message": "This is a query about creation progress",
            },
        )

        return {
            "type": "progress",
            "text": response_text,  # LLM生成的自然语言响应
            "data": {
                # 模拟的进度数据
                # TODO: 替换为真实的数据库查询结果
                "current_stage": "character_design",  # 当前创作阶段
                "completion": 30,  # 完成百分比
                "chapters_written": 0,  # 已写章节数
                "characters_created": 2,  # 已创建角色数
            },
        }

    async def _handle_character_query(
        self,
        query: str,
        session_id: str | None,
        user_id: str | None,
        novel_id: str | None,
        context: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """处理角色信息查询

        职责: 查询并返回小说中的角色信息

        TODO: 需要集成知识库查询真实的角色数据
              - 从Neo4j查询角色关系图谱
              - 从向量数据库查询角色描述
              - 支持角色名称模糊匹配
        """
        response_text = await self._generate_response(
            query=query,
            query_type="character",
            context_info={
                "session_id": session_id,
                "novel_id": novel_id,
                "message": "This is a query about characters",
            },
        )

        return {
            "type": "character",
            "text": response_text,
            "data": {
                # 模拟的角色数据
                # TODO: 替换为知识库查询结果
                "characters": [],  # 角色列表
                "main_character": None,  # 主要角色
            },
        }

    async def _handle_world_query(
        self,
        query: str,
        session_id: str | None,
        user_id: str | None,
        novel_id: str | None,
        context: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """处理世界观设定查询

        职责: 查询并返回小说的世界观设定信息

        TODO: 需要集成知识库查询真实的世界观数据
              - 从Neo4j查询世界观结构和关系
              - 从向量数据库查询场景描述
              - 支持地点、时代、规则等多维度查询
        """
        response_text = await self._generate_response(
            query=query,
            query_type="world",
            context_info={
                "session_id": session_id,
                "novel_id": novel_id,
                "message": "This is a query about world settings",
            },
        )

        return {
            "type": "world",
            "text": response_text,
            "data": {
                # 模拟的世界观数据
                # TODO: 替换为知识库查询结果
                "setting": None,  # 世界观设定
                "locations": [],  # 地点列表
            },
        }

    async def _handle_system_query(
        self,
        query: str,
        session_id: str | None,
        user_id: str | None,
        novel_id: str | None,
        context: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """处理系统功能查询

        职责: 返回InfiniteScribe系统的功能说明和使用帮助

        特点: 无需数据库查询，返回固定的功能列表
        """
        response_text = await self._generate_response(
            query=query, query_type="system", context_info={"message": "This is a query about system functions"}
        )

        return {
            "type": "system",
            "text": response_text,
            "data": {
                # InfiniteScribe核心功能列表
                # 这是静态数据，可根据系统功能更新扩展
                "features": [
                    "Character generation",  # 角色生成
                    "World building",  # 世界观构建
                    "Plot design",  # 情节设计
                    "Chapter writing",  # 章节写作
                    "Dialogue generation",  # 对话生成
                ]
            },
        }

    async def _handle_general_query(
        self,
        query: str,
        session_id: str | None,
        user_id: str | None,
        novel_id: str | None,
        context: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """处理通用查询

        职责: 处理无法归类到特定类型的查询

        特点: 作为兜底处理器，依赖LLM生成通用响应
        """
        response_text = await self._generate_response(
            query=query,
            query_type="general",
            context_info={
                "session_id": session_id,
                "novel_id": novel_id,
            },
        )

        return {"type": "general", "text": response_text, "data": {}}

    async def _generate_response(self, query: str, query_type: str, context_info: dict[str, Any]) -> str:
        """使用LLM生成查询响应

        核心职责: 将结构化的查询和上下文转化为自然语言响应

        设计考虑:
        1. 使用低温度参数保证响应的一致性
        2. 限制token数量控制响应长度和成本
        3. 构建明确的系统提示确保响应质量
        4. 异常时回退到预定义响应保证可用性

        Args:
            query: 用户的原始查询文本
            query_type: 查询类型，影响系统提示的构建
            context_info: 上下文信息，提供给LLM作为背景知识

        Returns:
            LLM生成的响应文本，或在失败时返回兜底响应
        """
        # 构建系统提示
        # 明确LLM的角色和能力边界，确保响应符合预期
        system_prompt = f"""You are InfiniteScribe's query assistant, specialized in answering user queries about novel creation.

Current query type: {query_type}
Context information: {context_info}

Please provide accurate and helpful answers based on the query content. If specific data or status is involved, please note that this is sample data (as the system is still in development).
"""

        # 构建用户消息
        # 保持简单直接的格式
        user_message = f"User query: {query}"

        try:
            # 调用LLM服务
            request = LLMRequest(
                model="deepseek-chat",  # 使用快速模型平衡成本和质量
                messages=[
                    ChatMessage(role="system", content=system_prompt),
                    ChatMessage(role="user", content=user_message),
                ],
                temperature=0.7,  # 中等温度，平衡创造性和一致性
                max_tokens=500,  # 限制响应长度，避免过长响应
            )

            response = await self.llm_service.generate(request)
            # 如果LLM返回空响应，使用默认消息
            return response.content or "Sorry, I couldn't understand your query."

        except Exception as e:
            # LLM调用失败时记录错误并使用兜底响应
            # 确保系统在LLM服务不可用时仍能工作
            logger.error(f"Failed to generate response: {e}")
            return self._get_fallback_response(query_type)

    def _get_fallback_response(self, query_type: str) -> str:
        """获取兜底响应

        当LLM服务不可用或调用失败时提供预定义的响应
        确保系统在降级状态下仍能提供基本服务

        设计原则:
        - 响应内容诚实透明，不编造信息
        - 按查询类型提供针对性的提示
        - 引导用户稍后重试或查看其他功能

        Args:
            query_type: 查询类型

        Returns:
            预定义的兜底响应文本
        """
        fallback_responses = {
            "progress": "Current creation is in progress, please check back later for detailed progress.",
            "character": "Character information is being organized, please check back later.",
            "world": "World settings are being built, please check back later.",
            "system": "InfiniteScribe provides intelligent novel creation assistance, including character design, world building, plot generation, etc.",
            "general": "Thank you for your query, I'm processing it.",
        }
        # 如果查询类型未知，返回通用错误消息
        return fallback_responses.get(query_type, "Sorry, I'm unable to answer your question at the moment.")

    def _get_timestamp(self) -> str:
        """获取当前UTC时间戳

        使用UTC时区避免时区混淆和夏令时问题
        ISO格式便于跨系统传输和日志记录

        Returns:
            ISO格式的UTC时间戳字符串
        """
        from datetime import UTC, datetime

        return datetime.now(UTC).isoformat()

    async def on_start(self):
        """智能体启动时的初始化

        生命周期钩子: 在智能体开始处理消息前调用

        TODO: 需要实现的初始化逻辑
              - 初始化知识库连接(Neo4j, Milvus)
              - 预热缓存(Redis)
              - 加载配置和模型
              - 健康检查
        """
        logger.info("InquiryAgent starting...")
        # TODO: Initialize knowledge base connections, cache, etc.

    async def on_stop(self):
        """智能体停止时的清理

        生命周期钩子: 在智能体停止处理消息后调用

        TODO: 需要实现的清理逻辑
              - 关闭数据库连接
              - 刷新待处理的消息
              - 释放资源
              - 记录停机状态
        """
        logger.info("InquiryAgent stopping...")
        # TODO: Clean up resources, close connections, etc.
