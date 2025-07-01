# 部署命令使用指南

本文档说明如何通过 `make` 或 `pnpm` 使用部署脚本。

## Make 命令

### 基础部署命令

```bash
# 默认部署（同步文件并部署所有服务）
make deploy

# 构建并部署所有服务
make deploy-build

# 显示部署脚本帮助
make deploy-help
```

### 按类型部署

```bash
# 部署基础设施服务
make deploy-infra

# 部署所有后端服务（API Gateway + 所有 Agents）
make deploy-backend
make deploy-backend-build    # 带构建

# 只部署所有 Agent 服务
make deploy-agents
make deploy-agents-build     # 带构建
```

### 部署特定服务

```bash
# 部署 API Gateway
make deploy-api
make deploy-api-build        # 带构建

# 部署特定服务（使用 SERVICE 变量）
SERVICE=agent-worldsmith make deploy-service
SERVICE=agent-plotmaster make deploy-service-build
```

### 查看所有可用命令

```bash
# 显示所有 make 命令
make help
```

## pnpm 命令

### 基础部署命令

```bash
# 默认部署（同步文件并部署所有服务）
pnpm deploy:dev

# 构建并部署所有服务
pnpm deploy:dev:build

# 显示部署脚本帮助
pnpm deploy:dev:help
```

### 按类型部署

```bash
# 部署基础设施服务
pnpm deploy:dev:infra

# 部署所有后端服务（API Gateway + 所有 Agents）
pnpm deploy:dev:backend
pnpm deploy:dev:backend:build    # 带构建

# 只部署所有 Agent 服务
pnpm deploy:dev:agents
pnpm deploy:dev:agents:build     # 带构建
```

### 部署特定服务

```bash
# 部署 API Gateway
pnpm deploy:dev:api
pnpm deploy:dev:api:build        # 带构建

# 部署特定服务（需要使用原始脚本）
./scripts/deployment/deploy-to-dev.sh --service agent-worldsmith
./scripts/deployment/deploy-to-dev.sh --service agent-plotmaster --build
```

### 查看所有可用脚本

```bash
# 查看 package.json 中的所有脚本
pnpm run
```

## 使用场景示例

### 1. 日常开发部署

当您修改了代码并想快速部署到开发服务器时：

```bash
# 使用 make
make deploy

# 或使用 pnpm
pnpm deploy:dev
```

### 2. 更新依赖后的完整构建部署

当您更新了 `pyproject.toml` 或 `requirements.txt` 等依赖文件时：

```bash
# 使用 make
make deploy-build

# 或使用 pnpm
pnpm deploy:dev:build
```

### 3. 只更新 API Gateway

当您只修改了 API Gateway 相关代码时：

```bash
# 快速部署（不重新构建）
make deploy-api
# 或
pnpm deploy:dev:api

# 需要重新构建镜像时
make deploy-api-build
# 或
pnpm deploy:dev:api:build
```

### 4. 只更新 Agent 服务

当您修改了某个特定的 Agent 时：

```bash
# 部署单个 Agent
SERVICE=agent-worldsmith make deploy-service
SERVICE=agent-worldsmith make deploy-service-build  # 带构建

# 部署所有 Agents
make deploy-agents
make deploy-agents-build  # 带构建
```

### 5. 后端整体更新

当您需要更新所有后端服务（API Gateway + 所有 Agents）时：

```bash
# 部署所有后端服务
make deploy-backend
# 或
pnpm deploy:dev:backend

# 带构建
make deploy-backend-build
# 或
pnpm deploy:dev:backend:build
```

### 6. 基础设施更新

当您需要更新基础设施配置时：

```bash
# 只更新基础设施服务
make deploy-infra
# 或
pnpm deploy:dev:infra
```

### 7. 查看部署选项

```bash
# 使用 make
make deploy-help

# 或使用 pnpm
pnpm deploy:dev:help
```

## 直接使用脚本

如果您想要更灵活的控制，也可以直接使用脚本：

```bash
# 查看帮助
./scripts/deployment/deploy-to-dev.sh --help

# 组合使用参数
./scripts/deployment/deploy-to-dev.sh --build --api-gateway-only
```

## 其他相关命令

### SSH 连接

```bash
# 连接到开发服务器
make ssh-dev
# 或
pnpm ssh:dev

# 连接到测试服务器
make ssh-test
# 或
pnpm ssh:test
```

### 查看日志

```bash
# 查看远程服务日志
pnpm logs:remote
```

### 检查服务状态

```bash
# 简单检查
pnpm check:services

# 完整检查
pnpm check:services:full
```

## 环境变量配置

部署脚本使用以下环境变量（可选）：

- `DEV_SERVER`: 开发服务器 IP（默认：192.168.2.201）
- `DEV_USER`: SSH 用户名（默认：zhiyue）

可以通过设置环境变量来覆盖默认值：

```bash
# 使用不同的服务器
DEV_SERVER=192.168.2.100 make deploy

# 使用不同的用户
DEV_USER=myuser pnpm deploy:dev
```

## 注意事项

1. **首次部署**：确保开发服务器上已经配置好 `.env.infrastructure` 文件
2. **权限要求**：需要有 SSH 免密登录到开发服务器的权限
3. **网络要求**：需要能够访问开发服务器的 SSH 端口（22）
4. **构建时间**：`--build` 选项会在远程服务器上构建镜像，可能需要几分钟时间