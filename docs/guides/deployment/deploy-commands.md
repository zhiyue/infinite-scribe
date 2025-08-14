# 部署命令使用指南

本文档说明如何使用新的统一部署命令系统。InfiniteScribe 现在使用两个简化的命令入口：
- `pnpm infra` - 基础设施管理
- `pnpm app` - 应用部署

## 基础设施管理 (pnpm infra)

### 基础设施部署

```bash
# 部署基础设施到开发服务器
pnpm infra deploy

# 本地部署基础设施
pnpm infra deploy --local

# 清除数据后重新部署
pnpm infra deploy --local --clean

# 启用邮件开发服务
pnpm infra deploy --profile development
```

### 本地基础设施管理

```bash
# 启动本地基础设施服务
pnpm infra up

# 停止本地基础设施服务
pnpm infra down

# 查看基础设施日志
pnpm infra logs

# 实时查看基础设施日志
pnpm infra logs --follow

# 查看特定服务日志
pnpm infra logs --service postgres

# 检查基础设施状态
pnpm infra status
```

### 查看基础设施帮助

```bash
# 显示基础设施管理帮助
pnpm infra --help
```

## 应用部署 (pnpm app)

### 基础部署命令

```bash
# 部署所有应用服务
pnpm app

# 构建并部署所有服务
pnpm app --build

# 显示应用部署帮助
pnpm app --help
```

### 按类型部署

```bash
# 部署所有后端服务
pnpm app --type backend

# 构建并部署所有后端服务
pnpm app --type backend --build

# 部署所有 Agent 服务
pnpm app --type agents

# 构建并部署所有 Agent 服务
pnpm app --type agents --build
```

### 部署特定服务

```bash
# 部署 API Gateway
pnpm app --service api-gateway

# 构建并部署 API Gateway
pnpm app --service api-gateway --build

# 部署特定 Agent 服务
pnpm app --service research-agent
pnpm app --service writing-agent

# 构建并部署特定服务
pnpm app --service research-agent --build
```

### 查看所有可用命令

```bash
# 查看所有可用脚本
pnpm run
```

## 使用场景示例

### 1. 日常开发部署

当您修改了代码并想快速部署到开发服务器时：

```bash
# 部署所有应用服务
pnpm app
```

### 2. 更新依赖后的完整构建部署

当您更新了 `pyproject.toml` 或 `requirements.txt` 等依赖文件时：

```bash
# 构建并部署所有服务
pnpm app --build
```

### 3. 只更新 API Gateway

当您只修改了 API Gateway 相关代码时：

```bash
# 快速部署（不重新构建）
pnpm app --service api-gateway

# 需要重新构建镜像时
pnpm app --service api-gateway --build
```

### 4. 只更新特定 Agent 服务

当您修改了某个特定的 Agent 时：

```bash
# 部署单个 Agent
pnpm app --service research-agent
pnpm app --service writing-agent

# 构建并部署特定 Agent
pnpm app --service research-agent --build

# 部署所有 Agents
pnpm app --type agents

# 构建并部署所有 Agents
pnpm app --type agents --build
```

### 5. 后端整体更新

当您需要更新所有后端服务时：

```bash
# 部署所有后端服务
pnpm app --type backend

# 构建并部署所有后端服务
pnpm app --type backend --build
```

### 6. 基础设施更新

当您需要更新基础设施配置时：

```bash
# 部署基础设施到开发服务器
pnpm infra deploy

# 本地部署基础设施
pnpm infra deploy --local
```

### 7. 查看帮助和选项

```bash
# 查看应用部署选项
pnpm app --help

# 查看基础设施管理选项
pnpm infra --help
```

## 高级用法

### 直接使用脚本

如果您需要更灵活的控制，也可以直接使用底层脚本：

```bash
# 查看应用部署脚本帮助
./scripts/deploy/app.sh --help

# 查看基础设施脚本帮助
./scripts/deploy/infra.sh --help

# 直接使用底层部署脚本
./scripts/deploy/deploy-to-dev.sh --help
```

### 组合参数使用

```bash
# 本地清理并重新部署基础设施
pnpm infra deploy --local --clean

# 构建并部署特定服务
pnpm app --service api-gateway --build

# 部署特定类型服务并构建
pnpm app --type backend --build
```

## 其他相关命令

### SSH 连接

```bash
# 连接到开发服务器
pnpm ssh:dev

# 连接到测试服务器
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
- `TEST_MACHINE_IP`: 测试服务器 IP（默认：192.168.2.202） 
- `DEV_USER`: SSH 用户名（默认：zhiyue）

可以通过设置环境变量来覆盖默认值：

```bash
# 使用不同的服务器
DEV_SERVER=192.168.2.100 pnpm app

# 使用不同的用户
DEV_USER=myuser pnpm app --build
```

## 注意事项

1. **首次部署**：确保开发服务器上已经配置好环境文件 `deploy/environments/.env.dev`
2. **权限要求**：需要有 SSH 免密登录到开发服务器的权限
3. **网络要求**：需要能够访问开发服务器的 SSH 端口（22）
4. **构建时间**：`--build` 选项会在远程服务器上构建镜像，可能需要几分钟时间
5. **服务依赖**：确保基础设施服务已启动（`pnpm infra deploy`）再部署应用服务
6. **命令简化**：新的统一命令系统将18+个旧命令简化为2个主要入口点