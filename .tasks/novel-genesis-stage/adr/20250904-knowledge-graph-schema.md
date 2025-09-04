---
id: ADR-005-knowledge-graph-schema
title: 知识图谱Schema设计
status: Accepted
date: 2025-09-04
decision_makers: [platform-arch, data-arch]
related_requirements: [FR-003, FR-004, FR-008, NFR-003]
related_stories: [STORY-003, STORY-004, STORY-008]
supersedes: []
superseded_by: null
tags: [architecture, neo4j, graph-database, data-model]
---

# 知识图谱Schema设计

## Status
Accepted

## Context

### Business Context
根据PRD中的世界观和人物关系管理需求：
- 相关用户故事：
  - STORY-003: 世界观对话式构建（需要管理复杂的世界规则）
  - STORY-004: 人物对话式设计（需要维护人物关系网）
  - STORY-008: 创世内容管理（需要图谱化的知识组织）
- 业务价值：通过图谱管理复杂关系，确保故事的一致性和连贯性
- 业务约束：需要支持动态扩展，适应不同类型的小说设定

### Technical Context
基于现有架构：
- 当前架构：Neo4j 5.x 已部署（开启 apoc 与 graph-data-science 插件）
- 现有技术栈：
  - Neo4j 作为图数据库
  - Python 后端使用官方 neo4j-driver（异步）
  - 已有 PostgreSQL 与 Milvus 协同工作
- 现有约定：图数据用于关系管理，属性与版本化内容存 PostgreSQL
- 集成点：需要与知识库、一致性检查、Agent 服务集成

### Requirements Driving This Decision
- FR-003: 世界观需要5个维度的规则管理
- FR-004: 人物关系网络，支持-10到+10的关系强度
- FR-008: 知识图谱需要支持≥10万节点、≥50万关系边
- NFR-003: 图查询性能要求

### Constraints
- 技术约束：Neo4j的查询性能与图的密度相关
- 业务约束：Schema需要足够灵活，支持各种类型的小说
- 成本约束：需要控制图的复杂度，避免查询爆炸

## Decision Drivers
- **灵活性**：支持不同类型小说的世界观
- **查询效率**：快速查找关系和路径
- **一致性检查**：支持规则验证和冲突检测
- **可扩展性**：支持动态添加新的实体和关系类型
- **可理解性**：模型直观，便于开发和维护

## Considered Options

### Option 1: 混合模型（层级+网状）（推荐）
- **描述**：顶层使用层级结构组织大类，底层使用网状结构表达复杂关系
- **与现有架构的一致性**：高 - 充分利用Neo4j的优势
- **实现复杂度**：中
- **优点**：
  - 平衡了组织清晰性和关系灵活性
  - 查询可以分层优化
  - 易于理解和维护
  - 支持不同粒度的操作
- **缺点**：
  - 需要设计两套查询模式
  - 层级边界需要明确定义
- **风险**：设计不当可能导致层级混乱

### Option 2: 纯层级模型
- **描述**：严格的树形结构，如世界→地区→城市→地点
- **与现有架构的一致性**：中 - 未充分利用图数据库
- **实现复杂度**：低
- **优点**：
  - 结构清晰
  - 查询路径明确
  - 易于实现权限控制
- **缺点**：
  - 无法表达横向关系
  - 不适合复杂的人物关系
  - 灵活性差
- **风险**：无法满足复杂关系需求

### Option 3: 纯网状模型
- **描述**：所有实体平等，通过关系连接
- **与现有架构的一致性**：中
- **实现复杂度**：高
- **优点**：
  - 最大灵活性
  - 可以表达任意复杂关系
  - 符合现实世界模型
- **缺点**：
  - 难以组织和导航
  - 查询可能很复杂
  - 性能优化困难
- **风险**：图过于复杂，难以管理

### Option 4: 标签属性图
- **描述**：使用标签分类，属性存储详细信息
- **与现有架构的一致性**：高 - Neo4j原生支持
- **实现复杂度**：低
- **优点**：
  - Neo4j原生模型
  - 灵活的标签系统
  - 丰富的属性支持
- **缺点**：
  - 需要良好的标签规划
  - 可能出现标签爆炸
- **风险**：标签管理可能失控

## Decision
建议采用 **Option 1: 混合模型（层级+网状）**

理由：
1. 最佳平衡结构化和灵活性
2. 符合小说世界的自然组织方式
3. 查询性能可优化
4. 易于理解和可视化
5. 支持渐进式复杂度

## Consequences

### Positive
- 清晰的顶层组织结构
- 灵活的底层关系网络
- 支持高效的分层查询
- 易于实现一致性检查
- 可视化友好

### Negative
- 需要维护两种关系模式
- 初始设计需要更多考虑
- 可能需要定期重构优化

### Risks
- **风险1：层级设计不当**
  - 缓解：提供灵活的重组工具
- **风险2：关系爆炸**
  - 缓解：设置关系数量限制和清理策略

## Implementation Plan

### Integration with Existing Architecture
- **代码位置**：
  - 知识图谱服务与查询：`apps/backend/src/common/services/knowledge_graph/`
  - Neo4j 客户端封装：`apps/backend/src/common/services/neo4j_service.py`
- **模块边界**：
  - KnowledgeGraphService: 图操作与业务接口
  - GraphQueryBuilder: 常用查询构建
  - ConsistencyChecker: 一致性检查
- **依赖管理**：使用官方 neo4j-driver（异步）

### Graph Schema Design
```cypher
// ==========================================
// 1. 顶层组织结构（层级部分）
// ==========================================

// 小说根节点
CREATE (n:Novel {
    novel_id: 'novel_uuid',
    title: '小说名称',
    created_at: datetime()
})

// ==========================================
// 2. 世界观层级结构
// ==========================================

// 世界观维度
CREATE (dim:WorldDimension {
    app_id: 'dim_uuid',
    novel_id: n.novel_id,
    type: 'geography|history|culture|rules|society',
    name: '地理',
    description: '世界的物理空间'
})<-[:HAS_DIMENSION]-(n)

// 世界规则
CREATE (rule:WorldRule {
    app_id: 'rule_uuid',
    novel_id: n.novel_id,
    name: '魔法体系',
    category: 'magic_system',
    level: 1,  // 规则等级：1-核心，2-重要，3-次要
    description: '这个世界的魔法运作原理'
})-[:RULE_IN]->(dim)

// 规则细节
CREATE (detail:RuleDetail {
    id: 'detail_uuid',
    content: '魔法需要等价交换',
    examples: ['案例1', '案例2'],
    exceptions: ['例外情况'],
    constraints: ['限制条件']
})-[:DETAILS]->(rule)

// 规则适用范围（示例）：规则适用于某地点或其上级地域
CREATE (rule)-[:APPLIES_TO]->(loc)

// 地理位置（层级：世界->大陆->国家->城市->地点）
CREATE (loc:Location {
    app_id: 'loc_uuid',
    novel_id: n.novel_id,
    name: '王都',
    type: 'city',  // world|continent|country|city|place
    description: '帝国的首都',
    coordinates: point({x: 100, y: 200, crs: 'cartesian'}),  // 可选的地图坐标
    population: 1000000,
    climate: 'temperate'
})

// 位置层级关系
CREATE (child_loc)-[:LOCATED_IN]->(parent_loc)

// ==========================================
// 3. 人物网络结构（网状部分）
// ==========================================

// 人物节点
CREATE (char:Character {
    app_id: 'char_uuid',
    novel_id: n.novel_id,
    name: '主角名',
    role: 'protagonist|antagonist|supporting',
    age: 25,
    gender: 'male|female|other',
    
    // 八维度设定（根据需求文档）
    appearance: '外貌描述',
    personality: 'INTJ',  // MBTI类型
    background: '背景故事',
    motivation: '核心动机',
    goals_short_term: '短期目标',
    goals_mid_term: '中期目标',
    goals_long_term: '长期目标',
    obstacles_internal: '内在障碍',
    obstacles_external: '外在障碍',
    obstacles_environmental: '环境障碍',
    arc: '成长弧线描述',
    secrets: '心结或秘密'
})-[:APPEARS_IN_NOVEL]->(n)

// 人物关系（可以有多种类型的关系）
CREATE (char1)-[rel:RELATES_TO {
    type: 'family|friend|rival|lover|mentor|enemy',
    strength: 8,  // -10 到 +10
    description: '青梅竹马',
    history: '从小一起长大',
    dynamic: 'mutual_support',  // 关系动态
    created_at: datetime(),
    updated_at: datetime()
}]->(char2)

// 人物与地点的关系
CREATE (char)-[:BORN_IN]->(location)
CREATE (char)-[:LIVES_IN]->(location)
CREATE (char)-[:VISITS {
    chapter: 5,
    purpose: '寻找线索'
}]->(location)

// 人物与规则的关系（使用单一关系 + kind 属性，避免多类型并列）
CREATE (char)-[:RULE_REL {
    kind: 'FOLLOWS',
    proficiency: 0.8,  // 掌握程度
    since_chapter: 10
}]->(rule)

// ==========================================
// 4. 情节结构
// ==========================================

// 章节节点
CREATE (chapter:Chapter {
    app_id: 'chapter_uuid',
    novel_id: n.novel_id,
    number: 1,
    title: '序章',
    summary: '故事开始',
    word_count: 3000,
    status: 'drafted|revised|published'
})-[:BELONGS_TO_NOVEL]->(n)

// 场景节点（地点与参与者使用关系表达，避免外键/列表）
CREATE (scene:Scene {
    app_id: 'scene_uuid',
    novel_id: n.novel_id,
    name: '初遇',
    time: '黄昏',
    mood: 'tense',
    purpose: 'character_introduction'
})-[:SCENE_IN]->(chapter)
// 场景地点与参与者
CREATE (scene)-[:TAKES_PLACE_AT]->(loc)
CREATE (char)-[:PARTICIPATES_IN {role: 'POV'}]->(scene)

// 事件节点
CREATE (event:Event {
    app_id: 'event_uuid',
    novel_id: n.novel_id,
    type: 'plot_point|conflict|revelation',
    description: '重要事件描述',
    impact: 'high|medium|low',
    timestamp: datetime('2025-01-01T00:00:00Z')
})-[:HAPPENS_IN]->(scene)

// 事件影响关系
CREATE (event)-[:TRIGGERS]->(next_event)
CREATE (event)-[:AFFECTS {
    impact_type: 'emotional|physical|social',
    degree: 0.8
}]->(char)

// 角色状态（用于弧线分析）
CREATE (state:CharacterState {
    app_id: 'state_uuid',
    novel_id: n.novel_id,
    chapter: 1,
    emotional: 'tense',
    relationships: ['friendship_strength:8'],
    goals: ['find_clue']
})
CREATE (char)-[:HAS_STATE]->(state)

// ==========================================
// 5. 一致性约束节点
// ==========================================

// 约束规则
CREATE (constraint:Constraint {
    id: 'constraint_uuid',
    type: 'timeline|causality|character|world',
    rule: 'MATCH (e1:Event)-[:TRIGGERS]->(e2:Event) WHERE e1.timestamp > e2.timestamp',
    description: '因果事件的时间顺序约束',
    severity: 'error|warning|info'
})

// 冲突记录
CREATE (conflict:Conflict {
    id: 'conflict_uuid',
    detected_at: datetime(),
    type: 'rule_violation|timeline_error|character_inconsistency',
    description: '检测到的冲突描述',
    involved_nodes: ['node_id1', 'node_id2'],
    resolution_status: 'pending|resolved|ignored'
})

// ==========================================
// 6. 索引和约束
// ==========================================

// 唯一性约束（Neo4j 5.x 语法）
CREATE CONSTRAINT unique_novel_id IF NOT EXISTS FOR (n:Novel) REQUIRE n.novel_id IS UNIQUE;
CREATE CONSTRAINT unique_character_app_id IF NOT EXISTS FOR (c:Character) REQUIRE c.app_id IS UNIQUE;
CREATE CONSTRAINT unique_location_app_id IF NOT EXISTS FOR (l:Location) REQUIRE l.app_id IS UNIQUE;
CREATE CONSTRAINT unique_rule_app_id IF NOT EXISTS FOR (r:WorldRule) REQUIRE r.app_id IS UNIQUE;
CREATE CONSTRAINT unique_chapter_app_id IF NOT EXISTS FOR (ch:Chapter) REQUIRE ch.app_id IS UNIQUE;
CREATE CONSTRAINT unique_event_app_id IF NOT EXISTS FOR (e:Event) REQUIRE e.app_id IS UNIQUE;

// 范围隔离索引（按 novel_id 提升过滤性能）
CREATE INDEX character_novel_id IF NOT EXISTS FOR (c:Character) ON (c.novel_id);
CREATE INDEX location_novel_id IF NOT EXISTS FOR (l:Location) ON (l.novel_id);
CREATE INDEX rule_novel_id IF NOT EXISTS FOR (r:WorldRule) ON (r.novel_id);
CREATE INDEX chapter_novel_id IF NOT EXISTS FOR (ch:Chapter) ON (ch.novel_id);
CREATE INDEX event_novel_id IF NOT EXISTS FOR (e:Event) ON (e.novel_id);

// 常用属性索引
CREATE INDEX character_name IF NOT EXISTS FOR (c:Character) ON (c.name);
CREATE INDEX location_name IF NOT EXISTS FOR (l:Location) ON (l.name);
CREATE INDEX chapter_number IF NOT EXISTS FOR (ch:Chapter) ON (ch.number);
CREATE INDEX event_time IF NOT EXISTS FOR (e:Event) ON (e.timestamp);
CREATE INDEX worldrule_category IF NOT EXISTS FOR (r:WorldRule) ON (r.category);

// 全文搜索索引
CALL db.index.fulltext.createNodeIndex(
    "character_search",
    ["Character"],
    ["name", "background", "personality"]
);

CALL db.index.fulltext.createNodeIndex(
    "location_search", 
    ["Location"],
    ["name", "description"]
);
```

### Query Examples
```python
# apps/backend/src/infrastructure/neo4j/queries.py
from neo4j import AsyncGraphDatabase
from typing import List, Dict, Any

class GraphQueryBuilder:
    """图查询构建器"""
    
    def __init__(self, driver):
        self.driver = driver
    
    async def get_character_network(
        self,
        novel_id: str,
        character_id: str,
        depth: int = 2
    ) -> Dict[str, Any]:
        """获取人物关系网络"""
        query = """
        MATCH (n:Novel {novel_id: $novel_id})
        MATCH (c:Character {app_id: $char_id})-[:APPEARS_IN_NOVEL]->(n)
        CALL apoc.path.subgraphAll(c, {
            relationshipFilter: "RELATES_TO>",
            maxLevel: $depth,
            bfs: true
        })
        YIELD nodes, relationships
        RETURN nodes, relationships
        """
        
        async with self.driver.session() as session:
            result = await session.run(
                query,
                novel_id=novel_id,
                char_id=character_id,
                depth=depth
            )
            return await result.single()
    
    async def check_timeline_consistency(
        self,
        novel_id: str
    ) -> List[Dict[str, Any]]:
        """检查时间线一致性"""
        query = """
        MATCH (n:Novel {novel_id: $novel_id})
        MATCH (e1:Event)-[:HAPPENS_IN]->(:Scene)-[:SCENE_IN]->(:Chapter)-[:BELONGS_TO_NOVEL]->(n)
        MATCH (e1)-[:TRIGGERS]->(e2:Event)
        WHERE e1.timestamp > e2.timestamp
        RETURN e1, e2, 'Timeline violation: cause after effect' as error
        """
        
        async with self.driver.session() as session:
            result = await session.run(query, novel_id=novel_id)
            return [record.data() async for record in result]
    
    async def find_plot_holes(
        self,
        novel_id: str
    ) -> List[Dict[str, Any]]:
        """查找情节漏洞"""
        query = """
        // 查找没有解决的伏笔
        MATCH (n:Novel {novel_id: $novel_id})
        MATCH (setup:Event {type: 'foreshadowing'})-[:HAPPENS_IN]->(:Scene)-[:SCENE_IN]->(:Chapter)-[:BELONGS_TO_NOVEL]->(n)
        WHERE NOT EXISTS {
            MATCH (setup)-[:RESOLVED_BY]->(:Event)
        }
        RETURN setup.id as unresolved_foreshadowing, setup.description
        
        UNION
        
        // 查找孤立的角色（没有任何关系）
        MATCH (n:Novel {novel_id: $novel_id})
        MATCH (c:Character)-[:APPEARS_IN_NOVEL]->(n)
        WHERE NOT EXISTS {
            MATCH (c)-[:RELATES_TO]-()
        }
        RETURN c.app_id as isolated_character, c.name
        """
        
        async with self.driver.session() as session:
            result = await session.run(query, novel_id=novel_id)
            return [record.data() async for record in result]
    
    async def get_world_rules_for_location(
        self,
        location_id: str
    ) -> List[Dict[str, Any]]:
        """获取特定地点适用的世界规则"""
        query = """
        MATCH (l:Location {app_id: $loc_id})
        MATCH (l)-[:LOCATED_IN*0..4]->(parent:Location)
        MATCH (rule:WorldRule)-[:APPLIES_TO]->(parent)
        RETURN DISTINCT rule
        ORDER BY rule.level
        """
        
        async with self.driver.session() as session:
            result = await session.run(query, loc_id=location_id)
            return [record["rule"] async for record in result]
    
    async def analyze_character_arc(
        self,
        character_id: str
    ) -> Dict[str, Any]:
        """分析角色成长弧线"""
        query = """
        MATCH (c:Character {id: $char_id})
        MATCH (c)-[:PARTICIPATES_IN]->(scene:Scene)-[:SCENE_IN]->(chapter:Chapter)
        WITH c, scene, chapter
        ORDER BY chapter.number
        
        // 收集角色在不同章节的状态变化
        MATCH (c)-[r:HAS_STATE]->(state:CharacterState)
        WHERE state.chapter = chapter.number
        
        RETURN c.name as character,
               collect({
                   chapter: chapter.number,
                   emotional_state: state.emotional,
                   relationships: state.relationships,
                   goals: state.goals
               }) as arc_progression
        """
        
        async with self.driver.session() as session:
            result = await session.run(query, char_id=character_id)
            return await result.single()
```

### Performance Optimization
```python
# 查询优化策略
class GraphOptimizer:
    """图查询优化器"""
    
    def __init__(self, driver):
        self.driver = driver
    
    async def warm_cache(self, novel_id: str):
        """预热缓存，加载常用数据"""
        queries = [
            # 预加载所有角色
            "MATCH (n:Novel {novel_id: $nid})<-[:APPEARS_IN_NOVEL]-(c:Character) RETURN c LIMIT 1000",
            # 预加载主要位置（城市）
            "MATCH (n:Novel {novel_id: $nid})<-[:BELONGS_TO_NOVEL]-(ch:Chapter)
             MATCH (sc:Scene)-[:SCENE_IN]->(ch)
             MATCH (sc)-[:TAKES_PLACE_AT]->(l:Location {type: 'city'}) RETURN l LIMIT 1000",
            # 预加载核心规则（level=1）
            "MATCH (n:Novel {novel_id: $nid})
             MATCH (n)-[:HAS_DIMENSION]->(dim:WorldDimension)
             MATCH (r:WorldRule {level: 1})-[:RULE_IN]->(dim) RETURN r LIMIT 500"
        ]
        
        async with self.driver.session() as session:
            for query in queries:
                await session.run(query, nid=novel_id)
    
    async def create_virtual_graph(self, novel_id: str):
        """创建虚拟图用于复杂分析"""
        query = """
        CALL gds.graph.project(
            $novel_id + '_virtual',
            ['Character', 'Location', 'Event'],
            {
                RELATES_TO: {orientation: 'UNDIRECTED'},
                HAPPENS_IN: {orientation: 'NATURAL'},
                AFFECTS: {orientation: 'NATURAL'}
            }
        )
        """
        
        async with self.driver.session() as session:
            await session.run(query, novel_id=novel_id)
    
    async def analyze_centrality(self, novel_id: str):
        """分析节点中心性（找出关键人物/地点）"""
        query = """
        CALL gds.pageRank.stream($novel_id + '_virtual')
        YIELD nodeId, score
        RETURN gds.util.asNode(nodeId).name AS name, score
        ORDER BY score DESC
        LIMIT 10
        """
        
        async with self.driver.session() as session:
            result = await session.run(query, novel_id=novel_id)
            return [record.data() async for record in result]

    async def drop_virtual_graph(self, novel_id: str):
        """清理虚拟图，释放内存"""
        query = """
        CALL gds.graph.exists($novel_id + '_virtual') YIELD exists
        WITH exists
        WHERE exists
        CALL gds.graph.drop($novel_id + '_virtual') YIELD graphName
        RETURN graphName
        """
        async with self.driver.session() as session:
            await session.run(query, novel_id=novel_id)
```

### Rollback Plan
- **触发条件**：图过于复杂导致查询性能下降
- **回滚步骤**：
  1. 导出关键关系到PostgreSQL
  2. 简化图结构，只保留核心关系
  3. 使用PostgreSQL处理属性查询
  4. 逐步优化图模型
- **数据恢复**：Neo4j支持备份和恢复

## Validation

### Alignment with Existing Patterns
- **架构一致性检查**：与现有的PostgreSQL和Milvus协同工作
- **代码审查重点**：
  - Cypher查询的性能
  - 事务管理
  - 并发更新处理

### Metrics
- **性能指标**：
  - 单跳查询：P95 < 50ms
  - 两跳查询：P95 < 200ms
  - 全图遍历：P95 < 2秒
  - 写入操作：P95 < 100ms
- **规模指标**：
  - 支持节点数：> 100,000
  - 支持关系数：> 500,000
  - 查询并发数：> 50

### Test Strategy
- **单元测试**：查询构建器的正确性
- **集成测试**：与PostgreSQL数据的一致性
- **性能测试**：大图的查询性能
- **压力测试**：并发读写操作
- **一致性测试**：验证约束和规则

## References
- [Neo4j最佳实践](https://neo4j.com/docs/cypher-manual/current/introduction/patterns/)
- [Graph Data Modeling](https://neo4j.com/developer/data-modeling/)
- [APOC库文档](https://neo4j.com/docs/apoc/current/)
- [Graph Data Science库](https://neo4j.com/docs/graph-data-science/current/)

## Changelog
- 2025-09-04: 初始草稿创建
- 2025-09-04: 对齐 Neo4j 5.x，统一 :Novel/novel_id 与 app_id，修正 Cypher 示例（关系与属性）、索引与约束语法、查询示例绑定 novel_id，新增 Scene/Event/CharacterState 关系示例与 GDS 清理
