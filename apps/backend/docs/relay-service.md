# Outbox Relay 服务（独立启动与部署）

Outbox Relay 负责从事务性发件箱（`event_outbox`）可靠地将事件发布到 Kafka。该服务不是 Agent（不消费 Kafka），而是轮询数据库、按行发布并维护发送状态（PENDING/SENT/FAILED）。

## 职责与特性

- 轮询条件：`status=PENDING` 且 `scheduled_at IS NULL OR <= now()`
- 并发安全：`SELECT … FOR UPDATE SKIP LOCKED` 加锁，避免多实例抢占同一行
- 可靠性：成功 → `SENT`；失败 → 指数退避重试；超限 → `FAILED`
- 配置集中：使用 `Settings.relay`（嵌套配置 + 环境变量）

## 前置条件

- PostgreSQL、Kafka 可用（推荐用仓库内 `pnpm infra up` 启动）
- 已执行数据库迁移（包含 `event_outbox` 表与 `outboxstatus` 枚举的 `FAILED`）：

```bash
cd apps/backend
uv run alembic upgrade head
```

## 本地单独启动（三种方式）

1) 脚本别名（推荐）

```bash
# 仓库根目录
pnpm backend relay:run
```

2) 直接模块运行

```bash
cd apps/backend
uv run python -m src.services.outbox.relay
```

3) 通过 Launcher（仅启 Relay）

```bash
cd apps/backend
uv run is-launcher up --components relay --apply --stay
```

> 说明：Launcher 集成了健康检查与优雅停机，建议在多服务协同时使用。

## 配置（环境变量 / TOML）

嵌套环境变量（建议）：

```bash
# 轮询配置
RELAY__POLL_INTERVAL_SECONDS=5
RELAY__BATCH_SIZE=100
RELAY__RETRY_BACKOFF_MS=1000
RELAY__MAX_RETRIES_DEFAULT=3
RELAY__MAX_BACKOFF_MS=60000
RELAY__YIELD_SLEEP_MS=100
RELAY__LOOP_ERROR_BACKOFF_MS=1000

# Kafka / PostgreSQL（示例）
KAFKA_HOST=localhost
KAFKA_PORT=9092
DATABASE__POSTGRES_HOST=localhost
DATABASE__POSTRES_PORT=5432
DATABASE__POSTGRES_USER=postgres
DATABASE__POSTGRES_PASSWORD=postgres
DATABASE__POSTGRES_DB=infinite_scribe
```

或在 `apps/backend/config.toml` 中：

```toml
[relay]
poll_interval_seconds = 5
batch_size = 100
retry_backoff_ms = 1000
max_retries_default = 3
max_backoff_ms = 60000
yield_sleep_ms = 100
loop_error_backoff_ms = 1000
```

> 完整模板请参考：`apps/backend/.env.example` 与 `apps/backend/config.toml.example`

## Docker Compose 部署（独立 Relay 服务）

在 `deploy/docker-compose.backend.yml` 的 services 内追加如下服务片段（或在外部 Compose 覆盖文件中添加）：

```yaml
  relay:
    build:
      context: .
      dockerfile: apps/backend/Dockerfile
    container_name: infinite-scribe-relay
    environment:
      SERVICE_TYPE: relay
      # Kafka（内部端口示例：29092 与 infra 配置保持一致）
      KAFKA_HOST: kafka
      KAFKA_PORT: 29092
      # PostgreSQL（与 infra 一致）
      DATABASE__POSTGRES_HOST: postgres
      DATABASE__POSTGRES_PORT: 5432
      DATABASE__POSTGRES_USER: ${POSTGRES_USER:-postgres}
      DATABASE__POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-postgres}
      DATABASE__POSTGRES_DB: ${POSTGRES_DB:-infinite_scribe}
      # Relay 配置（按需覆盖）
      RELAY__POLL_INTERVAL_SECONDS: 5
      RELAY__BATCH_SIZE: 100
      RELAY__RETRY_BACKOFF_MS: 1000
      RELAY__MAX_RETRIES_DEFAULT: 3
      RELAY__MAX_BACKOFF_MS: 60000
      LOG_LEVEL: ${LOG_LEVEL:-INFO}
    depends_on:
      postgres:
        condition: service_healthy
      kafka:
        condition: service_healthy
    networks:
      - infinite-scribe-network
```

启动：

```bash
cd deploy
docker compose -f docker-compose.yml -f docker-compose.backend.yml up -d relay
```

> 镜像基于同一 `apps/backend/Dockerfile`，入口点通过 `SERVICE_TYPE=relay` 调用 `python -m src.services.outbox.relay`。

## 观测与运维

- 日志：查看进程日志（本地控制台或 `docker logs -f infinite-scribe-relay`）
- 健康：当前 Relay 无 HTTP 健康端点；如通过 Launcher 启动，使用 `is-launcher status` 查看整体状态（包含 relay 的 `producer_ready/background_alive`）。
- 指标（建议后续）：可接入 Prometheus（处理成功/失败次数、重试次数、延时指标等）。

## 常见问题排查

- 无法连接 Kafka：确认 `KAFKA_HOST`/`KAFKA_PORT` 是否与 infra 对齐；容器内通常使用 `kafka:29092`。
- 无法连接数据库：确认 `DATABASE__POSTGRES_*` 连接串；容器内使用服务名 `postgres`。
- 事件一直重试：检查原始 payload 是否可序列化为 JSON（日志会记录失败原因），或是否存在目标 topic 权限/不存在。

