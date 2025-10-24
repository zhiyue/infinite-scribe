# InfiniteScribe - AI小说生成平台

> AI-Powered Novel Writing Platform

**⚠️ 项目状态：MVP 开发中** InfiniteScribe 是一个基于多智能体协作的 AI 小说创作
平台，目前正在积极开发中。本项目采用多个专业 AI 代理的协同工作来实现高质量、连贯
的长篇小说生成。

## 🚧 当前开发状态

- ✅ **基础设施配置**：Docker 容器化、开发工具链、参数化命令系统
- ✅ **后端开发**：API Gateway、认证系统、Agent 框架基础
- ✅ **前端开发**：React 18 + TypeScript、认证 UI、E2E 测试
- ✅ **开发工具**：统一脚本系统、邮件服务、API 工具、健康检查
- 🔄 **核心功能**：Agent 智能体实现、小说生成流程（开发中）
- 📋 **项目管理**：基于 bmad 方法论的故事驱动开发

## 🎯 项目概述

InfiniteScribe利用最先进的AI技术和多智能体架构，为用户提供一个全面的小说创作解决
方案。系统包含前端应用、API网关、多个专业智能体服务，以及完整的基础设施支持。

### 核心特性（规划中）

- 🤖 **多智能体协作**：世界观构建、剧情策划、角色塑造等专业 AI 代理
- 📚 **智能创作**：基于上下文的连贯性写作和情节发展
- 🎨 **个性化定制**：支持不同写作风格和题材
- 🔍 **质量控制**：自动化的内容审核和质量评估
- 💾 **版本管理**：完整的创作历史和版本控制

## 🏗️ 技术栈

### 已配置/生产就绪

- **后端**: Python 3.11 + FastAPI + Pydantic + SQLAlchemy
- **前端**: React 18.2 + TypeScript ~5.9.2 + Vite + Tailwind CSS + Shadcn UI  
- **数据库**: PostgreSQL 16 + Redis 7.2 + Neo4j 5.x + Milvus 2.6
- **消息队列**: Apache Kafka 3.7
- **工作流编排**: Prefect 3.x
- **对象存储**: MinIO
- **AI/LLM**: LiteLLM (统一多模型接口)
- **可观测性**: Langfuse
- **容器化**: Docker + Docker Compose
- **包管理**: pnpm ~8.15.9 (Monorepo) + uv (Python)
- **测试**: Pytest + Vitest + Playwright (E2E)
- **开发工具**: 参数化命令系统、MailDev、API 导出工具

## 📁 项目结构

```text
infinite-scribe/
├── apps/                       # 独立应用
│   ├── frontend/              # React前端应用（开发中）
│   │   ├── src/
│   │   │   ├── components/   # React组件（UI组件库、自定义组件）
│   │   │   ├── pages/        # 页面组件（认证、Dashboard等）
│   │   │   ├── services/     # API服务层（认证、健康检查等）
│   │   │   ├── hooks/        # React Hooks（认证、查询等）
│   │   │   ├── types/        # TypeScript类型定义
│   │   │   │   ├── models/   # 数据模型类型
│   │   │   │   ├── api/      # API接口类型
│   │   │   │   ├── events/   # 事件类型
│   │   │   │   └── enums/    # 枚举类型
│   │   │   ├── utils/        # 工具函数
│   │   │   └── lib/          # 共享库（查询客户端等）
│   │   ├── e2e/             # Playwright端到端测试
│   │   └── public/          # 静态资源
│   └── backend/               # 统一后端服务（已实现）
│       ├── src/
│       │   ├── api/          # API网关服务（FastAPI应用）
│       │   │   ├── routes/   # API路由（认证、健康检查等）
│       │   │   └── schemas/  # API Schema定义
│       │   ├── agents/       # Agent服务框架
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
│       │   ├── common/       # 共享服务层
│       │   │   ├── services/ # 业务服务（认证、数据库、缓存等）
│       │   │   └── utils/    # 工具函数
│       │   ├── core/         # 核心配置（数据库、设置等）
│       │   ├── db/           # 数据库连接层
│       │   │   ├── sql/      # PostgreSQL连接管理
│       │   │   ├── graph/    # Neo4j连接管理
│       │   │   └── vector/   # Milvus向量数据库
│       │   ├── middleware/   # 中间件（CORS、认证、限流等）
│       │   ├── models/       # SQLAlchemy ORM模型
│       │   └── schemas/      # Pydantic Schema（CQRS模式）
│       │       ├── chapter/  # 章节Schema
│       │       ├── novel/    # 小说Schema
│       │       ├── character/# 角色Schema
│       │       └── ...       # 其他领域Schema
│       ├── tests/           # 测试套件（单元测试、集成测试）
│       ├── scripts/         # 后端脚本
│       ├── alembic/         # 数据库迁移
│       ├── Dockerfile       # 统一Docker镜像
│       └── pyproject.toml   # Python依赖（使用uv管理）
├── deploy/                    # Docker Compose部署配置
│   ├── docker-compose.yml   # 基础设施服务
│   └── environments/        # 环境配置文件
├── docs/                     # 项目文档
│   ├── architecture/        # 架构文档
│   ├── guides/             # 开发和部署指南
│   ├── prd/                # 产品需求文档
│   └── stories/            # 用户故事（bmad方法论）
├── scripts/                 # 项目脚本
│   ├── deploy/             # 部署脚本
│   ├── dev/                # 开发工具脚本
│   ├── ops/                # 运维脚本
│   └── test/               # 测试脚本
├── api-docs/               # API文档和测试工具
├── Makefile                # Make命令定义
├── package.json            # Monorepo配置（pnpm）
└── pnpm-workspace.yaml     # pnpm工作区配置
```

## 🚀 快速开始

### 前置要求

- Node.js >=20.0.0
- pnpm ~8.15.9
- Docker & Docker Compose
- Python ~3.11
- uv (现代Python包管理器)

### 🎯 参数化命令系统 (核心功能)

本项目采用了统一的参数化脚本运行器，极大简化了开发命令的使用：

```bash
# 核心开发命令 (日常使用 95% 的命令)
pnpm backend run                     # 启动后端 API 网关
pnpm frontend run                    # 启动前端开发服务器
pnpm backend install                 # 安装 Python 依赖
pnpm frontend install               # 安装 Node.js 依赖

# 测试命令
pnpm test all                        # 运行所有测试（本地 Docker）
pnpm test all --remote               # 远程测试（192.168.2.202）
pnpm test unit                       # 单元测试
pnpm test coverage                   # 带覆盖率测试

# 服务管理
pnpm check services                  # 快速健康检查
pnpm check services --remote         # 检查远程服务器服务
pnpm infra up                        # 启动基础设施服务
pnpm infra down                      # 停止基础设施服务

# SSH 连接
pnpm ssh dev                         # 连接开发服务器 (192.168.2.201)
pnpm ssh test                        # 连接测试服务器 (192.168.2.202)

# API 工具
pnpm api export                      # 导出本地 API 定义
pnpm api export:dev                  # 导出开发环境 API 定义

# 获取帮助
pnpm run                             # 显示完整命令帮助
pnpm backend                         # 后端命令帮助  
pnpm test                            # 测试命令帮助
```

**优势**: 
- ✅ 减少 86% 重复代码 (从 88 个脚本 → 12 个核心脚本)
- ✅ 统一环境变量和参数管理
- ✅ 保持完全向后兼容性

### 安装依赖

#### 快速设置（推荐）

```bash
# 使用 Make
make setup

# 或使用原脚本
./scripts/dev/setup-dev.sh
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

InfiniteScribe 使用简化的环境配置结构，支持三种主要环境：

```bash
# 首次设置 - 整合现有环境文件（如果存在旧文件）
pnpm env:consolidate

# 创建本地开发环境配置
cp .env.example .env.local
# 编辑 .env.local，设置数据库密码、API密钥等

# 切换到本地开发环境（默认）
pnpm env:local

# 其他环境切换命令
pnpm env:dev      # 切换到开发服务器 (192.168.2.201)
pnpm env:test     # 切换到测试环境
pnpm env:show     # 查看当前环境
```

> 💡 **提示**: `.env` 是一个符号链接，指向当前激活的环境配置文件。详细环境配置说
> 明请参考 [环境变量结构说明](./docs/guides/deployment/environment-structure.md)。

#### 单独启动 Outbox Relay（数据库→Kafka）
- 本地运行：`pnpm backend relay:run`（或 `cd apps/backend && uv run python -m src.services.outbox.relay`）
- 通过 Launcher：`cd apps/backend && uv run is-launcher up --components relay --apply --stay`
- 配置说明与 Docker 部署示例：见 `apps/backend/docs/relay-service.md`

#### Outbox Relay 配置（可选）
- 位置：后端 `.env`（嵌套变量）或 `apps/backend/config.toml` 的 `[relay]` 段
- 变量（环境变量名 → 说明 → 默认）：
  - `RELAY__POLL_INTERVAL_SECONDS`：轮询频率（秒）→ 5
  - `RELAY__BATCH_SIZE`：每批处理条数 → 100
  - `RELAY__RETRY_BACKOFF_MS`：失败指数退避基数（毫秒）→ 1000
  - `RELAY__MAX_RETRIES_DEFAULT`：默认最大重试次数（当行内未指定时使用）→ 3
- TOML 示例（apps/backend/config.toml）：
  - `[relay]`
  - `poll_interval_seconds = 5`
  - `batch_size = 100`
  - `retry_backoff_ms = 1000`
  - `max_retries_default = 3`

### 🔄 开发工作流

推荐的日常开发流程：

```bash
# 1. 初始设置（只需要做一次）
./scripts/dev/setup-dev.sh  # 安装所有依赖
pnpm infra up               # 启动基础设施服务
pnpm check services         # 检查本地服务状态

# 2. 日常开发（在两个终端中运行）
pnpm backend run            # 终端 1: 启动后端 API 网关
pnpm frontend run           # 终端 2: 启动前端开发服务器

# 3. 代码质量检查（提交前）
pnpm backend lint           # Python 代码检查
pnpm backend typecheck      # Python 类型检查
pnpm backend test           # 单元测试
pnpm lint                   # 前端代码检查

# 4. 完整测试（提交前建议运行）
pnpm test all               # 全部测试（Docker 容器模式）

# 5. 部署到开发服务器
pnpm app                    # 部署所有应用服务
pnpm app --build            # 重新构建并部署（更新依赖后）
```

**快捷命令：**
- `pnpm run` - 查看所有可用命令和完整帮助
- `pnpm clean` - 清理缓存和构建产物  
- `pnpm format` - 格式化所有代码

**环境管理命令：**
```bash
# SSH 连接命令
pnpm ssh dev                # 连接开发服务器 (192.168.2.201)
pnpm ssh test               # 连接测试服务器 (192.168.2.202)

# 环境配置管理
pnpm env:local              # 切换到本地开发环境
pnpm env:dev                # 切换到开发服务器环境
pnpm env:show               # 查看当前环境

# 运维工具
pnpm logs:remote            # 查看远程服务日志
pnpm backup:dev             # 备份开发数据
```

### 启动开发环境

```bash
# 启动基础设施服务（数据库、消息队列等）
pnpm infra up

# 检查所有服务健康状态
pnpm check services

# 启动前端开发服务器
pnpm frontend run

# 启动API网关（在新终端）
pnpm backend run

# 高级用法：直接使用 uvicorn 启动后端
cd apps/backend
uv run uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# 高级用法：启动特定Agent服务
SERVICE_TYPE=agent-worldsmith python -m src.agents.worldsmith.main
```

> 📖 **注意**: 更多Python开发环境配置和使用说明，请参考
> [Python 开发快速入门](./docs/guides/development/python-dev-quickstart.md)。

#### 基础设施和部署命令

```bash
# 基础设施管理
pnpm infra up                # 启动所有基础设施服务
pnpm infra down              # 停止所有服务
pnpm infra deploy            # 部署基础设施到开发服务器
pnpm infra deploy --local    # 本地部署基础设施

# ⭐ 应用部署 - 最常用命令
pnpm app                     # 日常代码部署（90% 的时候用这个）
pnpm app --build             # 重新构建并部署（更新依赖后）
pnpm app --type backend      # 只部署后端服务
pnpm app --service api-gateway  # 只部署 API Gateway

# SSH 连接和运维
pnpm ssh dev                 # 连接开发服务器 (192.168.2.201)
pnpm ssh test                # 连接测试服务器 (192.168.2.202)

# 📖 完整部署命令参考：docs/guides/deployment/DEPLOY_SIMPLE.md
```

### 服务健康检查

```bash
# 检查所有必需服务的运行状态（本地）
pnpm check services

# 检查开发服务器上的服务状态
pnpm check services --remote

# 运行完整的服务健康检查（本地，需要额外依赖）
pnpm check services:full

# 运行完整的服务健康检查（开发服务器）
pnpm check services:full --remote
```

**服务检查包括**：
- PostgreSQL、Redis、Neo4j 数据库连接
- Kafka 消息队列状态
- Milvus 向量数据库
- MinIO 对象存储
- Prefect 工作流编排平台
- 所有服务的 Web UI 访问性

### 🧪 测试系统

本项目支持多层次的测试策略：

```bash
# 单元测试
pnpm backend test            # Python 单元测试
pnpm frontend test           # React 单元测试

# E2E 测试（前端）
pnpm frontend e2e            # 运行所有 E2E 测试
pnpm frontend e2e:ui         # UI 模式运行 E2E 测试
pnpm frontend e2e:auth       # 运行认证相关 E2E 测试

# 完整测试（推荐）
pnpm test all                # 本地 Docker 运行所有测试
pnpm test all --remote       # 远程测试机器运行
pnpm test coverage           # 生成覆盖率报告

# 项目结构验证
pnpm test structure          # 验证项目结构完整性
```

### 📧 开发工具

**邮件服务 (MailDev)**:
```bash
# 启动邮件开发服务器
pnpm maildev start          # 启动 MailDev
pnpm maildev logs           # 查看邮件服务日志
pnpm maildev stop           # 停止邮件服务

# 访问地址: http://localhost:1080
```

**API 工具**:
```bash
# 导出 API 定义（用于 Hoppscotch/Postman）
pnpm api export             # 导出本地 API
pnpm api export:dev         # 导出开发环境 API
pnpm api hoppscotch         # 导出并显示导入提示
```

## 📋 开发进度管理

本项目采用基于 **bmad 方法论**的故事驱动开发模式，通过用户故事来组织和跟踪开发进
度。

### 查看当前进度

```bash
# 查看所有用户故事
ls docs/stories/

# 查看特定故事详情
cat docs/stories/1.1.story.md
```

### 当前故事状态

| 故事                                     | 状态      | 描述                          |
| ---------------------------------------- | --------- | ----------------------------- |
| [Story 1.1](./docs/stories/1.1.story.md) | ✅ Done   | 初始化 Monorepo 项目结构      |
| [Story 1.2](./docs/stories/1.2.story.md) | ✅ Done   | 部署核心事件、存储与编排服务  |
| [Story 1.3](./docs/stories/1.3.story.md) | ✅ Done   | 创建并部署健康的 API 网关服务 |
| [Story 1.4](./docs/stories/1.4.story.md) | ✅ Done   | 创建并部署基础前端仪表盘UI    |
| [Story 2.1](./docs/stories/2.1.story.md) | ✅ Done   | 实现统一领域事件与命令模式的数据模型 |

### 下一步开发优先级

1. **Story 2.2** - 计划中：实现基于 Prefect 的核心工作流编排系统
2. **Story 2.3** - 计划中：构建 Agent 框架和 BaseAgent 抽象类
3. **核心 Agent 实现** - 计划中：世界观构建师等专业 AI 代理
4. **用户认证系统完善** - 进行中：React 应用的完整认证流程
5. **集成测试** - 计划中：端到端功能测试和 MVP 验证

> 📖 **故事详情**: 每个故事都包含详细的验收标准、任务分解、技术指导和测试要求，
> 请查看 `docs/stories/` 目录中的具体文档。

## 🔧 服务详情

### 基础设施说明

- **开发服务器 (192.168.2.201)**: 仅用于开发环境的持久化服务，**不可用于任何测
  试**
- **测试服务器 (192.168.2.202)**: 专门用于所有测试，支持破坏性测试

所有开发服务部署在 `192.168.2.201` 上，需要在同一内网才能访问。

### 服务端口映射

| 服务        | 端口      | 访问地址                         | 默认凭证                    |
| ----------- | --------- | -------------------------------- | ----------------------------- |
| **前端**    | 3000      | http://localhost:3000            | -                             |
| **API网关** | 8000      | http://192.168.2.201:8000       | -                             |
| PostgreSQL  | 5432      | 192.168.2.201:5432              | postgres/postgres             |
| Redis       | 6379      | 192.168.2.201:6379              | 见.env.infrastructure         |
| Neo4j       | 7474/7687 | http://192.168.2.201:7474       | neo4j/password                |
| Kafka       | 9092      | 192.168.2.201:9092              | -                             |
| Milvus      | 19530     | 192.168.2.201:19530             | -                             |
| MinIO       | 9000/9001 | http://192.168.2.201:9001       | admin/见.env.infrastructure    |
| Prefect     | 4200      | http://192.168.2.201:4200       | -                             |

> 💡 **详细配置**: 完整的服务配置、Web UI 访问地址、故障排除等详细信息请参考
> [详细开发指南](./docs/guides/development/detailed-development-guide.md)。

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
3. 查看 `docs/stories/` 中的用户故事确认开发优先级
4. 提交更改 (`git commit -m 'Add some amazing feature'`)
5. 推送到分支 (`git push origin feature/amazing-feature`)
6. 创建 Pull Request

### 代码规范

- **Python**: 使用 Ruff + Black 进行代码格式化
  ```bash
  make backend-lint      # 运行 Ruff 检查
  make backend-format    # 格式化 Python 代码
  make backend-typecheck # Mypy 类型检查
  ```
- **TypeScript**: 使用 ESLint + Prettier
  ```bash
  pnpm lint             # ESLint 检查
  pnpm format           # Prettier 格式化
  ```
- **提交信息**: 遵循 Conventional Commits 规范
- **测试**: 所有新功能需要包含相应测试
  ```bash
  make test-unit         # 单元测试
  make test-integration  # 集成测试  
  make test-coverage     # 测试覆盖率报告
  ```

> 📝 **详细规范**: 完整的代码规范说明、CI/CD 配置、测试环境配置等请参考
> [详细开发指南](./docs/guides/development/detailed-development-guide.md)。

## 📚 文档

> 📖 **完整文档索引**: 查看 [文档中心](./docs/README.md) 获取所有文档的分类索引
> 和快速导航。

### 核心文档

- [项目架构](./docs/architecture/)
- [产品需求文档](./docs/prd/)
- [前端规格说明](./docs/front-end-spec.md)

### 开发指南

- [详细开发指南](./docs/guides/development/detailed-development-guide.md) - 完整的技术
  配置和详细说明
- [开发最佳实践](./docs/guides/development/)
- [部署指南](./docs/guides/deployment/)

## 📄 许可证

本项目目前为私有项目，未开源。如需使用请联系项目维护者。

## 🔗 相关链接

- [项目仓库](https://github.com/zhiyue/infinite-scribe)
- [问题反馈](https://github.com/zhiyue/infinite-scribe/issues)
- [开发文档](./docs/)

---

**注意**: 这是一个正在积极开发的项目，功能和 API 可能会频繁变更。建议开发者关注
项目更新，并参考 `docs/stories/` 中的用户故事了解最新开发进度。
