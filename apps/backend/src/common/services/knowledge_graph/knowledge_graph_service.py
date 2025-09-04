from __future__ import annotations

from neo4j import AsyncDriver, AsyncSession

from src.common.services.neo4j_service import Neo4jService
from src.db.graph.schema import Neo4jSchemaManager, Neo4jNodeCreator, Neo4jRelationshipManager

from .graph_query_builder import GraphQueryBuilder
from .consistency_validator import ConsistencyValidator, ConsistencyReport


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
        self._schema_manager: Neo4jSchemaManager | None = None
        self._node_creator: Neo4jNodeCreator | None = None
        self._relationship_manager: Neo4jRelationshipManager | None = None
        self._consistency_validator: ConsistencyValidator | None = None

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
        type: str,
        strength: float | None = None,
        since_chapter: int | None = None,
    ) -> None:
        query = """
        MATCH (a:Character {app_id: $from}), (b:Character {app_id: $to})
        MERGE (a)-[r:RELATES_TO {type: $type}]->(b)
        ON CREATE SET r.strength = $strength, r.since_chapter = $since
        ON MATCH SET r.strength = coalesce($strength, r.strength), r.since_chapter = coalesce($since, r.since_chapter)
        """
        await self._neo4j.execute(
            query,
            {"from": from_app_id, "to": to_app_id, "type": type, "strength": strength, "since": since_chapter},
        )

    # New methods for enhanced schema management and consistency validation

    async def _get_session(self) -> AsyncSession:
        """Get a Neo4j session for advanced operations.""" 
        if not self._driver:
            await self.connect()
        if not self._driver:
            raise RuntimeError("Neo4j driver not available")
        return self._driver.session()

    async def initialize_genesis_schema(self) -> bool:
        """Initialize the complete Neo4j schema for novel genesis system."""
        try:
            async with self._get_session() as session:
                schema_manager = Neo4jSchemaManager(session)
                await schema_manager.initialize_schema()
                return await schema_manager.verify_schema()
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Failed to initialize genesis schema: {e}")
            return False

    async def create_novel_node(self, novel_id: str, title: str = "", **properties) -> bool:
        """Create a Novel node with genesis system constraints."""
        try:
            async with self._get_session() as session:
                node_creator = Neo4jNodeCreator(session)
                result = await node_creator.create_novel_node(
                    novel_id=novel_id, 
                    title=title,
                    **properties
                )
                return bool(result)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Failed to create novel node: {e}")
            return False

    async def create_character_node(self, character_id: str, novel_id: str, name: str, 
                                   appearance: str = "", personality: str = "", background: str = "",
                                   motivation: str = "", goals: str = "", obstacles: str = "",
                                   arc: str = "", wounds: str = "", **properties) -> bool:
        """Create a Character node with 8-dimensional design."""
        try:
            async with self._get_session() as session:
                node_creator = Neo4jNodeCreator(session)
                result = await node_creator.create_character_node(
                    character_id=character_id,
                    novel_id=novel_id,
                    name=name,
                    appearance=appearance,
                    personality=personality,
                    background=background,
                    motivation=motivation,
                    goals=goals,
                    obstacles=obstacles,
                    arc=arc,
                    wounds=wounds,
                    **properties
                )
                return bool(result)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Failed to create character node: {e}")
            return False

    async def create_world_rule_node(self, rule_id: str, novel_id: str, dimension: str,
                                   rule: str, priority: int = 0, scope: dict = None,
                                   examples: list = None, constraints: list = None, **properties) -> bool:
        """Create a WorldRule node for consistency checking."""
        try:
            async with self._get_session() as session:
                node_creator = Neo4jNodeCreator(session)
                result = await node_creator.create_world_rule_node(
                    rule_id=rule_id,
                    novel_id=novel_id,
                    dimension=dimension,
                    rule=rule,
                    priority=priority,
                    scope=scope or {},
                    examples=examples or [],
                    constraints=constraints or [],
                    **properties
                )
                return bool(result)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Failed to create world rule node: {e}")
            return False

    async def create_location_node(self, location_id: str, novel_id: str, name: str,
                                 x: float = 0.0, y: float = 0.0, **properties) -> bool:
        """Create a Location node with coordinates for spatial consistency."""
        try:
            async with self._get_session() as session:
                node_creator = Neo4jNodeCreator(session)
                result = await node_creator.create_location_node(
                    location_id=location_id,
                    novel_id=novel_id,
                    name=name,
                    x=x,
                    y=y,
                    **properties
                )
                return bool(result)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Failed to create location node: {e}")
            return False

    async def create_character_relationship(self, character1_id: str, character2_id: str,
                                          strength: int, rel_type: str, symmetric: bool = True) -> bool:
        """Create RELATES_TO relationship between characters."""
        try:
            async with self._get_session() as session:
                relationship_manager = Neo4jRelationshipManager(session)
                return await relationship_manager.create_character_relationship(
                    character1_id=character1_id,
                    character2_id=character2_id,
                    strength=strength,
                    rel_type=rel_type,
                    symmetric=symmetric
                )
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Failed to create character relationship: {e}")
            return False

    async def create_world_rule_conflict(self, rule1_id: str, rule2_id: str, severity: str = "major") -> bool:
        """Create CONFLICTS_WITH relationship between world rules."""
        try:
            async with self._get_session() as session:
                relationship_manager = Neo4jRelationshipManager(session)
                return await relationship_manager.create_world_rule_conflict(
                    rule1_id=rule1_id,
                    rule2_id=rule2_id,
                    severity=severity
                )
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Failed to create world rule conflict: {e}")
            return False

    async def validate_consistency(self, novel_id: str) -> ConsistencyReport:
        """Run comprehensive consistency validation for a novel."""
        try:
            async with self._get_session() as session:
                validator = ConsistencyValidator(session)
                return await validator.validate_all(novel_id)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Consistency validation failed: {e}")
            from .consistency_validator import ConsistencyReport, ConsistencyViolation, ViolationSeverity
            # Return error report
            return ConsistencyReport(
                violations=[ConsistencyViolation(
                    rule_type="system_error",
                    severity=ViolationSeverity.ERROR,
                    message=f"Consistency validation failed: {str(e)}",
                    affected_entities=[novel_id]
                )],
                score=0.0,
                total_checks=0,
                passed_checks=0
            )
