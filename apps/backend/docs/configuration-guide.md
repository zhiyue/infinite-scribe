# 配置管理指南

## 概述

Infinite Scribe 后端使用分层配置系统，支持多种配置源和灵活的环境变量插值。

## 配置优先级

配置按以下优先级加载（从高到低）：

1. **初始化参数** - 代码中直接提供的配置
2. **环境变量** - 系统环境变量
3. **.env 文件** - 本地环境变量文件
4. **config.toml 文件** - TOML 配置文件（支持环境变量插值）
5. **密钥文件** - Docker secrets等文件形式的密钥
6. **模型定义的默认值** - 代码中定义的默认值（当以上所有源都没有提供配置时使用）

## TOML 配置文件

### 基本结构

```toml
[service]
name = "infinite-scribe-backend"
type = "api-gateway"

[database]
postgres_host = "localhost"
postgres_port = 5432
```

### 环境变量插值

TOML 配置文件支持两种环境变量插值语法：

1. **必需的环境变量**：`${VAR_NAME}`
   ```toml
   api_key = "${OPENAI_API_KEY}"  # 如果环境变量不存在，保持原值
   ```

2. **带默认值的环境变量**：`${VAR_NAME:-default_value}`
   ```toml
   host = "${API_HOST:-0.0.0.0}"  # 如果 API_HOST 不存在，使用 0.0.0.0
   ```

### 类型自动转换

环境变量值会自动转换为适当的类型：

```toml
# 布尔值
use_cache = "${USE_CACHE:-true}"  # "true" 或 "false" 转换为布尔值

# 整数
port = "${PORT:-8000}"  # "8000" 转换为整数

# 浮点数
timeout = "${TIMEOUT:-30.5}"  # "30.5" 转换为浮点数

# 字符串（默认）
name = "${SERVICE_NAME:-my-service}"
```

## 环境变量命名规则

### 顶层配置
直接使用变量名：
- `NODE_ENV`
- `API_PORT`
- `LOG_LEVEL`

### 嵌套配置
使用双下划线（`__`）分隔：
- `AUTH__JWT_SECRET_KEY`
- `DATABASE__POSTGRES_HOST`
- `DATABASE__REDIS_PASSWORD`

### Launcher 配置（统一后端启动器）
Launcher 为 `Settings` 中的嵌套配置（键名 `launcher`）。常用环境变量：

```bash
LAUNCHER__DEFAULT_MODE=single            # single|multi（预留 auto）
LAUNCHER__COMPONENTS='["api","agents"]' # 列表字段建议使用 JSON 字符串
LAUNCHER__HEALTH_INTERVAL=1.0
LAUNCHER__API__HOST=0.0.0.0
LAUNCHER__API__PORT=8000
LAUNCHER__API__RELOAD=true
LAUNCHER__AGENTS__NAMES='["worldsmith","plotmaster"]'
```

更多细节（字段说明、示例与注意事项）参见：`apps/backend/docs/launcher-configuration.md`。

## 配置示例

### 1. 开发环境

创建 `.env` 文件：
```bash
NODE_ENV=development
DATABASE__POSTGRES_HOST=localhost
DATABASE__POSTGRES_PASSWORD=dev_password
```

### 2. 生产环境

设置环境变量：
```bash
export NODE_ENV=production
export AUTH__JWT_SECRET_KEY=your-secure-production-key
export DATABASE__POSTGRES_HOST=prod.database.com
export DATABASE__POSTGRES_PASSWORD=secure_prod_password
```

### 3. 使用 TOML 配置

创建 `config.toml`：
```toml
[service]
name = "my-app"
node_env = "${NODE_ENV:-development}"

[database]
postgres_host = "${DATABASE__POSTGRES_HOST:-localhost}"
postgres_port = "${DATABASE__POSTGRES_PORT:-5432}"
postgres_password = "${DATABASE__POSTGRES_PASSWORD}"  # 必须提供
```

## 最佳实践

1. **敏感信息**：永远不要将密码、API 密钥等敏感信息直接写在配置文件中，使用环境变量。

2. **配置文件版本控制**：
   - 将 `config.toml.example` 加入版本控制
   - 将 `config.toml` 和 `.env` 加入 `.gitignore`

3. **默认值**：在 TOML 文件中为非敏感配置提供合理的默认值。

4. **文档化**：为每个配置项添加注释，说明其用途和可能的值。

5. **验证**：使用 Pydantic 的验证功能确保配置值的正确性。

## 故障排查

### 查看当前配置

```python
from src.core.config import settings
print(settings.model_dump())
```

### 检查配置加载

启动应用时，如果 TOML 文件加载失败，会显示错误信息：
```
加载 TOML 配置失败: [错误详情]
```

### 环境变量未生效

确保：
1. 环境变量已正确设置（使用 `echo $VAR_NAME` 检查）
2. 环境变量名称符合命名规则
3. 重启应用以加载新的环境变量

## 配置迁移

从纯环境变量迁移到 TOML 配置：

1. 创建 `config.toml` 文件
2. 将环境变量转换为 TOML 格式
3. 使用环境变量插值语法保持灵活性
4. 逐步迁移，确保兼容性
