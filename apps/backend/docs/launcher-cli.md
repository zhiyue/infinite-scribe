# is-launcher 使用文档（统一后端启动器 CLI）

本指南详细说明如何使用 `is-launcher` 启动与管理 InfiniteScribe 后端组件（API 网关、Agents、Outbox Relay），并给出常见问题的排查建议与最佳实践。

## 基本概念

- 组件（components）
  - `api`: API Gateway（FastAPI）
  - `agents`: AI Agents（通过 `AgentLauncher` 管理）
  - `relay`: Outbox Relay（DB→Kafka，事务性发件箱轮询）
- 启动模式（mode）
  - `single`: 同进程启动（API 在当前 Python 进程内以 asyncio 任务运行）
  - `multi`: 子进程启动（API 通过子进程运行 uvicorn）
  - `auto`: 预留（未来自动判断）
- 推荐组合
  - 开发热重载（--reload）→ 使用 `multi` 更稳（详见下文“为什么 reload 选择 multi”）
  - 无热重载，专注调试单步 → 使用 `single` 更便于断点

## 快速上手

- 先决条件
  - 已在 `apps/backend` 同级（仓库根）执行过 `pnpm install` 与 `pnpm backend install`
  - 基础设施（PostgreSQL/Redis/Neo4j 等）已就绪：`pnpm infra up`

- 常用命令
  - 仅启动 API（推荐开发热重载）
    ```bash
    cd apps/backend
    uv run is-launcher up --components api --mode single --reload --apply --stay
    # 注：当 --reload 与 single 同时出现时，系统会自动切换到 multi，见下文
    ```
  - 同时启动 API 与 Agents（无热重载）
    ```bash
    cd apps/backend
    uv run is-launcher up --mode single --apply --stay
    ```
  - 指定部分 Agents（CSV 或 JSON）
    ```bash
    uv run is-launcher up --agents "worldsmith,plotmaster" --apply --stay
    # 或
    uv run is-launcher up --agents '["worldsmith","plotmaster"]' --apply --stay
    ```
  - 机器可读输出（JSON）
    ```bash
    uv run is-launcher up --components api --apply --json
    ```

> 停止：使用了 `--stay` 的前台会话内直接 Ctrl+C 即可优雅下线。

## 子命令与参数

- `up`：启动
  - `--mode {single|multi|auto}`：启动模式（默认 single）
  - `--components <CSV|JSON>`：要启动的组件，示例：`api,agents,relay` 或 `'["api","agents","relay"]'`
  - `--agents <CSV|JSON>`：要启动的 agent 名称列表
  - `--reload`：启用开发热重载（更适合配合 `multi`）
  - `--apply`：执行计划（不加则仅打印计划）
  - `--stay`：启动后驻留，接收 Ctrl+C 优雅关闭
  - `--json`：以 JSON 输出结果摘要

- `down`：停止
  - `--grace <seconds>`：优雅关闭等待时间（默认 10）
  - `--apply`：执行计划（不加则仅打印计划）
  - `--json`：以 JSON 输出结果摘要

- `status`：查看状态
  - `--watch`：持续观察

- `logs`：查看日志
  - `api|agents|all`：选择组件日志

> 说明：当前 `down` 在新开终端内无法“关联”之前一次 `up` 启动的子进程（因控制柄不在新进程内）。推荐在 `--stay` 的同一会话中使用 Ctrl+C 结束。

## 为什么 `--reload` + `single` 会自动切换为 `multi`

- Uvicorn 的热重载实现（reload）依赖文件监听与进程重启/重载机制，最佳实践是“外部监管（父）进程 + 内部实际服务（子）进程”。
- 当我们在同一 Python 进程内（`single`）以 asyncio 任务方式启动 `uvicorn.Server(...).serve()`，再开启 `--reload` 时，会出现：
  - FastAPI lifespan 与 uvicorn 内部重载协调导致 `CancelledError` 等取消异常在开发期频繁出现；
  - 信号处理（SIGINT/SIGTERM）由谁负责存在竞争：Launcher 自身与 uvicorn reload 线程/进程可能同时尝试接管；
  - 代码变更引发的热重载会“杀死并重启”应用层，但当前 orchestrator 仍持有旧的任务/事件循环上下文，稳定性下降。
- 改为 `multi`（子进程）后：
  - 启动器通过 `ProcessManager` 以子进程方式执行 uvicorn；热重载与生命周期管理在子进程内部自洽；
  - 主进程只负责健康检查与信号转发，做到职责分离；
  - 文件变更 → 子进程内自重启，不影响 orchestrator 主循环；
  - 信号（Ctrl+C、docker stop）语义更一致，端口占用释放也更可靠。

因此，当检测到 `--reload` 且用户选择了 `single`，启动器会打印提示并自动切换到 `multi`，保证开发体验稳定。

## 健康检查与验证

- 打开 `http://localhost:8000/docs`（Swagger UI）
- 检查健康：`curl -i http://localhost:8000/health`
  - 返回 200：依赖齐全且健康
  - 返回 503：网关已起，但某些依赖未就绪（PostgreSQL/Neo4j/Redis/Embedding 等）

## 超时与错误信息

- 启动等待时间：默认 30 秒（`startup_timeout`）。
- 若超时：启动器会并发探测 Postgres/Neo4j/Redis 的 TCP 可达性，并在错误信息中给出“不可达列表”和修复建议（例如先执行 `pnpm infra up`）。
- 目前 `startup_timeout` 暂未暴露为 CLI 选项；如需调整可在 `apps/backend/src/launcher/config.py` 的 `LauncherConfigModel.startup_timeout` 修改默认值，或提 Issue 由我们增加 CLI 参数。

## 最佳实践

- 开发期（推荐）：`multi + --reload + --stay`
- 精细调试（断点优先）：`single`（不加 `--reload`）
- 只跑 API：`--components api`（更快）
- 定位启动失败：
  1) `pnpm infra up`；
  2) 确认 `apps/backend/.env` 中 DATABASE/REDIS/NEO4J 主机、端口、密码与本地一致；
  3) 查看 `http://localhost:8000/health`；
  4) 提升日志：`LOG_LEVEL=DEBUG` 再启动。

## 已知限制

- `down` 目前无法跨进程管理之前一次 `up`（非同一进程）启动的子进程；建议使用 `--stay` 并以 Ctrl+C 结束会话。
- `startup_timeout` 暂不可通过 CLI 指定。

---

如需脚本别名（例如 `pnpm backend up` → `is-launcher up ...`）或增强功能（`--startup-timeout` 参数、统一日志过滤），请在仓库提 Issue 或留言，我们可以快速补全。
