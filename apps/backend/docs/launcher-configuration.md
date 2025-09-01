# 统一后端启动器（Launcher）配置说明

本说明文档介绍 Launcher 配置模型的字段定义、TOML/ENV 加载顺序、环境变量命名规则，以及在工程中的文件位置与实践建议。

## 总览

- 配置实现：Pydantic v2 + pydantic-settings，自定义 `TomlConfigSettingsSource`（支持 `${VAR}` 与 `${VAR:-default}` 插值）。
- 配置入口：`Settings`（`src/core/config.py`）中的嵌套字段 `launcher`。
- 配置来源优先级：环境变量 > `.env` > `config.toml` > 模型默认值。
- 配置文件位置：
  - 实际文件：`apps/backend/config.toml`（不纳入版本控制）。
  - 模板文件：`apps/backend/config.toml.example`（复制为 `config.toml` 后按需修改）。
  - `.env` 文件：`apps/backend/.env`（开发环境可选）。

## 字段结构

Launcher 配置由三个模型组成：

- `LauncherConfigModel`
  - `default_mode`: 启动模式，取值 `single` 或 `multi`（预留 `auto`）。
  - `components`: 启动组件列表，当前支持 `api`、`agents`，要求非空且去重。
  - `health_interval`: 健康检查间隔（秒），范围 `[0.1, 60.0]`。
  - `api`: `LauncherApiConfig`（见下）。
  - `agents`: `LauncherAgentsConfig`（见下）。

- `LauncherApiConfig`
  - `host`: 绑定地址，默认 `0.0.0.0`。
  - `port`: 端口，范围 `1024..65535`，默认 `8000`。
  - `reload`: 开发热重载，默认 `false`。

- `LauncherAgentsConfig`
  - `names`: 可选的 agent 名称列表；若为空表示使用内置可用列表。
    - 校验：名称仅允许 `a-zA-Z0-9_-`，且长度 ≤ 50。

说明：端口占用等“运行时冲突”不在模型层校验，应由启动逻辑（adapter/orchestrator）处理并给出友好错误提示。

## 环境变量命名与映射

- 采用双下划线 `__` 作为嵌套分隔符（`env_nested_delimiter="__"`）。
- 顶层键 `launcher` 省略不写，直接从嵌套键开始：
  - `LAUNCHER__DEFAULT_MODE`
  - `LAUNCHER__COMPONENTS`
  - `LAUNCHER__HEALTH_INTERVAL`
  - `LAUNCHER__API__HOST`、`LAUNCHER__API__PORT`、`LAUNCHER__API__RELOAD`
  - `LAUNCHER__AGENTS__NAMES`

数组/列表类型的环境变量建议使用 JSON 字符串表达，Pydantic 会自动解析为相应类型：

```bash
# .env 或系统环境变量示例
LAUNCHER__DEFAULT_MODE=multi
LAUNCHER__COMPONENTS='["api","agents"]'
LAUNCHER__HEALTH_INTERVAL=2.0
LAUNCHER__API__HOST=127.0.0.1
LAUNCHER__API__PORT=9001
LAUNCHER__API__RELOAD=true
LAUNCHER__AGENTS__NAMES='["worldsmith","plotmaster"]'
```

不建议使用以逗号分隔的纯字符串来表示列表（如 `a,b`），除非在自定义解析层显式支持。项目当前推荐 JSON 字符串方案，最稳健、可读性好。

## TOML 配置示例

参考 `apps/backend/config.toml.example`：

```toml
[launcher]
default_mode = "${LAUNCHER__DEFAULT_MODE:-single}"
components = ["api", "agents"]
health_interval = 1.0

[launcher.api]
host = "${LAUNCHER__API__HOST:-0.0.0.0}"
port = "${LAUNCHER__API__PORT:-8000}"
reload = true

[launcher.agents]
# 启动的 agents 列表；留空表示使用内置可用列表
# names = ["worldsmith", "plotmaster"]
# 如需用环境变量覆盖数组，推荐 JSON 字符串：
# LAUNCHER__AGENTS__NAMES='["worldsmith","plotmaster"]'
```

说明：`TomlConfigSettingsSource` 会在读取 `config.toml` 时执行 `${VAR}` 插值，并对布尔/整数/浮点进行基本类型转换；当整值就是一个变量引用时，才会尝试自动转换为数字或布尔。

## 在代码中读取

```python
from src.core.config import Settings

settings = Settings()

# 访问 launcher 配置
mode = settings.launcher.default_mode  # Enum/StrEnum（序列化为字符串）
components = settings.launcher.components
api_port = settings.launcher.api.port
agent_names = settings.launcher.agents.names
```

> 提示：如果需要与运行时 dataclass（如 `LaunchConfig`）对接，可在使用处提供从 `LauncherConfigModel` 到运行时结构的转换函数，避免配置来源“各自为政”。

## 常见问题（FAQ）

- Q: 我设置了 `port=9000`，但服务启动失败说端口被占用？
  - A: 这是运行时冲突，模型只校验取值范围。请修改端口或停止占用该端口的进程。

- Q: 我想只启动 `api`，如何配置？
  - A: 在 `config.toml` 里设置 `components = ["api"]`，或通过环境变量 `LAUNCHER__COMPONENTS='["api"]'` 覆盖。

- Q: `names` 通过环境变量设置数组的推荐方式？
  - A: 使用 JSON 字符串：`LAUNCHER__AGENTS__NAMES='["worldsmith","plotmaster"]'`。

- Q: 枚举字段和字符串如何对比？
  - A: 在代码层统一使用枚举类型；若需要与字符串比较，使用 `enum_member.value` 获取底层字符串值。若未来改为 `StrEnum`，可直接与同名字符串相等比较。

