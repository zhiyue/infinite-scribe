# Repository Guidelines

# Development Guidelines

## Philosophy

### Core Beliefs

- **Incremental progress over big bangs** - Small changes that compile and pass
  tests
- **Learning from existing code** - Study and plan before implementing
- **Pragmatic over dogmatic** - Adapt to project reality
- **Clear intent over clever code** - Be boring and obvious
- Follow SOLID principles and prefer composition over inheritance
- Use dependency injection for testability
- Apply repository pattern for data access and strategy pattern for algorithms

### Simplicity Means

- Single responsibility per function/class
- Avoid premature abstractions
- No clever tricks - choose the boring solution
- If you need to explain it, it's too complex

## Process

### 1. Planning & Staging

Break complex work into 3-5 stages. Document in `IMPLEMENTATION_PLAN.md`:

```markdown
## Stage N: [Name]

**Goal**: [Specific deliverable] **Success Criteria**: [Testable outcomes]
**Tests**: [Specific test cases] **Status**: [Not Started|In Progress|Complete]
```

- Update status as you progress
- Remove file when all stages are done

### 2. Implementation Flow

1. **Understand** - Study existing patterns in codebase
2. **Test** - Write test first (red)
3. **Implement** - Minimal code to pass (green)
4. **Refactor** - Clean up with tests passing
5. **Commit** - With clear message linking to plan

- Search codebase first when uncertain
- Write tests for core functionality using TDD approach
- Update documentation when modifying code
- Make atomic commits for each completed feature stage and push

### 3. When Stuck (After 3 Attempts)

**CRITICAL**: Maximum 3 attempts per issue, then STOP.

1. **Document what failed**:
   - What you tried
   - Specific error messages
   - Why you think it failed

2. **Research alternatives**:
   - Find 2-3 similar implementations
   - Note different approaches used

3. **Question fundamentals**:
   - Is this the right abstraction level?
   - Can this be split into smaller problems?
   - Is there a simpler approach entirely?

4. **Try different angle**:
   - Different library/framework feature?
   - Different architectural pattern?
   - Remove abstraction instead of adding?

## Technical Standards

### Architecture Principles

- **Composition over inheritance** - Use dependency injection
- **Interfaces over singletons** - Enable testing and flexibility
- **Explicit over implicit** - Clear data flow and dependencies
- **Test-driven when possible** - Never disable tests, fix them

### Code Quality

- **Every commit must**:
  - Compile successfully
  - Pass all existing tests
  - Include tests for new functionality
  - Follow project formatting/linting

- **Before committing**:
  - Run formatters/linters
  - Self-review changes
  - Ensure commit message explains "why"

- Use descriptive names and avoid abbreviations or magic numbers
- Keep functions under 20 lines and maintain concise files
- Handle all error scenarios with meaningful messages
- Comment "why" not "what"

### Error Handling

- Fail fast with descriptive messages
- Include context for debugging
- Handle errors at appropriate level
- Never silently swallow exceptions

## Decision Framework

When multiple valid approaches exist, choose based on:

1. **Testability** - Can I easily test this?
2. **Readability** - Will someone understand this in 6 months?
3. **Consistency** - Does this match project patterns?
4. **Simplicity** - Is this the simplest solution that works?
5. **Reversibility** - How hard to change later?

## Project Integration

### Learning the Codebase

- Find 3 similar features/components
- Identify common patterns and conventions
- Use same libraries/utilities when possible
- Follow existing test patterns

### Tooling

- Use project's existing build system
- Use project's test framework
- Use project's formatter/linter settings
- Don't introduce new tools without strong justification

## Quality Gates

### Definition of Done

- [ ] Tests written and passing
- [ ] Code follows project conventions
- [ ] No linter/formatter warnings
- [ ] Commit messages are clear
- [ ] Implementation matches plan
- [ ] No TODOs without issue numbers

### Test Guidelines

- Test behavior, not implementation
- One assertion per test when possible
- Clear test names describing scenario
- Use existing test utilities/helpers
- Tests should be deterministic

## Important Reminders

**NEVER**:

- Use `--no-verify` to bypass commit hooks
- Disable tests instead of fixing them
- Commit code that doesn't compile
- Make assumptions - verify with existing code

**ALWAYS**:

- Commit working code incrementally
- Update plan documentation as you go
- Learn from existing implementations
- Stop after 3 failed attempts and reassess

## Project Structure & Module Organization

- `apps/backend/`: FastAPI service and agents. Code in `src/` (API, agents,
  models, schemas, middleware). Tests in `tests/unit` and `tests/integration`。
  排查日志时到 `apps/backend/logs` 查看当日文件，例如 `is-launcher_20250919.log`
  中的 `20250919` 为当前日期（格式 `YYYYMMDD`）。
- `apps/frontend/`: React + Vite + TypeScript app. App code in `src/`, E2E in
  `e2e/`.
- `scripts/`: Unified runner and deployment tooling. `deploy/` contains Compose
  and deploy helpers.
- `docs/`: Architecture, design, and product docs.
- Root helpers: `Makefile`, `package.json` (pnpm workspace),
  `pnpm-workspace.yaml`.

## Build, Test, and Development Commands

- Install: `pnpm install` (workspace), `pnpm backend install`,
  `pnpm frontend install`.
- Run locally: `pnpm infra up` (services), `pnpm backend run` (API on 8000),
  `pnpm frontend run` (Vite on 5173).
- Tests: `pnpm backend test` (pytest), `pnpm frontend test` (vitest),
  `pnpm frontend e2e` (Playwright), `pnpm test coverage` (repo-level).
- Lint/format: `pnpm backend lint`, `pnpm backend format`, `pnpm frontend lint`,
  `pnpm format`.
- Makefile shortcuts: `make dev`, `make lint`, `make test-all`.

## Coding Style & Naming Conventions

- Python: Ruff for lint/format; type-check with mypy. Files and functions
  `snake_case`, classes `PascalCase`, tests `tests/**/test_*.py`.
- TypeScript/React: ESLint + Prettier; strict TS config. Components
  `PascalCase.tsx`, hooks `use*.ts`, tests `*.test.ts(x)`.
- General: prefer small modules, pure functions, and explicit types. Avoid
  console logs; use structured logging/utilities.

## Testing Guidelines

- Backend: pytest for unit/integration; generate coverage with
  `uv run pytest --cov=src --cov-report=html` (see `htmlcov/`).
- Frontend: vitest for unit; Playwright for E2E (`apps/frontend/e2e/**`). Mock
  network where possible; add integration tests for API flows.
- Add tests for new features and bug fixes; no hard coverage gate, but keep
  critical paths covered.

### 测试超时（Timeout）

- 目的：避免测试进入死循环或长时间挂起，尽快暴露问题并防止潜在内存泄露。
- 推荐阈值：
  - 单元测试：5–10 秒
  - 集成测试：30–60 秒
  - 全量测试：60–120 秒（视用例数量而定）

- Backend（pytest）：
  - 本地快速包裹进程（无需额外依赖）：
    ```bash
    # 单元测试（快速）
    timeout 10 uv run pytest tests/unit/ -v
    # 全量 + 覆盖率
    timeout 120 uv run pytest tests/ -v --cov=src --cov-report=html
    ```
  - 可选：使用 `pytest-timeout` 插件（更精细的用例级超时控制）：
    ```bash
    # 安装（开发依赖）
    uv add --group dev pytest-timeout
    # 运行时指定
    uv run pytest tests/ -v --timeout=60 --timeout-method=thread
    # 或在 pyproject.toml 中通过 addopts 统一配置（仅文档建议，需手动添加）：
    # [tool.pytest.ini_options]
    # addopts = "--timeout=60 --timeout-method=thread"
    ```

- Frontend（Vitest）：
  - 临时通过 CLI 指定：
    ```bash
    pnpm --filter @infinitescribe/frontend test -- --testTimeout=5000
    ```
  - 或在 `apps/frontend/vitest.config.ts` 的 `test` 配置中设置：
    ```ts
    export default defineConfig({
      test: {
        globals: true,
        environment: 'jsdom',
        setupFiles: './src/test/setup.ts',
        testTimeout: 5000,
      },
    })
    ```

- E2E（Playwright）：
  - 已在 `apps/frontend/playwright.config.ts` 配置了用例级
    `timeout`；如需加强，建议在 CI 使用 `--global-timeout` 限制整套测试总时长：
    ```bash
    pnpm --filter @infinitescribe/frontend test:e2e -- --timeout=60000 --global-timeout=300000
    ```

- CI 建议：
  - 在 CI 任务层面增加全局超时（Job 超时时长）以兜底。
  - 对于统一脚本（如
    `pnpm test all`、`pnpm backend test`、`pnpm frontend test`），可在外层使用系统
    `timeout` 包裹以限制整体运行时长：
    ```bash
    timeout 120 pnpm backend test
    timeout 120 pnpm frontend test
    ```

## Commit & Pull Request Guidelines

- Commits follow Conventional Commits (seen in history): `feat:`, `fix:`,
  `docs:`, `refactor:`, `chore:`. Example:
  `feat(auth): add password reset flow`.
- PRs include: concise description, linked issues, screenshots or recordings for
  UI changes, sample requests/responses for API changes, and migration notes
  when applicable.
- CI hygiene: run `pre-commit run --all-files` (ruff, mypy, bandit, shellcheck,
  hadolint, prettier), `pnpm lint`, and relevant tests before submitting.

## Security & Configuration Tips

- Never commit secrets. Use `apps/backend/.env.example` and
  `config.toml.example` as templates; local env lives in `.env` files or
  `deploy/environments`.
- Check services with `pnpm check:services`; verify infra via
  `pnpm infra status`.
- Run `gitleaks` (config in `.gitleaks.toml`) before pushing when touching
  credentials or scripts.

## Agent-Specific Notes

- New agents live under `apps/backend/src/agents/**`. Extend `BaseAgent`,
  implement `process_message`, and add an entrypoint (see `worldsmith/`). Keep
  topics and config in settings, not code.

### Agent Messaging & Kafka Semantics

- Processing settings (configurable in `apps/backend/config.toml`):
  - `agent_max_retries`: 每条消息最大重试次数（默认 3）。
  - `agent_retry_backoff_ms`: 重试基础退避毫秒（指数退避，默认 500ms）。
  - `agent_dlt_suffix`: DLT（死信队列）主题后缀（默认 `.DLT`）。
  - `agent_commit_batch_size`: 手动提交偏移的批量条数阈值（默认 20）。
  - `agent_commit_interval_ms`: 手动提交偏移的时间阈值（默认 1000ms）。

- Exactly-once vs at-least-once：当前实现采用“至少一次”消费语义：
  - 成功处理后手动记录并按批量/间隔提交 offset；
  - 失败时按重试策略重试，超过上限或不可重试错误则写入 DLT 并提交 offset（避免重复消费）。

- Producer 可靠性（全局默认）
  - `acks='all'`、`enable_idempotence=True`、`linger_ms=5`、`retries=5`，提升可靠性与吞吐。

- 消息路由与分区 key（建议约定）
  - 业务处理函数返回的结果可携带 `_topic` 与 `_key`：
    - `_topic`: 发送目标主题；
    - `_key`: 分区 key，用于基于实体的消息保序（例如 `project_id` 或
      `chapter_id`）。
  - 示例：
    - DirectorAgent 启动项目时，发送
      `story.outline.request`，`_key = project_id`；
    - WriterAgent 写作章节时，发送 `story.review.request`，`_key = chapter_id`。

- 错误分类
  - 抛出 `NonRetriableError`（`src/agents/errors.py`）可跳过重试并直接写入 DLT。
  - 其他异常按重试策略处理；超过阈值写入 DLT。

- DLT 消息 Envelope
  - 字段包含：`id`（uuid）、`ts`（UTC
    ISO）、`correlation_id`（从原消息中透传）、`retries`（尝试次数）以及原始
    `payload`、`original_topic/partition/offset`。

### Example: Partition by Entity Key

在 `WriterAgent` 中：

```python
return {
  "type": "chapter_written",
  "chapter_id": chapter_id,
  "content": content,
  "_topic": "story.review.request",
  "_key": str(chapter_id),  # 按章节ID做分区，保证同一章节的消息顺序
}
```

在 `DirectorAgent` 中：

```python
return {
  "type": "create_outline",
  "project_id": project_id,
  "_topic": "story.outline.request",
  "_key": str(project_id),  # 按项目ID做分区
}
```

注意：发送失败将抛异常触发重试/ DLT；请为关键路径添加 `correlation_id`
以便跨服务追踪。

### Canonical Agent IDs 与注册表（Registry）

- 命名规范：
  - Agent ID 使用 `snake_case`（canonical
    id），例如：`writer`、`director`、`character_expert`、`fact_checker`。
  - 目录/模块名与 ID 一致（推荐），类名使用
    `PascalCase + Agent`，例如：`WriterAgent`、`DirectorAgent`。

- 兼容别名（alias）：
  - 项目提供 `AGENT_ALIASES` 与 `CANONICAL_IDS`（见
    `src/agents/agent_config.py`）进行 ID 与现有目录键的兼容映射。
  - CLI/对外文档与健康输出统一展示 canonical id；内部仍可兼容历史命名（如
    `characterexpert`）。

- 注册表优先：
  - 显式注册表位于 `src/agents/registry.py`。在具体 Agent 包的 `__init__.py`
    中注册：

```python
from ..registry import register_agent
from .agent import WriterAgent

register_agent("writer", WriterAgent)
```

- 动态加载策略：
  - `AgentLauncher` 优先从注册表加载；若未注册，则按
    `{snake_to_pascal(id)}Agent` 反射加载；
  - 如仍未找到，会扫描模块中的第一个 `BaseAgent` 子类作为兜底，最后才降级为
    `GenericAgent`。

- 主题配置的单一真相源：
  - 统一从 `get_agent_topics(id)` 读取，避免在 Agent 类中硬编码主题；
  - 后续可迁移至 Settings/TOML（Pydantic 类型化配置），`AGENT_TOPICS`
    作为默认值。

### Error Classification（错误分类钩子）

- 默认策略（BaseAgent.classify_error）：
  - `NonRetriableError` → 直接判定为不可重试，发送到 DLT（Dead Letter Topic）。
  - 其他异常 → 视为可重试，按指数退避进行最多 `agent_max_retries`
    次重试，超限后进入 DLT。

- 业务自定义：Agent 可覆盖 `classify_error(self, error, message)`
  钩子，按错误码或内容决定是否可重试。例如：

```python
from typing import Literal
from src.agents.base import BaseAgent
from src.agents.errors import NonRetriableError

class WriterAgent(BaseAgent):
    # ... 省略初始化与业务处理 ...

    def classify_error(self, error: Exception, message: dict) -> Literal["retriable", "non_retriable"]:
        # 参数校验失败：直接进入 DLT（非重试）
        if isinstance(error, NonRetriableError):
            return "non_retriable"
        # 业务规则：稿件缺必填字段，直接 DLT（示例）
        if isinstance(error, ValueError) and "missing" in str(error).lower():
            return "non_retriable"
        # 临时性错误（如第三方限流）可选择重试（示例）
        if type(error).__name__ in {"RateLimitError", "TimeoutError"}:
            return "retriable"
        return "retriable"
```

```python
class DirectorAgent(BaseAgent):
    # ... 省略初始化与业务处理 ...

    def classify_error(self, error: Exception, message: dict) -> Literal["retriable", "non_retriable"]:
        # 配置/指令格式错误：不可重试
        if isinstance(error, NonRetriableError):
            return "non_retriable"
        if isinstance(error, KeyError):
            return "non_retriable"
        # 下游服务不可用：可重试
        if type(error).__name__ in {"ServiceUnavailable", "ConnectionError"}:
            return "retriable"
        return "retriable"
```

- 结果消息中的 `retries` 字段：
  - BaseAgent 在每次成功发送结果时，会自动附加 `retries`
    字段（默认值为本次处理的失败重试次数）。
  - 如业务已设置 `retries`，框架不会覆盖该值。

## Communication & Language

- 默认使用中文（简体）回答：所有面向用户的回复、解释、指导与讨论，除非用户明确要求其它语言。
- 情景例外：当用户提供英文模板、错误信息、或明确要求英文/其他语言时，按用户要求作答。
- 专业术语保留英文：库/框架名（如 React、FastAPI）、协议与标准（API、JWT、OAuth、WebSocket）、CLI 命令与子命令、配置键与环境变量、HTTP 方法/状态码、SQL/正则等关键字、云服务/产品名等在中文语境中也保持英文，不做直译；必要时可在括号内补充中文解释。
- 代码与接口：变量、函数、类、模块/包、文件名、API 字段与协议等一律使用英文命名规范；避免中英文混排（例如
  `用户Count`），必要时可在代码中添加简短中文注释（不强制）。
- 日志与提交：提交信息（commit/PR）、CI 日志等沿用现有规范（通常为英文）；若涉及用户可读变更说明，可适当补充中文描述。
- 文档协调：产品/使用者面向的文档优先提供中文版本；开发者内部文档可按现有约定保留英文或双语。
