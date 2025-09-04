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

### Integration with Existing Architecture
- **代码位置**：
  - 模板仓库：`prompts/` 目录在项目根目录
  - 加载器：`apps/backend/src/core/prompts/`
  - 缓存层：利用现有Redis基础设施
- **模块边界**：
  - PromptManager: 统一的模板管理接口
  - PromptLoader: 从文件系统/Git加载模板
  - PromptCache: Redis缓存实现
  - PromptRenderer: 模板渲染引擎
- **依赖管理**：
  - Jinja2用于模板渲染
  - GitPython用于Git操作（可选）

### Template Structure
```yaml
# prompts/templates/stage0_creative_seed.yaml
metadata:
  version: "1.0.0"
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
      {
        "hook": "...",
        "usp": "...",
        "extensibility": "..."
      }
    ]
  }
  ```

# prompts/components/common/output_format.yaml
json_format: |
  请以JSON格式输出，确保可以被json.loads()解析

markdown_format: |
  请以Markdown格式输出，使用适当的标题和列表

# prompts/chains/stage1_theme.yaml
chain:
  - component: common/role_definition
    params:
      role: "主题设计师"
  - component: stage1/theme_analysis
  - component: common/output_format
    params:
      format: "json"
```

### Implementation Code
```python
# apps/backend/src/core/prompts/manager.py
from pathlib import Path
from typing import Dict, Any, Optional
import yaml
import jinja2
from pydantic import BaseModel
from functools import lru_cache
import hashlib

class PromptTemplate(BaseModel):
    """提示词模板模型"""
    metadata: Dict[str, Any]
    variables: List[Dict[str, Any]]
    template: str
    version: str
    
class PromptManager:
    """提示词管理器"""
    
    def __init__(self, templates_dir: Path, cache_client: Optional[Redis] = None):
        self.templates_dir = templates_dir
        self.cache = cache_client
        self.jinja_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(templates_dir),
            undefined=jinja2.StrictUndefined
        )
        self._load_templates()
    
    def _load_templates(self):
        """加载所有模板到内存"""
        self.templates = {}
        for template_file in self.templates_dir.glob("**/*.yaml"):
            relative_path = template_file.relative_to(self.templates_dir)
            template_id = str(relative_path).replace(".yaml", "")
            
            with open(template_file) as f:
                data = yaml.safe_load(f)
                self.templates[template_id] = PromptTemplate(**data)
    
    @lru_cache(maxsize=128)
    def get_template(
        self, 
        template_id: str, 
        version: Optional[str] = None
    ) -> PromptTemplate:
        """获取模板，支持版本指定"""
        cache_key = f"prompt:{template_id}:{version or 'latest'}"
        
        # 尝试从缓存获取
        if self.cache:
            if cached := self.cache.get(cache_key):
                return PromptTemplate.parse_raw(cached)
        
        # 从内存获取
        template = self.templates.get(template_id)
        if not template:
            raise ValueError(f"Template {template_id} not found")
        
        # 缓存结果
        if self.cache:
            self.cache.setex(
                cache_key, 
                3600,  # 1小时过期
                template.json()
            )
        
        return template
    
    def render(
        self,
        template_id: str,
        variables: Dict[str, Any],
        version: Optional[str] = None
    ) -> str:
        """渲染模板"""
        template = self.get_template(template_id, version)
        
        # 验证必需变量
        required_vars = {
            v['name'] for v in template.variables 
            if v.get('required', False)
        }
        missing_vars = required_vars - set(variables.keys())
        if missing_vars:
            raise ValueError(f"Missing required variables: {missing_vars}")
        
        # 渲染模板
        jinja_template = self.jinja_env.from_string(template.template)
        return jinja_template.render(**variables)
    
    def get_ab_variant(
        self,
        template_id: str,
        user_id: str,
        variants: List[str] = ["v1", "v2"]
    ) -> str:
        """A/B测试变体选择"""
        # 基于用户ID的确定性哈希
        hash_val = int(hashlib.md5(
            f"{user_id}:{template_id}".encode()
        ).hexdigest(), 16)
        
        # 选择变体
        variant_idx = hash_val % len(variants)
        return variants[variant_idx]

# 使用示例
prompt_manager = PromptManager(Path("prompts/templates"))

# 渲染创意种子提示词
prompt = prompt_manager.render(
    "stage0_creative_seed",
    variables={
        "genre": "东方玄幻",
        "keywords": ["修仙", "系统", "重生"]
    }
)

# A/B测试
variant = prompt_manager.get_ab_variant(
    "stage1_theme",
    user_id="user123",
    variants=["v1.0.0", "v1.1.0"]
)
prompt = prompt_manager.render("stage1_theme", variables, version=variant)
```

### Migration Strategy
- **阶段1**：创建模板目录结构和基础模板（Day 1）
- **阶段2**：实现PromptManager和缓存机制（Day 1-2）
- **阶段3**：迁移现有提示词到模板系统（Day 2）
- **阶段4**：集成到Agent服务（Day 2-3）
- **向后兼容**：保留硬编码作为fallback

### Hot Reload Implementation
```python
# 文件监听和热更新
import watchdog
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class PromptReloadHandler(FileSystemEventHandler):
    def __init__(self, prompt_manager: PromptManager):
        self.prompt_manager = prompt_manager
    
    def on_modified(self, event):
        if event.src_path.endswith('.yaml'):
            logger.info(f"Reloading template: {event.src_path}")
            self.prompt_manager._load_templates()
            # 清理缓存
            if self.prompt_manager.cache:
                self.prompt_manager.cache.delete_pattern("prompt:*")

# 启动文件监听
observer = Observer()
observer.schedule(
    PromptReloadHandler(prompt_manager),
    path="prompts/templates",
    recursive=True
)
observer.start()
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
- **架构一致性检查**：符合配置与代码分离原则
- **代码审查重点**：
  - 模板语法正确性
  - 变量验证逻辑
  - 缓存失效策略

### Metrics
- **性能指标**：
  - 模板加载时间：P95 < 10ms（缓存命中）
  - 模板渲染时间：P95 < 5ms
  - 缓存命中率：> 95%
- **质量指标**：
  - 模板语法错误率：< 1%
  - A/B测试覆盖率：> 50%

### Test Strategy
- **单元测试**：模板加载、渲染、缓存逻辑
- **集成测试**：与Agent服务的集成
- **模板测试**：自动化验证模板语法和输出格式
- **A/B测试**：验证变体分配的确定性和均匀性
- **性能测试**：大量并发模板渲染

## References
- [Jinja2文档](https://jinja.palletsprojects.com/)
- [提示词工程最佳实践](https://platform.openai.com/docs/guides/prompt-engineering)
- [LiteLLM文档](https://docs.litellm.ai/)

## Changelog
- 2025-09-04: 初始草稿创建