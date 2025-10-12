"""Agent 实现模板

使用说明:
1. 复制此文件到对应的 agent 目录
2. 将 TemplateAgent 重命名为 XxxAgent(如 DirectorAgent)
3. 实现具体的业务逻辑
4. 在 __init__.py 中导出 Agent 类
5. 在 src/agents/agent_config.py 中配置主题映射

最佳实践:
- 支持依赖注入以提高可测试性
- 从集中配置读取主题映射（agent_config.py）
- 使用 'type' 字段标识消息类型（不是 event_type）
- 返回消息时可包含 '_key' 用于 Kafka 分区
- 使用结构化日志记录
"""

import logging
from typing import Any

from src.agents.base import BaseAgent

logger = logging.getLogger(__name__)


class TemplateAgent(BaseAgent):
    """Agent 模板类 - 请修改为具体的 Agent 描述"""

    def __init__(
        self,
        name: str | None = None,
        consume_topics: list[str] | None = None,
        produce_topics: list[str] | None = None,
        # TODO: 添加其他依赖注入参数（如 LLM service、数据库连接等）
        # llm_service: LLMService | None = None,
        # db_client: DatabaseClient | None = None,
    ):
        """
        初始化 Agent

        Args:
            name: Agent 名称（由 launcher 提供，默认为 "template"）
            consume_topics: 消费的主题列表（由 launcher 提供，回退到配置）
            produce_topics: 生产的主题列表（由 launcher 提供，回退到配置）
            # TODO: 文档化其他依赖参数
        """
        # 从集中配置读取主题映射（单一数据源）
        from src.agents.agent_config import get_agent_topics

        config_consume, config_produce = get_agent_topics("template")  # 修改为实际 agent_id
        # 优先使用提供的主题（来自 launcher），否则使用配置
        final_consume = consume_topics if consume_topics is not None else config_consume
        final_produce = produce_topics if produce_topics is not None else config_produce
        final_name = name or "template"  # 修改为实际默认名称

        super().__init__(name=final_name, consume_topics=final_consume, produce_topics=final_produce)

        # TODO: 初始化 agent 特定的配置和资源
        # self.llm_service = llm_service or LLMServiceFactory().create_service()
        # self.db_client = db_client or DatabaseClientFactory().create_client()

        logger.info(f"{self.name} initialized")

    async def process_message(
        self, message: dict[str, Any], context: dict[str, Any] | None = None
    ) -> dict[str, Any] | None:
        """处理消息

        Args:
            message: 输入消息，通常包含:
                - type: 消息类型（注意：不是 event_type）
                - content: 消息内容
                - metadata: 元数据
                - session_id: 会话 ID（可选，用于分区）
            context: 消息上下文，包含:
                - topic: 来源主题
                - partition: 分区号
                - offset: 偏移量
                - meta: 解码后的元数据（correlation_id、message_id 等）
                - headers: Kafka 消息头

        Returns:
            处理结果字典，可包含:
                - type: 消息类型（必需，用于标识响应类型）
                - _topic: 目标主题（可选，不指定则使用默认 produce_topics[0]）
                - _key: 分区键（可选，用于消息路由，推荐使用 session_id）
                - status: 处理状态
                - agent: Agent 名称
                - 其他业务数据...
            或 None 如果不需要响应
        """
        # 从 context 或 message 中获取消息类型
        message_type = (context or {}).get("meta", {}).get("type") or message.get("type")

        logger.info(
            f"{self.name} 正在处理消息: {message_type}",
            extra={
                "message_type": message_type,
                "message_keys": list(message.keys()),
                "context_keys": list(context.keys()) if context else [],
            },
        )

        # TODO: 实现具体的消息处理逻辑
        if message_type == "Example.Request":  # 使用规范的事件命名（见 event-types.md）
            return await self._handle_example_request(message, context)
        else:
            logger.warning(f"未知的消息类型: {message_type}")
            # 返回错误响应
            return {
                "type": "Template.Error.UnknownType",  # 使用规范的事件类型
                "status": "error",
                "agent": self.name,
                "error_message": f"未知的消息类型: {message_type}",
                "original_type": message_type,
            }

    async def _handle_example_request(
        self, message: dict[str, Any], context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """处理特定类型的消息示例

        Args:
            message: 输入消息
            context: 消息上下文

        Returns:
            处理结果

        Raises:
            NonRetriableError: 当遇到不可重试的错误时（如无效的请求参数）
        """
        # 提取业务数据
        # content = message.get("content")
        session_id = message.get("session_id")
        # user_id = context.get("user_id") if context else None

        # TODO: 实现具体的处理逻辑
        # 示例：调用外部服务
        # try:
        #     result = await self.llm_service.generate(...)
        # except ValidationError as e:
        #     # 业务逻辑错误，不应重试
        #     raise NonRetriableError(f"Invalid request: {e}")
        # except ServiceError as e:
        #     # 外部服务错误，可以重试（抛出普通异常）
        #     raise RuntimeError(f"Service error: {e}")

        # 构造响应消息
        return {
            "type": "Template.Response.Generated",  # 使用规范的事件类型
            "status": "success",
            "agent": self.name,
            "result": "处理完成",
            "session_id": session_id,
            "_key": session_id,  # 使用 session_id 作为分区键，确保同一会话的消息顺序
            # 可选：指定目标主题
            # "_topic": "specific.response.topic",
            "metadata": {
                "timestamp": self._get_timestamp(),
                # 其他元数据...
            },
        }

    def _get_timestamp(self) -> str:
        """获取当前 ISO 格式时间戳"""
        from datetime import UTC, datetime

        return datetime.now(UTC).isoformat()

    async def on_start(self):
        """启动时的初始化（可选）

        在 Agent 开始消费消息前调用，用于：
        - 初始化外部连接（数据库、缓存、知识库等）
        - 预加载配置或模型
        - 验证依赖服务可用性
        """
        logger.info(f"{self.name} 启动中...")
        # TODO: 实现启动逻辑
        # 示例：
        # await self.db_client.connect()
        # await self.cache.initialize()
        logger.info(f"{self.name} 启动完成")

    async def on_stop(self):
        """停止时的清理（可选）

        在 Agent 停止前调用，用于：
        - 关闭外部连接
        - 清理临时资源
        - 刷新缓存或持久化状态
        """
        logger.info(f"{self.name} 停止中...")
        # TODO: 实现清理逻辑
        # 示例：
        # await self.db_client.close()
        # await self.cache.flush()
        logger.info(f"{self.name} 已停止")
