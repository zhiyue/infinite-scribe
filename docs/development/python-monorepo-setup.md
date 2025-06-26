# Python Monorepo 开发环境配置指南 v3 (简化版)

## 核心理念

- **一个 pyproject.toml**：根目录维护唯一的依赖文件
- **一个虚拟环境**：所有开发工作使用根目录的 `.venv`
- **简单直接**：开发和部署使用相同的依赖配置

> **重要更新:** 后端服务（API Gateway和所有Agent）已整合到 `apps/backend/` 统一代码库中。通过 `SERVICE_TYPE` 环境变量选择运行的服务。

## 项目结构

```
infinite-scribe/
├── .venv/                          # 统一虚拟环境
├── pyproject.toml                  # 唯一的依赖配置文件
├── uv.lock                         # 依赖锁文件
├── .python-version                 # Python 版本 (3.11)
├── apps/
│   ├── frontend/
│   │   └── ...
│   └── backend/
│       ├── Dockerfile             # 统一的Dockerfile
│       ├── pyproject.toml          # 后端统一依赖
│       └── src/
│           ├── api/              # API Gateway
│           ├── agents/           # 所有Agent服务
│           ├── core/             # 核心配置
│           └── common/           # 共享逻辑
└── packages/
    └── shared-types/
        └── src/
```

## 1. 快速开始

### 1.1 初始化环境

```bash
# 在项目根目录
uv venv
uv sync --dev
source .venv/bin/activate  # Linux/macOS
```

### 1.2 运行服务

```bash
# API Gateway
cd apps/backend
uvicorn src.api.main:app --reload

# Agent 服务
python -m src.agents.worldsmith.main
python -m src.agents.plotmaster.main

# 或通过环境变量
SERVICE_TYPE=api-gateway uvicorn src.api.main:app --reload
SERVICE_TYPE=agent-worldsmith python -m src.agents.worldsmith.main
```

## 2. 根目录 pyproject.toml

```toml
# /pyproject.toml
[project]
name = "infinite-scribe"
version = "0.1.0"
description = "Infinite Scribe - AI-powered novel creation platform"
requires-python = ">=3.11"

dependencies = [
    # Core
    "fastapi~=0.115.13",
    "pydantic~=2.11.7",
    "uvicorn[standard]~=0.32.0",
    
    # Databases
    "asyncpg~=0.30.0",
    "neo4j~=5.26.0",
    "redis~=5.2.0",
    
    # AI/ML
    "openai~=1.54.0",
    "anthropic~=0.39.0",
    "litellm~=1.52.0",
    
    # Infrastructure
    "aiokafka~=0.11.0",
    "prefect~=2.19.0",
    "minio~=7.2.10",
    
    # Utils
    "python-dotenv~=1.0.1",
    "structlog~=24.4.0",
    "httpx~=0.27.0",
]

[project.optional-dependencies]
dev = [
    "pytest~=8.3.3",
    "pytest-asyncio~=0.24.0",
    "pytest-cov~=6.0.0",
    "ruff~=0.7.2",
    "black~=24.10.0",
    "mypy~=1.13.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.pytest.ini_options]
pythonpath = [
    ".",
    "apps/api-gateway",
    "apps/worldsmith-agent",
    "packages/shared-types/src",
]
```

## 3. Docker 构建

### 3.1 统一的 Dockerfile 模板

```dockerfile
# apps/api-gateway/Dockerfile
FROM python:3.11-slim as builder

# 安装 uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# 复制根目录的依赖文件
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

FROM python:3.11-slim

WORKDIR /app

# 复制虚拟环境和应用代码
COPY --from=builder /app/.venv ./.venv
COPY apps/api-gateway/app ./app

ENV PATH="/app/.venv/bin:$PATH"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 3.2 Docker Compose 配置

```yaml
# docker-compose.yml
services:
  api-gateway:
    build:
      context: .  # 使用根目录作为构建上下文
      dockerfile: apps/api-gateway/Dockerfile
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://...
```

## 4. 开发工具脚本

创建 `scripts/dev.py`:

```python
#!/usr/bin/env python
"""开发辅助脚本"""
import subprocess
import sys
from pathlib import Path

SERVICES = {
    "api-gateway": {
        "module": "apps.api-gateway.app.main",
        "command": "uvicorn {module}:app --reload --port 8000"
    },
    "worldsmith-agent": {
        "module": "apps.worldsmith-agent.agent.main",
        "command": "python -m {module}"
    },
}

def run_service(service_name):
    """运行指定服务"""
    if service_name not in SERVICES:
        print(f"Unknown service: {service_name}")
        sys.exit(1)
    
    service = SERVICES[service_name]
    command = service["command"].format(module=service["module"])
    subprocess.run(command, shell=True)

def test(service_name=None):
    """运行测试"""
    if service_name:
        cmd = f"pytest apps/{service_name}/tests -v"
    else:
        cmd = "pytest -v"
    subprocess.run(cmd, shell=True)

def lint():
    """代码检查"""
    subprocess.run("ruff check . && black --check .", shell=True)

def format_code():
    """格式化代码"""
    subprocess.run("ruff check --fix . && black .", shell=True)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")
    
    # run
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("service", choices=SERVICES.keys())
    
    # test
    test_parser = subparsers.add_parser("test")
    test_parser.add_argument("service", nargs="?")
    
    # lint & format
    subparsers.add_parser("lint")
    subparsers.add_parser("format")
    
    args = parser.parse_args()
    
    if args.command == "run":
        run_service(args.service)
    elif args.command == "test":
        test(args.service)
    elif args.command == "lint":
        lint()
    elif args.command == "format":
        format_code()
```

## 5. IDE 配置

### VS Code
`.vscode/settings.json`:
```json
{
    "python.defaultInterpreterPath": "${workspaceFolder}/.venv/bin/python",
    "python.analysis.extraPaths": [
        "${workspaceFolder}/apps/api-gateway",
        "${workspaceFolder}/apps/worldsmith-agent",
        "${workspaceFolder}/packages/shared-types/src"
    ]
}
```

### PyCharm
- Project Interpreter: `/path/to/project/.venv/bin/python`
- Mark as Sources Root: 每个 `apps/*/` 目录

## 6. 常用命令

```bash
# 依赖管理
uv add fastapi                    # 添加依赖
uv add --dev pytest              # 添加开发依赖
uv sync --dev                    # 同步所有依赖
uv sync --dev --upgrade          # 升级依赖

# 运行
python scripts/dev.py run api-gateway
python scripts/dev.py test
python scripts/dev.py format

# 直接运行
uvicorn apps.api-gateway.app.main:app --reload
pytest apps/api-gateway/tests -v
```

## 优势

1. **极简配置**：一个 pyproject.toml 管理所有依赖
2. **一致性**：开发和生产使用相同的依赖定义
3. **易维护**：不需要同步多个文件
4. **快速上手**：新开发者只需要 `uv sync --dev` 即可开始

## 注意事项

- 所有依赖都在根目录的 pyproject.toml 中管理
- Docker 构建时使用根目录作为上下文
- 确保 uv.lock 文件提交到版本控制
- 使用 `uv sync --frozen` 确保依赖版本一致性