from __future__ import annotations

from neo4j import AsyncDriver

from src.common.services.neo4j_service import Neo4jService

from .graph_query_builder import GraphQueryBuilder


class KnowledgeGraphService:
    """High-level operations against the story knowledge graph.

    - Uses Neo4j 5.x driver via Neo4jService
    - Provides simple helpers to bootstrap schema constraints and create basic nodes/relations
    - All operations are intended to be novel-scoped
    """

    def __init__(self, neo4j: Neo4jService) -> None:
        self._neo4j = neo4j
        self._driver: AsyncDriver | None = None
        self.queries: GraphQueryBuilder | None = None

    async def connect(self) -> None:
        if self._driver is None:
            await self._neo4j.connect()
            # access underlying driver from service (protected member not exposed; we can execute via execute)
            # to keep a consistent pattern, create a temporary driver via neo4j settings when needed
            # here we leverage the service's execute method instead of raw driver when possible
            # for query builder, we need the driver; reuse the service's private driver by attribute if present
            self._driver = self._neo4j._driver  # type: ignore[attr-defined]
            if self._driver is None:
                raise RuntimeError("Neo4j driver not available after connect()")
            self.queries = GraphQueryBuilder(self._driver)

    async def disconnect(self) -> None:
        await self._neo4j.disconnect()
        self._driver = None
        self.queries = None

    async def ensure_constraints(self) -> None:
        """Create required constraints and indexes (idempotent)."""
        statements = [
            # unique constraints
            "CREATE CONSTRAINT unique_novel_id IF NOT EXISTS FOR (n:Novel) REQUIRE n.novel_id IS UNIQUE",
            "CREATE CONSTRAINT unique_character_app_id IF NOT EXISTS FOR (c:Character) REQUIRE c.app_id IS UNIQUE",
            "CREATE CONSTRAINT unique_chapter_app_id IF NOT EXISTS FOR (c:Chapter) REQUIRE c.app_id IS UNIQUE",
            "CREATE CONSTRAINT unique_worldview_app_id IF NOT EXISTS FOR (w:WorldviewEntry) REQUIRE w.app_id IS UNIQUE",
            # scope indexes
            "CREATE INDEX character_novel_id IF NOT EXISTS FOR (c:Character) ON (c.novel_id)",
            "CREATE INDEX chapter_novel_id IF NOT EXISTS FOR (c:Chapter) ON (c.novel_id)",
            "CREATE INDEX worldview_novel_id IF NOT EXISTS FOR (w:WorldviewEntry) ON (w.novel_id)",
            # convenience indexes
            "CREATE INDEX character_name IF NOT EXISTS FOR (c:Character) ON (c.name)",
        ]
        for stmt in statements:
            await self._neo4j.execute(stmt)

    async def upsert_novel(self, *, novel_id: str, title: str | None = None) -> None:
        query = """
        MERGE (n:Novel {novel_id: $novel_id})
        ON CREATE SET n.title = coalesce($title, n.title)
        ON MATCH SET n.title = coalesce($title, n.title)
        """
        await self._neo4j.execute(query, {"novel_id": novel_id, "title": title})

    async def upsert_character(self, *, novel_id: str, app_id: str, name: str, role: str | None = None) -> None:
        query = """
        MATCH (n:Novel {novel_id: $novel_id})
        MERGE (c:Character {app_id: $app_id})-[:APPEARS_IN_NOVEL]->(n)
        ON CREATE SET c.novel_id = $novel_id, c.name = $name, c.role = $role
        ON MATCH SET c.name = coalesce($name, c.name), c.role = coalesce($role, c.role)
        """
        await self._neo4j.execute(query, {"novel_id": novel_id, "app_id": app_id, "name": name, "role": role})

    async def relate_characters(
        self,
        *,
        from_app_id: str,
        to_app_id: str,
        kind: str,
        strength: float | None = None,
        since_chapter: int | None = None,
    ) -> None:
        query = """
        MATCH (a:Character {app_id: $from}), (b:Character {app_id: $to})
        MERGE (a)-[r:RELATES_TO {kind: $kind}]->(b)
        ON CREATE SET r.strength = $strength, r.since_chapter = $since
        ON MATCH SET r.strength = coalesce($strength, r.strength), r.since_chapter = coalesce($since, r.since_chapter)
        """
        await self._neo4j.execute(
            query,
            {"from": from_app_id, "to": to_app_id, "kind": kind, "strength": strength, "since": since_chapter},
        )
