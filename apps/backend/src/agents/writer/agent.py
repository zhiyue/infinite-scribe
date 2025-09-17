"""Writer Agent 实现"""

from typing import Any

from ...external.clients.errors import ServiceAuthenticationError
from ...external.clients.llm import ChatMessage, LLMRequest
from ...services.llm import LLMService, LLMServiceFactory
from ..agent_config import get_agent_topics
from ..base import BaseAgent
from ..errors import NonRetriableError


class WriterAgent(BaseAgent):
    """Writer Agent - 负责生成文本内容"""

    def __init__(self, llm_service: LLMService | None = None):
        # 从集中配置读取主题映射（单一真相源）
        consume_topics, produce_topics = get_agent_topics("writer")
        super().__init__(name="writer", consume_topics=consume_topics, produce_topics=produce_topics)
        # 依赖注入 LLMService，缺省使用工厂构建的默认实例
        self.llm_service = llm_service or LLMServiceFactory().create_service()

    async def process_message(
        self, message: dict[str, Any], context: dict[str, Any] | None = None
    ) -> dict[str, Any] | None:
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

    async def _handle_write_chapter(
        self, message: dict[str, Any], context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """处理章节写作请求"""
        chapter_id = message.get("chapter_id")
        # outline = message.get("outline", {})

        self.log.info("writing_chapter", chapter_id=chapter_id)

        # 调用 LLM 生成章节内容
        prompt = message.get("prompt") or f"请为章节 {chapter_id} 写一段内容。"
        req = LLMRequest(
            model=self.config.llm.default_model or "gpt-4o-mini",
            messages=[
                ChatMessage(role="system", content="You are a helpful writing assistant."),
                ChatMessage(role="user", content=str(prompt)),
            ],
        )
        llm_resp = await self.llm_service.generate(req)
        content = llm_resp.content or f"第 {chapter_id} 章内容..."

        return {
            "type": "chapter_written",
            "chapter_id": chapter_id,
            "content": content,
            "word_count": len(content),
            # Writer 能力结果事件 -> 能力总线 events
            "_topic": "genesis.writer.events",
            "_key": str(chapter_id) if chapter_id is not None else None,
        }

    async def _handle_write_scene(
        self, message: dict[str, Any], context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """处理场景写作请求"""
        scene_id = message.get("scene_id")
        # scene_data = message.get("scene_data", {})

        self.log.info("writing_scene", scene_id=scene_id)

        prompt = message.get("prompt") or f"请撰写场景 {scene_id} 的内容。"
        req = LLMRequest(
            model=self.config.llm.default_model or "gpt-4o-mini",
            messages=[
                ChatMessage(role="system", content="You are a helpful writing assistant."),
                ChatMessage(role="user", content=str(prompt)),
            ],
        )
        llm_resp = await self.llm_service.generate(req)
        content = llm_resp.content or f"场景 {scene_id} 内容..."

        return {
            "type": "scene_written",
            "scene_id": scene_id,
            "content": content,
            "_topic": "genesis.writer.events",
            "_key": str(scene_id) if scene_id is not None else None,
        }

    async def _handle_rewrite_content(
        self, message: dict[str, Any], context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """处理内容重写请求"""
        content_id = message.get("content_id")
        # original_content = message.get("original_content")
        feedback = message.get("feedback", [])

        self.log.info("rewriting_content", content_id=content_id)

        base_text = message.get("original_content") or ""
        prompt = f"请基于以下反馈重写内容：{feedback}. 原文：{base_text}"
        req = LLMRequest(
            model=self.config.llm.default_model or "gpt-4o-mini",
            messages=[
                ChatMessage(role="system", content="You are a helpful writing assistant."),
                ChatMessage(role="user", content=str(prompt)),
            ],
        )
        llm_resp = await self.llm_service.generate(req)
        rewritten_content = llm_resp.content or f"重写后的内容 (基于 {len(feedback)} 条反馈)..."

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

    def classify_error(self, error: Exception, message: dict[str, Any]) -> "Literal['retriable','non_retriable']":
        """覆盖错误分类：
        - 参数/鉴权类错误 → non_retriable
        - 其他 → retriable（交由重试与DLT策略处理）
        """

        if isinstance(error, (NonRetriableError, ServiceAuthenticationError)):
            return "non_retriable"  # type: ignore[return-value]
        if isinstance(error, ValueError) and "missing" in str(error).lower():
            return "non_retriable"  # type: ignore[return-value]
        return "retriable"  # type: ignore[return-value]
