# 模型和数据库基础设施重构总结

## 完成的重构

### 1. 创建 schemas 目录结构
```
src/schemas/
├── __init__.py
├── base.py          # 基础 Pydantic 模型类
├── enums.py         # 共享的枚举类型
├── events.py        # 领域事件模型（从 models 迁移）
├── sse.py           # SSE 事件模型（从 models 迁移）
└── novel/           # 小说相关的 schemas
    ├── __init__.py
    ├── create.py    # 创建请求 DTO
    ├── update.py    # 更新请求 DTO
    └── read.py      # 查询响应 DTO
```

### 2. 拆分 orm_models.py
原来的单一文件被拆分为多个领域模块：

```
src/models/
├── novel.py         # Novel ORM 模型
├── chapter.py       # Chapter, ChapterVersion, Review ORM 模型
├── character.py     # Character ORM 模型
├── worldview.py     # WorldviewEntry, StoryArc ORM 模型
├── genesis.py       # GenesisSession, ConceptTemplate ORM 模型
├── event.py         # DomainEvent ORM 模型
└── workflow.py      # CommandInbox, AsyncTask, EventOutbox, FlowResumeHandle ORM 模型
```

### 3. 创建 db 基础设施层
将数据库相关的基础设施代码从 models 迁移到独立的 db 模块：

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

### 4. 完成所有 Pydantic 模型迁移
将 models/db.py 中的所有 Pydantic 模型迁移到 schemas 目录，并实现 Create/Update/Read 分离：

```
src/schemas/
├── base.py             # BaseSchema, TimestampMixin, BaseDBModel
├── enums.py            # 所有共享的枚举类型
├── chapter/            # 章节相关 schemas
│   ├── create.py      # ChapterCreateRequest, ChapterVersionCreate, ReviewCreate
│   ├── update.py      # ChapterUpdateRequest, ChapterVersionUpdate, ReviewUpdate
│   └── read.py        # ChapterResponse, ChapterVersionResponse, ReviewResponse
├── character/          # 角色相关 schemas
│   ├── create.py      # CharacterCreateRequest
│   ├── update.py      # CharacterUpdateRequest
│   └── read.py        # CharacterResponse
├── worldview/          # 世界观相关 schemas
│   ├── create.py      # WorldviewEntryCreateRequest, StoryArcCreateRequest
│   ├── update.py      # WorldviewEntryUpdateRequest, StoryArcUpdateRequest
│   └── read.py        # WorldviewEntryResponse, StoryArcResponse
├── genesis/            # 创世流程相关 schemas
│   ├── create.py      # ConceptTemplateCreateRequest, GenesisSessionCreateRequest
│   ├── update.py      # ConceptTemplateUpdateRequest, GenesisSessionUpdateRequest
│   └── read.py        # ConceptTemplateResponse, GenesisSessionResponse
├── workflow/           # 工作流相关 schemas
│   ├── create.py      # CommandInboxCreate, AsyncTaskCreate, EventOutboxCreate, FlowResumeHandleCreate
│   ├── update.py      # CommandInboxUpdate, AsyncTaskUpdate, EventOutboxUpdate, FlowResumeHandleUpdate
│   └── read.py        # CommandInboxResponse, AsyncTaskResponse, EventOutboxResponse, FlowResumeHandleResponse
└── domain_event.py     # DomainEventCreate, DomainEventResponse
```

### 5. 保持的文件
- `user.py`, `session.py`, `email_verification.py` - 认证相关的 ORM 模型
- `models/base.py` - 保留 BaseModel 类（用于认证模型）
- `database.py` - 改为兼容层，向后兼容旧代码
- ~~`models/db.py` - 暂时保留以保持向后兼容性~~ 已删除

## 架构改进

### 符合的设计原则
1. **职责单一**: 每个模块只负责一个领域
   - db/ - 数据访问基础设施
   - models/ - ORM 模型定义
   - schemas/ - API 数据传输对象
   
2. **依赖单向**: API → Service → Repo → DB/ORM
   - API 层使用 schemas（Pydantic）
   - Repository 层使用 models（SQLAlchemy）
   - 基础设施层（db）被 Repository 使用

3. **DTO 精准匹配用例**: Create/Update/Read 分离
   - NovelCreateRequest / NovelUpdateRequest / NovelResponse
   
4. **可测试性优先**: 每层都可以独立 mock/stub
   - 数据库连接可以独立配置
   - 会话管理支持依赖注入

### 文件组织
- 数据库基础设施在 `db/` 目录
- SQLAlchemy ORM 模型在 `models/` 目录
- Pydantic DTO 模型在 `schemas/` 目录
- 支持多种数据存储（SQL、Graph、Vector）

## 后续建议

1. ~~**完成 schemas 迁移**: 将 `db.py` 中剩余的 Pydantic 模型迁移到相应的 schemas 子模块~~ ✅ 已完成
2. ~~**创建更多领域 schemas**: 为 chapter, character, worldview, genesis 创建对应的 Create/Update/Read schemas~~ ✅ 已完成
3. ~~**更新导入路径**: 将所有使用 `from src.models.db import ...` 的代码更新为 `from src.schemas import ...`~~ ✅ 已完成
4. ~~**删除 db.py**: 完成迁移后删除 `models/db.py` 文件~~ ✅ 已完成
5. **添加类型提示**: 在 Service 和 Repository 层明确使用 schemas 和 ORM 模型的类型提示

## 使用示例

### 在 API 路由中使用
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

### 在 Service 层使用
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

## 测试验证
- ✅ 所有 ORM 模型导入正常
- ✅ 所有 schemas 导入正常
- ✅ 模型关系定义正确
- ✅ 无循环依赖问题
- ✅ 数据库基础设施层工作正常
- ✅ 向后兼容性保持完整

## 完成情况总结

### 已完成的重构任务
1. **分离 Pydantic 和 SQLAlchemy**：
   - SQLAlchemy ORM 模型保留在 `models/` 目录
   - Pydantic DTO 模型迁移到 `schemas/` 目录
   - 删除了混合定义的 `models/db.py` 文件

2. **实现 CQRS 模式**：
   - 每个领域都有独立的 Create/Update/Read DTO
   - Update DTO 所有字段可选，并验证至少有一个字段
   - Response DTO 包含完整的业务数据

3. **基础设施层分离**：
   - 创建独立的 `db/` 目录管理数据库连接
   - 支持多种数据存储（SQL、Graph、Vector）
   - 清晰的层次结构和依赖关系

4. **领域驱动设计**：
   - 按业务领域组织代码（novel、chapter、character 等）
   - 每个领域有清晰的边界和职责
   - 便于独立开发和测试

### 架构优势
- **清晰的职责分离**：API 层使用 schemas，数据层使用 ORM models
- **灵活的 DTO 设计**：Create/Update/Read 分离，精准匹配用例
- **良好的可扩展性**：易于添加新的领域和数据存储类型
- **高可测试性**：每层都可以独立 mock 和测试