# Infinite Scribe Backend

统一的后端服务，包含 API Gateway 和所有 Agent 服务。

## 结构

```
backend/
├── src/
│   ├── api/            # API Gateway 模块
│   ├── agents/         # 所有 Agent 服务
│   ├── core/           # 核心配置和共享功能
│   ├── common/         # 共享业务逻辑
│   ├── models/         # 数据模型（ORM、Pydantic）
│   └── middleware/     # 中间件（认证、CORS、限流）
├── alembic/            # 数据库迁移
├── scripts/            # 管理脚本
├── tests/              # 测试文件
├── pyproject.toml      # 依赖配置
└── Dockerfile          # 统一部署文件
```

## 本地开发

### 安装依赖

```bash
# 使用 uv 安装依赖（推荐）
uv sync --all-extras

# 或使用 pip
pip install -e .
```

### 数据库设置

项目使用 PostgreSQL 作为主数据库，需要先设置数据库：

```bash
# 1. 生成数据库迁移（如果模型有更新）
cd apps/backend
alembic revision --autogenerate -m "描述你的更改"

# 2. 应用数据库迁移
alembic upgrade head

# 3. 应用数据库触发器和函数
python scripts/apply_db_functions.py

# 4. 验证数据库设置
python scripts/verify_tables.py
```

#### 数据库架构

数据库包含 17 个表，分为四大类：

- **核心业务表**（7个）
  - `novels` - 小说表，存储小说项目的核心元数据
  - `chapters` - 章节元数据表，与版本内容分离
  - `chapter_versions` - 章节版本表，支持版本控制
  - `characters` - 角色表，存储角色信息
  - `worldview_entries` - 世界观条目表，存储设定条目
  - `story_arcs` - 故事弧表，组织章节的叙事结构
  - `reviews` - 评审表，存储 AI 智能体的评审记录

- **创世流程表**（2个）
  - `genesis_sessions` - 创世会话表，流程状态管理
  - `concept_templates` - 立意模板表，预设创作主题

- **架构机制表**（5个）
  - `domain_events` - 领域事件表，支持事件源架构
  - `command_inbox` - 命令收件箱表，CQRS 命令侧
  - `async_tasks` - 异步任务表，任务执行跟踪
  - `event_outbox` - 事件发件箱表，事务性消息发送
  - `flow_resume_handles` - 工作流恢复句柄表

- **用户认证表**（3个）
  - `users` - 用户表，存储用户基本信息
  - `sessions` - 会话表，管理用户登录状态
  - `email_verifications` - 邮箱验证表

#### 数据库特性

- **触发器和函数**：自动更新时间戳、版本控制、事件保护
- **枚举类型**：11 个枚举类型，确保数据一致性
- **索引优化**：56 个索引，优化查询性能
- **外键约束**：完整的引用完整性
- **JSONB 字段**：灵活存储半结构化数据

### 运行服务

```bash
# 运行 API Gateway
cd apps/backend
uvicorn src.main:app --reload

# 运行 Agent 服务
python -m src.agents.worldsmith.main
python -m src.agents.plotmaster.main
```

## Docker 部署

```bash
# 构建镜像
docker build -t infinite-scribe-backend .

# 运行不同服务
docker run -e SERVICE_TYPE=api-gateway infinite-scribe-backend
docker run -e SERVICE_TYPE=agent-worldsmith infinite-scribe-backend
```

## 环境变量

通过 `SERVICE_TYPE` 环境变量选择要运行的服务：
- `api-gateway`: API Gateway 服务
- `agent-worldsmith`: 世界铸造师 Agent
- `agent-plotmaster`: 剧情策划师 Agent
- 其他 agent 服务...

## 添加新的 Agent

1. 在 `src/agents/` 下创建新目录
2. 创建 `main.py` 文件作为入口
3. 在 `pyproject.toml` 中添加入口点
4. 在 `Dockerfile` 中添加对应的启动命令

# Backend API服务

## 概述

这是Infinite Scribe项目的后端API服务，基于FastAPI构建。

## 配置管理

### 项目根目录检测

配置模块使用智能的项目根目录检测机制，而不是脆弱的多级parent调用：

```python
# ❌ 旧的脆弱实现
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent

# ✅ 新的健壮实现
PROJECT_ROOT = get_project_root()  # 通过标记文件自动检测
```

检测逻辑：
1. **强标记文件优先**: 寻找 `pyproject.toml`, `.git`, `package.json`, `docker-compose.yml`, `pnpm-workspace.yaml`
2. **弱标记文件备选**: 如果找不到强标记文件，寻找 `README.md`, `Makefile`
3. **环境变量备选**: 使用 `PROJECT_ROOT` 环境变量
4. **固定路径兜底**: 最后使用计算的相对路径

### 优势

- **健壮性**: 不依赖特定的文件结构层级
- **可维护性**: 文件移动不会破坏配置
- **可测试性**: 容易模拟不同的环境
- **可读性**: 清晰表达项目根目录查找逻辑

## 数据库管理脚本

项目提供了多个实用的数据库管理脚本：

- **apply_db_functions.py** - 应用数据库触发器和函数
- **verify_tables.py** - 验证所有表是否成功创建


## 测试

运行测试：

```bash
# 运行所有测试
./scripts/run-tests.sh --all --docker-host

# 仅运行单元测试
./scripts/run-tests.sh --unit --docker-host

# 仅运行集成测试
./scripts/run-tests.sh --integration --docker-host

# 运行特定测试文件
uv run pytest apps/backend/tests/test_config.py -v
```

## 开发

确保安装开发依赖：

```bash
uv sync --group dev
```

### 关于数据库字段注释

在 ORM 模型中，我们使用了两种注释方式：

1. **Python 行内注释**（用于代码可读性）
   ```python
   title = Column(String(255), nullable=False)  # 小说标题
   ```

2. **SQLAlchemy comment 参数**（会传递到数据库）
   ```python
   title = Column(String(255), nullable=False, comment="小说标题")
   ```

只有第二种方式的注释会出现在数据库和 Alembic migration 中。如果需要将所有注释同步到数据库，可以参考：

```bash
# 注释转换脚本已移除
```

然后重新生成 migration。