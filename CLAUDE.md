# Infinite Scribe - Development Environment

## Project Overview

Infinite Scribe is a full-stack application with:

- Frontend: Next.js/React (TypeScript)
- Backend: FastAPI (Python)
- Databases: PostgreSQL, Neo4j
- Cache: Redis
- Package Management: pnpm (frontend), uv (backend)

## Remote Infrastructure

### Development Machine (192.168.2.201)

**Purpose**: Long-running development infrastructure services. NOT FOR TESTING.

- **Host**: 192.168.2.201
- **User**: zhiyue (SSH access available)
- **Services**:
  - PostgreSQL: Port 5432 (user: postgres, password: devPostgres123!, db:
    infinite_scribe)
  - Neo4j: Port 7687 (user: neo4j, password: devNeo4j123!, Web UI: 7474)
  - Redis: Port 6379 (password: devRedis123!)
- **Important**: This machine is for development use ONLY - NO tests should be
  run against these services

### Test Machine (default: 192.168.2.202)

**Purpose**: Test environment for running tests including destructive data
tests.

- **Host**: Configurable via `TEST_MACHINE_IP` env var (default: 192.168.2.202)
- **User**: zhiyue (SSH access available)
- **Features**:
  - Docker installed with TCP endpoint exposed on port 2375
  - Safe for destructive testing
  - Used by testcontainers for integration tests

### SSH Access

```bash
# Development machine
ssh zhiyue@192.168.2.201

# Test machine (default)
ssh zhiyue@192.168.2.202

# Test machine (custom)
ssh zhiyue@${TEST_MACHINE_IP}
```

### Testing

ALL tests must be run on the test machine. The development machine
(192.168.2.201) is NOT for testing.

**Recommended approach**: Use `--docker-host` for testing with Docker containers
on the test machine.

To use a custom test machine:

```bash
export TEST_MACHINE_IP=192.168.2.100
./scripts/run-tests.sh --all --docker-host
```

The project supports two testing approaches on the test machine:

#### Option 1: Using Docker Containers (--docker-host) [RECOMMENDED]

Use Docker on the test machine to spin up isolated containers:

```bash
# Run all tests with Docker containers
./scripts/run-tests.sh --all --docker-host

# Run unit tests only
./scripts/run-tests.sh --unit --docker-host

# Run integration tests only
./scripts/run-tests.sh --integration --docker-host
```

#### Option 2: Using Pre-deployed Services (--remote)

Connect to manually deployed services on the test machine (less commonly used):

```bash
# Run all tests with pre-deployed services
./scripts/run-tests.sh --all --remote

# Run unit tests only
./scripts/run-tests.sh --unit --remote

# Run integration tests only
./scripts/run-tests.sh --integration --remote
```

#### Other Options

```bash
# Show help
./scripts/run-tests.sh --help

# Run tests with coverage report
./scripts/run-tests.sh --all --docker-host --coverage
./scripts/run-tests.sh --all --remote --coverage

# Run only code quality checks (linting, formatting, type checking)
./scripts/run-tests.sh --lint

# Skip code quality checks
./scripts/run-tests.sh --all --docker-host --no-lint
./scripts/run-tests.sh --all --remote --no-lint
```

#### Test Machine Configuration Details

##### Docker Host Setup (--docker-host) [RECOMMENDED]

To use Docker containers on the test machine:

```bash
# Use default test machine Docker host
./scripts/run-tests.sh --all --docker-host

# Use a custom test machine
export TEST_MACHINE_IP=192.168.2.100
./scripts/run-tests.sh --all --docker-host

# Override Docker port if different from default
export DOCKER_HOST_PORT=2376
./scripts/run-tests.sh --all --docker-host

# Or set environment variables manually
export USE_REMOTE_DOCKER=true
export REMOTE_DOCKER_HOST=tcp://${TEST_MACHINE_IP:-192.168.2.202}:2375
./scripts/run-tests.sh --all

# Or use the .env.test configuration
export $(cat .env.test | xargs)
./scripts/run-tests.sh --all
```

**Docker Configuration Options:**

- `TEST_MACHINE_IP` - Test machine IP address (default: 192.168.2.202)
- `DOCKER_HOST_IP` - Docker host IP (default: uses TEST_MACHINE_IP)
- `DOCKER_HOST_PORT` - Docker daemon port (default: 2375)
- `USE_REMOTE_DOCKER=true` - Enable remote Docker host for testcontainers
- `REMOTE_DOCKER_HOST` - Full Docker daemon URL
- `DISABLE_RYUK=true` - Only set if experiencing Ryuk issues (not recommended)

**Docker Daemon Setup (on test machine):**

```bash
# Ensure Docker daemon is listening on TCP
# Edit /etc/docker/daemon.json to include:
# {
#   "hosts": ["unix:///var/run/docker.sock", "tcp://0.0.0.0:2375"]
# }
# Then restart Docker service
```

##### Pre-deployed Services Setup (--remote)

To use pre-deployed services on the test machine (less common approach):

1. Deploy PostgreSQL, Neo4j, and Redis on your test machine
2. Use the same ports and credentials as defined in `.env.test`
3. Run tests with `--remote` flag to connect to these services

**Service Configuration** (from `.env.test`):

- Host: Uses TEST_MACHINE_IP env var (default: 192.168.2.202)
- PostgreSQL: Port 5432, database: `infinite_scribe_test`
- Neo4j: Port 7687
- Redis: Port 6379

## Project Structure

```
infinite-scribe/
├── apps/
│   ├── backend/         # FastAPI Python backend
│   │   ├── src/        # Source code
│   │   └── tests/      # Unit and integration tests
│   └── frontend/       # Next.js frontend
├── packages/           # Shared packages
├── .github/           # GitHub Actions workflows
├── pyproject.toml     # Python project configuration
├── uv.lock           # Python dependency lock file
├── package.json      # Node.js project configuration
├── pnpm-lock.yaml   # Frontend dependency lock file
├── .env              # Active environment (symlink)
├── .env.local        # Local development config
├── .env.dev          # Dev server config (192.168.2.201)
├── .env.test         # Test environment config
└── .env.example      # Environment template
```

## Environment Management

The project uses a simplified environment structure with four main configuration
files:

### Environment Files

- `.env` - Symlink to the active environment configuration
- `.env.local` - Local development with Docker Compose
- `.env.dev` - Development server (192.168.2.201) configuration
- `.env.test` - Test environment configuration (used for testing)
- `.env.example` - Template for creating new environments

### Switching Environments

```bash
# Consolidate existing .env files (run once)
pnpm env:consolidate

# Switch to local development
pnpm env:local

# Switch to dev server
pnpm env:dev

# Switch to test environment
pnpm env:test

# Show current environment
pnpm env:show
```

## Common Commands

### Backend Development

```bash
# Install dependencies
uv sync --all-extras

# Run backend server
cd apps/backend && uv run uvicorn src.main:app --reload

# Run tests (recommended: use test script with Docker containers)
./scripts/run-tests.sh --all --docker-host        # All tests with Docker
./scripts/run-tests.sh --unit --docker-host       # Unit tests only
./scripts/run-tests.sh --integration --docker-host # Integration tests only

# Or run tests directly (local only, no external services)
cd apps/backend && uv run pytest tests/unit/ -v  # Unit tests only
cd apps/backend && uv run pytest tests/ -v       # All tests (requires services)

# Linting and formatting
cd apps/backend && uv run ruff check src/
cd apps/backend && uv run ruff format src/

# Type checking
uv run mypy apps/backend/src/ --ignore-missing-imports
```

### Frontend Development

```bash
# Install dependencies
pnpm install

# Run development server
pnpm dev

# Build
pnpm build

# Run tests
pnpm test
```

## CI/CD

- GitHub Actions workflows in `.github/workflows/`
- Trivy security scanning configured (CRITICAL vulnerabilities only)
- Automated testing on push/PR to main/develop branches

## Coding Guidelines

### Code Comments

- **Use Chinese (中文) for all code comments** - 项目统一使用中文注释
- This applies to all file types: Python, TypeScript, JavaScript, Shell scripts,
  etc.
- Example:
  ```python
  # 初始化数据库连接
  def init_database():
      # 从环境变量读取配置
      host = os.getenv("POSTGRES_HOST")
  ```

### Configuration Management

- **NEVER hardcode values** - Always use environment variables or configuration
  files
- IP addresses, ports, passwords, and other environment-specific values must be
  configurable
- Use sensible defaults with the ability to override via environment variables
- Example: `TEST_MACHINE_IP="${TEST_MACHINE_IP:-192.168.2.202}"` instead of
  hardcoding `192.168.2.202`

## Task Management

### Task Documentation Requirements

在开始任何开发任务之前，必须创建任务文档：

1. **创建任务目录**：在 `docs/development/tasks/` 下创建以任务名称命名的子目录
   ```bash
   # 示例：实现用户认证功能
   mkdir -p docs/development/tasks/user-authentication
   
   # 示例：修复数据库连接问题
   mkdir -p docs/development/tasks/fix-database-connection
   ```

2. **任务文档结构**：在任务目录中创建以下文件：
   - `README.md` - 任务概述和上下文
   - `implementation-plan.md` - 详细的实现方案
   - `todo-list.md` - 任务清单和进度跟踪
   - `progress.md` - 实施进度记录（可选）

3. **文档内容要求**：

   **README.md 应包含**：
   ```markdown
   # 任务名称
   
   ## 任务背景
   描述为什么需要这个任务
   
   ## 目标
   明确的任务目标
   
   ## 相关文件
   列出涉及的主要文件和模块
   
   ## 参考资料
   相关的文档、Issue 链接等
   ```

   **implementation-plan.md 应包含**：
   ```markdown
   # 实现方案
   
   ## 技术方案
   详细的技术实现方案
   
   ## 架构设计
   必要的架构图或流程图
   
   ## 风险评估
   潜在的风险和应对策略
   
   ## 测试计划
   如何验证实现的正确性
   ```

   **todo-list.md 应包含**：
   ```markdown
   # 任务清单
   
   ## 待办事项
   - [ ] 任务项1
   - [ ] 任务项2
   
   ## 进行中
   - [ ] 当前正在处理的任务
   
   ## 已完成
   - [x] 已完成的任务项
   ```

4. **任务恢复**：下次继续任务时，先查看任务文档了解上下文和进度

这种文档化方式确保：
- 任务上下文不会丢失
- 便于任务交接和协作
- 形成项目知识库
- 提高开发效率

## Important Notes

- Development machine (192.168.2.201): ONLY for development - NO tests of any
  kind
- Test machine (configurable, default 192.168.2.202): Use for ALL testing
  - **Recommended**: `--docker-host` - Use Docker containers on test machine for
    isolated testing
  - Alternative: `--remote` - Connect to pre-deployed services on test machine
    (less common)
- `.env.test` contains test machine service configuration (hosts are overridden
  by TEST_MACHINE_IP)
- Configure test machine with: `export TEST_MACHINE_IP=your.test.machine.ip`
- Local development does not require Docker
- DISABLE_RYUK is available but not recommended - only use if experiencing Ryuk
  cleanup issues

## Communication Language

**IMPORTANT**: Always respond in Chinese (中文) when answering questions and
providing explanations, unless the user explicitly requests a response in
another language.

# important-instruction-reminders

Do what has been asked; nothing more, nothing less. NEVER create files unless
they're absolutely necessary for achieving your goal. ALWAYS prefer editing an
existing file to creating a new one. NEVER proactively create documentation
files (\*.md) or README files. Only create documentation files if explicitly
requested by the User.


# Using Gemini CLI for Large Codebase Analysis

When analyzing large codebases or multiple files that might exceed context limits, use the Gemini CLI with its massive context window. Use `gemini -p` to leverage Google Gemini's large context capacity.

## File and Directory Inclusion Syntax

Use the `@` syntax to include files and directories in your Gemini prompts. The paths should be relative to WHERE you run the gemini command:

### Examples:

**Single file analysis:**
```bash
gemini -p "@src/main.py Explain this file's purpose and structure"
```

**Multiple files:**
```bash
gemini -p "@package.json @src/index.js Analyze the dependencies used in the code"
```

**Entire directory:**
```bash
gemini -p "@src/ Summarize the architecture of this codebase"
```

**Multiple directories:**
```bash
gemini -p "@src/ @tests/ Analyze test coverage for the source code"
```

**Current directory and subdirectories:**
```bash
gemini -p "@./ Give me an overview of this entire project"
# Or use --all_files flag:
gemini --all_files -p "Analyze the project structure and dependencies"
```

## Implementation Verification Examples

**Check if a feature is implemented:**
```bash
gemini -p "@src/ @lib/ Has dark mode been implemented in this codebase? Show me the relevant files and functions"
```

**Verify authentication implementation:**
```bash
gemini -p "@src/ @middleware/ Is JWT authentication implemented? List all auth-related endpoints and middleware"
```

**Check for specific patterns:**
```bash
gemini -p "@src/ Are there any React hooks that handle WebSocket connections? List them with file paths"
```

**Verify error handling:**
```bash
gemini -p "@src/ @api/ Is proper error handling implemented for all API endpoints? Show examples of try-catch blocks"
```

**Check for rate limiting:**
```bash
gemini -p "@backend/ @middleware/ Is rate limiting implemented for the API? Show the implementation details"
```

**Verify caching strategy:**
```bash
gemini -p "@src/ @lib/ @services/ Is Redis caching implemented? List all cache-related functions and their usage"
```

**Check for specific security measures:**
```bash
gemini -p "@src/ @api/ Are SQL injection protections implemented? Show how user inputs are sanitized"
```

**Verify test coverage for features:**
```bash
gemini -p "@src/payment/ @tests/ Is the payment processing module fully tested? List all test cases"
```

## When to Use Gemini CLI

Use `gemini -p` when:
- Analyzing entire codebases or large directories
- Comparing multiple large files
- Need to understand project-wide patterns or architecture
- Current context window is insufficient for the task
- Working with files totaling more than 100KB
- Verifying if specific features, patterns, or security measures are implemented
- Checking for the presence of certain coding patterns across the entire codebase

## Important Notes

- Paths in @ syntax are relative to your current working directory when invoking gemini
- The CLI will include file contents directly in the context
- No need for --yolo flag for read-only analysis
- Gemini's context window can handle entire codebases that would overflow Claude's context
- When checking implementations, be specific about what you're looking for to get accurate results

---

# Gemini CLI Integration Guide (Gemini CLI 集成指南)

## Overview (概述)
This guide explains how to integrate Gemini CLI within Claude Code to enable collaboration between the two AI models.

本指南说明如何在 Claude Code 中集成 Gemini CLI，实现两个 AI 模型的协同工作。

## Trigger Conditions (触发条件)

When users input any of the following commands, Claude will initiate collaboration mode with Gemini:

当用户输入以下任一指令时，Claude 将启动与 Gemini 的协作模式：

### Supported Trigger Words (支持的触发词)
- `Proceed with Gemini` / `与 Gemini 协商`
- `Consult with Gemini` / `咨询 Gemini`
- `Let's discuss this with Gemini` / `让我们和 Gemini 讨论这个`

### Regular Expression Matching (正则表达式匹配)
```regex
/(proceed|consult|discuss).*gemini/i
```

## Workflow (工作流程)

### 1. Prompt Generation (提示词生成)
Claude analyzes user requirements and generates appropriate prompts for Gemini:

Claude 分析用户需求，生成适合 Gemini 的提示词：

```bash
export PROMPT="<structured description of user requirements>"
```

### 2. Gemini CLI Invocation (Gemini CLI 调用)
Use heredoc to call Gemini:

使用 heredoc 方式调用 Gemini：

```bash
gemini -p "$PROMPT"

### 3. Response Processing (响应处理)
- **Raw Output**: Preserve Gemini's complete response
- **Claude Enhancement**: Add the following:
  - Key points summary
  - Additional context and explanations
  - Comparative analysis of both models' perspectives

• 原始输出：保留 Gemini 的完整响应
• Claude 增强：添加以下内容
  ▪ 关键要点总结
  ▪ 补充说明和上下文
  ▪ 两个模型观点的对比分析

### 4. Integrated Output (整合输出)
Final output format:

最终输出格式：

```markdown
## Gemini Response (Gemini 响应)
[Gemini's raw answer]

## Claude Analysis (Claude 分析)
[Claude's supplementary insights and integration]

## Comprehensive Conclusion (综合结论)
[Final recommendations after AI collaboration]
```

## Usage Example (使用示例)

```bash
# User input (用户输入)
"Analyze this code issue, proceed with Gemini"
"分析这个代码问题，proceed with Gemini"

# Claude execution (Claude 执行)
1. Generate PROMPT variable (生成 PROMPT 变量)
2. Call gemini CLI (调用 gemini CLI)
3. Integrate responses (整合双方响应)
4. Output comprehensive analysis (输出综合分析)
```

## Best Practices

1. **For Large Codebases**: Always use Gemini CLI when analyzing projects that exceed Claude's context window
2. **For Collaboration**: Use trigger words when you need perspectives from both AI models
3. **Path Specification**: Always ensure paths are relative to your current working directory
4. **Specific Queries**: Be precise about what you're looking for to get the most accurate results from Gemini