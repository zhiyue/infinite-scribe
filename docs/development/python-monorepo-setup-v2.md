# Python Monorepo 开发环境配置指南 v2

## 核心理念

- **开发时**：使用根目录的统一虚拟环境，包含所有服务的依赖
- **部署时**：每个服务使用自己的 `pyproject.toml` 独立打包

## 推荐的项目结构

```
infinite-scribe/
├── .venv/                          # 统一的开发虚拟环境
├── pyproject.toml                  # 开发环境的主配置（包含所有依赖）
├── uv.lock                         # 开发环境的锁文件
├── .python-version                 # Python 版本 (3.11)
├── apps/
│   ├── api-gateway/
│   │   ├── pyproject.toml         # 部署用（仅包含该服务依赖）
│   │   ├── Dockerfile
│   │   └── app/
│   ├── worldsmith-agent/
│   │   ├── pyproject.toml         # 部署用
│   │   ├── Dockerfile
│   │   └── agent/
│   └── ...
├── packages/
│   └── shared-types/
│       └── src/
└── scripts/
    └── dev.py                      # 开发辅助脚本
```

## 1. 根目录 pyproject.toml 配置

创建包含所有服务依赖的主配置文件：

```toml
# /pyproject.toml
[project]
name = "infinite-scribe-dev"
version = "0.1.0"
description = "Development environment for Infinite Scribe monorepo"
requires-python = ">=3.11"

# 合并所有服务的依赖
dependencies = [
    # API Gateway
    "fastapi~=0.115.13",
    "pydantic~=2.11.7",
    "uvicorn[standard]~=0.32.0",
    "asyncpg~=0.30.0",
    "neo4j~=5.26.0",
    "python-dotenv~=1.0.1",
    "httpx~=0.27.0",
    
    # Agent 共同依赖
    "openai~=1.54.0",
    "anthropic~=0.39.0",
    "litellm~=1.52.0",
    "langfuse~=2.57.0",
    
    # Kafka
    "aiokafka~=0.11.0",
    
    # Prefect
    "prefect~=2.19.0",
    
    # 工具类
    "pydantic-settings~=2.6.0",
    "structlog~=24.4.0",
]

[project.optional-dependencies]
dev = [
    # 测试
    "pytest~=8.3.3",
    "pytest-asyncio~=0.24.0",
    "pytest-cov~=6.0.0",
    "testcontainers~=4.8.0",
    
    # 代码质量
    "ruff~=0.7.2",
    "black~=24.10.0",
    "mypy~=1.13.0",
    
    # 开发工具
    "ipdb~=0.13.13",
    "rich~=13.9.2",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

# 工具配置
[tool.ruff]
line-length = 100
target-version = "py311"
exclude = [".venv", "build", "dist"]

[tool.black]
line-length = 100
target-version = ["py311"]

[tool.pytest.ini_options]
pythonpath = [
    ".",
    "apps/api-gateway",
    "apps/worldsmith-agent",
    "packages/shared-types/src",
]
testpaths = ["tests", "apps/*/tests"]
asyncio_mode = "auto"

[tool.mypy]
python_version = "3.11"
ignore_missing_imports = true
```

## 2. 服务特定的 pyproject.toml（部署用）

每个服务保留精简的配置，仅用于 Docker 构建：

```toml
# /apps/api-gateway/pyproject.toml
[project]
name = "api-gateway"
version = "0.1.0"
description = "FastAPI API Gateway Service"
requires-python = ">=3.11"

# 仅包含该服务需要的依赖
dependencies = [
    "fastapi~=0.115.13",
    "pydantic~=2.11.7",
    "uvicorn[standard]~=0.32.0",
    "asyncpg~=0.30.0",
    "neo4j~=5.26.0",
    "python-dotenv~=1.0.1",
    "pydantic-settings~=2.6.0",
    "structlog~=24.4.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

## 3. 开发环境设置

### 3.1 初始化开发环境

```bash
# 在项目根目录
uv venv
uv sync --dev

# 激活虚拟环境
source .venv/bin/activate  # Linux/macOS
# 或
.venv\Scripts\activate     # Windows
```

### 3.2 VS Code 配置

`.vscode/settings.json`:

```json
{
    "python.defaultInterpreterPath": "${workspaceFolder}/.venv/bin/python",
    "python.terminal.activateEnvironment": true,
    "python.analysis.extraPaths": [
        "${workspaceFolder}/apps/api-gateway",
        "${workspaceFolder}/apps/worldsmith-agent",
        "${workspaceFolder}/packages/shared-types/src"
    ],
    "python.linting.ruffEnabled": true,
    "python.formatting.provider": "black",
    "[python]": {
        "editor.formatOnSave": true,
        "editor.codeActionsOnSave": {
            "source.organizeImports": "explicit",
            "source.fixAll": "explicit"
        }
    }
}
```

### 3.3 PyCharm 配置

1. 设置项目解释器为 `/path/to/project/.venv/bin/python`
2. 标记源代码根目录：
   - `apps/api-gateway` → Mark as Sources Root
   - `apps/worldsmith-agent` → Mark as Sources Root
   - `packages/shared-types/src` → Mark as Sources Root

## 4. 开发工作流

### 4.1 运行服务

```bash
# API Gateway
uvicorn apps.api-gateway.app.main:app --reload

# Agent 服务
python -m apps.worldsmith-agent.agent.main

# 或使用开发脚本
python scripts/dev.py run api-gateway
python scripts/dev.py run worldsmith-agent
```

### 4.2 开发脚本

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
    # 添加其他服务...
}

def run_service(service_name):
    """运行指定服务"""
    if service_name not in SERVICES:
        print(f"Unknown service: {service_name}")
        print(f"Available services: {', '.join(SERVICES.keys())}")
        sys.exit(1)
    
    service = SERVICES[service_name]
    command = service["command"].format(module=service["module"])
    
    print(f"Running {service_name}...")
    subprocess.run(command, shell=True)

def test_service(service_name=None):
    """运行测试"""
    if service_name:
        test_path = f"apps/{service_name}/tests"
        command = f"pytest {test_path} -v"
    else:
        command = "pytest -v"
    
    subprocess.run(command, shell=True)

def lint():
    """运行代码检查"""
    commands = [
        "ruff check .",
        "black --check .",
        "mypy apps/",
    ]
    
    for cmd in commands:
        print(f"Running: {cmd}")
        result = subprocess.run(cmd, shell=True)
        if result.returncode != 0:
            sys.exit(1)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="开发辅助工具")
    subparsers = parser.add_subparsers(dest="command", help="命令")
    
    # run 命令
    run_parser = subparsers.add_parser("run", help="运行服务")
    run_parser.add_argument("service", choices=SERVICES.keys())
    
    # test 命令
    test_parser = subparsers.add_parser("test", help="运行测试")
    test_parser.add_argument("service", nargs="?", help="服务名称（可选）")
    
    # lint 命令
    subparsers.add_parser("lint", help="运行代码检查")
    
    args = parser.parse_args()
    
    if args.command == "run":
        run_service(args.service)
    elif args.command == "test":
        test_service(args.service)
    elif args.command == "lint":
        lint()
    else:
        parser.print_help()
```

## 5. 部署时的隔离

### 5.1 Docker 构建

每个服务使用自己的 `pyproject.toml`:

```dockerfile
# apps/api-gateway/Dockerfile
FROM python:3.11-slim as builder

# 安装 uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# 只复制该服务的 pyproject.toml
COPY pyproject.toml ./
RUN uv sync --frozen --no-dev

FROM python:3.11-slim

WORKDIR /app
COPY --from=builder /app/.venv ./.venv
COPY app ./app

ENV PATH="/app/.venv/bin:$PATH"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 5.2 CI/CD 脚本

```bash
#!/bin/bash
# scripts/build-service.sh

SERVICE=$1
cd "apps/$SERVICE"

# 使用该服务的 pyproject.toml 构建
docker build -t "infinite-scribe/$SERVICE:latest" .
```

## 6. 共享代码管理

### 6.1 本地包开发

在根目录的 `pyproject.toml` 中添加本地包：

```toml
[project]
dependencies = [
    # ... 其他依赖
    "infinite-scribe-shared @ file:///./packages/shared-types",
]
```

### 6.2 导入共享代码

```python
# 在任何服务中
from infinite_scribe_shared.models import Novel, Chapter
from infinite_scribe_shared.events import ChapterCreatedEvent
```

## 7. 环境变量管理

### 7.1 开发环境变量

创建根目录的 `.env.development`:

```bash
# 数据库（指向开发服务器）
DATABASE_URL=postgresql://user:pass@192.168.2.201:5432/novels
NEO4J_URI=bolt://192.168.2.201:7687
REDIS_URL=redis://192.168.2.201:6379

# API Keys
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# 服务配置
API_GATEWAY_PORT=8000
PREFECT_API_URL=http://192.168.2.201:4200/api
```

### 7.2 加载环境变量

```python
# apps/api-gateway/app/core/config.py
from pydantic_settings import BaseSettings
from pathlib import Path

# 开发时从根目录加载，部署时从服务目录加载
env_file = Path(__file__).parents[4] / ".env.development"
if not env_file.exists():
    env_file = ".env"

class Settings(BaseSettings):
    database_url: str
    redis_url: str
    
    class Config:
        env_file = str(env_file)
```

## 8. 测试策略

### 8.1 统一测试运行

```bash
# 运行所有测试
pytest

# 运行特定服务的测试
pytest apps/api-gateway/tests

# 运行集成测试
pytest tests/integration -m integration
```

### 8.2 测试配置

```python
# tests/conftest.py
import pytest
import sys
from pathlib import Path

# 添加所有服务到 Python 路径
root = Path(__file__).parent.parent
for app_dir in (root / "apps").iterdir():
    if app_dir.is_dir():
        sys.path.insert(0, str(app_dir))
```

## 总结

这种方式的优势：

1. **开发简单**：一个虚拟环境，一个 IDE 窗口
2. **部署独立**：每个服务仍然独立打包
3. **依赖清晰**：根目录包含所有依赖，服务目录只包含自己的
4. **测试方便**：可以轻松运行跨服务的集成测试
5. **共享代码**：本地包引用，开发时即时生效

这样既保持了开发的便利性，又确保了部署的独立性！