# InfiniteScribe - AI小说生成平台
> AI-Powered Novel Writing Platform

**⚠️ 项目状态：MVP 开发中**  
InfiniteScribe 是一个基于多智能体协作的 AI 小说创作平台，目前正在积极开发中。本项目采用多个专业 AI 代理的协同工作来实现高质量、连贯的长篇小说生成。

## 🚧 当前开发状态

- ✅ **基础设施配置**：Docker 容器化、开发工具链、CI/CD 流程
- 🔄 **后端开发**：API Gateway 和 Agent 服务架构（开发中）
- ⏳ **前端开发**：尚未开始，计划使用 React 18 + TypeScript
- 📋 **项目管理**：使用 Taskmaster 进行任务跟踪和进度管理

## 🎯 项目概述

InfiniteScribe利用最先进的AI技术和多智能体架构，为用户提供一个全面的小说创作解决方案。系统包含前端应用、API网关、多个专业智能体服务，以及完整的基础设施支持。

### 核心特性（规划中）
- 🤖 **多智能体协作**：世界观构建、剧情策划、角色塑造等专业 AI 代理
- 📚 **智能创作**：基于上下文的连贯性写作和情节发展
- 🎨 **个性化定制**：支持不同写作风格和题材
- 🔍 **质量控制**：自动化的内容审核和质量评估
- 💾 **版本管理**：完整的创作历史和版本控制

## 🏗️ 技术栈

### 已配置/开发中
- **后端**: Python 3.11 + FastAPI + Pydantic
- **数据库**: PostgreSQL 16 + Redis 7.2 + Neo4j 5.x + Milvus 2.6
- **消息队列**: Apache Kafka 3.7
- **工作流编排**: Prefect 3.x
- **对象存储**: MinIO
- **AI/LLM**: LiteLLM (统一多模型接口)
- **可观测性**: Langfuse
- **容器化**: Docker + Docker Compose
- **包管理**: pnpm 8.15 (Monorepo) + uv (Python)

### 计划中
- **前端**: React 18.2 + TypeScript 5.2 + Vite + Tailwind CSS + Shadcn UI

## 📁 项目结构

```
infinite-scribe/
├── apps/                       # 独立应用
│   ├── frontend/              # React前端应用（待开发）
│   └── backend/               # 统一后端服务（开发中）
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
├── scripts/                  # 项目脚本
└── .taskmaster/              # 项目管理和任务跟踪
```

## 🚀 快速开始

### 前置要求

- Node.js ~20.x
- pnpm ~8.15
- Docker & Docker Compose
- Python ~3.11

### 安装依赖

#### 快速设置（推荐）

```bash
# 运行开发环境设置脚本
./scripts/development/setup-dev.sh
```

这个脚本会自动：
- 安装 uv 包管理器（如果需要）
- 创建 Python 虚拟环境
- 安装所有 Python 依赖
- 设置 pre-commit hooks
- 安装前端依赖

#### 手动设置

```bash
# 安装 pnpm（如果未安装）
npm install -g pnpm@8.15.9

# 安装前端依赖
pnpm install

# 安装 uv（Python 包管理器）
curl -LsSf https://astral.sh/uv/install.sh | sh

# 创建 Python 虚拟环境并安装依赖
uv venv
uv sync --dev

# 激活虚拟环境
source .venv/bin/activate

# 设置 pre-commit hooks
pre-commit install
```

### 环境配置

InfiniteScribe 使用分层的环境变量管理方案，将配置按用途分离：

```bash
# 基础设施配置（Docker Compose使用）
cp .env.example .env.infrastructure
# 编辑 .env.infrastructure，设置数据库密码等

# 前端应用配置（暂未使用，前端待开发）
cp .env.frontend.example .env.frontend

# 后端服务配置（包含API Gateway和所有Agent配置）
cp .env.backend.example .env.backend
# 编辑 .env.backend，设置SERVICE_TYPE和相关配置
```

> 💡 **提示**: Docker Compose 默认使用 `.env` 文件，系统会自动创建指向 `.env.infrastructure` 的符号链接。详细环境配置说明请参考 [环境变量结构说明](./docs/deployment/environment-structure.md)。

### 启动开发环境

```bash
# 启动基础设施服务（数据库、消息队列等）
pnpm infra:up

# 检查所有服务健康状态
pnpm check:services

# ⚠️ 前端开发服务器（暂未实现）
# pnpm --filter frontend dev

# 启动API网关（在新终端）
cd apps/backend
SERVICE_TYPE=api-gateway uvicorn src.api.main:app --reload

# 或启动特定Agent服务
SERVICE_TYPE=agent-worldsmith python -m src.agents.worldsmith.main
```

> 📖 **注意**: 前端应用尚未开始开发，目前只能启动后端服务。更多Python开发环境配置和使用说明，请参考 [Python 开发快速入门](./docs/development/python-dev-quickstart.md)。

#### 基础设施管理命令

```bash
# 启动所有基础设施服务
pnpm infra:up

# 停止所有服务
pnpm infra:down

# 查看服务日志
pnpm infra:logs

# 部署到开发服务器 (192.168.2.201) - 仅用于开发环境
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

## 📋 开发进度管理

本项目使用 **Taskmaster** 进行任务管理和进度跟踪。

### 查看当前任务

```bash
# 安装 Taskmaster（如果未安装）
npm install -g task-master-ai

# 查看所有任务
task-master list

# 查看下一个要处理的任务
task-master next

# 查看特定任务详情
task-master show <task-id>
```

### 当前开发优先级

1. **基础设施搭建** - 高优先级（进行中）
2. **事件驱动架构** - 高优先级（待开始）
3. **Agent 框架开发** - 高优先级（待开始）
4. **核心 Agent 实现** - 中优先级（待开始）
5. **前端界面开发** - 中优先级（待开始）

## 🔧 服务详情

### 基础设施说明

- **开发服务器 (192.168.2.201)**: 仅用于开发环境的持久化服务，**不可用于任何测试**
- **测试服务器 (192.168.2.202)**: 专门用于所有测试，支持破坏性测试

所有开发服务部署在 `192.168.2.201` 上，需要在同一内网才能访问。

### 服务端口映射

| 服务 | 端口 | 访问地址 | 默认凭证 |
|------|------|----------|----------|
| PostgreSQL | 5432 | localhost:5432 | postgres/postgres |
| Redis | 6379 | localhost:6379 | - |
| Neo4j | 7474/7687 | http://localhost:7474 | neo4j/password |
| Kafka | 9092 | localhost:9092 | - |
| Milvus | 19530 | localhost:19530 | - |
| MinIO | 9000/9001 | http://localhost:9001 | admin/password |
| Prefect | 4200 | http://localhost:4200 | - |

> 💡 **详细配置**: 完整的服务配置、Web UI 访问地址、故障排除等详细信息请参考 [详细开发指南](./docs/development/detailed-development-guide.md)。

## 🤝 贡献指南

### 开发工作流

由于项目处于早期开发阶段，我们特别欢迎以下类型的贡献：

1. **基础架构完善**：完善 Docker 配置、CI/CD 流程
2. **Agent 框架开发**：实现 BaseAgent 抽象类和通用功能
3. **前端界面设计**：开始前端应用的开发
4. **文档完善**：API 文档、架构文档、开发指南

### 贡献流程

1. Fork 本仓库
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 查看 Taskmaster 任务确认开发优先级
4. 提交更改 (`git commit -m 'Add some amazing feature'`)
5. 推送到分支 (`git push origin feature/amazing-feature`)
6. 创建 Pull Request

### 代码规范

- Python: 使用 Ruff + Black 进行代码格式化
- TypeScript: 使用 ESLint + Prettier
- 提交信息: 遵循 Conventional Commits 规范
- 测试: 所有新功能需要包含相应测试

> 📝 **详细规范**: 完整的代码规范说明、CI/CD 配置、测试环境配置等请参考 [详细开发指南](./docs/development/detailed-development-guide.md)。

## 📚 文档

> 📖 **完整文档索引**: 查看 [文档中心](./docs/README.md) 获取所有文档的分类索引和快速导航。

### 核心文档
- [项目架构](./docs/architecture.md)
- [产品需求文档](./docs/prd.md)
- [前端规格说明](./docs/front-end-spec.md)

### 开发指南
- [详细开发指南](./docs/development/detailed-development-guide.md) - 完整的技术配置和详细说明
- [开发最佳实践](./docs/development/)
- [部署指南](./docs/deployment/)

## 📄 许可证

本项目目前为私有项目，未开源。如需使用请联系项目维护者。

## 🔗 相关链接

- [项目仓库](https://github.com/zhiyue/infinite-scribe)
- [问题反馈](https://github.com/zhiyue/infinite-scribe/issues)
- [开发文档](./docs/)

---

**注意**: 这是一个正在积极开发的项目，功能和 API 可能会频繁变更。建议开发者关注项目更新，并参考 Taskmaster 任务列表了解最新开发进度。
