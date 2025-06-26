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
# API Gateway
cd apps/backend
uvicorn src.api.main:app --reload

# Agent 服务
python -m src.agents.worldsmith.main
python -m src.agents.plotmaster.main
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
├── pyproject.toml       # 根项目依赖
├── uv.lock             # 依赖锁文件
├── scripts/
│   └── dev.py          # 开发辅助脚本
└── apps/
    ├── frontend/        # 前端应用
    └── backend/         # 统一后端
        ├── src/
        │   ├── api/     # API Gateway
        │   ├── agents/  # 所有Agent服务
        │   ├── core/    # 核心功能
        │   └── common/  # 共享逻辑
        ├── pyproject.toml # 后端依赖
        └── Dockerfile   # 统一部署配置
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

```bash
# 构建统一的后端镜像
docker build -t infinite-scribe-backend ./apps/backend

# 运行不同的服务
docker run -e SERVICE_TYPE=api-gateway infinite-scribe-backend
docker run -e SERVICE_TYPE=agent-worldsmith infinite-scribe-backend
docker run -e SERVICE_TYPE=agent-plotmaster infinite-scribe-backend

# 使用 docker-compose
docker-compose -f docker-compose.yml -f docker-compose.backend.yml up
```

## ⚡ IDE 配置

### VS Code
`.vscode/settings.json`:
```json
{
    "python.defaultInterpreterPath": "${workspaceFolder}/.venv/bin/python",
    "python.analysis.extraPaths": [
        "${workspaceFolder}/apps/backend",
        "${workspaceFolder}/packages/shared-types/src"
    ]
}
```

### PyCharm
- Project Interpreter: 选择 `.venv/bin/python`
- Mark as Sources Root: `apps/backend` 目录

---

详细文档：[Python Monorepo 开发环境配置指南](docs/development/python-monorepo-setup.md)