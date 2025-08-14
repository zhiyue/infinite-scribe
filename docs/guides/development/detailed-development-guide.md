# 详细开发指南

本文档包含 InfiniteScribe 项目的详细开发配置信息，补充主 README 中的简化说明。

## 📋 目录

- [服务详细配置](#服务详细配置)
- [统一后端架构](#统一后端架构)
- [测试环境详细配置](#测试环境详细配置)
- [CI/CD 和代码质量](#cicd-和代码质量)
- [代码规范详细说明](#代码规范详细说明)
- [故障排除](#故障排除)
- [完整文档索引](#完整文档索引)

## 服务详细配置

### 完整服务端口映射

| 服务 | 端口 | 访问地址 | 默认凭证 | 说明 |
| --- | --- | --- | --- | --- |
| PostgreSQL | 5432 | `192.168.2.201:5432` | 用户: postgres / 密码: (见.env.infrastructure) | 主数据库 |
| Redis | 6379 | `192.168.2.201:6379` | 密码: (见.env.infrastructure) | 缓存和会话存储 |
| Neo4j Bolt | 7687 | `bolt://192.168.2.201:7687` | 用户: neo4j / 密码: (见.env.infrastructure) | 图数据库连接 |
| Neo4j Browser | 7474 | http://192.168.2.201:7474 | 同上 | 图数据库 Web 界面 |
| Kafka | 9092 | `192.168.2.201:9092` | 无认证 | 消息队列 |
| Zookeeper | 2181 | `192.168.2.201:2181` | 无认证 | Kafka 协调器 |
| Milvus | 19530 | `192.168.2.201:19530` | 无认证 | 向量数据库 |
| Milvus Metrics | 9091 | http://192.168.2.201:9091/metrics | 无认证 | 向量数据库监控 |
| MinIO API | 9000 | http://192.168.2.201:9000 | 用户: minioadmin / 密码: (见.env.infrastructure) | 对象存储 API |
| MinIO Console | 9001 | http://192.168.2.201:9001 | 同上 | 对象存储管理界面 |
| Prefect API | 4200 | http://192.168.2.201:4200/api | 无认证 | 工作流 API |
| Prefect UI | 4200 | http://192.168.2.201:4200 | 无认证 | 工作流管理界面 |

### Web UI 访问

以下服务提供 Web 界面：

- **Neo4j Browser**: http://192.168.2.201:7474 - 图数据库查询界面
- **MinIO Console**: http://192.168.2.201:9001 - 对象存储管理界面
- **Prefect UI**: http://192.168.2.201:4200 - 工作流编排管理界面

### 网络要求

- 所有服务仅在内网可访问（192.168.2.0/24 网段）
- 确保您的开发机器与服务器在同一网络中
- 防火墙已配置允许上述端口的访问

## 统一后端架构

InfiniteScribe 采用统一的后端架构，所有后端服务（API Gateway 和各种 Agent）共享一个代码库和依赖配置。

### 服务类型

通过 `SERVICE_TYPE` 环境变量选择要运行的服务：

- `api-gateway` - API 网关服务
- `agent-worldsmith` - 世界铸造师 Agent
- `agent-plotmaster` - 剧情策划师 Agent
- `agent-outliner` - 大纲规划师 Agent
- `agent-director` - 导演 Agent
- `agent-characterexpert` - 角色专家 Agent
- `agent-worldbuilder` - 世界观构建师 Agent
- `agent-writer` - 作家 Agent
- `agent-critic` - 评论家 Agent
- `agent-factchecker` - 事实核查员 Agent
- `agent-rewriter` - 改写者 Agent

### 运行后端服务

```bash
# 进入后端目录
cd apps/backend

# 安装Python依赖（使用 uv）
uv venv
source .venv/bin/activate  # Linux/macOS
uv sync --dev

# 运行 API Gateway
SERVICE_TYPE=api-gateway uvicorn src.api.main:app --reload

# 运行特定 Agent
SERVICE_TYPE=agent-worldsmith python -m src.agents.worldsmith.main
```

### Docker 部署

统一的 Dockerfile 支持所有服务：

```bash
# 构建镜像
docker build -t infinite-scribe-backend apps/backend/

# 运行 API Gateway
docker run -e SERVICE_TYPE=api-gateway -p 8000:8000 infinite-scribe-backend

# 运行 Agent
docker run -e SERVICE_TYPE=agent-worldsmith infinite-scribe-backend
```

## 测试环境详细配置

### 测试环境说明

**重要**: 所有测试必须在测试服务器 (192.168.2.202) 上运行，开发服务器 (192.168.2.201) 仅用于开发，不可运行任何测试。

测试服务器支持两种模式：
- **预部署服务模式 (--remote)**: 连接到测试服务器上预先部署的服务
- **Docker 容器模式 (--docker-host)**: 使用测试服务器的 Docker 创建临时容器

### 配置测试服务器

```bash
# 使用默认测试服务器 (192.168.2.202)
./scripts/run-tests.sh --all --remote

# 使用自定义测试服务器
export TEST_MACHINE_IP=192.168.2.100
./scripts/run-tests.sh --all --remote
```

### 前端测试

```bash
# 运行所有测试
pnpm test

# 运行特定包的测试
pnpm --filter <package-name> test
```

### 后端测试

#### 默认行为

```bash
# 不带任何标志：运行单元测试 + 代码检查
./scripts/test/run-tests.sh

# 等同于：
./scripts/test/run-tests.sh --unit --lint
```

#### 使用预部署服务 (--remote)

```bash
# 运行所有测试 + 代码检查（使用测试服务器上的预部署服务）
./scripts/test/run-tests.sh --all --remote

# 仅运行单元测试（不含代码检查）
./scripts/test/run-tests.sh --unit --remote

# 仅运行集成测试（不含代码检查）
./scripts/test/run-tests.sh --integration --remote

# 运行所有测试 + 生成覆盖率报告（包含代码检查）
./scripts/test/run-tests.sh --all --remote --coverage

# 运行单元测试 + 生成覆盖率报告（不含代码检查）
./scripts/test/run-tests.sh --unit --remote --coverage
```

#### 使用 Docker 容器 (--docker-host)

```bash
# 运行所有测试 + 代码检查（使用测试服务器的 Docker）
./scripts/test/run-tests.sh --all --docker-host

# 仅运行单元测试（不含代码检查）
./scripts/test/run-tests.sh --unit --docker-host

# 仅运行集成测试（不含代码检查）
./scripts/test/run-tests.sh --integration --docker-host

# 运行所有测试 + 生成覆盖率报告（包含代码检查）
./scripts/test/run-tests.sh --all --docker-host --coverage

# 运行集成测试 + 生成覆盖率报告（不含代码检查）
./scripts/test/run-tests.sh --integration --docker-host --coverage
```

#### 代码检查控制

```bash
# 仅运行代码质量检查（linting + type checking）
./scripts/test/run-tests.sh --lint

# 运行所有测试但跳过代码检查
./scripts/test/run-tests.sh --all --remote --no-lint

# 注意：--unit 和 --integration 默认不运行代码检查
# 只有 --all 或无标志时才默认运行代码检查
```

#### 测试行为总结

| 命令标志 | 单元测试 | 集成测试 | 代码检查 | 说明 |
| --- | --- | --- | --- | --- |
| 无标志 | ✓ | ✗ | ✓ | 默认行为 |
| `--unit` | ✓ | ✗ | ✗ | 仅单元测试 |
| `--integration` | ✗ | ✓ | ✗ | 仅集成测试 |
| `--all` | ✓ | ✓ | ✓ | 完整测试套件 |
| `--lint` | ✗ | ✗ | ✓ | 仅代码检查 |
| `--all --no-lint` | ✓ | ✓ | ✗ | 所有测试，无代码检查 |

#### 查看帮助

```bash
# 查看所有可用选项
./scripts/test/run-tests.sh --help
```

## CI/CD 和代码质量

### Pre-commit Hooks

项目使用 pre-commit 自动检查代码质量：

```bash
# 初始化 pre-commit（首次设置，已包含在 setup-dev.sh 中）
./scripts/dev/setup-pre-commit.sh

# 或者直接运行（如果已安装依赖）
pre-commit install

# 手动运行所有检查
pre-commit run --all-files

# 更新 hooks 版本
pre-commit autoupdate
```

Pre-commit 会在每次提交时自动运行：
- **Ruff**: Python 代码检查和格式化
- **Mypy**: 静态类型检查
- **Bandit**: 安全漏洞扫描
- **Hadolint**: Dockerfile 检查
- 更多检查项见 `.pre-commit-config.yaml`

### GitHub Actions CI

每次推送到 `main` 或 `develop` 分支时，自动运行：
- 代码格式和质量检查
- 单元测试和集成测试
- 安全漏洞扫描
- 测试覆盖率报告

详细配置见 `.github/workflows/python-ci.yml`

## 代码规范详细说明

### 通用规范

- **禁止硬编码**: 永远不要硬编码 IP 地址、端口、密码等配置值
- **使用环境变量**: 所有环境相关的配置必须可通过环境变量覆盖
- **提供默认值**: 使用合理的默认值，但允许通过环境变量修改
- **示例**: `TEST_MACHINE_IP="${TEST_MACHINE_IP:-192.168.2.202}"`

### JavaScript/TypeScript

项目使用 ESLint 和 Prettier 确保前端代码质量：

```bash
# 运行代码检查
pnpm lint

# 格式化代码
pnpm format
```

### Python

后端使用 Ruff、Black 和 Mypy：

```bash
# 激活虚拟环境
source .venv/bin/activate

# 运行 Ruff 检查（包括导入排序）
ruff check apps/backend/

# 自动修复问题
ruff check --fix apps/backend/

# 格式化代码
black apps/backend/

# 类型检查
mypy apps/backend/src/
```

所有代码规范通过 pre-commit hooks 自动执行。

### 提交规范

使用约定式提交（Conventional Commits）：
- `feat:` 新功能
- `fix:` 修复bug
- `docs:` 文档更新
- `style:` 代码格式（不影响代码运行的变动）
- `refactor:` 重构
- `test:` 测试相关
- `chore:` 构建过程或辅助工具的变动

## 故障排除

### 服务无法连接

```bash
# 检查服务状态
pnpm check:services

# 查看特定服务日志
ssh zhiyue@192.168.2.201 "cd ~/workspace/mvp/infinite-scribe && docker compose logs [service-name]"

# 重启所有服务
ssh zhiyue@192.168.2.201 "cd ~/workspace/mvp/infinite-scribe && docker compose restart"
```

### 常见问题

1. **PostgreSQL 连接被拒绝**: 检查 .env.infrastructure 中的密码配置
2. **Redis 认证失败**: 确保使用正确的密码（REDIS_PASSWORD）
3. **Kafka 无法连接**: 检查 KAFKA_ADVERTISED_LISTENERS 配置
4. **MinIO bucket 不存在**: 服务启动时会自动创建 novels bucket
5. **Prefect 无法访问**: 确保 PostgreSQL 正常运行（Prefect 依赖它）

### 开发环境重置

```bash
# 停止所有服务
pnpm infra:down

# 清理所有数据卷（谨慎使用！）
docker compose --env-file .env.infrastructure down -v

# 重新启动服务
pnpm infra:up

# 检查服务状态
pnpm check:services
```

## 完整文档索引

### 架构和设计
- [架构设计](../architecture/)
- [产品需求文档](../prd/)
- [前端规范](../front-end-spec.md)
- [API文档](../architecture/rest-api-spec.md)

### 开发指南
- [Python 开发快速入门](./python-dev-quickstart.md)
- [环境变量配置指南](../deployment/environment-variables.md)
- [环境变量结构说明](../deployment/environment-structure.md)
- [Python 依赖管理](./python-dependency-management.md)
- [Python 导入最佳实践](./python-import-best-practices.md)
- [Docker 架构说明](./docker-architecture.md)
- [CI/CD 和 Pre-commit 配置](./ci-cd-and-pre-commit.md)
- [本地开发调试指南](./local-development-guide.md)
- [类型检查配置指南](./type-checking-setup.md)
- [Pyright 与 Mypy 兼容性](./pyright-mypy-compatibility.md)
- [VSCode Ruff 格式化设置](./vscode-ruff-setup.md)

### 测试和质量
- [测试最佳实践](../testing-best-practices.md)
- [测试迁移示例](../testing-migration-example.md)

### 部署和运维
- [部署指南](../deployment/)
- [运维文档](../operations/)

### 项目管理
- [用户故事](../stories/)
- [Scrum 相关](../scrum/)

---

**注意**: 本文档包含项目的详细技术配置信息，主要面向开发人员和系统管理员。日常开发请参考主 README 文件中的简化说明。 