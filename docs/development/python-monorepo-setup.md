# Python Monorepo 开发环境配置指南

## 概述

本项目使用 monorepo 结构，包含多个 Python 服务（API Gateway、各种 Agent 服务）。每个服务都有独立的 `pyproject.toml`，使用 `uv` 作为包管理器。

## 目录结构

```
infinite-scribe/
├── apps/
│   ├── api-gateway/
│   │   ├── pyproject.toml          # API 网关依赖
│   │   ├── .venv/                  # 独立虚拟环境
│   │   └── app/
│   ├── worldsmith-agent/
│   │   ├── pyproject.toml          # 世界铸造师依赖
│   │   ├── .venv/                  # 独立虚拟环境
│   │   └── agent/
│   └── ... (其他 agent 服务)
├── packages/                        # 共享包
│   └── shared-types/
│       ├── pyproject.toml          # 共享类型定义
│       └── src/
├── pyproject.toml                  # 根目录配置（可选）
└── .python-version                 # Python 版本锁定
```

## 1. 安装开发工具

### 1.1 安装 uv

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# 或使用 pip
pip install uv
```

### 1.2 设置 Python 版本

```bash
# 在项目根目录创建 .python-version
echo "3.11.8" > .python-version

# uv 会自动使用这个版本
```

## 2. 开发工作流

### 2.1 初始化服务环境

```bash
# 为每个服务创建独立的虚拟环境
cd apps/api-gateway
uv venv
uv sync --dev  # 安装包括开发依赖

cd ../worldsmith-agent
uv venv
uv sync --dev
```

### 2.2 激活虚拟环境

```bash
# 方式1：直接激活
cd apps/api-gateway
source .venv/bin/activate  # Linux/macOS
# 或
.venv\Scripts\activate     # Windows

# 方式2：使用 uv run（推荐）
cd apps/api-gateway
uv run uvicorn app.main:app --reload
```

## 3. 管理共享依赖

### 3.1 创建共享包

```toml
# packages/shared-types/pyproject.toml
[project]
name = "infinite-scribe-shared"
version = "0.1.0"
description = "Shared types and utilities"
dependencies = [
    "pydantic~=2.11.7",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

### 3.2 在服务中使用共享包

```toml
# apps/api-gateway/pyproject.toml
[project]
name = "api-gateway"
dependencies = [
    "fastapi~=0.115.13",
    "infinite-scribe-shared @ file://../../packages/shared-types",
]
```

## 4. 开发脚本

### 4.1 根目录脚本管理

创建 `scripts/dev.sh`：

```bash
#!/bin/bash
# 开发环境管理脚本

case "$1" in
    "install-all")
        echo "Installing all services..."
        for service in apps/*/; do
            if [ -f "$service/pyproject.toml" ]; then
                echo "Installing $service"
                (cd "$service" && uv venv && uv sync --dev)
            fi
        done
        ;;
    
    "update-all")
        echo "Updating all services..."
        for service in apps/*/; do
            if [ -f "$service/pyproject.toml" ]; then
                echo "Updating $service"
                (cd "$service" && uv sync --dev --upgrade)
            fi
        done
        ;;
    
    "run")
        service=$2
        shift 2
        echo "Running $service..."
        (cd "apps/$service" && uv run "$@")
        ;;
    
    *)
        echo "Usage: $0 {install-all|update-all|run <service> <command>}"
        exit 1
        ;;
esac
```

### 4.2 使用开发脚本

```bash
# 安装所有服务的依赖
./scripts/dev.sh install-all

# 更新所有依赖
./scripts/dev.sh update-all

# 运行特定服务
./scripts/dev.sh run api-gateway uvicorn app.main:app --reload
./scripts/dev.sh run worldsmith-agent python -m agent.main
```

## 5. VS Code 配置

### 5.1 多根工作区配置

创建 `.vscode/infinite-scribe.code-workspace`：

```json
{
    "folders": [
        {
            "name": "Root",
            "path": ".."
        },
        {
            "name": "API Gateway",
            "path": "../apps/api-gateway"
        },
        {
            "name": "Worldsmith Agent",
            "path": "../apps/worldsmith-agent"
        }
    ],
    "settings": {
        "python.defaultInterpreterPath": "${workspaceFolder}/.venv/bin/python",
        "python.terminal.activateEnvironment": true,
        "python.linting.enabled": true,
        "python.linting.ruffEnabled": true,
        "python.formatting.provider": "black",
        "[python]": {
            "editor.formatOnSave": true,
            "editor.codeActionsOnSave": {
                "source.organizeImports": true
            }
        }
    }
}
```

### 5.2 服务特定设置

每个服务目录下的 `.vscode/settings.json`：

```json
{
    "python.defaultInterpreterPath": "${workspaceFolder}/.venv/bin/python",
    "python.terminal.activateEnvironment": true
}
```

## 6. 依赖管理最佳实践

### 6.1 版本锁定

```bash
# 生成锁文件
cd apps/api-gateway
uv lock

# 提交 uv.lock 到版本控制
git add uv.lock
```

### 6.2 依赖更新策略

```toml
# pyproject.toml - 使用兼容版本
[project]
dependencies = [
    "fastapi~=0.115.13",     # 允许 0.115.x
    "pydantic>=2.11,<3",     # 允许 2.x 但不允许 3.0
    "asyncpg==0.30.0",       # 精确版本
]
```

## 7. 常见命令

```bash
# 添加新依赖
cd apps/api-gateway
uv add fastapi

# 添加开发依赖
uv add --dev pytest pytest-asyncio

# 移除依赖
uv remove package-name

# 显示依赖树
uv tree

# 运行测试
uv run pytest

# 运行脚本
uv run python scripts/migrate.py
```

## 8. Docker 集成

### 8.1 Dockerfile 模板

```dockerfile
# apps/api-gateway/Dockerfile
FROM python:3.11-slim as builder

# 安装 uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# 设置工作目录
WORKDIR /app

# 复制依赖文件
COPY pyproject.toml uv.lock ./

# 安装依赖
RUN uv sync --frozen --no-dev

# 运行阶段
FROM python:3.11-slim

WORKDIR /app

# 复制虚拟环境
COPY --from=builder /app/.venv ./.venv

# 复制应用代码
COPY app ./app

# 设置环境变量
ENV PATH="/app/.venv/bin:$PATH"

# 运行应用
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## 9. 环境变量管理

### 9.1 服务特定环境变量

```bash
# apps/api-gateway/.env
DATABASE_URL=postgresql://user:pass@localhost/db
REDIS_URL=redis://localhost:6379

# apps/worldsmith-agent/.env
OPENAI_API_KEY=sk-...
MODEL_NAME=gpt-4
```

### 9.2 使用 python-dotenv

```python
# app/core/config.py
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# 加载服务特定的 .env 文件
load_dotenv()

class Settings(BaseSettings):
    database_url: str
    redis_url: str
    
    class Config:
        env_file = ".env"
```

## 10. 故障排除

### 常见问题

1. **虚拟环境冲突**
   ```bash
   # 清理并重建
   rm -rf .venv
   uv venv
   uv sync
   ```

2. **共享包更新未生效**
   ```bash
   # 强制重新安装
   uv sync --reinstall-package infinite-scribe-shared
   ```

3. **Python 版本不匹配**
   ```bash
   # 检查并设置正确版本
   uv python install 3.11.8
   uv venv --python 3.11.8
   ```

## 总结

- 每个服务维护独立的虚拟环境和依赖
- 使用 `uv` 统一管理包和虚拟环境
- 共享代码通过本地包引用
- 开发脚本简化多服务管理
- Docker 构建优化依赖缓存

这种方式既保持了服务的独立性，又能高效地管理整个 monorepo。