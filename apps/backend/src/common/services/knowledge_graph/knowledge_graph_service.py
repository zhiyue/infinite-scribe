from __future__ import annotations

from src.db.graph.schema import Neo4jNodeCreator, Neo4jRelationshipManager, Neo4jSchemaManager

# 使用现有的 graph 模块抽象层，避免重复实现
from src.db.graph.session import create_neo4j_session, execute_query

from .consistency_validator import ConsistencyReport, ConsistencyValidator
from .graph_query_builder import GraphQueryBuilder


class KnowledgeGraphService:
    """小说知识图谱服务 - 提供针对小说故事知识图谱的高级操作。

    这个服务类封装了与Neo4j图数据库交互的复杂逻辑，专门用于管理小说创作系统中的
    知识图谱数据，包括角色关系、世界观设定、一致性校验等功能。

    主要功能：
    - 基于 src/db/graph 模块的成熟抽象层，避免重复实现连接管理
    - 提供模式约束和索引的自动创建和验证
    - 支持小说节点、角色节点、地点节点等核心实体的创建
    - 管理角色间关系、世界观规则冲突等复杂关系
    - 提供全面的一致性验证和评分机制
    - 所有操作都基于小说范围，确保数据隔离

    架构设计：
    - 高级服务层：封装复杂的图操作逻辑
    - 依赖现有抽象：复用 src/db/graph 模块的连接管理
    - 异步支持：所有操作都是异步的，支持高并发
    - 错误处理：完善的异常处理和日志记录
    - 模块化：将不同功能分离到专门的管理器中
    """

    def __init__(self) -> None:
        """初始化知识图谱服务。

        不再需要注入 Neo4jService，直接使用 src/db/graph 模块的全局驱动。
        这简化了依赖管理，避免了重复的连接管理代码。
        """
        # 移除了重复的驱动程序和连接管理逻辑
        # 现在完全依赖 src/db/graph 模块的抽象
        pass

    async def ensure_constraints(self) -> None:
        """创建所需的数据库约束和索引（幂等操作）。

        使用统一的 Neo4jSchemaManager 作为单一真相源，避免语句重复与漂移。
        """
        async with create_neo4j_session() as session:
            schema_manager = Neo4jSchemaManager(session)
            await schema_manager.initialize_schema()

    async def upsert_novel(self, *, novel_id: str, title: str | None = None) -> None:
        """创建或更新小说节点。

        使用MERGE操作确保小说节点的存在，如果不存在则创建，如果存在则更新。

        Args:
            novel_id: 小说的唯一标识符
            title: 小说标题，可选
        """
        query = """
        MERGE (n:Novel {novel_id: $novel_id})
        ON CREATE SET n.title = coalesce($title, n.title)
        ON MATCH SET n.title = coalesce($title, n.title)
        """
        await execute_query(query, {"novel_id": novel_id, "title": title})

    async def upsert_character(self, *, novel_id: str, app_id: str, name: str, role: str | None = None) -> None:
        """创建或更新角色节点并建立与小说的关系。

        该方法会：
        1. 查找指定的小说节点
        2. 创建或更新角色节点
        3. 建立角色与小说之间的 BELONGS_TO 关系

        Args:
            novel_id: 所属小说的唯一标识符
            app_id: 角色的应用层唯一标识符
            name: 角色姓名
            role: 角色在小说中的角色定位，可选
        """
        query = """
        MATCH (n:Novel {novel_id: $novel_id})
        MERGE (c:Character {app_id: $app_id})-[:BELONGS_TO]->(n)
        ON CREATE SET c.novel_id = $novel_id, c.name = $name, c.role = $role
        ON MATCH SET c.name = coalesce($name, c.name), c.role = coalesce($role, c.role)
        """
        await execute_query(query, {"novel_id": novel_id, "app_id": app_id, "name": name, "role": role})

    async def relate_characters(
        self,
        *,
        from_app_id: str,
        to_app_id: str,
        type: str,
        strength: float | None = None,
        since_chapter: int | None = None,
    ) -> None:
        """建立或更新角色间的关系。

        创建两个角色之间的RELATES_TO关系，支持关系强度和起始章节等属性。
        使用统一的'type'字段以保持与ConsistencyValidator的一致性。

        Args:
            from_app_id: 关系起始角色的应用ID
            to_app_id: 关系目标角色的应用ID
            type: 关系类型（如：friend, enemy, family等）
            strength: 关系强度（0-10），可选
            since_chapter: 关系建立的起始章节，可选
        """
        query = """
        MATCH (a:Character {app_id: $from}), (b:Character {app_id: $to})
        MERGE (a)-[r:RELATES_TO {type: $type}]->(b)
        ON CREATE SET r.strength = $strength, r.since_chapter = $since
        ON MATCH SET r.strength = coalesce($strength, r.strength), r.since_chapter = coalesce($since, r.since_chapter)
        """
        await execute_query(
            query,
            {"from": from_app_id, "to": to_app_id, "type": type, "strength": strength, "since": since_chapter},
        )

    # === 增强的创世系统方法 - 使用现有的 schema 管理器 ===

    async def initialize_genesis_schema(self) -> bool:
        """初始化完整的Neo4j创世系统模式。

        使用现有的 Neo4jSchemaManager 进行模式初始化，避免重复实现。

        Returns:
            bool: 初始化是否成功
        """
        try:
            async with create_neo4j_session() as session:
                schema_manager = Neo4jSchemaManager(session)
                await schema_manager.initialize_schema()
                return await schema_manager.verify_schema()
        except Exception as e:
            import logging

            logging.getLogger(__name__).error(f"Failed to initialize genesis schema: {e}")
            return False

    async def create_novel_node(self, novel_id: str, title: str = "", **properties) -> bool:
        """使用创世系统约束创建小说节点。

        Args:
            novel_id: 小说唯一标识符
            title: 小说标题
            **properties: 其他属性

        Returns:
            bool: 创建是否成功
        """
        try:
            async with create_neo4j_session() as session:
                node_creator = Neo4jNodeCreator(session)
                result = await node_creator.create_novel_node(novel_id=novel_id, title=title, **properties)
                return bool(result)
        except Exception as e:
            import logging

            logging.getLogger(__name__).error(f"Failed to create novel node: {e}")
            return False

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
    ) -> bool:
        """使用8维角色设计创建角色节点。

        Args:
            character_id: 角色唯一标识符
            novel_id: 所属小说ID
            name: 角色姓名
            appearance: 外貌描述
            personality: 性格特点
            background: 背景设定
            motivation: 动机驱动
            goals: 目标设定
            obstacles: 障碍挑战
            arc: 角色发展弧线
            wounds: 心理创伤
            **properties: 其他属性

        Returns:
            bool: 创建是否成功
        """
        try:
            async with create_neo4j_session() as session:
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
                    **properties,
                )
                return bool(result)
        except Exception as e:
            import logging

            logging.getLogger(__name__).error(f"Failed to create character node: {e}")
            return False

    async def create_world_rule_node(
        self,
        rule_id: str,
        novel_id: str,
        dimension: str,
        rule: str,
        priority: int = 0,
        scope: dict = None,
        examples: list = None,
        constraints: list = None,
        **properties,
    ) -> bool:
        """创建世界观规则节点用于一致性检查。

        Args:
            rule_id: 规则唯一标识符
            novel_id: 所属小说ID
            dimension: 规则维度（如：physics, magic, social等）
            rule: 规则描述
            priority: 规则优先级
            scope: 应用范围
            examples: 示例列表
            constraints: 约束列表
            **properties: 其他属性

        Returns:
            bool: 创建是否成功
        """
        try:
            async with create_neo4j_session() as session:
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
                    **properties,
                )
                return bool(result)
        except Exception as e:
            import logging

            logging.getLogger(__name__).error(f"Failed to create world rule node: {e}")
            return False

    async def create_location_node(
        self, location_id: str, novel_id: str, name: str, x: float = 0.0, y: float = 0.0, **properties
    ) -> bool:
        """创建带坐标的地点节点用于空间一致性检查。

        Args:
            location_id: 地点唯一标识符
            novel_id: 所属小说ID
            name: 地点名称
            x: X坐标
            y: Y坐标
            **properties: 其他属性

        Returns:
            bool: 创建是否成功
        """
        try:
            async with create_neo4j_session() as session:
                node_creator = Neo4jNodeCreator(session)
                result = await node_creator.create_location_node(
                    location_id=location_id, novel_id=novel_id, name=name, x=x, y=y, **properties
                )
                return bool(result)
        except Exception as e:
            import logging

            logging.getLogger(__name__).error(f"Failed to create location node: {e}")
            return False

    async def create_character_relationship(
        self, character1_id: str, character2_id: str, strength: int, rel_type: str, symmetric: bool = True
    ) -> bool:
        """在角色间创建RELATES_TO关系。

        Args:
            character1_id: 第一个角色ID
            character2_id: 第二个角色ID
            strength: 关系强度
            rel_type: 关系类型
            symmetric: 是否为对称关系

        Returns:
            bool: 创建是否成功
        """
        try:
            async with create_neo4j_session() as session:
                relationship_manager = Neo4jRelationshipManager(session)
                return await relationship_manager.create_character_relationship(
                    character1_id=character1_id,
                    character2_id=character2_id,
                    strength=strength,
                    rel_type=rel_type,
                    symmetric=symmetric,
                )
        except Exception as e:
            import logging

            logging.getLogger(__name__).error(f"Failed to create character relationship: {e}")
            return False

    async def create_world_rule_conflict(self, rule1_id: str, rule2_id: str, severity: str = "major") -> bool:
        """在世界观规则间创建CONFLICTS_WITH关系。

        Args:
            rule1_id: 第一个规则ID
            rule2_id: 第二个规则ID
            severity: 冲突严重程度

        Returns:
            bool: 创建是否成功
        """
        try:
            async with create_neo4j_session() as session:
                relationship_manager = Neo4jRelationshipManager(session)
                return await relationship_manager.create_world_rule_conflict(
                    rule1_id=rule1_id, rule2_id=rule2_id, severity=severity
                )
        except Exception as e:
            import logging

            logging.getLogger(__name__).error(f"Failed to create world rule conflict: {e}")
            return False

    async def validate_consistency(self, novel_id: str) -> ConsistencyReport:
        """对小说进行全面的一致性验证。

        Args:
            novel_id: 小说唯一标识符

        Returns:
            ConsistencyReport: 一致性验证报告
        """
        try:
            async with create_neo4j_session() as session:
                validator = ConsistencyValidator(session)
                return await validator.validate_all(novel_id)
        except Exception as e:
            import logging

            logging.getLogger(__name__).error(f"Consistency validation failed: {e}")
            from .consistency_validator import ConsistencyReport, ConsistencyViolation, ViolationSeverity

            # 返回错误报告
            return ConsistencyReport(
                violations=[
                    ConsistencyViolation(
                        rule_type="system_error",
                        severity=ViolationSeverity.ERROR,
                        message=f"Consistency validation failed: {e!s}",
                        affected_entities=[novel_id],
                    )
                ],
                score=0.0,
                total_checks=0,
                passed_checks=0,
            )

    # === 查询构建器支持 ===

    def create_query_builder(self) -> GraphQueryBuilder:
        """创建图查询构建器实例。

        注意：这里不再缓存 GraphQueryBuilder 实例，而是在需要时创建，
        因为我们不再管理驱动程序的生命周期。

        Returns:
            GraphQueryBuilder: 查询构建器实例

        Raises:
            RuntimeError: 当Neo4j驱动程序不可用时
        """
        # 在创建查询构建器前，确保全局 Neo4j 驱动已可用
        try:
            from src.db.graph.driver import neo4j_driver
        except Exception:  # pragma: no cover - 防御性导入
            neo4j_driver = None

        if neo4j_driver is None:
            raise RuntimeError("Neo4j driver not available")

        # 返回查询构建器实例；其内部将按需通过会话工厂获取会话
        return GraphQueryBuilder()
