from unittest.mock import AsyncMock, patch

import pytest
from src.common.services.knowledge_graph.knowledge_graph_service import (
    KnowledgeGraphService,
)


@pytest.mark.asyncio
async def test_knowledge_graph_service_bootstrap():
    """测试知识图谱服务的基本操作。

    现在使用重构后的架构，不再需要注入 Neo4jService，
    而是直接使用 src/db/graph 模块的抽象层。
    """
    # 同时 Mock create_neo4j_session / Neo4jSchemaManager / execute_query，避免真实连接
    with (
        patch("src.common.services.knowledge_graph.knowledge_graph_service.create_neo4j_session") as mock_session,
        patch("src.common.services.knowledge_graph.knowledge_graph_service.Neo4jSchemaManager") as mock_schema_manager,
        patch("src.common.services.knowledge_graph.knowledge_graph_service.execute_query") as mock_execute,
    ):
        mock_execute.return_value = []

        # 准备会话上下文
        mock_session_instance = AsyncMock()
        mock_session.return_value.__aenter__.return_value = mock_session_instance
        mock_session.return_value.__aexit__.return_value = None

        # 准备 SchemaManager
        mock_schema_mgr = mock_schema_manager.return_value
        mock_schema_mgr.initialize_schema = AsyncMock()

        kg = KnowledgeGraphService()  # 不再需要 Neo4jService 参数

        # 测试基本操作
        await kg.ensure_constraints()  # 使用 SchemaManager 初始化
        await kg.upsert_novel(novel_id="novel-1", title="Test Novel")
        await kg.upsert_character(novel_id="novel-1", app_id="char-1", name="Hero", role="PROTAGONIST")

        await kg.relate_characters(from_app_id="char-1", to_app_id="char-1", type="FRIEND", strength=1.0)

        # 验证调用
        mock_schema_mgr.initialize_schema.assert_called_once()
        assert mock_execute.call_count >= 3  # upsert_novel / upsert_character / relate_characters


@pytest.mark.asyncio
async def test_knowledge_graph_service_enhanced_methods():
    """测试增强的创世系统方法。"""

    # Mock the entire src.db.graph.schema module to avoid real database calls
    with (
        patch("src.common.services.knowledge_graph.knowledge_graph_service.create_neo4j_session") as mock_session,
        patch("src.common.services.knowledge_graph.knowledge_graph_service.Neo4jSchemaManager") as mock_schema_manager,
        patch("src.common.services.knowledge_graph.knowledge_graph_service.Neo4jNodeCreator") as mock_node_creator,
        patch(
            "src.common.services.knowledge_graph.knowledge_graph_service.Neo4jRelationshipManager"
        ) as mock_relationship_manager,
    ):
        # Setup session mock
        mock_session_instance = AsyncMock()
        mock_session.return_value.__aenter__.return_value = mock_session_instance
        mock_session.return_value.__aexit__.return_value = None

        # Setup schema manager mock
        mock_schema_mgr = mock_schema_manager.return_value
        mock_schema_mgr.initialize_schema = AsyncMock()
        mock_schema_mgr.verify_schema = AsyncMock(return_value=True)

        # Setup node creator mock
        mock_node_creator_instance = mock_node_creator.return_value
        mock_node_creator_instance.create_novel_node = AsyncMock(return_value={"id": "novel-1"})
        mock_node_creator_instance.create_character_node = AsyncMock(return_value={"id": "char-1"})
        mock_node_creator_instance.create_world_rule_node = AsyncMock(return_value={"id": "rule-1"})
        mock_node_creator_instance.create_location_node = AsyncMock(return_value={"id": "loc-1"})

        # Setup relationship manager mock
        mock_rel_mgr = mock_relationship_manager.return_value
        mock_rel_mgr.create_character_relationship = AsyncMock(return_value=True)
        mock_rel_mgr.create_world_rule_conflict = AsyncMock(return_value=True)

        kg = KnowledgeGraphService()

        # Test schema initialization
        result = await kg.initialize_genesis_schema()
        assert result is True
        mock_schema_manager.assert_called_once()
        mock_schema_mgr.initialize_schema.assert_called_once()
        mock_schema_mgr.verify_schema.assert_called_once()

        # Test node creation methods
        result = await kg.create_novel_node("novel-1", "Test Novel")
        assert result is True
        mock_node_creator.assert_called()

        result = await kg.create_character_node(
            character_id="char-1", novel_id="novel-1", name="Hero", appearance="Tall and strong", personality="Brave"
        )
        assert result is True

        result = await kg.create_world_rule_node(
            rule_id="rule-1", novel_id="novel-1", dimension="physics", rule="Gravity works normally"
        )
        assert result is True

        result = await kg.create_location_node(location_id="loc-1", novel_id="novel-1", name="Castle", x=10.0, y=20.0)
        assert result is True

        # Test relationship creation methods
        result = await kg.create_character_relationship(
            character1_id="char-1", character2_id="char-2", strength=8, rel_type="friend"
        )
        assert result is True
        mock_relationship_manager.assert_called()

        result = await kg.create_world_rule_conflict(rule1_id="rule-1", rule2_id="rule-2", severity="major")
        assert result is True


@pytest.mark.asyncio
async def test_knowledge_graph_service_query_builder():
    """测试查询构建器创建。"""

    # create_query_builder 不再依赖全局 driver，直接构造 GraphQueryBuilder()
    with patch("src.common.services.knowledge_graph.knowledge_graph_service.GraphQueryBuilder") as mock_query_builder:
        kg = KnowledgeGraphService()
        kg.create_query_builder()

        # 验证 GraphQueryBuilder 被正确初始化（无参）
        mock_query_builder.assert_called_once_with()


@pytest.mark.asyncio
async def test_knowledge_graph_service_error_handling():
    """测试错误处理。"""

    # 测试当 neo4j_driver 不可用时的情况 - 使用正确的模块路径
    with patch("src.db.graph.driver.neo4j_driver", None):
        kg = KnowledgeGraphService()

        with pytest.raises(RuntimeError, match="Neo4j driver not available"):
            kg.create_query_builder()


@pytest.mark.asyncio
async def test_consistency_validation():
    """测试一致性验证功能。"""

    with patch("src.common.services.knowledge_graph.knowledge_graph_service.create_neo4j_session") as mock_session:
        mock_session_instance = AsyncMock()
        mock_session.return_value.__aenter__.return_value = mock_session_instance
        mock_session.return_value.__aexit__.return_value = None

        with patch(
            "src.common.services.knowledge_graph.knowledge_graph_service.ConsistencyValidator"
        ) as mock_validator_class:
            # Mock 一致性报告
            from src.common.services.knowledge_graph.consistency_validator import ConsistencyReport

            mock_report = ConsistencyReport(violations=[], score=10.0, total_checks=5, passed_checks=5)

            mock_validator = mock_validator_class.return_value
            # validate_all 是异步方法，需要使用 AsyncMock
            mock_validator.validate_all = AsyncMock(return_value=mock_report)

            kg = KnowledgeGraphService()
            report = await kg.validate_consistency("novel-1")

            assert report.score == 10.0
            assert report.total_checks == 5
            assert len(report.violations) == 0
