# 服务架构与部署策略

## 服务分层架构

InfiniteScribe 采用分层的微服务架构，主要分为以下几个层次：

### 1. 基础设施层 (Infrastructure)
位于 `docker-compose.yml` 中，包含所有数据存储和消息中间件：

- **PostgreSQL** - 关系型数据库，存储结构化数据
- **Neo4j** - 图数据库，存储知识图谱和关系
- **Redis** - 缓存和会话存储
- **Kafka** - 消息队列，用于服务间异步通信
- **Milvus** - 向量数据库，用于语义搜索
- **MinIO** - 对象存储，存储文件和媒体
- **Prefect** - 工作流编排平台

### 2. 后端服务层 (Backend Services)
位于 `docker-compose.backend.yml` 中，包含：

#### API Gateway
- 服务名称：`api-gateway`
- 功能：统一入口，路由请求，身份验证，健康检查
- 端口：8000

#### Agent 服务
各个专业的 AI Agent，每个负责特定的创作任务：

- **agent-worldsmith** - 世界观构建师
- **agent-plotmaster** - 情节大师
- **agent-outliner** - 大纲规划师
- **agent-director** - 导演
- **agent-characterexpert** - 角色专家
- **agent-worldbuilder** - 世界建造者
- **agent-writer** - 写作者
- **agent-critic** - 评论家
- **agent-factchecker** - 事实核查员
- **agent-rewriter** - 重写者

### 3. 前端层 (Frontend)
- **服务名称**：`frontend`（尚未实现）
- **技术栈**：React + TypeScript + Vite
- **功能**：用户界面，创作管理，实时预览

## 部署策略

### 全量部署
适用于首次部署或重大更新：

```bash
# 部署所有服务
make deploy

# 构建并部署所有服务
make deploy-build
```

### 分层部署
根据更新范围选择合适的部署层次：

#### 1. 基础设施更新
当修改数据库配置、增加新的中间件时：

```bash
make deploy-infra
```

#### 2. 后端整体更新
当更新了共享依赖或需要同时更新多个服务时：

```bash
make deploy-backend
make deploy-backend-build  # 需要重新构建时
```

#### 3. Agent 批量更新
当只需要更新 Agent 服务，不影响 API Gateway 时：

```bash
make deploy-agents
make deploy-agents-build  # 需要重新构建时
```

### 精准部署
针对单个服务的快速迭代：

#### API Gateway 单独部署
```bash
make deploy-api
make deploy-api-build  # 需要重新构建时
```

#### 特定 Agent 部署
```bash
# 部署特定的 Agent
SERVICE=agent-worldsmith make deploy-service
SERVICE=agent-worldsmith make deploy-service-build  # 需要重新构建时
```

## 部署决策树

```
需要部署吗？
├── 是：继续
└── 否：结束

更新了什么？
├── 基础设施配置 → make deploy-infra
├── Python 依赖 (pyproject.toml) → 需要构建
│   ├── 影响所有服务 → make deploy-build
│   ├── 只影响后端 → make deploy-backend-build
│   └── 只影响 Agents → make deploy-agents-build
└── 源代码
    ├── 修改了多个服务 → 按服务类型
    │   ├── 后端服务 → make deploy-backend
    │   └── 只有 Agents → make deploy-agents
    └── 修改了单个服务
        ├── API Gateway → make deploy-api
        └── 特定 Agent → SERVICE=xxx make deploy-service
```

## 最佳实践

### 1. 日常开发流程
- 修改代码 → `make deploy` 或 `make deploy-service`
- 更新依赖 → 使用 `--build` 选项
- 大规模重构 → `make deploy-build`

### 2. 性能优化
- 优先使用精准部署，减少不必要的服务重启
- 基础设施服务保持长期运行，避免频繁重启
- 使用 `--service` 参数针对性部署单个服务

### 3. 故障隔离
- Agent 服务相互独立，单个 Agent 故障不影响其他服务
- API Gateway 作为必要服务，需要优先保证其稳定性
- 基础设施服务是所有服务的依赖，需要最高的稳定性保证

### 4. 部署顺序
1. 基础设施服务必须最先启动
2. API Gateway 依赖基础设施
3. Agent 服务可以并行启动
4. 前端服务可以独立部署

## 监控与日志

### 查看服务状态
```bash
# 检查所有服务健康状态
pnpm check:services

# 查看 Docker 容器状态
ssh zhiyue@192.168.2.201 "cd ~/workspace/mvp/infinite-scribe && docker compose ps"
```

### 查看服务日志
```bash
# 查看远程服务日志
pnpm logs:remote

# 查看特定服务日志
ssh zhiyue@192.168.2.201 "cd ~/workspace/mvp/infinite-scribe && docker compose logs -f api-gateway"
```

## 故障恢复

### 服务无响应
1. 检查服务日志找出错误原因
2. 尝试重启单个服务：`SERVICE=xxx make deploy-service`
3. 如果问题持续，重启整个服务类型：`make deploy-backend`

### 基础设施故障
1. 检查基础设施服务状态
2. 重启基础设施：`make deploy-infra`
3. 等待服务完全启动后，重启后端服务

### 依赖问题
1. 确认 `pyproject.toml` 和 `uv.lock` 同步
2. 使用构建选项重新部署：`make deploy-build`
3. 清理 Docker 缓存后重试