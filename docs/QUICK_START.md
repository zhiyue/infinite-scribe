# InfiniteScribe 本地开发快速开始指南

本指南将指导你完成 InfiniteScribe 的本地开发环境设置，从零开始到运行完整的开发环境。

## 前置条件

### 系统要求
- **Node.js**: >= 20.0.0
- **pnpm**: ~8.15.0
- **Python**: 3.11
- **Docker**: 最新版本（用于基础设施服务）
- **Git**: 最新版本

### 系统检查
```bash
node --version    # 应该 >= 20.0.0
pnpm --version    # 应该 ~8.15.0
python --version  # 应该是 3.11.x
docker --version  # 确保 Docker 正在运行
```

## 1. 项目克隆与依赖安装

### 1.1 克隆项目
```bash
git clone <repository-url>
cd infinite-scribe
```

### 1.2 安装根级依赖
```bash
# 安装 pnpm workspace 依赖
pnpm install
```

### 1.3 安装前端依赖
```bash
# 前端依赖（React + TypeScript）
pnpm frontend install
# 或直接进入目录
# cd apps/frontend && pnpm install
```

### 1.4 安装后端依赖
```bash
# 后端依赖（Python + uv）
pnpm backend install
# 或直接进入目录
# cd apps/backend && uv sync
```

## 2. 基础设施设置

### 2.1 环境配置
```bash
# 复制环境配置模板
cp deploy/environments/.env.example deploy/environments/.env.local

# 编辑本地环境配置（可选，默认配置通常可直接使用）
# 主要服务端点：PostgreSQL(5432), Redis(6379), Neo4j(7474), MinIO(9001)
```

### 2.2 启动基础设施服务
```bash
# 启动所有基础设施服务（PostgreSQL, Redis, Neo4j, MinIO, Kafka, Prefect）
pnpm infra deploy --local --profile development

# 验证服务启动状态
pnpm check services
```

**服务验证**:
- PostgreSQL: localhost:5432 (postgres/postgres)
- Redis: localhost:6379
- Neo4j: http://localhost:7474 (neo4j/password)
- MinIO: http://localhost:9001 (admin/password)
- Prefect: http://localhost:4200

如果服务未完全启动，等待1-2分钟后重新检查。

## 3. 数据库初始化

### 3.1 运行数据库迁移
```bash
cd apps/backend

# 应用所有数据库迁移
uv run alembic upgrade head

# 验证迁移状态
uv run alembic current
```

## 4. 启动开发服务

### 4.1 启动后端服务（推荐方式）
```bash
cd apps/backend

# 启动 API Gateway（带热重载）
uv run is-launcher up --components api --mode single --reload --apply --stay
```

**启动参数说明**:
- `--components api`: 只启动 API Gateway
- `--mode single`: 单进程模式（开发调试友好）
- `--reload`: 热重载（代码修改自动重启）
- `--apply`: 应用配置
- `--stay`: 前台运行（Ctrl+C 停止）

**可选启动方式**:
```bash
# 同时启动 API 和 Agents
uv run is-launcher up --mode single --apply --stay

# 启动指定的 Agent 服务
uv run is-launcher up --agents "worldsmith,plotmaster" --apply --stay
```

### 4.2 启动前端服务
在**新终端**中：
```bash
# 启动前端开发服务器
pnpm frontend run
# 或
# pnpm dev  # 会提示使用上述命令
```

前端默认运行在: http://localhost:5173

## 5. 开发环境验证

### 5.1 API 健康检查
```bash
# 检查 API Gateway 状态
curl http://localhost:8000/health

# 检查具体服务连接
curl http://localhost:8000/health/detailed
```

### 5.2 前端访问验证
浏览器访问: http://localhost:5173

### 5.3 完整服务检查
```bash
# 快速健康检查
pnpm check services

# 完整健康检查（包括连接测试）
pnpm check services:full
```

## 6. 常用开发命令

### 6.1 代码质量检查
```bash
# 后端代码检查
cd apps/backend
uv run ruff check src/         # 代码风格检查
uv run ruff format src/        # 代码格式化
uv run mypy src/              # 类型检查

# 前端代码检查
cd apps/frontend
pnpm lint                     # ESLint 检查
pnpm format                   # Prettier 格式化
```

### 6.2 测试运行
```bash
# 后端测试
cd apps/backend
uv run pytest tests/unit/ -v              # 单元测试
uv run pytest tests/integration/ -v       # 集成测试

# 前端测试
cd apps/frontend
pnpm test                     # Vitest 测试
pnpm test:e2e                 # Playwright E2E 测试
```

### 6.3 数据库管理
```bash
cd apps/backend

# 创建新迁移
uv run alembic revision --autogenerate -m "描述修改内容"

# 应用迁移
uv run alembic upgrade head

# 回滚迁移
uv run alembic downgrade -1
```

## 7. 开发工作流

### 7.1 典型开发会话
```bash
# Terminal 1: 基础设施
pnpm infra up                 # 如未启动

# Terminal 2: 后端开发
cd apps/backend
uv run is-launcher up --components api --mode single --reload --apply --stay

# Terminal 3: 前端开发  
pnpm frontend run

# Terminal 4: 测试/命令行操作
# 运行测试、数据库操作等
```

### 7.2 快速重启流程
```bash
# 停止所有服务
Ctrl+C (在各个终端)

# 重启基础设施（如需要）
pnpm infra down && pnpm infra up

# 重启应用服务
cd apps/backend && uv run is-launcher up --components api --mode single --reload --apply --stay
pnpm frontend run  # 在另一终端
```

## 8. 故障排除

### 8.1 常见问题

**端口冲突**:
```bash
# 检查端口占用
lsof -i :8000  # 后端 API
lsof -i :5173  # 前端开发服务器
lsof -i :5432  # PostgreSQL

# 停止冲突进程
kill -9 <PID>
```

**服务连接失败**:
```bash
# 重启基础设施服务
pnpm infra down
pnpm infra up

# 等待服务完全启动（约1-2分钟）
pnpm check services
```

**数据库连接错误**:
```bash
# 检查 PostgreSQL 状态
docker ps | grep postgres

# 重新运行迁移
cd apps/backend
uv run alembic upgrade head
```

**依赖安装问题**:
```bash
# 清理并重新安装
pnpm clean  # 清理缓存
rm -rf node_modules pnpm-lock.yaml
rm -rf apps/backend/uv.lock
pnpm install
pnpm backend install
```

### 8.2 获取帮助

**命令帮助**:
```bash
pnpm run                      # 查看所有可用命令
pnpm backend                  # 后端操作帮助
pnpm frontend                 # 前端操作帮助
pnpm test                     # 测试操作帮助
```

**服务状态检查**:
```bash
pnpm check services           # 快速健康检查
pnpm check services:full      # 完整健康检查
pnpm infra status             # 基础设施状态
```

## 9. 下一步

环境搭建完成后，你可以：

1. **阅读架构文档**: `docs/architecture/`
2. **查看 API 文档**: 访问 http://localhost:8000/docs
3. **了解前端架构**: `apps/frontend/CLAUDE.md`
4. **了解后端架构**: `apps/backend/CLAUDE.md`
5. **学习开发流程**: 根目录 `CLAUDE.md`

## 10. 开发规范

### 10.1 代码提交前检查
- [ ] 代码风格检查通过: `pnpm lint`
- [ ] 类型检查通过: `uv run mypy src/`
- [ ] 测试通过: `pnpm test all`
- [ ] 服务健康: `pnpm check services:full`

### 10.2 提交消息规范
```
feat: 添加新功能
fix: 修复问题
refactor: 重构代码
docs: 文档更新
test: 测试相关
```

祝你开发愉快！如有问题，请查阅相关 `CLAUDE.md` 文档或提 issue。