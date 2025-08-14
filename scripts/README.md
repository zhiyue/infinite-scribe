# InfiniteScribe 脚本

按类别组织的开发、测试、部署和运维实用脚本。

## 目录结构

脚本按功能分类存放在不同子目录中。选择正确的目录有助于维护和查找。

### 新脚本放置指南

**在添加新脚本前，问自己：**

- 这个脚本的主要目的是什么？
- 它在开发生命周期的哪个阶段使用？
- 谁会使用它？（开发者/运维人员/CI/CD）

**放置原则：**

- 如果脚本**设置开发环境**或**辅助日常开发** → `dev/`
- 如果脚本**运行测试**或**验证代码质量** → `test/`
- 如果脚本**构建或部署应用** → `deploy/`
- 如果脚本**监控、维护或管理生产环境** → `ops/`
- 如果脚本是**通用工具**或**与外部系统集成** → `tools/`
- 如果脚本**特定于某个应用** → `apps/{backend|frontend}/scripts/`

### 开发环境 (`dev/`)

**作用：** 开发者日常使用的环境配置和辅助工具  
**适用脚本：** 环境安装、依赖管理、代码格式化、本地服务启动、开发工具配置  
**使用者：** 开发人员、新加入团队成员

#### `setup-dev.sh`

设置完整的开发环境，包括 Python 虚拟环境和依赖。

```bash
# 运行开发环境设置脚本
./scripts/dev/setup-dev.sh
```

#### `setup-pre-commit.sh`

配置代码质量检查的 pre-commit 钩子。

```bash
# 设置 pre-commit 钩子
./scripts/dev/setup-pre-commit.sh
```

#### `dev.py`

用于运行服务、测试和代码质量检查的开发辅助脚本。

```bash
# 运行 API Gateway
python scripts/dev/dev.py run api-gateway

# 运行特定代理
python scripts/dev/dev.py run worldsmith-agent

# 运行带覆盖率的测试
python scripts/dev/dev.py test --coverage

# 格式化代码
python scripts/dev/dev.py format
```

#### `verify-ruff.sh`

验证 Ruff 安装和配置。

```bash
# 验证 Ruff 设置
./scripts/dev/verify-ruff.sh
```

#### `install-check-deps.sh`

安装完整服务健康检查的依赖。

```bash
# 安装健康检查依赖
./scripts/dev/install-check-deps.sh
```

### 测试 (`test/`)

**作用：** 代码质量保证和自动化验证  
**适用脚本：** 单元测试、集成测试、代码检查、覆盖率分析、项目结构验证  
**使用者：** 开发人员、CI/CD 系统

**脚本说明：**

- **`run-tests.sh`** - 综合测试运行器（单元/集成/代码检查/覆盖率）
- **`test-project-structure.js`** - 项目结构验证
- **`test-frontend-local.sh`** - 前端特定本地测试

### 部署 (`deploy/`)

**作用：** 应用程序构建、打包和部署到目标环境  
**适用脚本：** Docker 构建、服务部署、基础设施配置、版本发布  
**使用者：** DevOps 工程师、CI/CD 系统、发布管理员

#### 统一命令入口

- **`infra.sh`** - 基础设施管理统一入口（部署、启停、日志、状态）
- **`app.sh`** - 应用部署统一入口（按类型或服务部署）

#### 底层脚本

- **`deploy-to-dev.sh`** - 底层应用部署脚本
- **`deploy-infrastructure.sh`** - 底层基础设施部署脚本
- **`build.sh`** - Docker 构建操作
- **`deploy-frontend*.sh`** - 前端部署变体

#### 统一命令系统

**基础设施管理：**

```bash
pnpm infra deploy                    # 部署到开发服务器
pnpm infra deploy --local            # 本地部署
pnpm infra deploy --local --clean    # 清除数据后本地部署
pnpm infra deploy --profile development  # 部署并启用maildev
pnpm infra up                        # 启动本地服务
pnpm infra down                      # 停止本地服务
pnpm infra logs --service postgres   # 查看PostgreSQL日志
pnpm infra status                    # 检查服务状态
```

**应用部署：**

```bash
pnpm app                              # 部署所有服务
pnpm app --build                      # 构建并部署所有服务
pnpm app --type backend               # 只部署后端服务
pnpm app --service api-gateway --build  # 构建并部署API网关
```

### 运维 (`ops/`)

**作用：** 生产环境监控、维护和故障排除  
**适用脚本：** 服务健康检查、日志管理、数据备份、性能监控、系统维护  
**使用者：** 运维工程师、系统管理员、值班人员

**脚本说明：**

- **`check-services*.js`** - 服务健康监控
- **`remote-logs.sh`** - 远程日志查看和过滤
- **`backup-dev-data.sh`** - 开发数据备份
- **`start-agents.sh`** - 代理服务管理

**快速运维命令：**

```bash
pnpm check:services          # 健康检查
pnpm logs:remote             # 查看日志
pnpm backup:dev              # 备份数据
```

### 工具 (`tools/`)

**作用：** 通用实用工具和第三方系统集成  
**适用脚本：** 代码生成、文档生成、数据迁移、外部服务集成、通用工具  
**使用者：** 所有团队成员、外部工具集成

**脚本说明：**

- **`hoppscotch-integration.sh`** - API 文档和 Hoppscotch 集合生成

### 应用特定脚本

**作用：** 针对特定应用模块的专用脚本  
**放置位置：**

- **后端脚本**: `apps/backend/scripts/` (API Gateway 启动、数据库工具)
- **前端脚本**: `apps/frontend/scripts/` (构建和测试自动化)

**何时使用：**

- 脚本仅用于单个应用模块
- 需要应用特定的配置或环境
- 与应用代码紧密耦合

## 脚本放置决策流程

```
新脚本需要放置在哪里？
│
├─ 是否仅用于单个应用（backend/frontend）？
│  └─ 是 → apps/{backend|frontend}/scripts/
│
├─ 主要用于开发环境设置或日常开发？
│  └─ 是 → scripts/dev/
│
├─ 用于运行测试或代码质量检查？
│  └─ 是 → scripts/test/
│
├─ 用于构建或部署应用？
│  └─ 是 → scripts/deploy/
│
├─ 用于生产环境监控或维护？
│  └─ 是 → scripts/ops/
│
└─ 是通用工具或外部集成？
   └─ 是 → scripts/tools/
```

**常见场景示例：**

- 新的数据库迁移脚本 → `apps/backend/scripts/`
- 新的代码格式化工具 → `scripts/dev/`
- 新的 E2E 测试运行器 → `scripts/test/`
- 新的容器构建脚本 → `scripts/deploy/`
- 新的日志分析工具 → `scripts/ops/`
- 新的 API 文档生成器 → `scripts/tools/`

## 快速命令

### 基础设施管理

```bash
# 本地开发
pnpm infra up                        # 启动本地基础设施服务
pnpm infra down                      # 停止本地基础设施服务
pnpm infra logs --follow             # 查看实时日志
pnpm infra status                    # 检查服务状态

# 部署到开发服务器
pnpm infra deploy                    # 部署基础设施到开发服务器
pnpm infra deploy --local            # 本地部署基础设施
pnpm infra deploy --clean            # 清除数据后重新部署
```

### 应用部署

```bash
# 应用部署
pnpm app                             # 部署所有应用服务
pnpm app --build                     # 构建并部署所有应用
pnpm app --type backend              # 只部署后端服务
pnpm app --service api-gateway       # 只部署API网关
```

### 开发和测试

```bash
# 设置环境
./scripts/dev/setup-dev.sh           # 设置开发环境
pnpm backend:install                 # 安装后端依赖
pnpm frontend:install                # 安装前端依赖

# 测试
pnpm test:all                        # 所有测试
pnpm test:coverage                   # 带覆盖率的测试
pnpm backend:test:unit               # 后端单元测试
pnpm frontend:test                   # 前端测试
```

### 监控和运维

```bash
# 服务监控
pnpm check:services                  # 快速健康检查
pnpm check:services:full             # 完整健康检查
pnpm logs:remote                     # 查看远程服务日志
pnpm backup:dev                      # 备份开发环境数据

# SSH 访问
pnpm ssh:dev                         # SSH 到开发服务器
pnpm ssh:test                        # SSH 到测试服务器
```

## 环境变量

- `DEV_SERVER` - 目标服务器 IP （默认: 192.168.2.201）
- `TEST_MACHINE_IP` - 测试服务器 IP （默认: 192.168.2.202）
- `DEV_USER` - SSH 用户 （默认: zhiyue）

## 要求

- 对开发/测试服务器的 SSH 访问权限
- Docker 和 Docker Compose
- Node.js 20+ 和 Python 3.11+ （带 uv）
- 环境文件 (deploy/environments/.env.\*)
- Docker Compose 配置 (deploy/docker-compose\*.yml)

## 故障排除

- **SSH 问题**: 检查 SSH 密钥和连接性
- **服务故障**: 运行 `pnpm check:services` 并查看日志
- **测试失败**: 使用 `make test-all` 和 Docker 容器
- **环境问题**: 运行 `./scripts/dev/setup-dev.sh` 重置环境
