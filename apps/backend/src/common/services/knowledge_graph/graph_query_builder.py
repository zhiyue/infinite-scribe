from __future__ import annotations

from typing import Any

from neo4j import AsyncDriver


class GraphQueryBuilder:
    """Reusable Neo4j query helpers aligned with our schema.

    All queries are novel-scoped and assume Neo4j 5.x.
    """

    def __init__(self, driver: AsyncDriver):
        self.driver = driver

    async def get_character_network(
        self, *, novel_id: str, character_app_id: str, depth: int = 2
    ) -> dict[str, Any] | None:
        query = """
        MATCH (n:Novel {novel_id: $novel_id})
        MATCH (c:Character {app_id: $char_id})-[:APPEARS_IN_NOVEL]->(n)
        CALL apoc.path.subgraphAll(c, {
          relationshipFilter: 'RELATES_TO>',
          maxLevel: $depth,
          bfs: true
        })
        YIELD nodes, relationships
        RETURN nodes, relationships
        """
        async with self.driver.session() as session:
            result = await session.run(query, novel_id=novel_id, char_id=character_app_id, depth=depth)
            return await result.single()

    async def check_timeline_consistency(self, *, novel_id: str) -> list[dict[str, Any]]:
        query = """
        MATCH (n:Novel {novel_id: $novel_id})
        MATCH (e1:Event)-[:HAPPENS_IN]->(:Scene)-[:SCENE_IN]->(:Chapter)-[:BELONGS_TO_NOVEL]->(n)
        MATCH (e1)-[:TRIGGERS]->(e2:Event)
        WHERE e1.timestamp > e2.timestamp
        RETURN e1, e2, 'Timeline violation: cause after effect' AS error
        """
        async with self.driver.session() as session:
            result = await session.run(query, novel_id=novel_id)
            return [record.data() async for record in result]

    async def find_plot_holes(self, *, novel_id: str) -> list[dict[str, Any]]:
        query = """
        // unresolved foreshadowing
        MATCH (n:Novel {novel_id: $novel_id})
        MATCH (setup:Event {type: 'foreshadowing'})-[:HAPPENS_IN]->(:Scene)-[:SCENE_IN]->(:Chapter)-[:BELONGS_TO_NOVEL]->(n)
        WHERE NOT EXISTS { MATCH (setup)-[:RESOLVED_BY]->(:Event) }
        RETURN setup.app_id AS unresolved_foreshadowing, setup.description

        UNION

        // isolated characters
        MATCH (n:Novel {novel_id: $novel_id})
        MATCH (c:Character)-[:APPEARS_IN_NOVEL]->(n)
        WHERE NOT EXISTS { MATCH (c)-[:RELATES_TO]-() }
        RETURN c.app_id AS isolated_character, c.name
        """
        async with self.driver.session() as session:
            result = await session.run(query, novel_id=novel_id)
            return [record.data() async for record in result]

    async def get_world_rules_for_location(self, *, location_app_id: str) -> list[dict[str, Any]]:
        query = """
        MATCH (l:Location {app_id: $loc_id})
        MATCH (l)-[:LOCATED_IN*0..4]->(parent:Location)
        MATCH (rule:WorldRule)-[:APPLIES_TO]->(parent)
        RETURN DISTINCT rule
        ORDER BY rule.level
        """
        async with self.driver.session() as session:
            result = await session.run(query, loc_id=location_app_id)
            return [record["rule"] async for record in result]

    async def analyze_character_arc(self, *, character_app_id: str) -> dict[str, Any] | None:
        query = """
        MATCH (c:Character {app_id: $char_id})
        MATCH (c)-[:PARTICIPATES_IN]->(scene:Scene)-[:SCENE_IN]->(chapter:Chapter)
        WITH c, scene, chapter
        ORDER BY chapter.number
        MATCH (c)-[r:HAS_STATE]->(state:CharacterState)
        WHERE state.chapter = chapter.number
        RETURN c.name AS character,
               collect({
                   chapter: chapter.number,
                   emotional_state: state.emotional,
                   relationships: state.relationships,
                   goals: state.goals
               }) AS arc_progression
        """
        async with self.driver.session() as session:
            result = await session.run(query, char_id=character_app_id)
            return await result.single()
