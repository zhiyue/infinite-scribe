"""KnowledgeUpdateAgent

消费内容分析结果，将结构化事实更新至：
- Neo4j（知识图谱）
- 向量库（Milvus）
- 关系型数据库（占位，后续可扩展为具体表的幂等 UPSERT）

注意：全部为尽力而为（best-effort），任一子更新失败不影响其他子任务执行。
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any

from src.agents.agent_config import get_agent_topics
from src.agents.base import BaseAgent
from src.common.services.knowledge_graph.knowledge_graph_service import KnowledgeGraphService
from src.db.vector.milvus import MilvusEmbeddingManager, MilvusSchemaManager
from src.external.clients import get_embedding_service
from src.services.outbox.egress import OutboxEgress


class KnowledgeUpdateAgent(BaseAgent):
    """将分析结果投影到各类存储的 Agent。"""

    def __init__(
        self,
        name: str | None = None,
        consume_topics: list[str] | None = None,
        produce_topics: list[str] | None = None,
    ) -> None:
        if consume_topics is None or produce_topics is None or name is None:
            c, p = get_agent_topics("knowledge_updater")
            super().__init__(name or "knowledge_updater", c, p)
        else:
            super().__init__(name, consume_topics, produce_topics)

        self.kg = KnowledgeGraphService()
        self._embed_provider = get_embedding_service()
        self._milvus_schema = MilvusSchemaManager()
        self._milvus = MilvusEmbeddingManager(self._milvus_schema)
        self.egress = OutboxEgress()

    async def process_message(
        self, message: dict[str, Any], context: dict[str, Any] | None = None
    ) -> dict[str, Any] | None:
        if message.get("type") != "content_analyzed":
            return None

        analysis: dict[str, Any] = message.get("analysis") or {}
        chapter_id = message.get("chapter_id") or message.get("scene_id")
        novel_id = analysis.get("novel_id") or message.get("novel_id")

        # 并行更新：图谱 / 向量 / SQL
        await asyncio.gather(
            self._update_knowledge_graph(novel_id, chapter_id, analysis),
            self._update_vector_store(novel_id, chapter_id, analysis),
            self._update_sql_database(novel_id, chapter_id, analysis),
        )

        corr_id = (context or {}).get("meta", {}).get("correlation_id") if context else None
        await self.egress.enqueue_envelope(
            agent=self.name,
            topic="genesis.knowledge.events",
            key=(str(chapter_id) if chapter_id is not None else None),
            result={
                "type": "knowledge_updated",
                "chapter_id": chapter_id,
                "novel_id": novel_id,
                "update_timestamp": datetime.now(UTC).isoformat(),
            },
            correlation_id=corr_id,
        )
        return None

    async def _update_knowledge_graph(self, novel_id: str | None, chapter_id: Any, analysis: dict[str, Any]) -> None:
        # 需要 novel_id 的操作：若缺失则跳过图谱投影
        if not novel_id:
            return

        # 人物关系
        for rel in analysis.get("character_relationships") or []:
            try:
                await self.kg.relate_characters(
                    from_app_id=str(rel.get("from_character")),
                    to_app_id=str(rel.get("to_character")),
                    type=str(rel.get("relationship_type")),
                    strength=(rel.get("strength") if isinstance(rel.get("strength"), (int, float)) else None),
                    since_chapter=int(chapter_id) if isinstance(chapter_id, int) else None,
                )
            except Exception as e:
                self.log.warning("kg_relate_characters_failed", error=str(e))

        # 世界观规则
        for rule in analysis.get("world_building") or []:
            try:
                await self.kg.create_world_rule_node(
                    rule_id=str(rule.get("rule_id") or f"rule-{chapter_id}-{hash(str(rule))}"),
                    novel_id=str(novel_id),
                    dimension=str(rule.get("dimension") or "misc"),
                    rule=str(rule.get("description") or ""),
                )
            except Exception as e:
                self.log.warning("kg_world_rule_failed", error=str(e))

        # 地点信息
        for loc in analysis.get("location_details") or []:
            try:
                name = str(loc.get("name") or "")
                await self.kg.create_location_node(
                    location_id=str(loc.get("location_id") or f"loc-{chapter_id}-{hash(name)}"),
                    novel_id=str(novel_id),
                    name=name or "Unknown",
                    x=int(loc.get("x") or 0),
                    y=int(loc.get("y") or 0),
                )
            except Exception as e:
                self.log.warning("kg_location_failed", error=str(e))

    async def _update_vector_store(self, novel_id: str | None, chapter_id: Any, analysis: dict[str, Any]) -> None:
        # 尝试生成一个简要索引摘要并写入 Milvus
        try:
            # 生成摘要文本（不依赖 novel_id）
            summary_lines: list[str] = []
            cr = analysis.get("character_relationships") or []
            if cr:
                summary_lines.append(f"relationships:{len(cr)}")
            wb = analysis.get("world_building") or []
            if wb:
                summary_lines.append(f"world_rules:{len(wb)}")
            pd = analysis.get("plot_developments") or []
            if pd:
                summary_lines.append(f"plot:{len(pd)}")
            text = " | ".join(summary_lines) or "analysis summary"

            vec = await self._embed_provider.get_embedding(text)
            meta: dict[str, Any] = {"source": "content_analyzer", "kind": "analysis_summary"}

            await self._milvus.insert_novel_embedding(
                novel_id=str(novel_id or "unknown"),
                chunk_id=str(chapter_id or "unknown"),
                content_type="analysis_summary",
                content=text,
                embedding=vec,
                metadata=meta,
            )
        except Exception as e:
            self.log.warning("vector_update_failed", error=str(e))

    async def _update_sql_database(self, novel_id: str | None, chapter_id: Any, analysis: dict[str, Any]) -> None:
        # 预留：可在此将关键事实落库（characters/worldview_entries 等）。
        # 为避免引入未对齐的数据模型，此处仅记录日志，后续可接入仓储模式的幂等 UPSERT。
        try:
            has_rel = bool(analysis.get("character_relationships"))
            has_wb = bool(analysis.get("world_building"))
            has_loc = bool(analysis.get("location_details"))
            self.log.info(
                "sql_update_summary",
                novel_id=novel_id,
                chapter_id=chapter_id,
                relationships=has_rel,
                world_rules=has_wb,
                locations=has_loc,
            )
        except Exception:
            # no-op
            pass
