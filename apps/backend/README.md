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