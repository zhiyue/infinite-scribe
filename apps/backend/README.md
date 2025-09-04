# Infinite Scribe Backend

统一的后端服务，包含 API Gateway 和所有 Agent 服务。基于 FastAPI 构建，使用 PostgreSQL、Redis、Neo4j 等数据库。

## 🚀 第一次开发设置流程

### 前置条件

1. **Python 3.11+** 已安装
2. **uv** 包管理器已安装 (`pip install uv`)
3. **基础设施服务** 已运行（PostgreSQL、Redis、Neo4j 等）

### 步骤 1: 启动基础设施服务

从项目根目录运行：

```bash
# 启动所有基础设施服务（PostgreSQL、Redis、Neo4j、MinIO等）
pnpm infra up

# 验证服务状态
pnpm check:services
```

服务端点：
- PostgreSQL: `localhost:5432` (postgres/postgres)
- Redis: `localhost:6379`
- Neo4j: `http://localhost:7474` (neo4j/password)
- MinIO: `http://localhost:9001` (admin/password)

### 步骤 2: 安装 Backend 依赖

```bash
cd apps/backend

# 安装所有依赖（包括开发依赖）
uv sync --all-extras --group dev

# 验证安装
uv run python --version
uv run python -c "import fastapi; print('FastAPI installed successfully')"
```

### 步骤 3: 数据库初始化

```bash
# 运行数据库迁移（创建所有表和结构）
uv run alembic upgrade head

# 应用数据库触发器和函数
uv run python scripts/apply_db_functions.py

# 验证数据库设置
uv run python scripts/verify_tables.py

# 可选：一键初始化全部数据存储（PostgreSQL/Neo4j/Milvus/Redis）
uv run is-db-bootstrap
```

**预期输出**：
- 18 个表成功创建
- 所有约束和索引已应用
- 触发器和函数正常工作

### 步骤 4: 验证设置

```bash
# 运行代码质量检查
uv run ruff check src/
uv run ruff format src/

# 运行类型检查
uv run mypy src/ --ignore-missing-imports

# 运行单元测试
uv run pytest tests/unit/ -v
```

### 步骤 5: 启动开发服务

```bash
# 启动 API Gateway（主要服务）
uv run uvicorn src.api.main:app --reload --port 8000

# 在另一个终端启动 Agent 服务（可选）
SERVICE_TYPE=agent-worldsmith uv run python -m src.agents.worldsmith.main
```

**访问服务**：
- API 文档: `http://localhost:8000/docs`
- Health Check: `http://localhost:8000/health`

## 🏗️ 项目架构

### 目录结构

```
backend/
├── src/
│   ├── api/              # FastAPI API Gateway
│   │   ├── main.py      # 主应用入口
│   │   ├── routes/      # API 路由
│   │   └── schemas/     # API 响应模式
│   ├── agents/           # AI Agent 服务
│   │   ├── base.py      # Agent 基类
│   │   ├── worldsmith/  # 世界观构建 Agent
│   │   └── director/    # 故事导演 Agent
│   ├── models/           # SQLAlchemy ORM 模型
│   ├── schemas/          # Pydantic 数据模式（CQRS）
│   ├── common/
│   │   └── services/    # 业务逻辑服务
│   ├── db/              # 数据库连接管理
│   ├── core/            # 核心配置
│   └── middleware/      # 中间件
├── alembic/             # 数据库迁移
├── scripts/             # 管理和部署脚本
├── tests/               # 测试文件
│   ├── unit/           # 单元测试
│   └── integration/    # 集成测试
├── pyproject.toml       # 项目配置和依赖
└── Dockerfile          # Docker 部署文件
```

### 数据库架构

**18 个表，分为四大类**：

#### 核心业务表 (7个)
- `novels` - 小说项目元数据
- `chapters` - 章节元数据
- `chapter_versions` - 章节版本控制
- `characters` - 角色信息
- `worldview_entries` - 世界观设定
- `story_arcs` - 故事弧结构
- `reviews` - AI 评审记录

#### 创世流程表 (2个)
- `genesis_sessions` - 创作会话管理
- `concept_templates` - 立意模板

#### 架构机制表 (5个)
- `domain_events` - 领域事件（事件溯源）
- `command_inbox` - 命令处理（CQRS）
- `async_tasks` - 异步任务跟踪
- `event_outbox` - 事务消息发送
- `flow_resume_handles` - 工作流恢复

#### 用户认证表 (3个)
- `users` - 用户基本信息
- `sessions` - 会话管理
- `email_verifications` - 邮箱验证

## 🛠️ 日常开发工作流

### 本地开发

```bash
# 启动开发服务器（支持热重载）
uv run uvicorn src.api.main:app --reload --port 8000

# 运行特定 Agent
SERVICE_TYPE=agent-worldsmith uv run python -m src.agents.worldsmith.main
```

### 数据库更改

```bash
# 1. 修改 src/models/ 中的模型
# 2. 生成迁移
uv run alembic revision --autogenerate -m "描述你的更改"

# 3. 检查生成的迁移文件
# 4. 应用迁移
uv run alembic upgrade head

# 5. 验证更改
uv run python scripts/verify_tables.py
```

### 代码质量

```bash
# 代码格式化和检查
uv run ruff check src/ --fix
uv run ruff format src/

# 类型检查
uv run mypy src/ --ignore-missing-imports

# 运行测试
uv run pytest tests/ -v

# 测试覆盖率
uv run pytest tests/ --cov=src --cov-report=html
```

## 🔧 故障排除

### 常见问题

#### 1. 数据库迁移失败

```bash
# 症状: "constraint does not exist" 错误
# 解决方案: 重置迁移状态
uv run alembic stamp base
uv run alembic upgrade head
```

#### 2. 基础设施服务连接失败

```bash
# 检查服务状态
pnpm check:services

# 重启服务
pnpm infra down
pnpm infra up
```

#### 3. 依赖安装问题

```bash
# 清理并重新安装
rm -rf .venv/
uv sync --all-extras --group dev
```

#### 4. 导入错误

```bash
# 验证 Python 路径
uv run python -c "import sys; print(sys.path)"
uv run python -c "from src.api.main import app; print('Import success')"
```

### 日志和调试

```bash
# 启用详细日志
uv run uvicorn src.api.main:app --reload --log-level debug

# 查看数据库连接
uv run python -c "
from src.common.services.postgres_service import PostgresService
service = PostgresService()
print('Database connection successful')
"
```

## 🧪 测试

### 运行测试

```bash
# 所有测试
uv run pytest tests/ -v

# 单元测试（快速）
uv run pytest tests/unit/ -v

# 集成测试（需要数据库）
uv run pytest tests/integration/ -v

# 特定测试文件
uv run pytest tests/unit/services/test_user_service.py -v

# 带覆盖率报告
uv run pytest tests/ --cov=src --cov-report=html
# 查看报告: htmlcov/index.html
```

### 测试数据库

测试使用独立的测试数据库容器，确保测试不会影响开发数据。

## 🚢 部署

### Docker 构建

```bash
# 构建镜像
docker build -t infinite-scribe-backend .

# 运行 API Gateway
docker run -p 8000:8000 -e SERVICE_TYPE=api-gateway infinite-scribe-backend

# 运行 Agent 服务
docker run -e SERVICE_TYPE=agent-worldsmith infinite-scribe-backend
```

### 环境变量

关键环境变量：
- `SERVICE_TYPE`: 服务类型 (`api-gateway`, `agent-worldsmith`, `agent-director`, 等)
- `DATABASE_URL`: PostgreSQL 连接字符串
- `REDIS_URL`: Redis 连接字符串
- `NEO4J_URL`: Neo4j 连接字符串

## 📚 添加新功能

### 添加新 API 端点

1. 在 `src/api/routes/v1/` 创建路由文件
2. 定义 Pydantic 模式在 `src/schemas/`
3. 实现业务逻辑在 `src/common/services/`
4. 添加测试在 `tests/unit/api/` 和 `tests/integration/api/`

### 添加新 Agent

1. 在 `src/agents/` 创建新目录
2. 继承 `BaseAgent` 类
3. 实现 `process_request` 方法
4. 创建 `main.py` 入口点
5. 添加到 `pyproject.toml` 入口点
6. 更新 `Dockerfile`

### 添加数据库模型

1. 在 `src/models/` 创建模型文件
2. 继承 `BaseModel` 类
3. 创建对应的 Pydantic 模式
4. 生成数据库迁移
5. 添加服务层方法
6. 编写测试

## 📖 更多资源

- [FastAPI 文档](https://fastapi.tiangolo.com/)
- [SQLAlchemy 文档](https://docs.sqlalchemy.org/)
- [Alembic 迁移指南](https://alembic.sqlalchemy.org/)
- [项目架构文档](../../docs/architecture/)

## 💡 开发提示

- 遵循 [CLAUDE.md](./CLAUDE.md) 中的开发准则
- 使用类型提示和文档字符串
- 编写测试覆盖新功能
- 提交前运行代码质量检查
- 保持数据库迁移的向后兼容性
