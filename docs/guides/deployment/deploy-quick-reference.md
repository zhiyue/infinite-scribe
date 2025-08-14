# 部署快速参考

## Make 命令（推荐）

### 基础命令
| 命令 | 说明 | 使用场景 |
|------|------|----------|
| `make deploy` | 同步并部署所有服务 | 日常代码更新 |
| `make deploy-build` | 构建并部署所有服务 | 依赖更新后 |
| `make deploy-help` | 显示帮助 | 查看所有选项 |

### 按类型部署
| 命令 | 说明 | 使用场景 |
|------|------|----------|
| `make deploy-infra` | 部署基础设施 | 更新数据库等配置 |
| `make deploy-backend` | 部署所有后端服务 | 后端整体更新 |
| `make deploy-backend-build` | 构建并部署所有后端 | 后端依赖更新 |
| `make deploy-agents` | 部署所有 Agent | Agent 批量更新 |
| `make deploy-agents-build` | 构建并部署所有 Agent | Agent 依赖更新 |

### 特定服务部署
| 命令 | 说明 | 使用场景 |
|------|------|----------|
| `make deploy-api` | 只部署 API Gateway | API 快速迭代 |
| `make deploy-api-build` | 构建并部署 API Gateway | API 依赖更新 |
| `SERVICE=xxx make deploy-service` | 部署特定服务 | 单个服务更新 |
| `SERVICE=xxx make deploy-service-build` | 构建并部署特定服务 | 单个服务依赖更新 |

## pnpm 命令

### 基础命令
| 命令 | 说明 | 使用场景 |
|------|------|----------|
| `pnpm deploy:dev` | 同步并部署所有服务 | 日常代码更新 |
| `pnpm deploy:dev:build` | 构建并部署所有服务 | 依赖更新后 |
| `pnpm deploy:dev:help` | 显示帮助 | 查看所有选项 |

### 按类型部署
| 命令 | 说明 | 使用场景 |
|------|------|----------|
| `pnpm deploy:dev:infra` | 部署基础设施 | 更新数据库等配置 |
| `pnpm deploy:dev:backend` | 部署所有后端服务 | 后端整体更新 |
| `pnpm deploy:dev:backend:build` | 构建并部署所有后端 | 后端依赖更新 |
| `pnpm deploy:dev:agents` | 部署所有 Agent | Agent 批量更新 |
| `pnpm deploy:dev:agents:build` | 构建并部署所有 Agent | Agent 依赖更新 |

### 特定服务部署
| 命令 | 说明 | 使用场景 |
|------|------|----------|
| `pnpm deploy:dev:api` | 只部署 API Gateway | API 快速迭代 |
| `pnpm deploy:dev:api:build` | 构建并部署 API Gateway | API 依赖更新 |

## 最常用的命令

```bash
# 90% 的情况使用这个
make deploy

# 更新了依赖时使用
make deploy-build

# 只改了 API 时使用
make deploy-api

# 只改了某个 Agent 时使用
SERVICE=agent-worldsmith make deploy-service

# 更新所有后端服务
make deploy-backend
```

## 可用的服务名称

用于 `SERVICE=xxx` 参数：

- `api-gateway` - API Gateway
- `agent-worldsmith` - 世界观构建师
- `agent-plotmaster` - 情节大师
- `agent-outliner` - 大纲规划师
- `agent-director` - 导演
- `agent-characterexpert` - 角色专家
- `agent-worldbuilder` - 世界建造者
- `agent-writer` - 写作者
- `agent-critic` - 评论家
- `agent-factchecker` - 事实核查员
- `agent-rewriter` - 重写者

## 相关命令

```bash
# SSH 到开发服务器
make ssh-dev

# 查看服务状态
pnpm check:services

# 查看远程日志
pnpm logs:remote
```