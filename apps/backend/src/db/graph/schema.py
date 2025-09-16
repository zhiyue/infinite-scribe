"""
Neo4j Graph Schema Management

Manages Neo4j database schema creation, constraints, and indexes
for the novel genesis system according to ADR-005.
"""

import logging
from typing import Any, LiteralString, TypedDict, cast

from neo4j import AsyncSession

logger = logging.getLogger(__name__)

# Schema definitions as data structures for maintainability
SCHEMA_CONFIG: dict[str, dict[str, Any]] = {
    "constraints": {
        "unique_novel_novel_id": ("Novel", "novel_id"),
        "unique_character_id": ("Character", "id"),
        "unique_world_rule_id": ("WorldRule", "id"),
        "unique_event_id": ("Event", "id"),
        "unique_location_id": ("Location", "id"),
        "unique_transportation_id": ("Transportation", "id"),
        "unique_character_state_id": ("CharacterState", "id"),
    },
    "indexes": {
        "novel_app_id_index": ("Novel", ["app_id"]),
        "character_novel_index": ("Character", ["novel_id"]),
        "worldrule_novel_index": ("WorldRule", ["novel_id"]),
        "event_novel_index": ("Event", ["novel_id"]),
        "location_novel_index": ("Location", ["novel_id"]),
        "event_timestamp_index": ("Event", ["timestamp"]),
        "character_state_chapter_index": ("CharacterState", ["chapter"]),
        "location_coords_index": ("Location", ["x", "y"]),
    },
}


class Neo4jSchemaManager:
    """Manages Neo4j schema creation and validation."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def _execute_schema_item(self, item_type: str, name: str, query: str) -> None:
        """Execute a single schema item with consistent error handling."""
        try:
            await self.session.run(cast(LiteralString, query))  # type: ignore[redundant-cast]
            logger.info(f"Created {item_type}: {name}")
        except Exception as e:
            logger.warning(f"{item_type.capitalize()} creation failed or already exists: {e}")

    async def create_constraints(self) -> None:
        """Create all required constraints for the novel genesis system."""
        for name, (label, property_name) in SCHEMA_CONFIG["constraints"].items():
            variable = label.lower()[0]
            query = f"CREATE CONSTRAINT {name} IF NOT EXISTS FOR ({variable}:{label}) REQUIRE {variable}.{property_name} IS UNIQUE"
            await self._execute_schema_item("constraint", name, query)

    async def create_indexes(self) -> None:
        """Create performance optimization indexes."""
        for name, (label, properties) in SCHEMA_CONFIG["indexes"].items():
            variable = label.lower()[0]
            props_str = ", ".join(f"{variable}.{prop}" for prop in properties)
            query = f"CREATE INDEX {name} IF NOT EXISTS FOR ({variable}:{label}) ON ({props_str})"
            await self._execute_schema_item("index", name, query)

    async def initialize_schema(self) -> None:
        """Initialize the complete Neo4j schema."""
        logger.info("Initializing Neo4j schema for novel genesis system...")
        await self.create_constraints()
        await self.create_indexes()
        logger.info("Neo4j schema initialization completed")

    async def verify_schema(self) -> bool:
        """Verify all required constraints and indexes exist."""
        try:
            return await self._verify_constraints() and await self._verify_indexes()
        except Exception as e:
            logger.error(f"Schema verification failed: {e}")
            return False

    async def _verify_constraints(self) -> bool:
        """Verify all required constraints exist."""
        result = await self.session.run("SHOW CONSTRAINTS")
        constraints = await result.data()

        required_constraints = set(SCHEMA_CONFIG["constraints"].keys())
        existing_constraints = {c.get("name", "") for c in constraints}
        missing_constraints = required_constraints - existing_constraints

        if missing_constraints:
            logger.warning(f"Missing constraints: {missing_constraints}")
            return False
        return True

    async def _verify_indexes(self) -> bool:
        """Verify all required indexes exist."""
        result = await self.session.run("SHOW INDEXES")
        indexes = await result.data()

        required_indexes = set(SCHEMA_CONFIG["indexes"].keys())
        existing_indexes = {i.get("name", "") for i in indexes}
        missing_indexes = required_indexes - existing_indexes

        if missing_indexes:
            logger.warning(f"Missing indexes: {missing_indexes}")
            return False
        return True


# Node templates define structure for each node type
class NodeTemplate(TypedDict):
    variable: str
    merge_field: str
    base_fields: dict[str, Any]
    relationship: tuple[str, str, str] | None


NODE_TEMPLATES: dict[str, NodeTemplate] = {
    "Novel": {
        "variable": "n",
        "merge_field": "novel_id",
        "base_fields": {"app_id": "infinite-scribe", "created_at": "datetime()"},
        "relationship": None,
    },
    "Character": {
        "variable": "c",
        "merge_field": "id",
        "base_fields": {
            "novel_id": None,
            "name": "",
            "appearance": "",
            "personality": "",
            "background": "",
            "motivation": "",
            "goals": "",
            "obstacles": "",
            "arc": "",
            "wounds": "",
        },
        "relationship": ("BELONGS_TO", "Novel", "novel_id"),
    },
    "WorldRule": {
        "variable": "w",
        "merge_field": "id",
        "base_fields": {
            "novel_id": None,
            "dimension": "",
            "rule": "",
            "priority": 0,
            "scope": None,
            "examples": None,
            "constraints": None,
            "created_at": "datetime()",
        },
        "relationship": ("GOVERNS", "Novel", "novel_id"),
    },
    "Location": {
        "variable": "l",
        "merge_field": "id",
        "base_fields": {
            "novel_id": None,
            "name": "",
            "x": 0.0,
            "y": 0.0,
            "timestamp": "datetime()",
        },
        "relationship": None,
    },
}


class Neo4jNodeCreator:
    """Helper class to create and manage Neo4j nodes."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def _create_node(self, node_type: str, merge_value: str, **properties) -> dict[str, Any]:
        """Generic node creation method that eliminates duplication."""
        template = NODE_TEMPLATES[node_type]
        var = template["variable"]
        merge_field = template["merge_field"]

        # Build parameters from template defaults and provided values
        params: dict[str, Any] = {f"{var}_{merge_field}": merge_value}
        for field, default_value in template["base_fields"].items():
            if field in properties:
                params[field] = properties[field]
            elif default_value is not None:
                params[field] = default_value

        # Add any extra properties
        extra_props = {k: v for k, v in properties.items() if k not in template["base_fields"]}
        if extra_props:
            params["extra_properties"] = extra_props

        # Build query
        query_parts = [f"MERGE ({var}:{node_type} {{{merge_field}: ${var}_{merge_field}}})", "SET"]

        # Set base fields
        set_clauses = []
        for field in template["base_fields"]:
            if field in params:
                if params[field] == "datetime()":
                    set_clauses.append(f"{var}.{field} = datetime()")
                else:
                    set_clauses.append(f"{var}.{field} = ${field}")

        # Add extra properties if present
        if extra_props:
            set_clauses.append(f"{var} += $extra_properties")

        query_parts.append(", ".join(set_clauses))

        # Add relationship if defined
        if template["relationship"]:
            rel_type, target_type, target_field = template["relationship"]
            query_parts.extend(
                [
                    f"WITH {var}",
                    f"MATCH (target:{target_type} {{{target_field}: ${target_field}}})",
                    f"MERGE ({var})-[:{rel_type}]->(target)",
                ]
            )

        query_parts.append(f"RETURN {var}")
        query = "\n".join(query_parts)

        result = await self.session.run(cast(LiteralString, query), params)  # type: ignore[redundant-cast]
        record = await result.single()
        return dict(record[var]) if record else {}

    async def create_novel_node(self, novel_id: str, app_id: str = "infinite-scribe", **properties) -> dict[str, Any]:
        """Create a Novel node."""
        return await self._create_node("Novel", novel_id, app_id=app_id, **properties)

    async def create_character_node(
        self,
        character_id: str,
        novel_id: str,
        name: str,
        appearance: str = "",
        personality: str = "",
        background: str = "",
        motivation: str = "",
        goals: str = "",
        obstacles: str = "",
        arc: str = "",
        wounds: str = "",
        **properties,
    ) -> dict[str, Any]:
        """Create a Character node with 8 dimensions."""
        return await self._create_node(
            "Character",
            character_id,
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
            **properties,
        )

    async def create_world_rule_node(
        self,
        rule_id: str,
        novel_id: str,
        dimension: str,
        rule: str,
        priority: int = 0,
        scope: dict | None = None,
        examples: list[str] | None = None,
        constraints: list[str] | None = None,
        **properties,
    ) -> dict[str, Any]:
        """Create a WorldRule node."""
        return await self._create_node(
            "WorldRule",
            rule_id,
            novel_id=novel_id,
            dimension=dimension,
            rule=rule,
            priority=priority,
            scope=scope,
            examples=examples,
            constraints=constraints,
            **properties,
        )

    async def create_location_node(
        self, location_id: str, novel_id: str, name: str, x: float = 0.0, y: float = 0.0, **properties
    ) -> dict[str, Any]:
        """Create a Location node with coordinates."""
        return await self._create_node("Location", location_id, novel_id=novel_id, name=name, x=x, y=y, **properties)


class Neo4jRelationshipManager:
    """Helper class to manage Neo4j relationships."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def _create_relationship(
        self,
        from_label: str,
        from_field: str,
        from_id: str,
        to_label: str,
        to_field: str,
        to_id: str,
        rel_type: str,
        properties: dict[str, Any],
        symmetric: bool = False,
    ) -> bool:
        """Generic relationship creation method."""
        # Build property setters
        prop_setters = [f"r.{key} = ${key}" for key in properties]
        set_clause = f"SET {', '.join(prop_setters)}" if prop_setters else ""

        query = f"""
        MATCH (from:{from_label} {{{from_field}: $from_id}}), (to:{to_label} {{{to_field}: $to_id}})
        MERGE (from)-[r:{rel_type}]->(to)
        {set_clause}
        """

        params = {"from_id": from_id, "to_id": to_id, **properties}
        await self.session.run(cast(LiteralString, query), params)  # type: ignore[redundant-cast]

        # Create reverse relationship if symmetric
        if symmetric:
            reverse_query = f"""
            MATCH (from:{from_label} {{{from_field}: $from_id}}), (to:{to_label} {{{to_field}: $to_id}})
            MERGE (to)-[r:{rel_type}]->(from)
            {set_clause}
            """
            await self.session.run(cast(LiteralString, reverse_query), params)  # type: ignore[redundant-cast]

        return True

    async def create_character_relationship(
        self, character1_id: str, character2_id: str, strength: int, rel_type: str, symmetric: bool = True
    ) -> bool:
        """Create RELATES_TO relationship between characters."""
        return await self._create_relationship(
            "Character",
            "id",
            character1_id,
            "Character",
            "id",
            character2_id,
            "RELATES_TO",
            {"strength": strength, "type": rel_type, "symmetric": symmetric},
            symmetric=symmetric,
        )

    async def create_world_rule_conflict(self, rule1_id: str, rule2_id: str, severity: str = "major") -> bool:
        """Create CONFLICTS_WITH relationship between world rules."""
        return await self._create_relationship(
            "WorldRule",
            "id",
            rule1_id,
            "WorldRule",
            "id",
            rule2_id,
            "CONFLICTS_WITH",
            {"severity": severity},
            symmetric=True,
        )


__all__ = ["Neo4jSchemaManager", "Neo4jNodeCreator", "Neo4jRelationshipManager"]
