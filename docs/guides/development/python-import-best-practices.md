# Python 导入最佳实践

## 项目导入规范

本项目使用**绝对导入**而非相对导入，遵循 Python 社区的最佳实践。

### 导入示例

✅ **推荐（绝对导入）：**
```python
from src.core.config import settings
from src.common.services.neo4j_service import neo4j_service
from src.api.routes import health
```

❌ **避免（相对导入）：**
```python
from ...core.config import settings
from ..services.neo4j_service import neo4j_service
from . import health
```

### 为什么使用绝对导入？

1. **可读性更好**
   - 立即知道模块的完整位置
   - 不需要数点来理解层级关系

2. **重构更容易**
   - 移动文件时，导入路径保持清晰
   - IDE 更容易进行自动重构

3. **避免循环导入**
   - 绝对导入使依赖关系更清晰
   - 更容易发现和解决循环依赖

4. **符合 PEP 8**
   - Python 官方风格指南推荐绝对导入

### 项目配置

#### 1. 开发环境

在 `pyproject.toml` 中配置了 Python 路径：
```toml
[tool.pytest.ini_options]
pythonpath = [
    ".",
    "apps/backend",
    "apps/frontend",
    "packages/shared-types/src",
]
```

#### 2. Docker 环境

在 `Dockerfile` 中设置了 `PYTHONPATH`：
```dockerfile
ENV PYTHONPATH=/app
```

#### 3. IDE 配置

**VSCode** (`.vscode/settings.json`)：
```json
{
    "python.analysis.extraPaths": [
        "${workspaceFolder}/apps/backend"
    ]
}
```

**PyCharm**：
- 将 `apps/backend` 标记为 Sources Root
- 将 `apps/backend/src` 标记为 Sources Root

### 导入顺序

遵循 PEP 8 的导入顺序：

```python
# 1. 标准库导入
import os
import sys
from typing import Optional

# 2. 第三方库导入
import fastapi
from pydantic import BaseModel

# 3. 本地应用导入
from src.core.config import settings
from src.common.services.postgres_service import postgres_service
```

### 常见问题

**Q: 为什么不用相对导入？**
A: 虽然相对导入在包内部是允许的，但绝对导入更明确、更易维护。

**Q: 如何处理长导入路径？**
A: 可以使用别名：
```python
from src.common.services.very_long_module_name import VeryLongClassName as VLC
```

**Q: 测试文件如何导入？**
A: 测试文件同样使用绝对导入：
```python
# 在 tests/unit/test_health.py 中
from src.api.routes.health import health_check
```

### 迁移指南

如果需要从相对导入迁移到绝对导入：

1. **查找所有相对导入**：
   ```bash
   grep -r "from \.\." apps/backend/src/
   ```

2. **批量替换**：
   - `from ...core` → `from src.core`
   - `from ..common` → `from src.common`
   - `from .` → `from src.current_package`

3. **验证导入**：
   ```bash
   cd apps/backend
   python -m pytest tests/
   ```

### 总结

- 始终使用绝对导入（`from src.module import ...`）
- 配置正确的 PYTHONPATH
- 遵循 PEP 8 导入顺序
- 保持导入语句的一致性