# Command Reference: Make vs pnpm

This document provides a quick reference for using either `make` or `pnpm` commands to perform common development tasks.

> **⚠️ 重要更新**: 部署命令已简化！InfiniteScribe 现在使用统一的命令系统，将18+个部署命令简化为仅2个主要入口点：`pnpm infra`（基础设施）和 `pnpm app`（应用部署）。

## Backend Commands

| Task | Make Command | pnpm Command |
|------|--------------|--------------|
| Install dependencies | `make backend-install` | `pnpm run backend:install` |
| Run development server | `make backend-run` | `pnpm run backend:run` |
| Run API Gateway (simple) | - | `pnpm run backend:api:simple` |
| Run API Gateway (local) | - | `pnpm run backend:api:local` |
| Run API Gateway (dev) | - | `pnpm run backend:api:dev` |
| Lint code | `make backend-lint` | `pnpm run backend:lint` |
| Format code | `make backend-format` | `pnpm run backend:format` |
| Type check | `make backend-typecheck` | `pnpm run backend:typecheck` |
| Run unit tests | `make backend-test-unit` | `pnpm run backend:test:unit` |

## Frontend Commands

| Task | Make Command | pnpm Command |
|------|--------------|--------------|
| Install dependencies | `make frontend-install` | `pnpm run frontend:install` |
| Run development server | `make frontend-run` | `pnpm run frontend:run` |
| Build for production | `make frontend-build` | `pnpm run frontend:build` |
| Run tests | `make frontend-test` | `pnpm run frontend:test` |

## Testing Commands

| Task | Make Command | pnpm Command |
|------|--------------|--------------|
| Run all tests (Docker) | `make test-all` | `pnpm run test:all` |
| Run unit tests only | `make test-unit` | `pnpm run test:unit` |
| Run integration tests | `make test-integration` | `pnpm run test:integration` |
| Run with coverage | `make test-coverage` | `pnpm run test:coverage` |
| Run lint checks only | `make test-lint` | `pnpm run test:lint` |
| Run with remote services | `make test-all-remote` | `pnpm run test:all:remote` |

## Development Shortcuts

| Task | Make Command | pnpm Command |
|------|--------------|--------------|
| Install all dependencies | `make install` | `pnpm run install` |
| Run all dev servers | `make dev` | `pnpm run backend:run` + `pnpm run frontend:run` |
| Run all linting | `make lint` | `pnpm run lint:all` |
| Format all code | `make format` | `pnpm run format:all` |
| Run all type checks | `make typecheck` | `pnpm run typecheck:all` |
| Run all checks | `make check` | `pnpm run check` |
| Clean build artifacts | `make clean` | `pnpm run clean` |

## SSH Access

| Task | Make Command | pnpm Command |
|------|--------------|--------------|
| SSH to dev machine | `make ssh-dev` | `pnpm ssh:dev` |
| SSH to test machine | `make ssh-test` | `pnpm ssh:test` |

## 基础设施管理 (Infrastructure)

| Task | 新统一命令 | 说明 |
|------|------------|------|
| 启动本地基础设施 | `pnpm infra up` | 启动本地 Docker 服务 |
| 停止本地基础设施 | `pnpm infra down` | 停止本地 Docker 服务 |
| 部署基础设施到开发服务器 | `pnpm infra deploy` | 部署到 192.168.2.201 |
| 本地部署基础设施 | `pnpm infra deploy --local` | 本地容器化部署 |
| 查看基础设施日志 | `pnpm infra logs` | 查看服务日志 |
| 查看实时日志 | `pnpm infra logs --follow` | 实时跟踪日志 |
| 查看特定服务日志 | `pnpm infra logs --service postgres` | 查看指定服务 |
| 检查基础设施状态 | `pnpm infra status` | 健康检查 |

## 应用部署 (Application Deployment)

| Task | 新统一命令 | 说明 |
|------|------------|------|
| 部署所有应用服务 | `pnpm app` | 日常代码更新部署 |
| 构建并部署所有服务 | `pnpm app --build` | 依赖更新后部署 |
| 部署所有后端服务 | `pnpm app --type backend` | 后端整体部署 |
| 构建并部署后端 | `pnpm app --type backend --build` | 后端依赖更新 |
| 部署所有 Agent 服务 | `pnpm app --type agents` | Agent 批量部署 |
| 部署 API Gateway | `pnpm app --service api-gateway` | 单独部署 API |
| 构建并部署 API | `pnpm app --service api-gateway --build` | API 依赖更新 |
| 部署特定 Agent | `pnpm app --service research-agent` | 部署研究代理 |
| 显示部署帮助 | `pnpm app --help` | 查看所有选项 |

## Environment Variables

Both Make and pnpm commands support the same environment variables:

- `TEST_MACHINE_IP`: IP address of the test machine (default: 192.168.2.202)
- `SSH_USER`: SSH username (default: zhiyue)
- `DEV_SERVER`: Development server IP (default: 192.168.2.201) - for deployment commands
- `DEV_USER`: Development server SSH user (default: zhiyue) - for deployment commands

### Examples:

```bash
# Testing with custom machine
TEST_MACHINE_IP=192.168.2.100 make test-all
TEST_MACHINE_IP=192.168.2.100 pnpm run test:all

# SSH with custom user
SSH_USER=myuser pnpm ssh:dev

# Deploy to custom server
DEV_SERVER=192.168.2.100 pnpm app
DEV_SERVER=192.168.2.100 pnpm infra deploy
```

## Quick Start

```bash
# 1. Setup project (install all dependencies)
make setup
# or
./scripts/dev/setup-dev.sh

# 2. Start infrastructure services
pnpm infra up

# 3. Run development servers (in separate terminals)
pnpm run backend:run
pnpm run frontend:run

# Alternative: Run API Gateway with different configurations
pnpm run backend:api:simple  # Simple mode, no external service checks
pnpm run backend:api:local   # Local mode with .env.local
pnpm run backend:api:dev     # Dev mode connecting to 192.168.2.201

# 4. Deploy to development server (when ready)
pnpm infra deploy    # Deploy infrastructure first
pnpm app            # Then deploy application services

# 5. Run all tests
make test-all
# or
pnpm run test:all

# Show all available commands
make help
# or
pnpm run
```

## Tips

1. **Make** is generally shorter to type and provides colored output
2. **pnpm** commands are more explicit and integrate well with Node.js tooling
3. Both approaches are equally valid - choose based on your preference
4. Environment variables work the same way with both tools
5. **新部署系统**: 使用 `pnpm infra` 和 `pnpm app` 代替旧的复杂部署命令
6. **本地开发**: 先运行 `pnpm infra up` 启动基础设施，再启动应用服务
7. **生产部署**: 先部署基础设施 (`pnpm infra deploy`)，再部署应用 (`pnpm app`)
