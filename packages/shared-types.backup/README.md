# Shared Types Package

该包包含 Infinite Scribe 项目的共享数据类型和模型。

## 结构

```
packages/shared-types/
├── src/
│   ├── __init__.py          # Python 包初始化
│   ├── models_db.py         # PostgreSQL 数据库模型 (Pydantic)
│   ├── models_api.py        # API 请求/响应模型 (Pydantic)
│   ├── events.py            # Kafka 事件 Schema (Pydantic)
│   └── index.ts             # TypeScript 类型定义
├── pyproject.toml           # Python 包配置
├── package.json             # TypeScript 包配置
├── tsconfig.json            # TypeScript 编译配置
├── build.sh                 # 构建脚本
└── dev-check.sh             # 开发检查脚本
```

## 开发

### Python 开发

```bash
# 安装依赖 (在项目根目录)
uv sync --all-extras

# 检查 Python 模块
python -c "import sys; sys.path.insert(0, 'packages/shared-types/src'); import models_db"
```

### TypeScript 开发

```bash
# 安装依赖
pnpm install

# 构建 TypeScript
pnpm run build

# 类型检查
pnpm run typecheck

# Lint 检查
pnpm run lint
```

### 快速验证

```bash
# 运行所有检查
./dev-check.sh

# 完整构建
./build.sh
```

## 使用

### 在 Python 中使用

```python
from shared_types.models_db import BaseDBModel
from shared_types.models_api import BaseAPIModel
from shared_types.events import BaseEvent
```

### 在 TypeScript 中使用

```typescript
import { BaseDBModel, BaseAPIModel, BaseEvent } from '@infinitescribe/shared-types';
```

## 状态

当前状态: **基础结构已创建** (Story 2.1 Task 1)

待实施:
- Task 3: 实现完整的 Pydantic 数据库模型
- Task 4: 创建对应的 TypeScript 接口
- Task 5: 创建 API 请求/响应模型