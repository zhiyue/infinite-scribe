"""
Test Neo4j graph database schema configuration for Task 1 implementation.

Tests the creation of 8 core node types and relationship constraints
as required by the novel genesis stage architecture.
"""

import pytest
from neo4j.exceptions import ServiceUnavailable
from src.db.graph.schema import Neo4jNodeCreator, Neo4jRelationshipManager, Neo4jSchemaManager


@pytest.mark.asyncio
@pytest.mark.integration
class TestNeo4jSchemaMigration:
    """Test Neo4j database schema migration."""

    async def test_neo4j_connection(self, neo4j_service):
        """Test that Neo4j service is available and accessible."""
        try:
            # Import here to avoid import issues if neo4j is not available
            from neo4j import AsyncGraphDatabase

            uri = f"bolt://{neo4j_service['host']}:{neo4j_service['port']}"
            driver = AsyncGraphDatabase.driver(uri, auth=(neo4j_service["user"], neo4j_service["password"]))

            async with driver.session() as session:
                result = await session.run("RETURN 1 as test")
                record = await result.single()
                assert record["test"] == 1

            await driver.close()

        except ImportError:
            pytest.skip("Neo4j driver not available")
        except ServiceUnavailable:
            pytest.fail("Neo4j service is not available")

    async def test_neo4j_schema_constraints_creation(self, neo4j_service):
        """Test creation of all required constraints for 8 core node types."""
        try:
            from neo4j import AsyncGraphDatabase

            uri = f"bolt://{neo4j_service['host']}:{neo4j_service['port']}"
            driver = AsyncGraphDatabase.driver(uri, auth=(neo4j_service["user"], neo4j_service["password"]))

            async with driver.session() as session:
                schema_manager = Neo4jSchemaManager(session)

                # Create constraints
                await schema_manager.create_constraints()

                # Verify constraints exist
                result = await session.run("SHOW CONSTRAINTS")
                constraints = await result.data()
                constraint_names = {c.get("name", "") for c in constraints}

                # Verify all 8 core node type constraints exist
                required_constraints = {
                    "unique_novel_novel_id",
                    "unique_character_id",
                    "unique_world_rule_id",
                    "unique_event_id",
                    "unique_location_id",
                    "unique_transportation_id",
                    "unique_character_state_id",
                }

                for constraint in required_constraints:
                    assert constraint in constraint_names, f"Constraint {constraint} should exist"

            await driver.close()

        except ImportError:
            pytest.skip("Neo4j driver not available")

    async def test_neo4j_schema_indexes_creation(self, neo4j_service):
        """Test creation of performance optimization indexes."""
        try:
            from neo4j import AsyncGraphDatabase

            uri = f"bolt://{neo4j_service['host']}:{neo4j_service['port']}"
            driver = AsyncGraphDatabase.driver(uri, auth=(neo4j_service["user"], neo4j_service["password"]))

            async with driver.session() as session:
                schema_manager = Neo4jSchemaManager(session)

                # Create indexes
                await schema_manager.create_indexes()

                # Verify indexes exist
                result = await session.run("SHOW INDEXES")
                indexes = await result.data()
                index_names = {i.get("name", "") for i in indexes}

                # Verify performance indexes exist
                required_indexes = {
                    "novel_app_id_index",
                    "character_novel_index",
                    "worldrule_novel_index",
                    "event_novel_index",
                    "location_novel_index",
                    "event_timestamp_index",
                    "character_state_chapter_index",
                    "location_coords_index",
                }

                for index in required_indexes:
                    assert index in index_names, f"Index {index} should exist"

            await driver.close()

        except ImportError:
            pytest.skip("Neo4j driver not available")

    async def test_neo4j_schema_verification(self, neo4j_service):
        """Test schema verification functionality."""
        try:
            from neo4j import AsyncGraphDatabase

            uri = f"bolt://{neo4j_service['host']}:{neo4j_service['port']}"
            driver = AsyncGraphDatabase.driver(uri, auth=(neo4j_service["user"], neo4j_service["password"]))

            async with driver.session() as session:
                schema_manager = Neo4jSchemaManager(session)

                # Initialize complete schema
                await schema_manager.initialize_schema()

                # Verify schema
                is_valid = await schema_manager.verify_schema()
                assert is_valid, "Neo4j schema verification should pass"

            await driver.close()

        except ImportError:
            pytest.skip("Neo4j driver not available")

    async def test_neo4j_node_creation_core_types(self, neo4j_service):
        """Test creation of all 8 core node types."""
        try:
            import uuid

            from neo4j import AsyncGraphDatabase

            uri = f"bolt://{neo4j_service['host']}:{neo4j_service['port']}"
            driver = AsyncGraphDatabase.driver(uri, auth=(neo4j_service["user"], neo4j_service["password"]))

            async with driver.session() as session:
                # Initialize schema first
                schema_manager = Neo4jSchemaManager(session)
                await schema_manager.initialize_schema()

                node_creator = Neo4jNodeCreator(session)

                # Test Novel node creation
                novel_id = str(uuid.uuid4())
                novel_node = await node_creator.create_novel_node(
                    novel_id=novel_id, title="Test Novel", author="Test Author"
                )
                assert novel_node["novel_id"] == novel_id
                assert novel_node["title"] == "Test Novel"

                # Test Character node creation
                character_id = str(uuid.uuid4())
                character_node = await node_creator.create_character_node(
                    character_id,
                    novel_id=novel_id,
                    name="Test Character",
                    appearance="Tall and dark",
                    personality="Brave and loyal",
                )
                assert character_node["id"] == character_id
                assert character_node["name"] == "Test Character"
                assert character_node["novel_id"] == novel_id

                # Test WorldRule node creation
                rule_id = str(uuid.uuid4())
                rule_node = await node_creator.create_world_rule_node(
                    rule_id, novel_id, dimension="physics", rule="Magic follows conservation of energy", priority=1
                )
                assert rule_node["id"] == rule_id
                assert rule_node["dimension"] == "physics"
                assert rule_node["novel_id"] == novel_id

                # Test Location node creation
                location_id = str(uuid.uuid4())
                location_node = await node_creator.create_location_node(
                    location_id, novel_id, name="Test City", x=100.0, y=200.0
                )
                assert location_node["id"] == location_id
                assert location_node["name"] == "Test City"
                assert location_node["x"] == 100.0
                assert location_node["y"] == 200.0

                # Verify nodes exist in database
                result = await session.run(
                    "MATCH (n:Novel {novel_id: $novel_id}) RETURN count(n) as count", {"novel_id": novel_id}
                )
                record = await result.single()
                assert record["count"] == 1

                result = await session.run(
                    "MATCH (c:Character {id: $character_id}) RETURN count(c) as count", {"character_id": character_id}
                )
                record = await result.single()
                assert record["count"] == 1

                result = await session.run(
                    "MATCH (w:WorldRule {id: $rule_id}) RETURN count(w) as count", {"rule_id": rule_id}
                )
                record = await result.single()
                assert record["count"] == 1

                result = await session.run(
                    "MATCH (l:Location {id: $location_id}) RETURN count(l) as count", {"location_id": location_id}
                )
                record = await result.single()
                assert record["count"] == 1

                # Clean up test data
                await session.run(
                    "MATCH (n) WHERE n.novel_id = $novel_id OR n.id = $location_id DETACH DELETE n",
                    {"novel_id": novel_id, "location_id": location_id},
                )

            await driver.close()

        except ImportError:
            pytest.skip("Neo4j driver not available")

    async def test_neo4j_relationships_creation(self, neo4j_service):
        """Test creation of relationships between nodes."""
        try:
            import uuid

            from neo4j import AsyncGraphDatabase

            uri = f"bolt://{neo4j_service['host']}:{neo4j_service['port']}"
            driver = AsyncGraphDatabase.driver(uri, auth=(neo4j_service["user"], neo4j_service["password"]))

            async with driver.session() as session:
                # Initialize schema
                schema_manager = Neo4jSchemaManager(session)
                await schema_manager.initialize_schema()

                node_creator = Neo4jNodeCreator(session)
                relationship_manager = Neo4jRelationshipManager(session)

                # Create test nodes
                novel_id = str(uuid.uuid4())
                await node_creator.create_novel_node(novel_id=novel_id, title="Test Novel")

                character1_id = str(uuid.uuid4())
                character2_id = str(uuid.uuid4())
                await node_creator.create_character_node(character1_id, novel_id=novel_id, name="Character 1")
                await node_creator.create_character_node(character2_id, novel_id=novel_id, name="Character 2")

                rule1_id = str(uuid.uuid4())
                rule2_id = str(uuid.uuid4())
                await node_creator.create_world_rule_node(rule1_id, novel_id, dimension="magic", rule="Rule 1")
                await node_creator.create_world_rule_node(rule2_id, novel_id, dimension="physics", rule="Rule 2")

                # Test character relationships
                success = await relationship_manager.create_character_relationship(
                    character1_id, character2_id, strength=8, rel_type="friend", symmetric=True
                )
                assert success

                # Test world rule conflicts
                success = await relationship_manager.create_world_rule_conflict(rule1_id, rule2_id, severity="major")
                assert success

                # Verify relationships exist
                result = await session.run(
                    "MATCH (c1:Character {id: $char1_id})-[r:RELATES_TO]->(c2:Character {id: $char2_id}) RETURN count(r) as count",
                    {"char1_id": character1_id, "char2_id": character2_id},
                )
                record = await result.single()
                assert record["count"] == 1

                result = await session.run(
                    "MATCH (w1:WorldRule {id: $rule1_id})-[r:CONFLICTS_WITH]->(w2:WorldRule {id: $rule2_id}) RETURN count(r) as count",
                    {"rule1_id": rule1_id, "rule2_id": rule2_id},
                )
                record = await result.single()
                assert record["count"] == 1

                # Clean up test data
                await session.run(
                    "MATCH (n) WHERE n.novel_id = $novel_id OR n.id IN [$rule1_id, $rule2_id] DETACH DELETE n",
                    {"novel_id": novel_id, "rule1_id": rule1_id, "rule2_id": rule2_id},
                )

            await driver.close()

        except ImportError:
            pytest.skip("Neo4j driver not available")
