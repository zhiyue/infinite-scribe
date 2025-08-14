# InfiniteScribe 脚本

按类别组织的开发、测试、部署和运维实用脚本。

## 目录结构

### 开发环境 (`dev/`)
环境设置和开发工具。

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
测试运行器和验证脚本。

- **`run-tests.sh`** - 综合测试运行器（单元/集成/代码检查/覆盖率）
- **`test-project-structure.js`** - 项目结构验证
- **`test-frontend-local.sh`** - 前端特定本地测试

### 部署 (`deploy/`)
部署和构建脚本。

- **`deploy-to-dev.sh`** - 主部署脚本（所有服务）
- **`deploy-infrastructure.sh`** - 仅基础设施部署
- **`build.sh`** - Docker 构建操作
- **`deploy-frontend*.sh`** - 前端部署变体

**快速部署命令：**
```bash
make deploy                  # 日常代码部署
make deploy-build            # 重新构建并部署
make deploy-api              # 只部署 API Gateway
```

### 运维 (`ops/`)
监控、日志和备份脚本。

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

### 应用特定脚本
- **后端脚本**: `apps/backend/scripts/` (API Gateway 启动、数据库工具)
- **前端脚本**: `apps/frontend/scripts/` (构建和测试自动化)

### 工具 (`tools/`)
实用工具和集成脚本。

- **`hoppscotch-integration.sh`** - API 文档和 Hoppscotch 集合生成


## 快速命令

```bash
# 设置
make setup                   # 安装依赖
make dev                     # 启动开发服务器

# 测试
make test-all                # 所有测试
make test-coverage           # 带覆盖率的测试

# 部署
make deploy                  # 部署到开发服务器
make ssh-dev                 # SSH 到开发服务器

# 监控
pnpm check:services          # 健康检查
pnpm logs:remote             # 查看日志
pnpm backup:dev              # 备份数据
```

## 环境变量

- `DEV_SERVER` - 目标服务器 IP （默认: 192.168.2.201）
- `TEST_MACHINE_IP` - 测试服务器 IP （默认: 192.168.2.202）
- `DEV_USER` - SSH 用户 （默认: zhiyue）

## 要求

- 对开发/测试服务器的 SSH 访问权限
- Docker 和 Docker Compose
- Node.js 20+ 和 Python 3.11+ （带 uv）
- 环境文件 (.env.*, docker-compose.yml)

## 故障排除

- **SSH 问题**: 检查 SSH 密钥和连接性
- **服务故障**: 运行 `pnpm check:services` 并查看日志
- **测试失败**: 使用 `make test-all` 和 Docker 容器
- **环境问题**: 运行 `./scripts/dev/setup-dev.sh` 重置环境