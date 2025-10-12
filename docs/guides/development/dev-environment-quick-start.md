# 开发环境快速启动指南

> 本文档专注于日常开发环境的快速启动命令和参数说明。如需完整的开发环境配置和调试指南，请参考 [本地开发调试指南](./local-development-guide.md)。

## 📋 目录

- [前置准备](#前置准备)
- [后端开发环境](#后端开发环境)
- [前端开发环境](#前端开发环境)
- [完整开发流程](#完整开发流程)
- [常见问题](#常见问题)

## 前置准备

### 1. 确保基础设施服务已启动

```bash
# 启动本地基础设施服务（PostgreSQL, Redis, Neo4j, Milvus, MinIO, Kafka）
pnpm infra up

# 验证服务状态
pnpm check services
```

### 2. 确保已安装依赖

```bash
# 后端依赖（在项目根目录）
pnpm backend install

# 前端依赖（在项目根目录）
pnpm frontend install
```

## 后端开发环境

### 标准启动命令

```bash
cd apps/backend

# 完整启动命令（包含所有常用组件）
uv run is-launcher up \
  --components api,relay,eventbridge,agents \
  --agents orchestrator,inquiry \
  --reload \
  --apply \
  --stay
```

### 参数详解

#### `--components` 参数

指定要启动的后端组件类型：

| 组件 | 说明 | 端口 |
|------|------|------|
| `api` | API Gateway - RESTful API 服务 | 8000 |
| `relay` | 事件中继服务 - 处理事件转发 | 8001 |
| `eventbridge` | 事件桥接器 - 连接Kafka与内部事件系统 | 8002 |
| `agents` | Agent服务容器 - 运行AI智能体 | 动态分配 |

**示例：**
```bash
# 只启动 API Gateway
uv run is-launcher up --components api --apply --stay

# 启动 API 和事件系统
uv run is-launcher up --components api,relay,eventbridge --apply --stay
```

#### `--agents` 参数

指定要启动的具体 Agent 类型（仅当 `--components` 包含 `agents` 时有效）：

| Agent | 说明 | 职责 |
|-------|------|------|
| `orchestrator` | 编排器Agent | 协调整体创作流程，管理任务分配 |
| `inquiry` | 询问Agent | 处理与用户的交互式对话 |
| `worldsmith` | 世界铸造师 | 负责世界观和初始设定 |
| `plotmaster` | 剧情策划师 | 管理故事整体走向 |
| `outliner` | 大纲规划师 | 设计章节大纲 |
| `director` | 导演 | 规划场景序列 |
| `characterexpert` | 角色专家 | 管理角色设定和互动 |
| `worldbuilder` | 世界观构建师 | 扩展世界观细节 |
| `writer` | 作家 | 生成章节内容 |
| `critic` | 评论家 | 评估内容质量 |
| `factchecker` | 事实核查员 | 检查内容一致性 |
| `rewriter` | 改写者 | 修订和改进内容 |

**示例：**
```bash
# 只启动编排器和询问Agent
uv run is-launcher up --components agents --agents orchestrator,inquiry --apply --stay

# 启动完整的创作团队
uv run is-launcher up --components agents \
  --agents orchestrator,worldsmith,plotmaster,outliner,director,writer,critic \
  --apply --stay
```

#### 其他重要参数

| 参数 | 说明 | 使用场景 |
|------|------|----------|
| `--reload` | 启用热重载 | **开发时必备** - 代码修改后自动重启服务 |
| `--apply` | 应用配置变更 | 确保使用最新的配置文件 |
| `--stay` | 前台运行 | 方便查看实时日志，Ctrl+C 停止 |
| `--mode single` | 单进程模式 | 简化调试，所有服务在同一进程 |

### 常用启动组合

#### 1. 全栈开发（推荐）

```bash
# 启动所有核心服务和主要Agents
uv run is-launcher up \
  --components api,relay,eventbridge,agents \
  --agents orchestrator,inquiry,writer,critic \
  --reload \
  --apply \
  --stay
```

#### 2. 仅 API 开发

```bash
# 只需要测试API接口时
uv run is-launcher up \
  --components api \
  --reload \
  --apply \
  --stay
```

#### 3. Agent 开发

```bash
# 专注于开发特定Agent
uv run is-launcher up \
  --components agents \
  --agents writer,critic \
  --reload \
  --apply \
  --stay
```

#### 4. 调试模式（单进程）

```bash
# 所有服务在单进程中运行，便于调试
uv run is-launcher up \
  --components api,agents \
  --agents orchestrator,inquiry \
  --mode single \
  --reload \
  --apply \
  --stay
```

### 查看服务日志

```bash
# 查看今天的日志
tail -f apps/backend/logs/is-launcher_$(date +%Y%m%d).log

# 查看指定日期的日志（例如：2025年1月12日）
tail -f apps/backend/logs/is-launcher_20250112.log

# 搜索特定内容
grep "ERROR" apps/backend/logs/is-launcher_*.log
```

## 前端开发环境

### 标准启动命令

```bash
# 在项目根目录执行
VITE_USE_MOCK_GENESIS=false pnpm run dev
```

### 参数详解

#### `VITE_USE_MOCK_GENESIS` 环境变量

| 值 | 说明 | 使用场景 |
|----|------|----------|
| `false` | 使用真实后端API | **开发时推荐** - 完整测试前后端集成 |
| `true` | 使用Mock数据 | 前端独立开发，不依赖后端服务 |

### 常用启动组合

#### 1. 连接本地后端（推荐）

```bash
# 使用本地后端服务
VITE_USE_MOCK_GENESIS=false pnpm run dev

# 前端将运行在: http://localhost:5173
# API代理到: http://localhost:8000
```

#### 2. 使用Mock数据

```bash
# 前端独立开发模式
VITE_USE_MOCK_GENESIS=true pnpm run dev
```

#### 3. 连接开发服务器

```bash
# 连接远程开发服务器（需要修改 vite.config.ts 中的代理配置）
VITE_API_URL=http://192.168.2.201:8000 \
VITE_USE_MOCK_GENESIS=false \
pnpm run dev
```

### 访问地址

- **前端应用**: http://localhost:5173
- **后端 API**: http://localhost:8000
- **API 文档**: http://localhost:8000/docs
- **API OpenAPI**: http://localhost:8000/openapi.json

## 完整开发流程

### 典型的开发会话（3个终端）

#### Terminal 1: 基础设施

```bash
# 启动并保持基础设施运行
pnpm infra up

# 查看基础设施状态
pnpm check services
```

#### Terminal 2: 后端服务

```bash
cd apps/backend

# 启动后端开发服务器
uv run is-launcher up \
  --components api,relay,eventbridge,agents \
  --agents orchestrator,inquiry \
  --reload \
  --apply \
  --stay

# 实时查看日志
# （日志已经显示在控制台，因为使用了 --stay）
```

#### Terminal 3: 前端服务

```bash
# 在项目根目录

# 启动前端开发服务器
VITE_USE_MOCK_GENESIS=false pnpm run dev

# 前端现在运行在 http://localhost:5173
```

### 快速验证流程

```bash
# 1. 验证后端健康
curl http://localhost:8000/health

# 2. 验证详细健康检查
curl http://localhost:8000/health/detailed

# 3. 查看API文档
open http://localhost:8000/docs  # macOS
# 或
xdg-open http://localhost:8000/docs  # Linux

# 4. 访问前端应用
open http://localhost:5173  # macOS
# 或
xdg-open http://localhost:5173  # Linux
```

## 常见问题

### 1. 后端启动失败

**症状**: `is-launcher` 命令报错或服务无法启动

**排查步骤**:

```bash
# 1. 检查基础设施服务状态
pnpm check services

# 2. 查看详细错误日志
tail -100 apps/backend/logs/is-launcher_$(date +%Y%m%d).log

# 3. 检查端口占用
lsof -i :8000  # API Gateway
lsof -i :8001  # Relay
lsof -i :8002  # EventBridge

# 4. 重启基础设施
pnpm infra down
pnpm infra up

# 5. 重新安装依赖
pnpm backend install
```

### 2. 前端无法连接后端

**症状**: 前端页面加载，但API调用失败

**排查步骤**:

```bash
# 1. 验证后端正在运行
curl http://localhost:8000/health

# 2. 检查前端代理配置
cat apps/frontend/vite.config.ts | grep -A 10 proxy

# 3. 查看浏览器控制台网络请求
# 打开浏览器开发工具 (F12) -> Network 标签

# 4. 确认环境变量
echo $VITE_USE_MOCK_GENESIS  # 应该是 false
```

### 3. 热重载不工作

**症状**: 修改代码后服务没有自动重启

**解决方案**:

```bash
# 1. 确认启动时使用了 --reload 参数
# 检查启动命令是否包含 --reload

# 2. 手动重启服务
# Ctrl+C 停止服务，然后重新启动

# 3. 检查文件监视器限制 (Linux)
# 如果使用 Linux，可能需要增加 inotify 限制
echo fs.inotify.max_user_watches=524288 | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```

### 4. Agent 无法启动

**症状**: 特定 Agent 启动失败或崩溃

**排查步骤**:

```bash
# 1. 查看日志中的错误信息
grep "ERROR" apps/backend/logs/is-launcher_$(date +%Y%m%d).log | tail -20

# 2. 尝试单独启动该 Agent
uv run is-launcher up \
  --components agents \
  --agents orchestrator \
  --apply \
  --stay

# 3. 检查 Agent 配置
cat apps/backend/config/agents.toml

# 4. 验证必要的环境变量
# 检查 .env 文件中的 API keys 和配置
```

### 5. 数据库连接失败

**症状**: 后端日志显示数据库连接错误

**解决方案**:

```bash
# 1. 检查 PostgreSQL 服务
docker ps | grep postgres

# 2. 测试数据库连接
psql -h localhost -U postgres -d infinite_scribe

# 3. 检查 Redis 连接
redis-cli -h localhost -p 6379 ping

# 4. 重启数据库服务
pnpm infra down
pnpm infra up

# 5. 等待服务完全启动（约30秒）
sleep 30
pnpm check services
```

### 6. 端口冲突

**症状**: "Address already in use" 错误

**解决方案**:

```bash
# 查找占用端口的进程
lsof -i :8000  # API Gateway 默认端口
lsof -i :5173  # 前端开发服务器默认端口

# 停止占用端口的进程
kill -9 <PID>

# 或者在启动时指定不同端口
# 后端（需要修改配置文件）
# 前端
pnpm run dev --port 5174
```

## 性能优化建议

### 1. 只启动需要的组件

```bash
# 如果只开发 API，不需要启动 Agents
uv run is-launcher up --components api --reload --apply --stay
```

### 2. 使用单进程模式进行调试

```bash
# 减少进程数量，降低资源消耗
uv run is-launcher up \
  --components api,agents \
  --agents orchestrator \
  --mode single \
  --reload \
  --apply \
  --stay
```

### 3. 关闭不需要的基础设施服务

```bash
# 如果不使用某些服务，可以选择性启动
# 编辑 deploy/docker-compose.yml 或使用 profiles
```

## 相关文档

- [本地开发调试指南](./local-development-guide.md) - 完整的调试技巧和配置
- [Python 开发快速入门](./python-dev-quickstart.md) - Python 环境配置
- [后端 CLAUDE.md](../../apps/backend/CLAUDE.md) - 后端架构详解
- [前端 CLAUDE.md](../../apps/frontend/CLAUDE.md) - 前端架构详解
- [QUICK_START.md](../../QUICK_START.md) - 项目整体快速入门

## 快速参考卡片

### 📌 每日开发必备命令

```bash
# 1. 启动基础设施
pnpm infra up

# 2. 启动后端（Terminal 1）
cd apps/backend
uv run is-launcher up \
  --components api,relay,eventbridge,agents \
  --agents orchestrator,inquiry \
  --reload --apply --stay

# 3. 启动前端（Terminal 2）
VITE_USE_MOCK_GENESIS=false pnpm run dev

# 4. 验证服务
curl http://localhost:8000/health
```

### 🔍 快速检查命令

```bash
# 检查所有服务状态
pnpm check services

# 查看后端日志
tail -f apps/backend/logs/is-launcher_$(date +%Y%m%d).log

# 测试 API
curl http://localhost:8000/health/detailed
```

---

**💡 提示**: 将这些命令保存为 shell 别名或脚本，可以进一步提升开发效率！
