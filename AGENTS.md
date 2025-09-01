# Repository Guidelines

## Project Structure & Module Organization

- `apps/backend/`: FastAPI service and agents. Code in `src/` (API, agents, models, schemas, middleware). Tests in `tests/unit` and `tests/integration`.
- `apps/frontend/`: React + Vite + TypeScript app. App code in `src/`, E2E in `e2e/`.
- `scripts/`: Unified runner and deployment tooling. `deploy/` contains Compose and deploy helpers.
- `docs/`: Architecture, design, and product docs.
- Root helpers: `Makefile`, `package.json` (pnpm workspace), `pnpm-workspace.yaml`.

## Build, Test, and Development Commands

- Install: `pnpm install` (workspace), `pnpm backend install`, `pnpm frontend install`.
- Run locally: `pnpm infra up` (services), `pnpm backend run` (API on 8000), `pnpm frontend run` (Vite on 5173).
- Tests: `pnpm backend test` (pytest), `pnpm frontend test` (vitest), `pnpm frontend e2e` (Playwright), `pnpm test coverage` (repo-level).
- Lint/format: `pnpm backend lint`, `pnpm backend format`, `pnpm frontend lint`, `pnpm format`.
- Makefile shortcuts: `make dev`, `make lint`, `make test-all`.

## Coding Style & Naming Conventions

- Python: Ruff for lint/format; type-check with mypy. Files and functions `snake_case`, classes `PascalCase`, tests `tests/**/test_*.py`.
- TypeScript/React: ESLint + Prettier; strict TS config. Components `PascalCase.tsx`, hooks `use*.ts`, tests `*.test.ts(x)`.
- General: prefer small modules, pure functions, and explicit types. Avoid console logs; use structured logging/utilities.

## Testing Guidelines

- Backend: pytest for unit/integration; generate coverage with `uv run pytest --cov=src --cov-report=html` (see `htmlcov/`).
- Frontend: vitest for unit; Playwright for E2E (`apps/frontend/e2e/**`). Mock network where possible; add integration tests for API flows.
- Add tests for new features and bug fixes; no hard coverage gate, but keep critical paths covered.

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
  - 已在 `apps/frontend/playwright.config.ts` 配置了用例级 `timeout`；如需加强，建议在 CI 使用 `--global-timeout` 限制整套测试总时长：
    ```bash
    pnpm --filter @infinitescribe/frontend test:e2e -- --timeout=60000 --global-timeout=300000
    ```

- CI 建议：
  - 在 CI 任务层面增加全局超时（Job 超时时长）以兜底。
  - 对于统一脚本（如 `pnpm test all`、`pnpm backend test`、`pnpm frontend test`），可在外层使用系统 `timeout` 包裹以限制整体运行时长：
    ```bash
    timeout 120 pnpm backend test
    timeout 120 pnpm frontend test
    ```

## Commit & Pull Request Guidelines

- Commits follow Conventional Commits (seen in history): `feat:`, `fix:`, `docs:`, `refactor:`, `chore:`. Example: `feat(auth): add password reset flow`.
- PRs include: concise description, linked issues, screenshots or recordings for UI changes, sample requests/responses for API changes, and migration notes when applicable.
- CI hygiene: run `pre-commit run --all-files` (ruff, mypy, bandit, shellcheck, hadolint, prettier), `pnpm lint`, and relevant tests before submitting.

## Security & Configuration Tips

- Never commit secrets. Use `apps/backend/.env.example` and `config.toml.example` as templates; local env lives in `.env` files or `deploy/environments`.
- Check services with `pnpm check:services`; verify infra via `pnpm infra status`.
- Run `gitleaks` (config in `.gitleaks.toml`) before pushing when touching credentials or scripts.

## Agent-Specific Notes

- New agents live under `apps/backend/src/agents/**`. Extend `BaseAgent`, implement `process_message`, and add an entrypoint (see `worldsmith/`). Keep topics and config in settings, not code.

## Communication & Language

- 默认使用中文（简体）回答：所有面向用户的回复、解释、指导与讨论，除非用户明确要求其它语言。
- 情景例外：当用户提供英文模板、错误信息、或明确要求英文/其他语言时，按用户要求作答。
- 专业术语保留英文：库/框架名（如 React、FastAPI）、协议与标准（API、JWT、OAuth、WebSocket）、CLI 命令与子命令、配置键与环境变量、HTTP 方法/状态码、SQL/正则等关键字、云服务/产品名等在中文语境中也保持英文，不做直译；必要时可在括号内补充中文解释。
- 代码与接口：变量、函数、类、模块/包、文件名、API 字段与协议等一律使用英文命名规范；避免中英文混排（例如 `用户Count`），必要时可在代码中添加简短中文注释（不强制）。
- 日志与提交：提交信息（commit/PR）、CI 日志等沿用现有规范（通常为英文）；若涉及用户可读变更说明，可适当补充中文描述。
- 文档协调：产品/使用者面向的文档优先提供中文版本；开发者内部文档可按现有约定保留英文或双语。
