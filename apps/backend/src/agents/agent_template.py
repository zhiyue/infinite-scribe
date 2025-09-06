"""Agent 实现模板

使用说明:
1. 复制此文件到对应的 agent 目录
2. 将 TemplateAgent 重命名为 XxxAgent(如 DirectorAgent)
3. 实现具体的业务逻辑
4. 在 __init__.py 中导出 Agent 类
"""

import logging
from typing import Any

from ..base import BaseAgent
from ..errors import NonRetriableError  # noqa: F401 - 示例用途

logger = logging.getLogger(__name__)


class TemplateAgent(BaseAgent):
    """Agent 模板类 - 请修改为具体的 Agent 描述"""

    def __init__(self):
        # 配置消费/生产主题
        consume_topics: list[str] = [
            # "example.request",
        ]
        produce_topics: list[str] = [
            # "example.response",
        ]
        super().__init__(name="template", consume_topics=consume_topics, produce_topics=produce_topics)

        # TODO: 初始化 agent 特定的配置和资源（模型、数据库、缓存等）

    async def process_message(
        self, message: dict[str, Any], context: dict[str, Any] | None = None
    ) -> dict[str, Any] | None:
        """处理消息

        Args:
            message: 输入消息,通常包含:
                - type: 消息类型
                - content: 消息内容
                - metadata: 元数据
            context: 消息上下文with metadata

        Returns:
            处理结果字典, 或 None 如果不需要响应
        """
        logger.info(f"{self.name} 正在处理消息: {message.get('type', 'unknown')}")

        # TODO: 实现具体的消息处理逻辑
        message_type = message.get("type")

        if message_type == "example_type":
            return await self._handle_example_type(message, context)
        else:
            logger.warning(f"未知的消息类型: {message_type}")
            return {
                "status": "error",
                "agent": self.name,
                "message": f"未知的消息类型: {message_type}",
            }

    async def _handle_example_type(
        self, message: dict[str, Any], context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """处理特定类型的消息"""
        # TODO: 实现具体的处理逻辑
        # 如需不可重试错误，抛出 NonRetriableError
        # raise NonRetriableError("invalid request")
        return {"status": "success", "agent": self.name, "result": "处理完成"}

    async def on_start(self):
        """启动时的初始化（可选）"""
        logger.info(f"{self.name} 初始化完成")

    async def on_stop(self):
        """停止时的清理（可选）"""
        logger.info(f"{self.name} 资源清理完成")
