"""Writer Agent 实现"""

from typing import Any, Literal

from src.agents.agent_config import get_agent_topics
from src.agents.base import BaseAgent
from src.agents.errors import NonRetriableError
from src.agents.writer.tools import get_writer_tool_specs
from src.external.clients.errors import ServiceAuthenticationError
from src.external.clients.llm import ChatMessage, LLMRequest
from src.services.llm import LLMService, LLMServiceFactory
from src.services.llm.context_builder import PreContextBuilder


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
        """处理章节写作请求（结构化 Prompt + 工具调用回路）。"""
        chapter_id = message.get("chapter_id")
        outline = message.get("outline")
        style = message.get("style", "严谨/细腻/叙事性强")
        locale = message.get("locale", "zh-CN")
        length = message.get("length", "中等")

        self.log.info("writing_chapter", chapter_id=chapter_id)

        user_prompt = {
            "task": "write_chapter",
            "chapter_id": chapter_id,
            "outline": outline,
            "style": style,
            "locale": locale,
            "length": length,
            "extra": message.get("extra", {}),
        }
        content = await self._generate_with_tools(user_prompt)

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
        """处理场景写作请求（结构化 Prompt + 工具调用回路）。"""
        scene_id = message.get("scene_id")
        scene_data = message.get("scene_data")
        tone = message.get("tone", "沉浸/悬疑")

        self.log.info("writing_scene", scene_id=scene_id)

        user_prompt = {
            "task": "write_scene",
            "scene_id": scene_id,
            "scene_data": scene_data,
            "tone": tone,
        }
        content = await self._generate_with_tools(user_prompt)

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
        """处理内容重写请求（结构化 Prompt + 工具调用回路）。"""
        content_id = message.get("content_id")
        feedback = message.get("feedback", [])
        original_content = message.get("original_content")

        self.log.info("rewriting_content", content_id=content_id)

        user_prompt = {
            "task": "rewrite",
            "content_id": content_id,
            "feedback": feedback,
            "original_content": original_content,
        }
        rewritten_content = await self._generate_with_tools(user_prompt)

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

        if isinstance(error, NonRetriableError | ServiceAuthenticationError):
            return "non_retriable"  # type: ignore[return-value]
        if isinstance(error, ValueError) and "missing" in str(error).lower():
            return "non_retriable"  # type: ignore[return-value]
        return "retriable"  # type: ignore[return-value]

    async def _generate_with_tools(self, user_prompt: dict[str, Any]) -> str:
        """先流式获取可能的工具调用，执行工具后再二次生成，最终返回内容。"""
        # Build pre-context from KB to reduce tool calls and cost
        pre = await PreContextBuilder.build_for_writer(user_prompt)
        system = ChatMessage(role="system", content=PreContextBuilder.as_system_context(pre))
        import json as _json

        user = ChatMessage(role="user", content=_json.dumps(user_prompt, ensure_ascii=False))
        model = self.config.llm.default_model or "gpt-4o-mini"

        initial_messages: list[Any] = [system, user]
        tool_calls: list[dict[str, Any]] = []
        content_parts: list[str] = []
        try:
            # If pre-context has some data, we can disable tool calls initially to prefer fast path
            has_pre = bool((pre.get("worldview") or {}).get("items")) or bool(pre.get("characters"))
            async for event in self.llm_service.stream(
                LLMRequest(
                    model=model,
                    messages=initial_messages,
                    tools=get_writer_tool_specs(),
                    tool_choice=("none" if has_pre else "auto"),
                    stream=True,
                )
            ):
                if event["type"] == "delta":
                    content_parts.append(str(event["data"].get("content", "")))
                elif event["type"] == "complete":
                    tool_calls = event["data"].get("tool_calls", []) or []
                    break
        except Exception as e:
            self.log.warning("stream_failed_fallback_generate", error=str(e))
            resp = await self.llm_service.generate(
                LLMRequest(
                    model=model,
                    messages=initial_messages,
                    tools=get_writer_tool_specs(),
                    tool_choice=("none" if has_pre else "auto"),
                )
            )
            return resp.content or ""

        if not tool_calls:
            content = "".join(content_parts).strip()
            if content:
                return content
            resp = await self.llm_service.generate(
                LLMRequest(
                    model=model,
                    messages=initial_messages,
                    tools=get_writer_tool_specs(),
                    tool_choice=("none" if has_pre else "auto"),
                )
            )
            return resp.content or ""

        # 执行工具
        tool_results = await self._execute_tools(tool_calls)
        assistant_msg = {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "id": tc.get("id"),
                    "type": "function",
                    "function": {"name": tc.get("name"), "arguments": tc.get("arguments", "")},
                }
                for tc in tool_calls
            ],
        }
        tool_msgs = [{"role": "tool", "tool_call_id": tr["id"], "content": tr["result"]} for tr in tool_results]
        final_messages: list[Any] = [system, user, assistant_msg, *tool_msgs]
        final_resp = await self.llm_service.generate(
            LLMRequest(
                model=model,
                messages=final_messages,
                tools=get_writer_tool_specs(),
                tool_choice="auto",
            )
        )
        return final_resp.content or ""

    async def _execute_tools(self, tool_calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """执行工具调用，返回 [{id,name,result}] 列表。"""
        results: list[dict[str, Any]] = []
        for tc in tool_calls:
            name = tc.get("name")
            args_str = tc.get("arguments", "")
            tool_id = tc.get("id") or ""
            try:
                import json as _json

                args = _json.loads(args_str) if isinstance(args_str, str) and args_str else {}
            except Exception:
                args = {}
            # 工具集（真实接入 + 兜底）
            if name in {"kb_search", "get_kb_context"}:
                from src.services.kb.service import KnowledgeBaseService

                keyword = args.get("keyword") or args.get("topic") or ""
                limit = int(args.get("limit", 3))
                obj = await KnowledgeBaseService.search_worldview(str(keyword), limit)
                import json as _json2

                result = _json2.dumps(obj, ensure_ascii=False)
            elif name in {"get_character_profile", "character_profile"}:
                from src.services.kb.service import KnowledgeBaseService

                char_id = args.get("id") or args.get("character_id")
                char_name = args.get("name")
                obj = await KnowledgeBaseService.get_character_profile(
                    name=str(char_name) if char_name else None, character_id=str(char_id) if char_id else None
                )
                import json as _json2

                result = _json2.dumps(obj, ensure_ascii=False)
            elif name in {"get_glossary", "glossary"}:
                from src.services.kb.service import KnowledgeBaseService

                keyword = args.get("keyword") or args.get("term") or ""
                limit = int(args.get("limit", 5))
                obj = await KnowledgeBaseService.get_glossary(str(keyword), limit)
                import json as _json2

                result = _json2.dumps(obj, ensure_ascii=False)
            elif name == "outline_expand":
                outline = args.get("outline", "")
                style = args.get("style", "文风")
                import json as _json2

                result = _json2.dumps(
                    {"outline_expanded": f"扩展大纲（{style}）：{outline[:50]}..."}, ensure_ascii=False
                )
            else:
                import json as _json2

                result = _json2.dumps({"error": f"unknown tool {name}", "args": args}, ensure_ascii=False)
            results.append({"id": tool_id, "name": name, "result": result})
        return results
