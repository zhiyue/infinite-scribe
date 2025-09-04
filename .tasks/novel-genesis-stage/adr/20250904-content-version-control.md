---
id: ADR-004-content-version-control
title: 内容版本控制实现方案
status: Proposed
date: 2025-09-04
decision_makers: [platform-arch, backend-lead]
related_requirements: [FR-007, FR-009, NFR-002, NFR-004]
related_stories: [STORY-007, STORY-009]
supersedes: []
superseded_by: null
tags: [architecture, versioning, data-management, storage]
---

# 内容版本控制实现方案

## Status
Proposed

## Context

### Business Context
根据PRD中的版本管理和分支需求：
- 相关用户故事：
  - STORY-007: 内容审核与调整（需要版本对比）
  - STORY-009: 对话历史回溯（需要完整历史）
- 业务价值：支持创意探索、内容回滚、分支创作，提高创作灵活性
- 业务约束：需要保留至少30天的历史，支持分支和合并操作

### Technical Context
基于现有架构：
- 当前架构：
  - PostgreSQL存储结构化数据
  - MinIO存储大文本内容
  - Kafka事件总线记录所有变更
- 现有技术栈：Python后端、PostgreSQL、MinIO、Redis
- 现有约定：事件驱动架构，所有变更通过事件传播
- 集成点：需要与知识库、对话管理、内容生成模块集成

### Requirements Driving This Decision
- FR-007: 版本管理，保留所有版本便于对比
- FR-009: 分支管理，支持从历史节点创建新分支
- NFR-002: 数据持久性≥99.999%
- NFR-004: 需要审计追踪，记录所有变更

### Constraints
- 技术约束：需要处理大量文本数据（每个项目可能100MB+）
- 业务约束：必须支持并排对比、分支合并
- 成本约束：需要控制存储成本，避免无限增长

## Decision Drivers
- **存储效率**：百万字小说的多版本存储
- **查询性能**：快速获取任意版本内容
- **分支管理**：支持Git-like的分支操作
- **合并能力**：智能合并不同分支的内容
- **审计需求**：完整的变更历史记录

## Considered Options

### Option 1: Event Sourcing（事件溯源）
- **描述**：存储所有变更事件，通过重放事件获得任意版本
- **与现有架构的一致性**：高 - 完美契合事件驱动架构
- **实现复杂度**：高
- **优点**：
  - 完整的审计日志
  - 自然支持时间旅行
  - 存储效率高（仅存储变更）
  - 与Kafka事件总线天然集成
- **缺点**：
  - 重建状态可能很慢
  - 实现复杂度高
  - 需要处理事件顺序和幂等性
- **风险**：MVP时间限制下难以完全实现

### Option 2: 快照 + 增量（推荐）
- **描述**：定期保存完整快照，中间保存增量变更（类似Git）
- **与现有架构的一致性**：高 - 可以利用现有存储
- **实现复杂度**：中
- **优点**：
  - 平衡存储效率和访问性能
  - 实现相对简单
  - 支持快速版本切换
  - 容易实现分支管理
- **缺点**：
  - 需要定期创建快照
  - 合并逻辑需要自行实现
- **风险**：快照策略需要优化

### Option 3: Copy-on-Write（写时复制）
- **描述**：每次修改创建新版本，共享未修改部分
- **与现有架构的一致性**：中
- **实现复杂度**：中
- **优点**：
  - 版本独立，无依赖
  - 访问性能好
  - 实现较简单
- **缺点**：
  - 存储成本高
  - 大量重复数据
  - 难以实现增量同步
- **风险**：存储成本可能失控

### Option 4: 使用Git作为后端
- **描述**：直接使用Git管理内容版本
- **与现有架构的一致性**：低 - 需要集成Git
- **实现复杂度**：低
- **优点**：
  - 成熟的版本控制功能
  - 强大的分支合并能力
  - 开发者熟悉
- **缺点**：
  - Git不适合管理大二进制文件
  - 难以与数据库集成
  - 性能可能成为瓶颈
- **风险**：不适合生产环境的高并发场景

## Decision
建议采用 **Option 2: 快照 + 增量方案**

理由：
1. 平衡了存储效率和访问性能
2. 实现复杂度适中，适合MVP时间限制
3. 与现有存储系统兼容良好
4. 支持分支和合并操作
5. 可以逐步优化，具有良好的演进性

## Consequences

### Positive
- 高效的存储利用率（增量存储）
- 快速的版本访问（通过快照）
- 支持复杂的分支操作
- 完整的变更历史
- 可以渐进式实现和优化

### Negative
- 需要实现快照策略和管理
- 合并算法需要自行开发
- 存储层逻辑相对复杂

### Risks
- **风险1：快照过多导致存储增长**
  - 缓解：实施快照合并和清理策略
- **风险2：增量链过长影响性能**
  - 缓解：定期创建新快照，限制增量链长度

## Implementation Plan

### Integration with Existing Architecture
- **代码位置**：
  - 版本控制核心：`apps/backend/src/core/versioning/`
  - 存储适配器：`apps/backend/src/infrastructure/storage/`
- **模块边界**：
  - VersionManager: 版本管理接口
  - SnapshotStore: 快照存储（MinIO）
  - DeltaStore: 增量存储（PostgreSQL）
  - MergeEngine: 合并引擎
- **依赖管理**：
  - 使用diff-match-patch进行文本差异计算
  - 使用MinIO SDK存储大对象

### Data Model
```python
# PostgreSQL Schema
from sqlalchemy import Column, String, JSON, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID

class ContentVersion(Base):
    __tablename__ = 'content_versions'
    
    id = Column(UUID, primary_key=True)
    project_id = Column(UUID, ForeignKey('projects.id'))
    version_number = Column(String, nullable=False)  # 语义化版本
    parent_version_id = Column(UUID, ForeignKey('content_versions.id'))
    branch_name = Column(String, default='main')
    
    # 版本类型
    version_type = Column(Enum('snapshot', 'delta'))
    
    # 存储位置
    storage_path = Column(String)  # MinIO路径或Delta ID
    
    # 元数据
    metadata = Column(JSON)  # 包含作者、描述、标签等
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(UUID, ForeignKey('users.id'))

class ContentDelta(Base):
    __tablename__ = 'content_deltas'
    
    id = Column(UUID, primary_key=True)
    version_id = Column(UUID, ForeignKey('content_versions.id'))
    
    # 差异数据
    delta_type = Column(Enum('addition', 'deletion', 'modification'))
    target_path = Column(String)  # 章节/段落路径
    delta_content = Column(JSON)  # 差异内容
    
    # 操作信息
    operation_timestamp = Column(DateTime)
    operation_metadata = Column(JSON)

class BranchInfo(Base):
    __tablename__ = 'branches'
    
    id = Column(UUID, primary_key=True)
    project_id = Column(UUID, ForeignKey('projects.id'))
    name = Column(String, unique=True)
    head_version_id = Column(UUID, ForeignKey('content_versions.id'))
    base_version_id = Column(UUID, ForeignKey('content_versions.id'))
    
    status = Column(Enum('active', 'merged', 'abandoned'))
    created_at = Column(DateTime)
    merged_at = Column(DateTime, nullable=True)
```

### Implementation Code
```python
# apps/backend/src/core/versioning/manager.py
from typing import Optional, List, Dict, Any
import diff_match_patch as dmp_module
from datetime import datetime
import json

class VersionManager:
    """内容版本管理器"""
    
    def __init__(
        self,
        db_session: AsyncSession,
        minio_client: MinioClient,
        redis_client: Redis
    ):
        self.db = db_session
        self.minio = minio_client
        self.cache = redis_client
        self.dmp = dmp_module.diff_match_patch()
    
    async def create_version(
        self,
        project_id: str,
        content: Dict[str, Any],
        branch: str = "main",
        message: str = "",
        create_snapshot: bool = False
    ) -> ContentVersion:
        """创建新版本"""
        
        # 获取当前HEAD版本
        current_head = await self._get_branch_head(project_id, branch)
        
        # 决定创建快照还是增量
        if create_snapshot or self._should_create_snapshot(current_head):
            return await self._create_snapshot(
                project_id, content, branch, message, current_head
            )
        else:
            return await self._create_delta(
                project_id, content, branch, message, current_head
            )
    
    def _should_create_snapshot(self, head: Optional[ContentVersion]) -> bool:
        """判断是否应该创建快照"""
        if not head:
            return True  # 首个版本必须是快照
        
        # 获取自上次快照以来的增量数
        delta_count = self._count_deltas_since_snapshot(head)
        
        # 策略：每10个增量创建一次快照
        return delta_count >= 10
    
    async def _create_snapshot(
        self,
        project_id: str,
        content: Dict[str, Any],
        branch: str,
        message: str,
        parent: Optional[ContentVersion]
    ) -> ContentVersion:
        """创建快照版本"""
        
        # 序列化内容
        content_json = json.dumps(content, ensure_ascii=False)
        
        # 上传到MinIO
        object_name = f"snapshots/{project_id}/{datetime.utcnow().isoformat()}.json"
        await self.minio.put_object(
            bucket_name="novel-versions",
            object_name=object_name,
            data=content_json.encode('utf-8')
        )
        
        # 创建版本记录
        version = ContentVersion(
            project_id=project_id,
            version_type="snapshot",
            storage_path=object_name,
            branch_name=branch,
            parent_version_id=parent.id if parent else None,
            metadata={"message": message}
        )
        
        self.db.add(version)
        await self.db.commit()
        
        # 更新分支HEAD
        await self._update_branch_head(project_id, branch, version.id)
        
        # 清理缓存
        await self.cache.delete(f"version:content:{project_id}:*")
        
        return version
    
    async def _create_delta(
        self,
        project_id: str,
        content: Dict[str, Any],
        branch: str,
        message: str,
        parent: ContentVersion
    ) -> ContentVersion:
        """创建增量版本"""
        
        # 获取父版本内容
        parent_content = await self.get_version_content(parent.id)
        
        # 计算差异
        deltas = self._calculate_deltas(parent_content, content)
        
        # 创建版本记录
        version = ContentVersion(
            project_id=project_id,
            version_type="delta",
            branch_name=branch,
            parent_version_id=parent.id,
            metadata={"message": message, "delta_count": len(deltas)}
        )
        
        self.db.add(version)
        await self.db.flush()
        
        # 存储差异
        for delta in deltas:
            delta_record = ContentDelta(
                version_id=version.id,
                delta_type=delta["type"],
                target_path=delta["path"],
                delta_content=delta["content"]
            )
            self.db.add(delta_record)
        
        await self.db.commit()
        
        # 更新分支HEAD
        await self._update_branch_head(project_id, branch, version.id)
        
        return version
    
    def _calculate_deltas(
        self,
        old_content: Dict[str, Any],
        new_content: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """计算内容差异"""
        deltas = []
        
        # 对每个章节计算差异
        for chapter_id in new_content.get("chapters", {}):
            old_chapter = old_content.get("chapters", {}).get(chapter_id, "")
            new_chapter = new_content["chapters"][chapter_id]
            
            if old_chapter != new_chapter:
                # 使用diff-match-patch计算文本差异
                diffs = self.dmp.diff_main(old_chapter, new_chapter)
                self.dmp.diff_cleanupSemantic(diffs)
                
                deltas.append({
                    "type": "modification",
                    "path": f"chapters/{chapter_id}",
                    "content": {
                        "diffs": diffs,
                        "patch": self.dmp.patch_make(old_chapter, diffs)
                    }
                })
        
        return deltas
    
    async def get_version_content(
        self,
        version_id: str,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """获取特定版本的完整内容"""
        
        # 尝试从缓存获取
        cache_key = f"version:content:{version_id}"
        if use_cache:
            if cached := await self.cache.get(cache_key):
                return json.loads(cached)
        
        # 获取版本信息
        version = await self.db.get(ContentVersion, version_id)
        
        if version.version_type == "snapshot":
            # 直接从MinIO读取
            content = await self._load_snapshot(version.storage_path)
        else:
            # 递归构建：获取父版本内容并应用增量
            parent_content = await self.get_version_content(
                version.parent_version_id
            )
            content = await self._apply_deltas(parent_content, version.id)
        
        # 缓存结果
        if use_cache:
            await self.cache.setex(
                cache_key,
                3600,  # 1小时
                json.dumps(content)
            )
        
        return content
    
    async def create_branch(
        self,
        project_id: str,
        branch_name: str,
        from_version_id: str
    ) -> BranchInfo:
        """创建分支"""
        
        branch = BranchInfo(
            project_id=project_id,
            name=branch_name,
            base_version_id=from_version_id,
            head_version_id=from_version_id,
            status="active"
        )
        
        self.db.add(branch)
        await self.db.commit()
        
        return branch
    
    async def merge_branches(
        self,
        project_id: str,
        source_branch: str,
        target_branch: str,
        strategy: str = "three_way"
    ) -> ContentVersion:
        """合并分支"""
        
        # 获取两个分支的HEAD
        source_head = await self._get_branch_head(project_id, source_branch)
        target_head = await self._get_branch_head(project_id, target_branch)
        
        # 找到共同祖先
        common_ancestor = await self._find_common_ancestor(
            source_head, target_head
        )
        
        # 获取三个版本的内容
        source_content = await self.get_version_content(source_head.id)
        target_content = await self.get_version_content(target_head.id)
        base_content = await self.get_version_content(common_ancestor.id)
        
        # 执行三路合并
        merged_content = await self._three_way_merge(
            base_content,
            source_content,
            target_content
        )
        
        # 创建合并版本
        merge_version = await self.create_version(
            project_id,
            merged_content,
            target_branch,
            f"Merge {source_branch} into {target_branch}",
            create_snapshot=True  # 合并总是创建快照
        )
        
        return merge_version
    
    async def _three_way_merge(
        self,
        base: Dict[str, Any],
        source: Dict[str, Any],
        target: Dict[str, Any]
    ) -> Dict[str, Any]:
        """三路合并算法"""
        merged = {}
        
        # 合并元数据
        merged["metadata"] = {**target.get("metadata", {}), 
                             **source.get("metadata", {})}
        
        # 合并章节
        merged["chapters"] = {}
        all_chapter_ids = set(
            list(base.get("chapters", {}).keys()) +
            list(source.get("chapters", {}).keys()) +
            list(target.get("chapters", {}).keys())
        )
        
        for chapter_id in all_chapter_ids:
            base_chapter = base.get("chapters", {}).get(chapter_id, "")
            source_chapter = source.get("chapters", {}).get(chapter_id, "")
            target_chapter = target.get("chapters", {}).get(chapter_id, "")
            
            # 如果只有一方修改，直接采用修改版本
            if source_chapter == base_chapter:
                merged["chapters"][chapter_id] = target_chapter
            elif target_chapter == base_chapter:
                merged["chapters"][chapter_id] = source_chapter
            else:
                # 两方都有修改，尝试自动合并
                # 这里可以使用更复杂的文本合并算法
                # 简单起见，标记冲突
                merged["chapters"][chapter_id] = (
                    f"<<<<<<< SOURCE\n{source_chapter}\n"
                    f"=======\n{target_chapter}\n>>>>>>> TARGET"
                )
        
        return merged
```

### Storage Optimization
```python
# 存储优化策略
class StorageOptimizer:
    """存储优化器"""
    
    async def compact_snapshots(self, project_id: str):
        """合并旧快照，减少存储"""
        # 保留策略：
        # - 最近7天：保留所有快照
        # - 7-30天：每天保留一个快照
        # - 30天以上：每周保留一个快照
        
        snapshots = await self._get_project_snapshots(project_id)
        to_delete = []
        
        for snapshot in snapshots:
            age = (datetime.utcnow() - snapshot.created_at).days
            
            if age > 30:
                # 只保留每周第一个
                week_num = snapshot.created_at.isocalendar()[1]
                if not self._is_first_of_week(snapshot, snapshots):
                    to_delete.append(snapshot)
            elif age > 7:
                # 只保留每天第一个
                if not self._is_first_of_day(snapshot, snapshots):
                    to_delete.append(snapshot)
        
        # 删除冗余快照
        for snapshot in to_delete:
            await self._convert_to_delta(snapshot)
    
    async def archive_old_versions(self, project_id: str):
        """归档旧版本到冷存储"""
        # 将30天以上的版本移到冷存储
        pass
```

### Rollback Plan
- **触发条件**：性能问题或实现复杂度过高
- **回滚步骤**：
  1. 停止创建增量版本
  2. 全部使用快照模式（Option 3）
  3. 逐步迁移历史数据
- **数据恢复**：快照包含完整数据，可随时恢复

## Validation

### Alignment with Existing Patterns
- **架构一致性检查**：符合事件驱动模式，版本变更触发事件
- **代码审查重点**：
  - 并发版本控制
  - 合并算法正确性
  - 存储路径管理

### Metrics
- **性能指标**：
  - 版本创建时间：P95 < 500ms
  - 版本读取时间：P95 < 200ms（缓存命中）
  - 分支创建时间：P95 < 100ms
  - 合并操作时间：P95 < 5秒
- **存储指标**：
  - 存储增长率：< 10% 每月
  - 压缩比：> 5:1（相比全量存储）

### Test Strategy
- **单元测试**：差异计算、合并算法
- **集成测试**：完整的版本创建和获取流程
- **性能测试**：大文本的版本操作
- **压力测试**：并发版本创建和合并
- **端到端测试**：分支创建、修改、合并全流程

## References
- [diff-match-patch](https://github.com/google/diff-match-patch)
- [Event Sourcing Pattern](https://martinfowler.com/eaaDev/EventSourcing.html)
- [Git内部原理](https://git-scm.com/book/en/v2/Git-Internals-Plumbing-and-Porcelain)

## Changelog
- 2025-09-04: 初始草稿创建