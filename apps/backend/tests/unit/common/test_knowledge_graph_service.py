from unittest.mock import AsyncMock

import pytest
from src.common.services.knowledge_graph.knowledge_graph_service import (
    KnowledgeGraphService,
)
from src.common.services.neo4j_service import Neo4jService


@pytest.mark.asyncio
async def test_knowledge_graph_service_bootstrap(monkeypatch):
    svc = Neo4jService()

    # stub out execute to avoid real DB
    async def fake_execute(query: str, parameters: dict | None = None):
        return []

    monkeypatch.setattr(svc, "execute", fake_execute)

    # prevent real connect/disconnect
    async def fake_connect():
        svc._driver = AsyncMock()  # type: ignore[attr-defined]

    async def fake_disconnect():
        svc._driver = None  # type: ignore[attr-defined]

    monkeypatch.setattr(svc, "connect", fake_connect)
    monkeypatch.setattr(svc, "disconnect", fake_disconnect)

    kg = KnowledgeGraphService(svc)
    await kg.connect()
    await kg.ensure_constraints()  # should not raise
    await kg.upsert_novel(novel_id="novel-1", title="Test Novel")
    await kg.upsert_character(novel_id="novel-1", app_id="char-1", name="Hero", role="PROTAGONIST")
    await kg.relate_characters(from_app_id="char-1", to_app_id="char-1", kind="FRIEND", strength=1.0)
    await kg.disconnect()
