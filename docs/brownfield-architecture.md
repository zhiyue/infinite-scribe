# Infinite Scribe Brownfield 架构文档

## 简介

本文档记录了 Infinite Scribe（多智能体网络小说自动写作系统）的当前实际状态，包括已实现部分、技术债务、约束条件以及与 PRD 需求的映射关系。本文档旨在为 AI 开发代理提供准确的项目现状参考，以便高效推进后续开发工作。

### 文档范围
聚焦于 PRD 中定义的五个 Epic 的实现状态和技术路径，特别关注：
- Epic 1: 基础设施与核心服务引导
- Epic 2: 创世阶段人机交互流程
- Epic 3: 端到端章节生成 MVP
- Epic 4: 规模化生成与稳定性验证
- Epic 5: 全功能长篇小说生成

### 变更日志
| 日期 | 版本 | 描述 | 作者 |
|------|---------|-------------|--------|
| 2025-06-29 | 1.0 | 初始 brownfield 分析 | BMad Master |

## 快速参考 - 关键文件和入口点

### 理解系统的关键文件
- **API 主入口**: `apps/backend/src/api/main.py`
- **配置中心**: `apps/backend/src/core/config.py`
- **数据库 Schema**: `infrastructure/docker/init/postgres/02-init-schema.sql`
- **环境配置**: `.env.dev`（开发服务器）、`.env.test`（测试环境）
- **Docker 编排**: `docker-compose.yml`、`docker-compose.backend.yml`
- **Agent 基类**: `apps/backend/src/agents/base.py`

### PRD 影响区域 - 需要重点开发的模块
- **创世流程 API**: `apps/backend/src/api/routes/v1/genesis.py` ❌ (待创建)
- **事件系统**: `apps/backend/src/events/` ❌ (待创建)
- **工作流编排**: `apps/backend/src/workflows/` ❌ (待创建)
- **前端应用**: `apps/frontend/` ❌ (空目录)

## 高层架构

### 技术总结
项目采用**微服务架构**，基于**事件驱动模式**，目前基础设施搭建完成（约 30%），但核心业务逻辑几乎未实现（< 5%）。系统设计专业，文档齐全，但存在大量待实现功能。

### 实际技术栈
| 类别 | 技术 | 版本 | 状态 | 备注 |
|----------|------------|---------|--------|--------|
| 运行时 | Python | 3.11+ | ✅ 已配置 | uv 包管理 |
| 运行时 | Node.js | 20.x | ✅ 已配置 | pnpm 8.15 |
| Web 框架 | FastAPI | 0.115.6 | ✅ 基础实现 | 仅健康检查端点 |
| 前端框架 | React | 18.2 | ❌ 未实现 | 计划使用 Next.js |
| 数据库 | PostgreSQL | 16 | ✅ 已部署 | Schema 已定义 |
| 图数据库 | Neo4j | 5 | ✅ 已部署 | 未集成代码 |
| 向量数据库 | Milvus | 2.4 | ✅ 已部署 | 未集成代码 |
| 缓存 | Redis | 7 | ✅ 已部署 | 基础连接实现 |
| 消息队列 | Kafka | 3.8 | ✅ 已部署 | 未集成代码 |
| 工作流 | Prefect | 3 | ✅ 已部署 | 无工作流定义 |
| 对象存储 | MinIO | latest | ✅ 已部署 | 未集成代码 |
| LLM 代理 | LiteLLM | 1.57.3 | ⚠️ 已安装 | 未配置使用 |
| 监控 | Langfuse | 3 | ⚠️ 已配置 | 未启用 |

### 仓库结构现实检查
- 类型: Monorepo（pnpm workspace）
- 包管理: pnpm（前端）、uv（后端）
- 特殊之处: 统一的后端 Dockerfile，通过 SERVICE_TYPE 环境变量运行不同服务

## 源代码树和模块组织

### 项目结构（实际）
```
infinite-scribe/
├── apps/
│   ├── backend/            # FastAPI 后端（开发中）
│   │   ├── src/
│   │   │   ├── api/       # API Gateway（基础框架 ✅）
│   │   │   ├── agents/    # 10 个 AI Agent（空壳 ❌）
│   │   │   ├── common/    # 共享服务（部分实现 ⚠️）
│   │   │   └── core/      # 核心配置（已实现 ✅）
│   │   ├── tests/         # 测试框架（已搭建 ✅）
│   │   └── Dockerfile     # 统一镜像（已配置 ✅）
│   └── frontend/          # React 前端（未开始 ❌）
├── packages/              # 共享包（待创建 ❌）
├── infrastructure/        # 基础设施配置
│   └── docker/           # Docker 初始化脚本
├── scripts/              # 开发和部署脚本
├── docs/                 # 项目文档（完善 ✅）
└── .bmad-core/           # BMAD 方法论资源
```

### 关键模块及其用途
- **API Gateway**: `apps/backend/src/api/` - 系统入口，目前仅健康检查
- **Agent 服务**: `apps/backend/src/agents/` - 10 个专业 AI Agent，均未实现
  - worldsmith - 世界铸造师（创世阶段的核心）
  - plotmaster - 剧情策划师（高层剧情决策）
  - outliner - 大纲规划师（章节规划）
  - director - 导演（场景设计）
  - characterexpert - 角色专家（角色互动）
  - worldbuilder - 世界观构建师（世界观扩展）
  - writer - 作家（章节写作）
  - critic - 评论家（质量评审）
  - factchecker - 事实核查员（一致性检查）
  - rewriter - 改写者（修订和修正）
- **数据库服务**: `apps/backend/src/common/services/` - PostgreSQL、Neo4j、Redis 连接管理

## 数据模型和 API

### 数据模型
- **PostgreSQL Schema**: 见 `infrastructure/docker/init/postgres/02-init-schema.sql`
  - novels - 小说主表
  - chapters - 章节内容
  - characters - 角色信息
  - worldview_entries - 世界观条目
  - story_arcs - 故事线
  - reviews - 评审记录
- **Neo4j 模型**: 待定义节点和关系类型
- **Pydantic 模型**: 待在 `packages/shared-types` 中创建

### API 规范
- **已实现端点**:
  - `GET /health` - 健康检查
  - `GET /ready` - 就绪检查
- **待实现端点**（根据 PRD）:
  - `POST /genesis/start` - 启动创世流程
  - `POST /genesis/{session_id}/worldview` - 提交世界观设定
  - `POST /genesis/{session_id}/characters` - 提交角色设定
  - `POST /genesis/{session_id}/plot` - 提交剧情设定
  - `POST /genesis/{session_id}/finish` - 完成创世
  - `POST /novels/{novel_id}/generate-chapter` - 生成章节
  - `GET /chapters/{chapter_id}` - 获取章节内容
  - `GET /metrics` - 获取系统指标

## 技术债务和已知问题

### 关键技术债务
1. **前端完全缺失**: `apps/frontend/` 目录为空，需要从零开始搭建
2. **Agent 实现缺失**: 所有 Agent 仅有目录结构，无实际逻辑
3. **事件系统未集成**: Kafka 已部署但代码中未使用
4. **工作流未定义**: Prefect 已部署但无任何工作流
5. **向量数据库未集成**: Milvus 已部署但无代码接口
6. **对象存储未集成**: MinIO 已部署但无上传/下载逻辑

### 约束和注意事项
- **环境变量**: 必须使用 `.env` 文件管理配置，支持 local/dev/test 环境切换
- **远程服务器**: 开发服务器 192.168.2.201 仅用于开发，测试必须在 192.168.2.202
- **Docker 依赖**: 所有服务通过 Docker Compose 管理，本地开发需要 Docker
- **Python 版本**: 必须使用 Python 3.11+，通过 uv 管理依赖

### 已知问题
1. Neo4j 浏览器端口（7474）在某些配置中可能冲突
2. Milvus 需要较大内存（建议 8GB+）
3. 开发环境配置较复杂，需要多个服务同时运行

## 集成点和外部依赖

### 外部服务
| 服务 | 用途 | 集成状态 | 关键文件 |
|---------|---------|------------------|-----------|
| OpenAI/Anthropic | LLM API | ❌ 待集成 | 需创建 `litellm_service.py` |
| LiteLLM | API 代理 | ❌ 待配置 | 依赖已安装 |
| Langfuse | 监控追踪 | ❌ 待启用 | Docker 配置已存在 |

### 内部集成点
- **Agent 间通信**: 通过 Kafka 事件总线（待实现）
- **数据持久化**: PostgreSQL + Neo4j + Milvus + MinIO（部分实现）
- **工作流协调**: Prefect（待实现）
- **缓存层**: Redis（基础连接已实现）

## 开发和部署

### 本地开发设置
```bash
# 1. 切换到开发环境
pnpm env:dev

# 2. 启动基础设施
make infra-up

# 3. 启动后端服务
make backend-dev

# 4. 前端开发（待实现）
# pnpm dev
```

### 实际可用命令
```bash
# 基础设施管理
make infra-up      # 启动所有基础服务
make infra-down    # 停止所有服务
make infra-ps      # 查看服务状态

# 后端开发
make backend-dev   # 启动 API Gateway（开发模式）
make backend-test  # 运行测试
make backend-lint  # 代码检查

# 环境管理
pnpm env:local    # 切换到本地环境
pnpm env:dev      # 切换到开发服务器
pnpm env:test     # 切换到测试环境
```

### 构建和部署流程
- **构建**: 使用统一的 `apps/backend/Dockerfile`
- **部署**: 通过 `docker-compose.backend.yml` 管理
- **环境**: 支持 local、dev、test、prod（生产环境配置待定）

## 测试现状

### 当前测试覆盖
- 单元测试: 框架已搭建，覆盖率 0%
- 集成测试: 支持 Docker 容器和远程服务测试
- E2E 测试: 无（前端未实现）

### 运行测试
```bash
# 推荐：使用 Docker 容器测试
./scripts/run-tests.sh --all --docker-host

# 仅单元测试
./scripts/run-tests.sh --unit --docker-host

# 代码质量检查
./scripts/run-tests.sh --lint
```

## PRD 实现影响分析

### Epic 1: 基础设施与核心服务引导
**完成度: 75%**
- ✅ Story 1.1: Monorepo 项目结构
- ✅ Story 1.2: 核心服务部署
- ⚠️ Story 1.3: API Gateway（需添加业务端点）
- ❌ Story 1.4: 前端仪表盘 UI

**需要的工作**:
1. 完善 API Gateway 业务端点
2. 初始化前端应用

### Epic 2: 创世阶段人机交互流程
**完成度: 15%**
- ✅ Story 2.1: 数据模型设计（仅 SQL Schema）
- ❌ Story 2.2: 创世流程 API 端点
- ❌ Story 2.3: 世界铸造师 Agent 逻辑
- ❌ Story 2.4: 前端创世向导

**需要的工作**:
1. 创建 Pydantic 数据模型
2. 实现创世流程 API 端点
3. 开发世界铸造师 Agent 核心逻辑
4. 构建前端创世向导界面

### Epic 3: 端到端章节生成 MVP
**完成度: 5%**
- ⚠️ Story 3.1: Agent 服务部署（仅框架）
- ❌ Story 3.2: 事件 Schema 定义
- ❌ Story 3.3: Prefect 工作流
- ❌ Story 3.4: 评审流程

**需要的工作**:
1. 定义并实现事件系统
2. 实现所有 Agent 的核心逻辑
3. 创建 Prefect 工作流
4. 集成 LiteLLM 和 LLM API

### Epic 4 & 5: 高级功能
**完成度: 0%**
- 完全未开始，依赖前三个 Epic 的完成

## 实施建议和优先级

### 第一阶段：基础设施完善（1-2 周）
1. **创建共享类型定义**
   - Pydantic 模型（`packages/shared-types/models.py`）
   - TypeScript 接口（前端类型定义）

2. **完善数据库集成**
   - 实现 Milvus 服务接口
   - 实现 MinIO 文件操作
   - Neo4j 节点和关系定义

3. **配置 LiteLLM**
   - 创建 LLM 服务封装
   - 配置模型路由和成本控制

### 第二阶段：创世流程实现（2-3 周）
1. **API 端点开发**
   - 实现所有创世相关端点
   - 添加请求验证和错误处理

2. **世界铸造师 Agent**
   - 实现 LLM 调用逻辑
   - 结构化输出生成
   - 数据持久化

3. **前端初始化**
   - 搭建 Next.js 应用
   - 实现项目仪表盘
   - 创建创世向导组件

### 第三阶段：章节生成 MVP（3-4 周）
1. **事件系统搭建**
   - Kafka 生产者/消费者
   - 事件 Schema 定义
   - 错误处理和重试

2. **Agent 逐个实现**
   - 从大纲规划师开始
   - 确保事件驱动通信
   - 集成知识库检索

3. **工作流编排**
   - Prefect Flow 定义
   - 条件分支逻辑
   - 监控和日志

### 第四阶段：优化和扩展（持续）
1. 完善前端功能
2. 添加监控和可观测性
3. 性能优化
4. 实现高级 Agent

## 附录 - 有用的命令和脚本

### 常用命令
```bash
# 查看所有 make 命令
make help

# 数据库连接
psql -h 192.168.2.201 -U postgres -d infinite_scribe
cypher-shell -a neo4j://192.168.2.201:7687 -u neo4j

# 查看日志
docker-compose logs -f api-gateway
docker-compose logs -f kafka

# 环境变量检查
cat .env | grep -E "(POSTGRES|NEO4J|REDIS|KAFKA)"
```

### 调试和故障排除
- **日志位置**: Docker 容器日志，使用 `docker-compose logs`
- **调试模式**: 设置 `LOG_LEVEL=DEBUG` 环境变量
- **常见问题**: 见 `docs/troubleshooting.md`（待创建）

---

本文档真实反映了 Infinite Scribe 项目的当前状态。系统设计专业且完善，但实现工作刚刚开始。建议按照上述实施计划，从创世流程开始逐步推进，确保每个 Epic 的核心功能都能端到端运行后再进入下一阶段。