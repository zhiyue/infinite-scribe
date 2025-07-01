"""Writer Agent 实现"""

import logging
from typing import Any

from ..base import BaseAgent

logger = logging.getLogger(__name__)


class WriterAgent(BaseAgent):
    """Writer Agent - 负责生成文本内容"""

    def __init__(self):
        # 定义消费和生产的 Kafka 主题
        consume_topics = [
            "story.write.request",  # 写作请求
            "story.rewrite.request",  # 重写请求
        ]
        produce_topics = [
            "story.write.response",  # 写作响应
            "story.review.request",  # 发送给评审的请求
        ]

        super().__init__(
            name="writer", consume_topics=consume_topics, produce_topics=produce_topics
        )

    async def process_message(self, message: dict[str, Any]) -> dict[str, Any] | None:
        """处理消息"""
        message_type = message.get("type")
        logger.info(f"Writer agent 处理消息类型: {message_type}")

        if message_type == "write_chapter":
            return await self._handle_write_chapter(message)
        elif message_type == "write_scene":
            return await self._handle_write_scene(message)
        elif message_type == "rewrite_content":
            return await self._handle_rewrite_content(message)
        else:
            logger.warning(f"未知的消息类型: {message_type}")
            return None

    async def _handle_write_chapter(self, message: dict[str, Any]) -> dict[str, Any]:
        """处理章节写作请求"""
        chapter_id = message.get("chapter_id")
        # outline = message.get("outline", {})

        logger.info(f"开始写作章节: {chapter_id}")

        # TODO: 调用 LLM 生成章节内容
        # content = await self._generate_chapter_content(outline)

        # 模拟生成的内容
        content = f"第 {chapter_id} 章内容..."

        return {
            "type": "chapter_written",
            "chapter_id": chapter_id,
            "content": content,
            "word_count": len(content),
            "_topic": "story.review.request",  # 发送给评审
        }

    async def _handle_write_scene(self, message: dict[str, Any]) -> dict[str, Any]:
        """处理场景写作请求"""
        scene_id = message.get("scene_id")
        # scene_data = message.get("scene_data", {})

        logger.info(f"开始写作场景: {scene_id}")

        # TODO: 调用 LLM 生成场景内容
        content = f"场景 {scene_id} 内容..."

        return {
            "type": "scene_written",
            "scene_id": scene_id,
            "content": content,
            "_topic": "story.write.response",
        }

    async def _handle_rewrite_content(self, message: dict[str, Any]) -> dict[str, Any]:
        """处理内容重写请求"""
        content_id = message.get("content_id")
        # original_content = message.get("original_content")
        feedback = message.get("feedback", [])

        logger.info(f"重写内容: {content_id}")

        # TODO: 基于反馈重写内容
        rewritten_content = f"重写后的内容 (基于 {len(feedback)} 条反馈)..."

        return {
            "type": "content_rewritten",
            "content_id": content_id,
            "content": rewritten_content,
            "_topic": "story.review.request",
        }

    async def on_start(self):
        """启动时的初始化"""
        logger.info("Writer agent 正在初始化...")
        # TODO: 加载模型、初始化资源等

    async def on_stop(self):
        """停止时的清理"""
        logger.info("Writer agent 正在清理资源...")
        # TODO: 保存状态、释放资源等
