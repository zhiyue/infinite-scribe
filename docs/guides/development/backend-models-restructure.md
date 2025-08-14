# 后端模型架构重构总结

## 重构概述

本次重构实现了后端模型的清晰层次分离，遵循清洁架构原则，将 Pydantic DTOs、SQLAlchemy ORM 模型和数据库基础设施完全分离。

## 架构变更

### 1. 创建独立的数据库基础设施层 (db/)

```
src/db/
├── __init__.py         # 统一数据层接口
├── sql/                # PostgreSQL 基础设施
│   ├── base.py        # DeclarativeBase 和 metadata
│   ├── engine.py      # 引擎创建和配置
│   └── session.py     # 会话管理
├── graph/             # Neo4j 基础设施
│   ├── driver.py      # 驱动创建和管理
│   └── session.py     # 会话管理
└── vector/            # 向量数据库（预留）
    └── __init__.py
```

### 2. 重组 SQLAlchemy ORM 模型 (models/)

将原来的巨大 `orm_models.py` 文件拆分为多个领域模块：

```
src/models/
├── base.py          # 基础模型类（认证相关）
├── user.py          # 用户认证模型
├── session.py       # 会话管理模型
├── email_verification.py # 邮箱验证模型
├── novel.py         # 小说领域模型
├── chapter.py       # 章节相关模型（Chapter, ChapterVersion, Review）
├── character.py     # 角色模型
├── worldview.py     # 世界观模型（WorldviewEntry, StoryArc）
├── genesis.py       # 创世流程模型（GenesisSession, ConceptTemplate）
├── event.py         # 领域事件模型
└── workflow.py      # 工作流模型（CommandInbox, AsyncTask, EventOutbox, FlowResumeHandle）
```

### 3. 实现 CQRS 模式的 Pydantic DTOs (schemas/)

所有 API 数据传输对象迁移到独立的 schemas 目录，实现 Create/Update/Read 分离：

```
src/schemas/
├── base.py          # 基础 Pydantic 模型类
├── enums.py         # 共享的枚举类型
├── events.py        # 事件系统模型
├── sse.py           # SSE 推送事件模型
├── domain_event.py  # 领域事件 DTOs
├── novel/           # 小说相关 schemas
│   ├── create.py    # NovelCreateRequest
│   ├── update.py    # NovelUpdateRequest
│   └── read.py      # NovelResponse
├── chapter/         # 章节相关 schemas（同样的 CQRS 结构）
├── character/       # 角色相关 schemas
├── worldview/       # 世界观相关 schemas
├── genesis/         # 创世相关 schemas
└── workflow/        # 工作流相关 schemas
```

## 设计原则

### 1. 职责单一原则
- **db/**: 仅负责数据库连接和会话管理
- **models/**: 仅包含 SQLAlchemy ORM 定义
- **schemas/**: 仅包含 Pydantic DTOs 用于 API 层

### 2. 依赖方向
```
API Routes → Schemas (DTOs) → Services → Models (ORM) → DB Infrastructure
```

### 3. CQRS 模式
每个领域都有独立的：
- **CreateRequest**: 创建操作的请求 DTO
- **UpdateRequest**: 更新操作的请求 DTO（所有字段可选）
- **Response**: 查询操作的响应 DTO

### 4. 领域驱动设计
- 按业务领域组织代码（novel、chapter、character 等）
- 每个领域有清晰的边界和职责
- 便于独立开发和测试

## 主要改进

1. **解决循环依赖**: 分离 ORM 和 DTO 避免了循环导入问题
2. **提高可测试性**: 每层都可以独立 mock 和测试
3. **支持多数据库**: 统一的 db 层支持 SQL、Graph、Vector 数据库
4. **更好的类型安全**: 明确的 DTO 类型定义提供更好的 IDE 支持
5. **灵活的数据验证**: Pydantic 模型提供强大的验证能力

## 使用示例

### API 路由中使用
```python
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.sql.session import get_sql_session
from src.schemas.novel import NovelCreateRequest, NovelResponse
from src.models import Novel

@router.post("/novels", response_model=NovelResponse)
async def create_novel(
    novel_data: NovelCreateRequest,
    db: AsyncSession = Depends(get_sql_session)
):
    # 使用 schema 验证输入，使用 ORM 操作数据库
    novel = Novel(**novel_data.model_dump())
    db.add(novel)
    await db.commit()
    return NovelResponse.model_validate(novel)
```

### Service 层使用
```python
from src.db.sql.session import create_sql_session
from src.models import Novel
from src.schemas.novel import NovelCreateRequest

async def create_novel_service(data: NovelCreateRequest) -> Novel:
    async with create_sql_session() as session:
        novel = Novel(**data.model_dump())
        session.add(novel)
        # 自动提交或回滚
    return novel
```

## 向后兼容性

- `database.py` 保留为兼容层，支持旧代码逐步迁移
- 所有导入路径都已更新，确保现有功能正常工作
- 保留了认证相关的模型结构不变

## 后续建议

1. 在 Service 层明确使用 schemas 作为输入，ORM 模型作为内部处理
2. 为每个领域创建独立的 Repository 层封装数据访问
3. 考虑添加 Mapper 层处理 DTO 和 ORM 模型之间的转换
4. 为复杂查询创建专门的 Query DTOs

## 文件变更摘要

- **删除**: `models/api.py`, `models/db.py`, `models/orm_models.py`
- **移动**: `models/events.py` → `schemas/events.py`, `models/sse.py` → `schemas/sse.py`
- **新增**: 整个 `db/` 目录，整个 `schemas/` 目录的 CQRS 结构
- **更新**: 所有相关的导入路径