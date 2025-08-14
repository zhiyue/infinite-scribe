# Scripts 目录重新组织总结

## 📋 概述

为了更好地管理和维护 InfiniteScribe 项目的脚本，我们对 `scripts/` 目录进行了重新组织，按功能将脚本分类到不同的子目录中。

## 🗂️ 新的目录结构

```
scripts/
├── README.md
├── dev/          # 开发环境设置
│   ├── dev.py           # 开发辅助脚本
│   ├── install-check-deps.sh
│   ├── setup-dev.sh
│   ├── setup-pre-commit.sh
│   ├── sync-frontend-env.sh
│   └── verify-ruff.sh
├── deploy/          # 部署相关
│   ├── build.sh
│   ├── deploy-frontend.sh
│   ├── deploy-frontend-compose.sh
│   ├── deploy-infrastructure.sh
│   └── deploy-to-dev.sh
├── ops/          # 监控维护
│   ├── backup-dev-data.sh
│   ├── check-services-simple.js
│   ├── check-services.js
│   ├── remote-logs.sh
│   └── start-agents.sh
├── test/            # 测试相关
│   ├── run-tests.sh
│   ├── test-frontend-local.sh
│   └── test-project-structure.js
├── tools/           # 工具相关
│   └── hoppscotch-integration.sh
└── db/              # 数据库相关
    ├── run_migrations.py
    └── verify_db_migration.py
```

## 🔄 脚本分类详情

### Development & Setup (`dev/`)
开发环境设置和配置相关脚本：
- `setup-dev.sh` - 设置完整开发环境
- `setup-pre-commit.sh` - 配置 pre-commit hooks
- `dev.py` - 开发辅助脚本（运行服务、测试、代码检查等）
- `verify-ruff.sh` - 验证 Ruff 配置
- `install-check-deps.sh` - 安装健康检查依赖

### Testing (`test/`)
测试和验证相关脚本：
- `run-tests.sh` - 综合测试运行器
- `test-project-structure.js` - 项目结构验证

### Deployment (`deploy/`)
部署相关脚本：
- `deploy-to-dev.sh` - 部署到开发服务器
- `deploy-infrastructure.sh` - 部署基础设施服务

### Operations & Maintenance (`ops/`)
监控和维护相关脚本：
- `check-services.js` / `check-services-simple.js` - 服务健康检查
- `remote-logs.sh` - 查看远程日志
- `backup-dev-data.sh` - 备份开发数据


## 📝 更新的文件

### 文档更新
以下文档已更新以反映新的脚本路径：

- `scripts/README.md` - 重写为分类结构文档
- `README.md` - 更新所有脚本引用路径
- `docs/development/python-dev-quickstart.md`
- `docs/development/vscode-ruff-setup.md`
- `docs/development/local-development-guide.md`
- `docs/operations/service-health-check.md`
- `docs/deployment/environment-variables.md`
- `docs/scrum/monorepo-update-summary.md`
- `docs/development/MONOREPO_SIMPLIFICATION_SUMMARY.md`
- `docs/development/python-monorepo-setup.md`

### 配置文件更新
- `package.json` - 更新所有脚本路径引用

## 🚨 路径变更对照表

| 旧路径 | 新路径 | 分类 |
|--------|--------|------|
| `scripts/setup-dev.sh` | `scripts/dev/setup-dev.sh` | Development |
| `scripts/setup-pre-commit.sh` | `scripts/dev/setup-pre-commit.sh` | Development |
| `scripts/dev.py` | `scripts/dev/dev.py` | Development |
| `scripts/verify-ruff.sh` | `scripts/dev/verify-ruff.sh` | Development |
| `scripts/install-check-deps.sh` | `scripts/dev/install-check-deps.sh` | Development |
| `sync-frontend-env.sh` | `scripts/dev/sync-frontend-env.sh` | Development |
| `scripts/run-tests.sh` | `scripts/test/run-tests.sh` | Testing |
| `scripts/test-project-structure.js` | `scripts/test/test-project-structure.js` | Testing |
| `test-frontend-local.sh` | `scripts/test/test-frontend-local.sh` | Testing |
| `scripts/deploy-to-dev.sh` | `scripts/deploy/deploy-to-dev.sh` | Deployment |
| `scripts/deploy-infrastructure.sh` | `scripts/deploy/deploy-infrastructure.sh` | Deployment |
| `scripts/docker/build.sh` | `scripts/deploy/build.sh` | Deployment |
| `deploy-frontend.sh` | `scripts/deploy/deploy-frontend.sh` | Deployment |
| `deploy-frontend-compose.sh` | `scripts/deploy/deploy-frontend-compose.sh` | Deployment |
| `scripts/check-services.js` | `scripts/ops/check-services.js` | Operations |
| `scripts/check-services-simple.js` | `scripts/ops/check-services-simple.js` | Operations |
| `scripts/remote-logs.sh` | `scripts/ops/remote-logs.sh` | Operations |
| `scripts/backup-dev-data.sh` | `scripts/ops/backup-dev-data.sh` | Operations |
| `start-agents.sh` | `scripts/ops/start-agents.sh` | Operations |
| `hoppscotch-integration.sh` | `scripts/tools/hoppscotch-integration.sh` | Tools |
| `run_migrations.py` | `scripts/db/run_migrations.py` | Database |
| `verify_db_migration.py` | `scripts/db/verify_db_migration.py` | Database |

## ✅ pnpm 脚本命令（保持不变）

为了向后兼容，所有 `pnpm` 命令保持不变：

```bash
# 开发环境
pnpm setup:dev              # setup-dev.sh
pnpm setup:pre-commit       # setup-pre-commit.sh

# 测试
pnpm test                    # run-tests.sh
pnpm test:structure          # test-project-structure.js

# 基础设施管理
pnpm infra:deploy            # deploy-infrastructure.sh
pnpm deploy:dev              # deploy-to-dev.sh

# 监控
pnpm check:services          # check-services-simple.js
pnpm check:services:full     # check-services.js
pnpm logs:remote             # remote-logs.sh
pnpm backup:dev              # backup-dev-data.sh
```

## 🎯 优势

1. **更好的组织**: 脚本按功能分类，更容易找到和维护
2. **清晰的职责**: 每个目录有明确的功能范围
3. **便于扩展**: 新脚本可以轻松放入合适的分类
4. **保持兼容**: pnpm 命令保持不变，确保向后兼容
5. **文档同步**: 所有相关文档已同步更新

## 🔄 迁移影响

### 开发者需要注意
- 直接调用脚本时需要使用新路径
- pnpm 命令保持不变，推荐使用 pnpm 命令
- IDE 中的配置可能需要更新路径

### CI/CD 影响
- 如果 CI 脚本直接引用了脚本路径，需要更新
- GitHub Actions 等可能需要更新脚本路径

## 📅 变更记录

- **日期**: 2024-06-28
- **类型**: 重构
- **影响**: 脚本路径变更，文档更新
- **向后兼容**: pnpm 命令保持兼容 