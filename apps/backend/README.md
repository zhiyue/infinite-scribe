# Infinite Scribe Backend

统一的后端服务，包含 API Gateway 和所有 Agent 服务。

## 结构

```
backend/
├── src/
│   ├── api/        # API Gateway 模块
│   ├── agents/     # 所有 Agent 服务
│   ├── core/       # 核心配置和共享功能
│   └── common/     # 共享业务逻辑
├── tests/          # 测试文件
├── pyproject.toml  # 依赖配置
└── Dockerfile      # 统一部署文件
```

## 本地开发

```bash
# 安装依赖
pip install -e .

# 运行 API Gateway
uvicorn src.api.main:app --reload

# 运行 Agent 服务
python -m src.agents.worldsmith.main
python -m src.agents.plotmaster.main
```

## Docker 部署

```bash
# 构建镜像
docker build -t infinite-scribe-backend .

# 运行不同服务
docker run -e SERVICE_TYPE=api-gateway infinite-scribe-backend
docker run -e SERVICE_TYPE=agent-worldsmith infinite-scribe-backend
```

## 环境变量

通过 `SERVICE_TYPE` 环境变量选择要运行的服务：
- `api-gateway`: API Gateway 服务
- `agent-worldsmith`: 世界铸造师 Agent
- `agent-plotmaster`: 剧情策划师 Agent
- 其他 agent 服务...

## 添加新的 Agent

1. 在 `src/agents/` 下创建新目录
2. 创建 `main.py` 文件作为入口
3. 在 `pyproject.toml` 中添加入口点
4. 在 `Dockerfile` 中添加对应的启动命令

# Backend API服务

## 概述

这是Infinite Scribe项目的后端API服务，基于FastAPI构建。

## 配置管理

### 项目根目录检测

配置模块使用智能的项目根目录检测机制，而不是脆弱的多级parent调用：

```python
# ❌ 旧的脆弱实现
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent

# ✅ 新的健壮实现
PROJECT_ROOT = get_project_root()  # 通过标记文件自动检测
```

检测逻辑：
1. **强标记文件优先**: 寻找 `pyproject.toml`, `.git`, `package.json`, `docker-compose.yml`, `pnpm-workspace.yaml`
2. **弱标记文件备选**: 如果找不到强标记文件，寻找 `README.md`, `Makefile`
3. **环境变量备选**: 使用 `PROJECT_ROOT` 环境变量
4. **固定路径兜底**: 最后使用计算的相对路径

### 优势

- **健壮性**: 不依赖特定的文件结构层级
- **可维护性**: 文件移动不会破坏配置
- **可测试性**: 容易模拟不同的环境
- **可读性**: 清晰表达项目根目录查找逻辑

## 测试

运行配置测试：

```bash
uv run pytest apps/backend/tests/test_config.py -v
```

## 开发

确保安装开发依赖：

```bash
uv sync --group dev
```