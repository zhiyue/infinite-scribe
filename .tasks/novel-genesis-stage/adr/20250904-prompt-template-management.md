---
id: ADR-003-prompt-template-management
title: 提示词模板管理方案
status: Proposed
date: 2025-09-04
decision_makers: [platform-arch, ai-lead]
related_requirements: [FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, NFR-005]
related_stories: [STORY-001, STORY-002, STORY-003, STORY-004, STORY-005, STORY-006]
supersedes: []
superseded_by: null
tags: [ai, prompts, versioning, template-management]
---

# 提示词模板管理方案

## Status
Proposed

## Context

### Business Context
基于PRD的对话式创作引擎需求，系统需要管理大量复杂的提示词模板：
- 相关用户故事：STORY-001至STORY-006（所有涉及AI生成的功能）
- 业务价值：高质量的提示词是AI生成内容质量的关键，直接影响用户满意度
- 业务约束：需要支持快速迭代和A/B测试，不停机更新模板

### Technical Context
基于现有架构：
- 当前架构：多Agent微服务架构，每个Agent有特定职责
- 现有技术栈：
  - LiteLLM作为统一的LLM调用层
  - FastAPI后端
  - PostgreSQL存储元数据
  - Redis缓存
- 现有约定：所有LLM调用通过LiteLLM代理
- 集成点：需要与所有Agent服务、工作流编排器集成

### Requirements Driving This Decision
- FR-001至FR-006: 每个功能都需要专门的提示词模板
- NFR-005: AI生成质量要求
  - 采纳率≥70%
  - 一致性≥90%
  - 创新度≥7/10
- 需要支持模板的版本管理、A/B测试、热更新

### Constraints
- 技术约束：提示词可能很长（数千tokens），需要高效管理
- 业务约束：需要非技术人员也能理解和调整模板
- 成本约束：避免重复的模板导致token浪费

## Decision Drivers
- **版本控制**：需要追踪模板变更历史
- **热更新**：支持不停机更新模板
- **A/B测试**：支持多版本并行测试
- **复用性**：模板组件的复用和组合
- **可维护性**：清晰的组织结构，便于管理

## Considered Options

### Option 1: 集中式模板仓库 + 版本化管理（推荐）
- **描述**：使用Git仓库管理模板文件，通过语义化版本控制，运行时从数据库/缓存加载
- **与现有架构的一致性**：高 - 符合GitOps理念
- **实现复杂度**：中
- **优点**：
  - 完整的版本历史和diff功能
  - 支持代码审查流程
  - 便于协作和回滚
  - 可以使用Jinja2等模板引擎
  - 与CI/CD集成容易
- **缺点**：
  - 需要构建加载和缓存机制
  - 热更新需要额外实现
- **风险**：模板同步延迟

### Option 2: 数据库存储 + Web管理界面
- **描述**：将模板存储在PostgreSQL，提供Web UI进行管理
- **与现有架构的一致性**：中 - 需要新增管理界面
- **实现复杂度**：高
- **优点**：
  - 实时更新，无需部署
  - 非技术人员友好
  - 容易实现A/B测试
- **缺点**：
  - 缺少版本控制的高级功能
  - 难以进行代码审查
  - 需要开发管理界面
- **风险**：误操作风险高，恢复困难

### Option 3: 硬编码在代码中
- **描述**：将提示词直接写在Agent代码中
- **与现有架构的一致性**：低 - 违反关注点分离原则
- **实现复杂度**：低
- **优点**：
  - 实现简单直接
  - 无额外基础设施
- **缺点**：
  - 更新需要重新部署
  - 难以管理和维护
  - 无法进行A/B测试
- **风险**：快速迭代困难，不适合生产环境

### Option 4: 配置中心服务
- **描述**：使用专门的配置中心（如Consul、Apollo）管理模板
- **与现有架构的一致性**：低 - 引入新的基础设施组件
- **实现复杂度**：中
- **优点**：
  - 成熟的配置管理功能
  - 支持热更新和灰度发布
  - 有审计日志
- **缺点**：
  - 增加系统复杂度
  - 需要学习新工具
  - MVP时间紧张
- **风险**：过度工程化

## Decision
建议采用 **Option 1: 集中式模板仓库 + 版本化管理**

理由：
1. 利用Git的强大版本管理能力
2. 符合团队现有的开发流程
3. 便于代码审查和协作
4. 实现复杂度适中，适合MVP
5. 未来可以逐步增加Web管理界面

## Consequences

### Positive
- 完整的变更历史和审计跟踪
- 支持多人协作和审查机制
- 便于回滚和问题排查
- 可以使用模板引擎实现复杂逻辑
- 与现有CI/CD流程无缝集成

### Negative
- 非技术人员需要学习Git基础
- 热更新需要额外的同步机制
- 初期需要建立模板规范和流程

### Risks
- **风险1：模板更新延迟**
  - 缓解：实现webhook自动同步，缓存失效机制
- **风险2：版本混乱**
  - 缓解：严格的版本命名规范，自动化测试

## Implementation Plan

### Integration with Existing Architecture（对齐当前代码库）
- **代码位置**：
  - 模板目录：`apps/backend/src/templates/prompts/`
  - 加载与渲染：`apps/backend/src/core/prompts/`
  - Agent 集成：各 Agent 在业务处理前通过 `PromptManager.render(...)` 获取提示词
- **配置（Settings）**：
  - `prompts_dir`: 默认 `"src/templates/prompts"`
  - `prompts_hot_reload`: 开发环境开启热更新（生产关闭）
  - `prompts_cache_ttl_seconds`: Redis 缓存 TTL（默认 3600）
- **缓存层**：复用现有异步 Redis 服务（`src/common/services/redis_service.py`）
- **模块边界**：
  - PromptManager: 统一模板索引/获取/渲染（异步，带强校验）
  - PromptLoader: 文件系统加载与版本索引（按目录版本化）
  - PromptCache: Redis 缓存封装（Key 规范与批量失效）
  - PromptRenderer: 基于 Jinja2 的严格渲染（StrictUndefined/Sandbox 可选）
- **依赖管理**：
  - `jinja2`（新增依赖，用于模板渲染）
  - `pyyaml`（已存在）
  - `watchdog`（开发依赖，热更新；生产不启用）
  - `GitPython`（可选，未来用于 Git 同步，非 MVP 必须）

### Template Structure
推荐采用“按目录版本化”的单一真相源（版本来源于文件路径，不再在 YAML 内重复 version；如保留需与路径一致）：

```
apps/backend/src/templates/prompts/
  stage0_creative_seed/
    1.0.0.yaml
    1.1.0.yaml
  stage1_theme/
    1.0.0.yaml
```

示例文件：`apps/backend/src/templates/prompts/stage0_creative_seed/1.0.0.yaml`

```yaml
metadata:
  author: "ai-team"
  tags: ["stage0", "creative_seed"]
  models: ["gpt-4o", "claude-3"]

variables:
  - name: genre
    type: string
    required: true
  - name: keywords
    type: list
    required: false
    default: []

template: |
  你是一位经验丰富的小说创意策划师。

  用户选择的类型：{{ genre }}
  {% if keywords %}
  关键词：{{ keywords | join(', ') }}
  {% endif %}

  请生成3-6个高概念（High Concept）创意，每个包含：
  1. 一句话钩子（15-30字）
  2. 独特卖点（50-100字）
  3. 可延展性分析

  输出格式：
  ```json
  {
    "concepts": [
      { "hook": "...", "usp": "...", "extensibility": "..." }
    ]
  }
  ```
```

组件与链式（第二阶段引入）：
- 组件：`apps/backend/src/templates/prompts/components/**`
- 链编排：`apps/backend/src/templates/prompts/chains/**`
- MVP 可先不启用链式，优先打通单模板渲染路径

### Implementation Code（对齐异步 Redis 与目录版本化）
```python
# apps/backend/src/core/prompts/manager.py（示例骨架）
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Literal
import hashlib
import yaml
import jinja2
from jinja2 import StrictUndefined, FileSystemLoader
from pydantic import BaseModel, Field

from src.core.config import settings
from src.common.services.redis_service import redis_service

VariableType = Literal["string", "list", "enum", "number", "boolean", "object"]

class VariableSpec(BaseModel):
    name: str
    type: VariableType = "string"
    required: bool = False
    default: Any | None = None
    enum: List[str] | None = None

class TemplateMeta(BaseModel):
    author: str = "ai-team"
    tags: List[str] = Field(default_factory=list)
    models: List[str] = Field(default_factory=list)

class PromptTemplate(BaseModel):
    metadata: TemplateMeta
    variables: List[VariableSpec]
    template: str

class PromptManager:
    def __init__(self, templates_dir: Path | None = None, cache_ttl: int | None = None) -> None:
        self.templates_dir = Path(templates_dir) if templates_dir else Path(settings.prompts_dir)
        self.cache_ttl = cache_ttl or getattr(settings, "prompts_cache_ttl_seconds", 3600)
        self.jinja_env = jinja2.Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            undefined=StrictUndefined,
            autoescape=False,
        )
        # (template_id, version) -> PromptTemplate
        self.index: dict[tuple[str, str], PromptTemplate] = {}

    async def load_all(self) -> None:
        """加载并索引所有模板（按目录版本化：{id}/{version}.yaml）。"""
        self.index.clear()
        for file in self.templates_dir.glob("**/*.yaml"):
            # 期望路径：.../prompts/{template_id}/{version}.yaml
            try:
                version = file.stem
                template_id = file.parent.name
                with file.open("r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                tmpl = PromptTemplate(**data)
                self.index[(template_id, version)] = tmpl
            except Exception as e:
                # 记录日志/统计（省略）
                pass

    def _default_version(self, template_id: str) -> str:
        """选择该模板的默认版本（语义化排序可后续引入）。"""
        versions = [v for (tid, v) in self.index.keys() if tid == template_id]
        if not versions:
            raise ValueError(f"Template {template_id} not found")
        # 简单按字符串逆序选择“最新”；后续可替换为 packaging.version 语义排序
        return sorted(versions)[-1]

    async def get_template(self, template_id: str, version: str | None = None) -> PromptTemplate:
        ver = version or self._default_version(template_id)
        cache_key = f"prompt:template:{template_id}:{ver}"
        async with redis_service.acquire() as r:
            cached = await r.get(cache_key)
            if cached:
                try:
                    # 命中缓存时应反序列化为模型（此处示意略过具体实现）
                    pass
                except Exception:
                    cached = None
            # 内存回退
            tmpl = self.index.get((template_id, ver))
            if not tmpl:
                raise ValueError(f"Template {template_id}:{ver} not found")
            # 写入缓存（建议 JSON 序列化，此处简化）
            await r.setex(cache_key, self.cache_ttl, "1")
            return tmpl

    def _validate_variables(self, tmpl: PromptTemplate, variables: dict[str, Any]) -> None:
        specs = {v.name: v for v in tmpl.variables}
        # 必填校验
        missing = [name for name, spec in specs.items() if spec.required and name not in variables]
        if missing:
            raise ValueError(f"Missing required variables: {missing}")
        # 类型/枚举校验（简化示例）
        for name, value in variables.items():
            spec = specs.get(name)
            if not spec:
                continue
            if spec.enum and value not in spec.enum:
                raise ValueError(f"Variable {name} must be one of {spec.enum}")

    async def render(self, template_id: str, variables: dict[str, Any], version: str | None = None) -> str:
        tmpl = await self.get_template(template_id, version)
        self._validate_variables(tmpl, variables)
        jinja_tmpl = self.jinja_env.from_string(tmpl.template)
        return jinja_tmpl.render(**variables)

    def get_ab_variant(self, template_id: str, user_id: str, variants: list[tuple[str, float]]) -> str:
        """加权 A/B 版本分配（权重和为 1.0）。"""
        seed = int(hashlib.md5(f"{user_id}:{template_id}".encode()).hexdigest(), 16) / (2**128)
        acc = 0.0
        for ver, w in variants:
            acc += w
            if seed <= acc:
                return ver
        return variants[-1][0]

    async def invalidate_cache(self, template_id: str | None = None) -> None:
        """按前缀模式失效缓存，使用 scan_iter 实现。"""
        prefix = "prompt:template:" if template_id is None else f"prompt:template:{template_id}:"
        async with redis_service.acquire() as r:
            async for key in r.scan_iter(match=f"{prefix}*"):
                await r.delete(key)

# 使用示例（异步环境）：
# pm = PromptManager()
# await pm.load_all()
# prompt = await pm.render("stage0_creative_seed", {"genre": "东方玄幻", "keywords": ["修仙", "系统"]})
```

### Migration Strategy
- **阶段1（Day 1）**：创建目录 `apps/backend/src/templates/prompts/` 与 1 个示例模板；在 `Settings` 增加 `prompts_*` 配置；声明 `jinja2` 依赖
- **阶段2（Day 1-2）**：实现 `PromptManager`（异步 Redis、按路径版本化、变量强校验、渲染）
- **阶段3（Day 2）**：将 `WriterAgent` 接入模板渲染路径，打通端到端
- **阶段4（Day 2-3）**：引入链式/组件（可选）、A/B 加权分流、开发态热更新
- **向后兼容**：保留硬编码提示词作为 fallback

### Hot Reload Implementation
开发环境启用；生产通过滚动发布与版本切换实现热更新。

```python
# 仅开发环境启用文件监听（简化示例，生产禁用）
import asyncio
import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class PromptReloadHandler(FileSystemEventHandler):
    def __init__(self, pm: PromptManager, loop: asyncio.AbstractEventLoop):
        self.pm = pm
        self.loop = loop

    def on_modified(self, event):
        if event.src_path.endswith(".yaml"):
            # 在线程安全的方式调度协程
            self.loop.call_soon_threadsafe(lambda: asyncio.create_task(self._reload()))

    async def _reload(self):
        await self.pm.load_all()
        await self.pm.invalidate_cache()

def start_hot_reload(pm: PromptManager):
    if not getattr(settings, "prompts_hot_reload", False):
        return
    loop = asyncio.get_event_loop()
    handler = PromptReloadHandler(pm, loop)
    observer = Observer()
    observer.schedule(handler, path=str(pm.templates_dir), recursive=True)
    t = threading.Thread(target=observer.start, daemon=True)
    t.start()
```

### Rollback Plan
- **触发条件**：模板管理过于复杂或性能问题
- **回滚步骤**：
  1. 停止使用PromptManager
  2. 回退到硬编码模板（保留作为常量）
  3. 逐步迁移到数据库方案（Option 2）
- **数据恢复**：Git历史保留所有模板版本

## Validation

### Alignment with Existing Patterns
- **架构一致性检查**：符合配置与代码分离原则；异步 Redis 与现有 `RedisService` 保持一致
- **代码审查重点**：
  - 目录版本化与默认版本选择逻辑
  - 变量强类型与必填/枚举校验
  - 渲染安全性（StrictUndefined/Sandbox）
  - Redis 缓存键设计与模式删除（scan_iter）
  - 开发态热更新仅在 dev 生效

### Metrics
- **性能指标**：
  - 模板加载时间：P95 < 10ms（缓存命中）
  - 模板渲染时间：P95 < 5ms
  - 缓存命中率：> 95%
- **质量指标**：
  - 模板语法错误率：< 1%
  - A/B测试覆盖率：> 50%

### Test Strategy
- **单元测试**：
  - 加载与索引（路径解析：id/version）
  - 变量强校验（缺失/类型/枚举）与默认值
  - 渲染成功/失败与错误信息
  - Redis 缓存命中/失效与模式删除
- **集成测试**：与 `WriterAgent` 的端到端渲染接入
- **模板测试**：CI 中对全部模板做语法与“干跑”渲染校验
- **A/B 测试**：分配稳定性（同 user_id 稳定）、加权分布近似性
- **性能测试**：并发渲染 P95 与缓存命中率

## References
- [Jinja2文档](https://jinja.palletsprojects.com/)
- [提示词工程最佳实践](https://platform.openai.com/docs/guides/prompt-engineering)
- [LiteLLM文档](https://docs.litellm.ai/)

## Changelog
- 2025-09-04: 初始草稿创建
- 2025-09-04: 修订以对齐现有代码库（目录版本化、异步 Redis、依赖与热更新方式、变量强校验、缓存失效策略）
