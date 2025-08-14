# 部署系统改进总结

## 概述

部署系统已经从仅支持 API Gateway 的简单部署升级为支持多服务、多类型的通用部署系统。

## 主要改进

### 1. 部署脚本增强 (`deploy-to-dev.sh`)

#### 新增参数
- `--service <name>` - 部署特定服务
- `--type <type>` - 按类型部署服务
- `--build` - 在远程服务器构建镜像（保留）
- `--api-gateway-only` - 保留以保持向后兼容（已标记为 deprecated）

#### 支持的服务类型
- `infra` - 基础设施服务
- `backend` - 所有后端服务（API Gateway + Agents）
- `agents` - 仅 Agent 服务
- `frontend` - 前端应用（预留）

#### 支持的服务名称
- `api-gateway` - API Gateway
- `agent-worldsmith` - 世界观构建师
- `agent-plotmaster` - 情节大师
- 其他 8 个 Agent 服务
- `frontend` - Web UI（预留）

### 2. Make 命令增强

新增命令：
- `make deploy-infra` - 部署基础设施
- `make deploy-backend[build]` - 部署所有后端服务
- `make deploy-agents[build]` - 部署所有 Agent 服务
- `make deploy-service[build]` - 部署特定服务（使用 SERVICE 变量）

使用示例：
```bash
SERVICE=agent-worldsmith make deploy-service
SERVICE=agent-plotmaster make deploy-service-build
```

### 3. pnpm 脚本增强

新增脚本：
- `pnpm deploy:dev:infra` - 部署基础设施
- `pnpm deploy:dev:backend[:build]` - 部署所有后端服务
- `pnpm deploy:dev:agents[:build]` - 部署所有 Agent 服务

### 4. 文档更新

#### 更新的文档
- `README.md` - 添加了新的部署命令示例
- `docs/development/command-reference.md` - 更新了部署命令对照表
- `docs/deployment/deploy-commands.md` - 完整的部署命令使用指南
- `docs/deployment/deploy-quick-reference.md` - 快速参考卡片

#### 新增的文档
- `docs/deployment/service-architecture.md` - 服务架构与部署策略详解
- `docs/deployment/deployment-improvements-summary.md` - 本总结文档

## 使用场景

### 1. 日常开发
```bash
# 部署所有更改
make deploy

# 只部署 API Gateway
make deploy-api

# 只部署某个 Agent
SERVICE=agent-worldsmith make deploy-service
```

### 2. 依赖更新
```bash
# 重新构建并部署所有服务
make deploy-build

# 只构建并部署后端服务
make deploy-backend-build

# 只构建并部署 Agents
make deploy-agents-build
```

### 3. 批量操作
```bash
# 更新所有后端服务
make deploy-backend

# 只更新所有 Agents
make deploy-agents

# 只更新基础设施
make deploy-infra
```

## 优势

1. **灵活性** - 支持全量部署、分类部署和精准部署
2. **效率** - 避免不必要的服务重启，加快部署速度
3. **可维护性** - 清晰的命令结构，易于理解和使用
4. **扩展性** - 轻松添加新服务，只需更新服务列表
5. **向后兼容** - 保留原有的 `--api-gateway-only` 参数

## 注意事项

1. 前端部署功能预留但尚未实现
2. 部署特定服务时需要确保服务名称正确
3. 基础设施服务必须先于应用服务启动
4. 使用 `--build` 选项会增加部署时间