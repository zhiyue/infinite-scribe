# 迁移到 Python Monorepo v3 (统一配置)

## 从 v1/v2 迁移到 v3

### 主要变化

1. **只有一个 pyproject.toml**：根目录的配置文件包含所有依赖
2. **只有一个虚拟环境**：根目录的 `.venv` 用于所有服务
3. **简化的 Docker 构建**：所有服务都使用根目录配置

### 迁移步骤

#### 1. 清理旧环境

```bash
# 删除各服务的虚拟环境和配置
rm -rf apps/*/pyproject.toml
rm -rf apps/*/uv.lock
rm -rf apps/*/.venv/
```

#### 2. 创建统一的 pyproject.toml

在根目录创建 `pyproject.toml`，合并所有服务的依赖：

```toml
[project]
name = "infinite-scribe"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    # 这里包含所有服务的依赖
    "fastapi~=0.115.13",
    "pydantic~=2.11.7",
    # ... 更多依赖
]
```

#### 3. 初始化新环境

```bash
# 在根目录
uv venv
uv sync --dev
source .venv/bin/activate
```

#### 4. 更新 Docker 文件

每个服务的 Dockerfile 需要更新为使用根目录配置：

```dockerfile
# 旧版本
COPY pyproject.toml uv.lock ./

# 新版本
COPY ../../pyproject.toml ../../uv.lock ./

# 或者在 docker-compose.yml 中设置正确的 context
```

#### 5. 更新 VS Code 配置

确保 `.vscode/settings.json` 指向根目录的虚拟环境：

```json
{
    "python.defaultInterpreterPath": "${workspaceFolder}/.venv/bin/python"
}
```

#### 6. 更新导入路径

由于使用统一环境，可以直接导入其他服务的模块：

```python
# 之前可能需要相对导入或包安装
# 现在可以直接导入
from apps.api_gateway.app.core.config import Settings
from packages.shared_types.src.models import Novel
```

### 常见问题

#### Q: Docker 镜像会不会太大？

A: 会稍微大一些，但对于中小型项目影响不大。优势是维护简单。

#### Q: 如何处理服务特定的依赖？

A: 都放在根目录的 `pyproject.toml` 中。可以用注释分组：

```toml
dependencies = [
    # API Gateway
    "fastapi~=0.115.13",
    
    # Agents
    "openai~=1.54.0",
    
    # 共享
    "pydantic~=2.11.7",
]
```

#### Q: 测试怎么运行？

A: 在根目录运行，pytest 会自动发现所有测试：

```bash
# 运行所有测试
pytest

# 运行特定服务的测试
pytest apps/api-gateway/tests/
```

### 回滚方案

如果需要回到独立配置：

1. 为每个服务创建独立的 `pyproject.toml`
2. 在每个服务目录运行 `uv venv` 和 `uv sync`
3. 更新 Docker 文件使用本地配置

但建议先试用 v3 方案，它真的简单很多！