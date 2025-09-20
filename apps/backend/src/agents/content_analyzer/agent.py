"""ContentAnalyzerAgent

使用 LLM 对生成内容进行结构化分析与信息抽取。

职责：
- 消费 WriterAgent 输出的内容事件（genesis.writer.events）
- 通过 LLM 对章节/场景内容进行多维度分析（人物、世界观、情节、伏笔等）
- 产出标准化分析结果事件到 genesis.analyzer.events
"""

from __future__ import annotations

from external.clients.llm.types import LLMResponse
import json
from typing import Any

from src.agents.agent_config import get_agent_topics
from src.agents.base import BaseAgent
from src.external.clients.llm import ChatMessage, LLMRequest
from src.services.llm import LLMService, LLMServiceFactory
from src.services.outbox.egress import OutboxEgress


class ContentAnalyzerAgent(BaseAgent):
    """内容分析 Agent（LLM 驱动）。"""

    def __init__(
        self,
        name: str | None = None,
        consume_topics: list[str] | None = None,
        produce_topics: list[str] | None = None,
        *,
        llm_service: LLMService | None = None,
        egress: OutboxEgress | None = None,
    ) -> None:
        # 允许从注册表传参，亦允许自决获取主题
        if consume_topics is None or produce_topics is None or name is None:
            c, p = get_agent_topics("content_analyzer")
            super().__init__(name or "content_analyzer", c, p)
        else:
            super().__init__(name, consume_topics, produce_topics)
        self.llm = llm_service or LLMServiceFactory().create_service()
        self.egress = egress or OutboxEgress()

    async def process_message(
        self, message: dict[str, Any], context: dict[str, Any] | None = None
    ) -> dict[str, Any] | None:
        msg_type = message.get("type")
        if msg_type == "chapter_written":
            return await self._analyze_chapter(message)
        if msg_type == "scene_written":
            return await self._analyze_scene(message)
        # 其他 Writer 能力事件暂不处理
        return None

    async def _analyze_chapter(self, message: dict[str, Any], context: dict[str, Any] | None = None) -> dict[str, Any] | None:
        chapter_id = message.get("chapter_id")
        content = message.get("content") or ""

        prompt = self._build_analysis_prompt(content)
        analysis = await self._call_llm(prompt)

        corr_id = (context or {}).get("meta", {}).get("correlation_id") if context else None
        await self.egress.enqueue_envelope(
            agent=self.name,
            topic="genesis.analyzer.events",
            key=(str(chapter_id) if chapter_id is not None else None),
            result={
                "type": "content_analyzed",
                "scope": "chapter",
                "chapter_id": chapter_id,
                "analysis": analysis,
            },
            correlation_id=corr_id,
        )
        return None

    async def _analyze_scene(self, message: dict[str, Any], context: dict[str, Any] | None = None) -> dict[str, Any] | None:
        scene_id = message.get("scene_id")
        content = message.get("content") or ""

        prompt = self._build_analysis_prompt(content)
        analysis = await self._call_llm(prompt)

        corr_id = (context or {}).get("meta", {}).get("correlation_id") if context else None
        await self.egress.enqueue_envelope(
            agent=self.name,
            topic="genesis.analyzer.events",
            key=(str(scene_id) if scene_id is not None else None),
            result={
                "type": "content_analyzed",
                "scope": "scene",
                "scene_id": scene_id,
                "analysis": analysis,
            },
            correlation_id=corr_id,
        )
        return None

    def _build_analysis_prompt(self, content: str) -> list[ChatMessage]:
        system = ChatMessage(
            role="system",
            content=(
                "You are a senior story analyst. Extract key structured facts in strict JSON. "
                "Use concise fields and stable identifiers when possible."
            ),
        )
        user = ChatMessage(
            role="user",
            content={
                "task": "analyze_story_content",
                "content": content,
                "analysis_types": [
                    "character_relationships",
                    "plot_developments",
                    "foreshadowing",
                    "world_building",
                    "location_details",
                    "timeline_events",
                    "character_development",
                    "conflicts_tensions",
                ],
                # 返回严格 JSON，样例 schema（宽松，可缺省任一字段）
                "output_schema": {
                    "character_relationships": [
                        {"from_character": "str", "to_character": "str", "relationship_type": "str", "strength": 0}
                    ],
                    "world_building": [{"rule_id": "str", "dimension": "str", "description": "str"}],
                    "location_details": [{"location_id": "str", "name": "str", "x": 0, "y": 0}],
                    "timeline_events": [{"ts": "str", "summary": "str"}],
                    "foreshadowing": [{"id": "str", "hint": "str", "payoff_window": "str"}],
                    "character_development": [{"character": "str", "arc": "str", "stage": "str"}],
                    "plot_developments": [{"summary": "str", "impact": "str"}],
                    "conflicts_tensions": [{"parties": ["str"], "type": "str", "level": 0}],
                },
            },
        )
        return [system, user]

    async def _call_llm(self, messages: list[ChatMessage]) -> dict[str, Any]:
        req = LLMRequest(model=self.config.llm.default_model or "gpt-4o-mini", messages=messages)
        try:
            resp: LLMResponse = await self.llm.generate(req)
            raw = resp.content or "{}"
            # 宽松解析：优先 JSON，失败则返回包装的原文
            try:
                return json.loads(raw)
            except Exception:
                return {"raw": raw}
        except Exception as e:  # 最小失败兜底：不阻塞主流程
            self.log.warning("analysis_llm_failed", error=str(e))
            return {}
