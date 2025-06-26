# Python 开发快速入门

## 🚀 快速开始

### 1. 安装 uv
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. 初始化开发环境（在项目根目录）
```bash
uv venv                    # 创建虚拟环境
uv sync --dev             # 安装所有依赖
source .venv/bin/activate  # 激活虚拟环境
```

### 3. 运行服务
```bash
# 使用开发脚本（推荐）
python scripts/dev.py run api-gateway
python scripts/dev.py run worldsmith-agent

# 或直接运行
uvicorn apps.api-gateway.app.main:app --reload
python -m apps.worldsmith-agent.agent.main
```

## 📦 依赖管理

### 添加依赖
```bash
# 编辑 pyproject.toml 添加新依赖，然后：
uv sync --dev             # 同步依赖
```

### 更新依赖
```bash
uv sync --dev --upgrade
```

## 🏗️ 项目结构

```
infinite-scribe/
├── .venv/               # 统一虚拟环境
├── pyproject.toml       # 所有服务依赖
├── uv.lock             # 依赖锁文件
├── scripts/
│   └── dev.py          # 开发辅助脚本
└── apps/
    ├── api-gateway/
    │   ├── app/        # 源代码
    │   └── Dockerfile  # 部署配置
    └── [agent-name]/   # 其他服务
```

## 🔧 常用命令

| 命令 | 说明 |
|------|------|
| `uv venv` | 创建虚拟环境 |
| `uv sync --dev` | 安装所有依赖 |
| `python scripts/dev.py run <service>` | 运行服务 |
| `python scripts/dev.py test` | 运行测试 |
| `python scripts/dev.py lint` | 代码检查 |
| `python scripts/dev.py format` | 格式化代码 |

## 📝 pyproject.toml 管理

项目使用单一的 `pyproject.toml` 文件管理所有依赖：

```toml
[project]
name = "infinite-scribe"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    # 所有服务的依赖都在这里
    "fastapi~=0.115.13",
    "pydantic~=2.11.7",
    # ...
]

[project.optional-dependencies]
dev = [
    "pytest~=8.3.3",
    "ruff~=0.7.2",
    # ...
]
```

## 🐳 Docker 使用

```dockerfile
# 使用根目录的依赖配置
FROM python:3.11-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY apps/api-gateway/app ./app
ENV PATH="/app/.venv/bin:$PATH"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0"]
```

## ⚡ IDE 配置

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
- Project Interpreter: 选择 `.venv/bin/python`
- Mark as Sources Root: 各个 `apps/*/` 目录

---

详细文档：[Python Monorepo 开发环境配置指南](docs/development/python-monorepo-setup-v3.md)