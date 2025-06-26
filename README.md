# InfiniteScribe - AI小说生成平台
> AI-Powered Novel Writing Platform

InfiniteScribe是一个基于多智能体协作的AI小说创作平台，通过多个专业AI代理的协同工作，实现高质量、连贯的长篇小说生成。

## 🎯 项目概述

InfiniteScribe利用最先进的AI技术和多智能体架构，为用户提供一个全面的小说创作解决方案。系统包含前端应用、API网关、多个专业智能体服务，以及完整的基础设施支持。

## 🏗️ 技术栈

- **前端**: React 18.2 + TypeScript 5.2 + Vite + Tailwind CSS + Shadcn UI
- **后端**: Python 3.11 + FastAPI + Pydantic
- **数据库**: PostgreSQL 16 + Redis 7.2 + Neo4j 5.x + Milvus 2.6
- **消息队列**: Apache Kafka 3.7
- **工作流编排**: Prefect 3.x
- **对象存储**: MinIO
- **AI/LLM**: LiteLLM (统一多模型接口)
- **可观测性**: Langfuse
- **包管理**: pnpm 8.15 (Monorepo)

## 📁 项目结构

```
infinite-scribe/
├── apps/                       # 独立应用
│   ├── frontend/              # React前端应用
│   └── backend/               # 统一后端服务
│       ├── src/
│       │   ├── api/          # API网关服务
│       │   ├── agents/       # 所有Agent服务
│       │   │   ├── worldsmith/      # 世界铸造师Agent
│       │   │   ├── plotmaster/      # 剧情策划师Agent
│       │   │   ├── outliner/        # 大纲规划师Agent
│       │   │   ├── director/        # 导演Agent
│       │   │   ├── characterexpert/ # 角色专家Agent
│       │   │   ├── worldbuilder/    # 世界观构建师Agent
│       │   │   ├── writer/          # 作家Agent
│       │   │   ├── critic/          # 评论家Agent
│       │   │   ├── factchecker/     # 事实核查员Agent
│       │   │   └── rewriter/        # 改写者Agent
│       │   ├── core/         # 核心配置
│       │   └── common/       # 共享逻辑
│       ├── Dockerfile        # 统一Docker镜像
│       └── pyproject.toml   # 统一Python依赖
├── packages/                  # 共享代码包
│   ├── shared-types/         # 共享类型定义
│   ├── common-utils/         # 通用工具函数
│   ├── eslint-config-custom/ # ESLint配置
│   └── tsconfig-custom/      # TypeScript配置
├── infrastructure/           # 基础设施配置
├── docs/                     # 项目文档
│   ├── architecture/         # 架构文档
│   ├── prd/                  # 产品需求文档
│   └── stories/              # 用户故事
└── scripts/                  # 项目脚本
```

## 🚀 快速开始

### 前置要求

- Node.js ~20.x
- pnpm ~8.15
- Docker & Docker Compose
- Python ~3.11

### 安装依赖

```bash
# 安装pnpm（如果未安装）
npm install -g pnpm@8.15.9

# 安装项目依赖
pnpm install
```

### 环境配置

InfiniteScribe 使用分层的环境变量管理方案，将配置按用途分离：

```bash
# 基础设施配置（Docker Compose使用）
cp .env.example .env.infrastructure
# 编辑 .env.infrastructure，设置数据库密码等

# 前端应用配置（可选，仅在需要时创建）
cp .env.frontend.example .env.frontend

# 后端服务配置（包含API Gateway和所有Agent配置）
cp .env.backend.example .env.backend
# 编辑 .env.backend，设置SERVICE_TYPE和相关配置
```

> 💡 **提示**: Docker Compose 默认使用 `.env` 文件，系统会自动创建指向 `.env.infrastructure` 的符号链接。

### 启动开发环境

```bash
# 启动基础设施服务（数据库、消息队列等）
pnpm infra:up

# 检查所有服务健康状态
pnpm check:services

# 启动前端开发服务器
pnpm --filter frontend dev

# 启动API网关（在新终端）
cd apps/backend
SERVICE_TYPE=api-gateway uvicorn src.api.main:app --reload

# 或启动特定Agent服务
SERVICE_TYPE=agent-worldsmith python -m src.agents.worldsmith.main
```

#### 基础设施管理命令

```bash
# 启动所有基础设施服务
pnpm infra:up

# 停止所有服务
pnpm infra:down

# 查看服务日志
pnpm infra:logs

# 部署到开发服务器 (192.168.2.201)
pnpm infra:deploy
```

### 服务健康检查

```bash
# 检查所有必需服务的运行状态
pnpm check:services

# 运行完整的服务健康检查（需要额外依赖）
pnpm check:services:full
```

服务检查包括：
- PostgreSQL、Redis、Neo4j 数据库连接
- Kafka 消息队列状态
- Milvus 向量数据库
- MinIO 对象存储
- Prefect 工作流编排平台
- 所有服务的 Web UI 访问性

### 项目结构验证

```bash
# 运行项目结构测试
pnpm test:structure
```

## 🔧 服务详情

所有服务部署在开发服务器 `192.168.2.201` 上，需要在同一内网才能访问。

### 服务端口映射

| 服务 | 端口 | 访问地址 | 默认凭证 |
| --- | --- | --- | --- |
| PostgreSQL | 5432 | `192.168.2.201:5432` | 用户: postgres / 密码: (见.env.infrastructure) |
| Redis | 6379 | `192.168.2.201:6379` | 密码: (见.env.infrastructure) |
| Neo4j Bolt | 7687 | `bolt://192.168.2.201:7687` | 用户: neo4j / 密码: (见.env.infrastructure) |
| Neo4j Browser | 7474 | http://192.168.2.201:7474 | 同上 |
| Kafka | 9092 | `192.168.2.201:9092` | 无认证 |
| Zookeeper | 2181 | `192.168.2.201:2181` | 无认证 |
| Milvus | 19530 | `192.168.2.201:19530` | 无认证 |
| Milvus Metrics | 9091 | http://192.168.2.201:9091/metrics | 无认证 |
| MinIO API | 9000 | http://192.168.2.201:9000 | 用户: minioadmin / 密码: (见.env.infrastructure) |
| MinIO Console | 9001 | http://192.168.2.201:9001 | 同上 |
| Prefect API | 4200 | http://192.168.2.201:4200/api | 无认证 |
| Prefect UI | 4200 | http://192.168.2.201:4200 | 无认证 |

### Web UI 访问

以下服务提供 Web 界面：

- **Neo4j Browser**: http://192.168.2.201:7474 - 图数据库查询界面
- **MinIO Console**: http://192.168.2.201:9001 - 对象存储管理界面
- **Prefect UI**: http://192.168.2.201:4200 - 工作流编排管理界面

### 网络要求

- 所有服务仅在内网可访问（192.168.2.0/24 网段）
- 确保您的开发机器与服务器在同一网络中
- 防火墙已配置允许上述端口的访问

### 故障排除

#### 服务无法连接

```bash
# 检查服务状态
pnpm check:services

# 查看特定服务日志
ssh zhiyue@192.168.2.201 "cd ~/workspace/mvp/infinite-scribe && docker compose logs [service-name]"

# 重启所有服务
ssh zhiyue@192.168.2.201 "cd ~/workspace/mvp/infinite-scribe && docker compose restart"
```

#### 常见问题

1. **PostgreSQL 连接被拒绝**: 检查 .env.infrastructure 中的密码配置
2. **Redis 认证失败**: 确保使用正确的密码（REDIS_PASSWORD）
3. **Kafka 无法连接**: 检查 KAFKA_ADVERTISED_LISTENERS 配置
4. **MinIO bucket 不存在**: 服务启动时会自动创建 novels bucket
5. **Prefect 无法访问**: 确保 PostgreSQL 正常运行（Prefect 依赖它）

## 🏭 统一后端架构

InfiniteScribe 采用统一的后端架构，所有后端服务（API Gateway 和各种 Agent）共享一个代码库和依赖配置。

### 服务类型

通过 `SERVICE_TYPE` 环境变量选择要运行的服务：

- `api-gateway` - API 网关服务
- `agent-worldsmith` - 世界铸造师 Agent
- `agent-plotmaster` - 剧情策划师 Agent
- `agent-outliner` - 大纲规划师 Agent
- `agent-director` - 导演 Agent
- `agent-characterexpert` - 角色专家 Agent
- `agent-worldbuilder` - 世界观构建师 Agent
- `agent-writer` - 作家 Agent
- `agent-critic` - 评论家 Agent
- `agent-factchecker` - 事实核查员 Agent
- `agent-rewriter` - 改写者 Agent

### 运行后端服务

```bash
# 进入后端目录
cd apps/backend

# 安装Python依赖（使用 uv）
uv venv
source .venv/bin/activate  # Linux/macOS
uv sync --dev

# 运行 API Gateway
SERVICE_TYPE=api-gateway uvicorn src.api.main:app --reload

# 运行特定 Agent
SERVICE_TYPE=agent-worldsmith python -m src.agents.worldsmith.main
```

### Docker 部署

统一的 Dockerfile 支持所有服务：

```bash
# 构建镜像
docker build -t infinite-scribe-backend apps/backend/

# 运行 API Gateway
docker run -e SERVICE_TYPE=api-gateway -p 8000:8000 infinite-scribe-backend

# 运行 Agent
docker run -e SERVICE_TYPE=agent-worldsmith infinite-scribe-backend
```

## 🧪 测试

```bash
# 运行所有测试
pnpm test

# 运行特定包的测试
pnpm --filter <package-name> test
```

## 🎨 代码规范

项目使用ESLint和Prettier确保代码质量和一致性：

```bash
# 运行代码检查
pnpm lint

# 格式化代码
pnpm format
```

## 📖 文档

- [架构设计](./docs/architecture.md)
- [产品需求文档](./docs/prd.md)
- [前端规范](./docs/front-end-spec.md)
- [API文档](./docs/architecture/rest-api-spec.md)
- [环境变量配置指南](./docs/deployment/environment-variables.md)

## 🤝 贡献指南

1. Fork本仓库
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'feat: add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建Pull Request

### 提交规范

使用约定式提交（Conventional Commits）：
- `feat:` 新功能
- `fix:` 修复bug
- `docs:` 文档更新
- `style:` 代码格式（不影响代码运行的变动）
- `refactor:` 重构
- `test:` 测试相关
- `chore:` 构建过程或辅助工具的变动

## 📄 许可证

本项目为私有软件，版权所有。
