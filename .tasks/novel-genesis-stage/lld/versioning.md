# 版本控制实现

## 版本化范围定义

### 已版本化内容（已实现）

```yaml
chapter_versions:
  storage: PostgreSQL + MinIO
  tracking:
    - content: MinIO URL引用
    - metadata: 创建时间、作者、版本号
    - status: draft/published/archived
  operations:
    - create_version  # 创建新版本
    - restore_version # 恢复历史版本
    - compare_versions # 版本对比
```

### 创世内容版本化（新增）

```python
class GenesisVersioning:
    """创世内容版本控制"""

    # 世界规则版本化
    async def version_world_rules(self, novel_id: str, rule_id: str):
        """世界规则版本化（Neo4j属性版本）"""
        query = """
        MATCH (r:WorldRule {id: $rule_id, novel_id: $novel_id})
        CREATE (v:WorldRuleVersion {
            id: apoc.create.uuid(),
            rule_id: $rule_id,
            version: r.version + 1,
            content: r.rule,
            dimension: r.dimension,
            priority: r.priority,
            scope: r.scope,
            created_at: datetime(),
            is_active: false
        })
        CREATE (r)-[:HAS_VERSION]->(v)
        SET r.version = r.version + 1
        RETURN v
        """
        return await self.neo4j.execute(query, {
            "novel_id": novel_id,
            "rule_id": rule_id
        })

    # 角色卡版本化
    async def version_character_card(self, novel_id: str, character_id: str):
        """角色卡版本化（Neo4j关系建模）"""
        query = """
        MATCH (c:Character {id: $character_id, novel_id: $novel_id})

        // 创建角色版本节点
        CREATE (cv:CharacterVersion {
            id: apoc.create.uuid(),
            character_id: $character_id,
            version: c.version + 1,
            created_at: datetime(),

            // 8维度数据快照
            name: c.name,
            appearance: c.appearance,
            personality: c.personality,
            background: c.background,
            motivation: c.motivation,
            goals: c.goals,
            obstacles: c.obstacles,
            arc: c.arc,
            wounds: c.wounds
        })

        // 建立版本关系
        CREATE (c)-[:HAS_VERSION {
            version_number: c.version + 1,
            is_active: false
        }]->(cv)

        // 更新当前版本号
        SET c.version = c.version + 1

        // 标记活跃版本
        WITH c, cv
        MATCH (c)-[r:HAS_VERSION]->(old_cv:CharacterVersion)
        WHERE r.is_active = true
        SET r.is_active = false

        WITH c, cv
        MATCH (c)-[r:HAS_VERSION]->(cv)
        SET r.is_active = true

        RETURN cv
        """
        return await self.neo4j.execute(query, {
            "novel_id": novel_id,
            "character_id": character_id
        })

    # 情节节点版本化
    async def version_plot_node(self, novel_id: str, node_id: str):
        """情节节点版本化"""
        # 序列化为JSON
        plot_node = await self.get_plot_node(node_id)

        # 存储到MinIO
        version_key = f"novels/{novel_id}/plot_nodes/{node_id}/v{plot_node.version}.json"
        await self.minio.put_object(
            bucket="genesis-versions",
            key=version_key,
            data=json.dumps(plot_node.to_dict()),
            metadata={
                "novel_id": novel_id,
                "node_id": node_id,
                "version": str(plot_node.version),
                "created_at": datetime.now().isoformat()
            }
        )

        # 更新Neo4j引用
        query = """
        MATCH (p:PlotNode {id: $node_id, novel_id: $novel_id})
        SET p.version = p.version + 1,
            p.minio_url = $minio_url,
            p.updated_at = datetime()
        RETURN p
        """
        return await self.neo4j.execute(query, {
            "novel_id": novel_id,
            "node_id": node_id,
            "minio_url": version_key
        })
```

## 版本边界与合并

```python
class VersionBoundaries:
    """版本控制边界定义"""

    # Neo4j版本化（图内管理）
    NEO4J_VERSIONED = [
        "WorldRule",       # 世界规则：属性版本
        "Character",       # 角色卡：关系版本
        "CharacterState",  # 角色状态：时间序列版本
        "Event"           # 事件：不可变记录
    ]

    # MinIO版本化（对象存储）
    MINIO_VERSIONED = [
        "ChapterContent",  # 章节内容：完整快照
        "PlotNode",       # 情节节点：JSON序列化
        "DialogueTree",   # 对话树：结构化数据
        "DetailBatch"     # 批量细节：压缩归档
    ]

    # 混合版本化（Neo4j元数据+MinIO内容）
    HYBRID_VERSIONED = [
        "Novel",          # 小说：Neo4j索引+MinIO快照
        "Outline",        # 大纲：Neo4j结构+MinIO详情
        "WorldSettings"   # 世界设定：Neo4j规则+MinIO文档
    ]

class VersionMergeStrategy:
    """版本合并策略"""

    async def merge_world_rules(
        self,
        base_version: str,
        current_version: str,
        incoming_version: str
    ):
        """三路合并世界规则"""
        # 获取三个版本
        base = await self.get_rule_version(base_version)
        current = await self.get_rule_version(current_version)
        incoming = await self.get_rule_version(incoming_version)

        # 冲突检测
        conflicts = []

        # 规则文本冲突
        if current.rule != base.rule and incoming.rule != base.rule:
            if current.rule != incoming.rule:
                conflicts.append({
                    "type": "rule_conflict",
                    "current": current.rule,
                    "incoming": incoming.rule
                })

        # 优先级冲突
        if current.priority != incoming.priority:
            conflicts.append({
                "type": "priority_conflict",
                "current": current.priority,
                "incoming": incoming.priority
            })

        # 范围冲突
        if not self._is_scope_compatible(current.scope, incoming.scope):
            conflicts.append({
                "type": "scope_conflict",
                "current": current.scope,
                "incoming": incoming.scope
            })

        if conflicts:
            return {
                "status": "conflict",
                "conflicts": conflicts,
                "resolution_required": True
            }

        # 自动合并
        merged = WorldRuleVersion(
            rule=incoming.rule if incoming.rule != base.rule else current.rule,
            priority=max(current.priority, incoming.priority),
            scope=self._merge_scopes(current.scope, incoming.scope)
        )

        return {
            "status": "merged",
            "result": merged,
            "auto_merged": True
        }
```

## 版本化边界总结

| 内容类型 | 存储位置   | 版本化策略 | 快照频率    |
| -------- | ---------- | ---------- | ----------- |
| 章节内容 | MinIO      | 完整快照   | 每次保存    |
| 世界规则 | Neo4j      | 属性版本   | 规则变更时  |
| 角色卡   | Neo4j      | 关系版本   | 8维度变更时 |
| 角色状态 | Neo4j      | 时间序列   | 章节边界    |
| 情节节点 | MinIO      | JSON序列化 | 节点修改时  |
| 对话历史 | PostgreSQL | 增量记录   | 实时        |
| 向量嵌入 | Milvus     | 版本字段   | 内容更新时  |

## 版本保留策略

```yaml
retention_policy:
  chapters:
    draft: 30_days # 草稿保留30天
    published: forever # 发布版永久保留

  world_rules:
    active: forever # 活跃版本永久
    historical: 90_days # 历史版本90天

  characters:
    current: forever # 当前版本永久
    snapshots: 10 # 保留最近10个快照

  plot_nodes:
    working: 60_days # 工作版本60天
    milestone: forever # 里程碑版本永久
```