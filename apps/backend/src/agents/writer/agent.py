"""Writer Agent 实现"""

from typing import Any

from ..agent_config import get_agent_topics
from ..base import BaseAgent


class WriterAgent(BaseAgent):
    """Writer Agent - 负责生成文本内容"""

    def __init__(self):
        # 从集中配置读取主题映射（单一真相源）
        consume_topics, produce_topics = get_agent_topics("writer")
        super().__init__(name="writer", consume_topics=consume_topics, produce_topics=produce_topics)

    async def process_message(self, message: dict[str, Any], context: dict[str, Any] | None = None) -> dict[str, Any] | None:
        """处理消息"""
        message_type = message.get("type")
        self.log.info("processing_message", message_type=message_type)

        if message_type == "write_chapter":
            return await self._handle_write_chapter(message, context)
        elif message_type == "write_scene":
            return await self._handle_write_scene(message, context)
        elif message_type == "rewrite_content":
            return await self._handle_rewrite_content(message, context)
        else:
            self.log.warning("unknown_message_type", message_type=message_type)
            return None

    async def _handle_write_chapter(self, message: dict[str, Any], context: dict[str, Any] | None = None) -> dict[str, Any]:
        """处理章节写作请求"""
        chapter_id = message.get("chapter_id")
        # outline = message.get("outline", {})

        self.log.info("writing_chapter", chapter_id=chapter_id)

        # TODO: 调用 LLM 生成章节内容
        # content = await self._generate_chapter_content(outline)

        # 模拟生成的内容
        content = f"第 {chapter_id} 章内容..."

        return {
            "type": "chapter_written",
            "chapter_id": chapter_id,
            "content": content,
            "word_count": len(content),
            # Writer 能力结果事件 -> 能力总线 events
            "_topic": "genesis.writer.events",
            "_key": str(chapter_id) if chapter_id is not None else None,
        }

    async def _handle_write_scene(self, message: dict[str, Any], context: dict[str, Any] | None = None) -> dict[str, Any]:
        """处理场景写作请求"""
        scene_id = message.get("scene_id")
        # scene_data = message.get("scene_data", {})

        self.log.info("writing_scene", scene_id=scene_id)

        # TODO: 调用 LLM 生成场景内容
        content = f"场景 {scene_id} 内容..."

        return {
            "type": "scene_written",
            "scene_id": scene_id,
            "content": content,
            "_topic": "genesis.writer.events",
            "_key": str(scene_id) if scene_id is not None else None,
        }

    async def _handle_rewrite_content(self, message: dict[str, Any], context: dict[str, Any] | None = None) -> dict[str, Any]:
        """处理内容重写请求"""
        content_id = message.get("content_id")
        # original_content = message.get("original_content")
        feedback = message.get("feedback", [])

        self.log.info("rewriting_content", content_id=content_id)

        # TODO: 基于反馈重写内容
        rewritten_content = f"重写后的内容 (基于 {len(feedback)} 条反馈)..."

        return {
            "type": "content_rewritten",
            "content_id": content_id,
            "content": rewritten_content,
            "_topic": "genesis.writer.events",
            "_key": str(content_id) if content_id is not None else None,
        }

    async def on_start(self):
        """启动时的初始化"""
        self.log.info("writer_agent_starting")
        # TODO: 加载模型、初始化资源等

    async def on_stop(self):
        """停止时的清理"""
        self.log.info("writer_agent_stopping")
        # TODO: 保存状态、释放资源等
