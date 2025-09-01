# 实施计划 - 统一后端启动器（对齐最新 HLD/LLD）

分阶段落地，优先交付 P1 最小可用方案；P2 增强可观测性与健壮性；P3 进阶能力可选。

## P1 最小可用（MVP）

- [ ] 1. 目录与骨架
  - 创建 `apps/backend/src/launcher/`：`__init__.py`, `cli.py`, `orchestrator.py`, `adapters/api.py`, `adapters/agents.py`, `health.py`, `types.py`, `errors.py`
  - 在 `apps/backend/pyproject.toml` 注册 `console_scripts`: `is-launcher = src.launcher.cli:main`
  - 关联: 支撑项（为 FR-001/002/003/004/005/006 与 NFR 全部提供基础）

- [x] 2. 配置示例
  - 在 `apps/backend/config.toml.example` 新增 `[launcher]` 段（mode、components、health_interval、api、agents）
  - 关联: FR-006

- [ ] 3. 启动器配置模型
  - 定义 `LauncherConfigModel`（`default_mode`, `components`, `health_interval`, `api`, `agents`）
  - 复用现有 TOML 加载器与 pydantic-settings 的多层合并与环境变量覆盖
  - 关联: FR-006, NFR-004

- [ ] 4. CLI（最小集）
  - `is-launcher up --mode [single|multi] --components api,agents --agents <list> --reload`
  - `is-launcher down [--grace 10]`
  - `is-launcher status [--watch]`
  - `is-launcher logs <component>`
  - 关联: FR-001, FR-002, NFR-003

- [ ] 5. 适配器层
  - ApiAdapter：
    - single：同进程后台任务方式运行 uvicorn（或事件循环内启动）
    - multi：`asyncio.create_subprocess_exec` 启动 uvicorn；实现停止（进程组/信号）与超时强杀
  - AgentsAdapter：复用 `apps/backend/src/agents/launcher.py`（加载、start/stop、信号处理）
  - 关联: FR-001, FR-002, FR-004, NFR-002

- [ ] 6. 轻量编排器
  - 基于手写状态表与拓扑分层：按依赖启动/逆序停止，失败回滚
  - 组件状态：`INIT/STARTING/RUNNING/DEGRADED/STOPPING/STOPPED/ERROR`
  - 关联: FR-001, FR-002, FR-004, NFR-002

- [ ] 7. 健康监控（最小）
  - 使用 `httpx` 实现 API 健康检查，默认 1Hz（可配 1–20Hz）
  - 订阅通知机制；集群健康聚合（API + AgentsAdapter 内部状态）
  - 关联: FR-003, NFR-003

- [ ] 8. 管理端点（开发默认启用）
  - 在 API Gateway 新增只读端点：`GET /admin/launcher/status`、`GET /admin/launcher/health`
  - 生产禁用或强制鉴权，并仅绑定 127.0.0.1
  - 关联: FR-003, NFR-003

- [ ] 9. 信号与跨平台停止
  - POSIX：以新进程组启动；`SIGTERM` → 超时 `SIGKILL`
  - Windows：`CREATE_NEW_PROCESS_GROUP` + `CTRL_BREAK_EVENT`
  - 关联: FR-004, NFR-002, NFR-004

- [ ] 10. 结构化日志
  - 统一使用 `structlog`，字段：component、mode、state、elapsed_ms、attempt、error_type
  - 关联: NFR-005

- [ ] 11. 单元与集成测试
  - 单元：CLI 解析、ApiAdapter/AgentsAdapter、Orchestrator、HealthMonitor
  - 集成：依赖已就绪下 `up`→`/health` 200→`down`（single 与 multi 各一条）
  - 关联: NFR-005, NFR-002

## P2 支撑完善（可观测性/健壮性）

- [ ] 12. 依赖与重试
  - 失败重试（指数退避+抖动）与回滚增强；`DependencyNotReadyError` 等异常分类
  - 关联: FR-002, NFR-002

- [ ] 13. 指标采集（可选）
  - Prometheus 指标（launcher_state、service_state_count、startup_duration 等）
  - 通过 API Gateway 暴露 `/metrics`（不单独起指标端口）
  - 关联: FR-003, NFR-003

- [ ] 14. 配置能力增强
  - `[launcher]` 容量/并发可选项（TOML）；健康检查频率可配
  - 关联: FR-006, NFR-004

- [ ] 15. 开发体验
  - watchdog 热重载（开发）；更丰富的 `status --watch` 输出
  - 关联: FR-005

## P3 进阶能力（可选）

- [ ] 16. 模式推荐器（AUTO）
  - 基于核数/内存/容器/CI 环境进行模式推荐
  - 关联: FR-007

- [ ] 17. 插件化适配器
  - 可插拔服务适配器（entry points/配置注册）
  - 关联: FR-001, FR-002

- [ ] 18. 编排平台与追踪
  - K8s 探针/生命周期对齐；Jaeger 追踪集成
  - 关联: FR-003, NFR-004

## 验收与 NFR 校验

- [ ] A1. 启动性能
  - 依赖就绪前提下，服务启动 P95 < 25s（记录“依赖就绪时间”与“应用启动时间”）
  - 关联: NFR-001

- [ ] A2. 健康与停止
  - 健康检查 1Hz（可配），优雅停止成功率 > 99.5%
  - 关联: NFR-002

- [ ] A3. 可观测性（P2/可选）
  - 结构化日志覆盖核心路径；指标可通过 `/metrics` 暴露
  - 关联: NFR-003, NFR-005

## 文档

- [ ] D1. 使用说明与故障排查
  - CLI 使用示例、配置说明（[launcher]）、常见问题
  - 开发/测试/本地一体化启动手册
  - 关联: NFR-005

- [ ] D2. 代码内联文档
  - 关键模块与公共接口注释（adapters/orchestrator/cli）
  - 关联: NFR-005
