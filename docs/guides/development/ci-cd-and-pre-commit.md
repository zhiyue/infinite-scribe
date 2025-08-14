# CI/CD 和 Pre-commit 配置指南

## 概述

本项目使用 GitHub Actions 进行持续集成（CI）和 pre-commit hooks 进行本地代码质量检查。

## Pre-commit Hooks

### 安装和设置

1. **安装 pre-commit**（已包含在开发依赖中）：
   ```bash
   # 使用 uv 安装所有开发依赖（包括 pre-commit）
   uv sync --dev
   
   # 激活虚拟环境
   source .venv/bin/activate
   ```

2. **安装 git hooks**：
   ```bash
   pre-commit install
   ```

3. **手动运行所有检查**：
   ```bash
   pre-commit run --all-files
   ```

### 配置的 Hooks

#### Python 代码质量
- **Ruff**: 代码检查和格式化（替代 Black + isort + Flake8）
  - 自动修复代码问题
  - 检查和修复导入顺序
  - 格式化代码

- **Mypy**: 静态类型检查
  - 检查类型注解
  - 发现潜在的类型错误

- **Bandit**: 安全漏洞扫描
  - 检查常见的安全问题
  - 扫描硬编码密码等

#### 通用检查
- 移除尾随空格
- 修复文件末尾
- 检查 YAML/JSON/TOML 语法
- 检查大文件（>1MB）
- 检查合并冲突标记
- 检查调试语句（print、debugger）

#### 其他语言
- **Hadolint**: Dockerfile 最佳实践检查
- **ShellCheck**: Shell 脚本检查
- **Markdownlint**: Markdown 格式检查
- **Prettier**: YAML 和 Markdown 格式化

### 跳过 Hooks

如果需要临时跳过 pre-commit（不推荐）：
```bash
git commit --no-verify -m "紧急修复"
```

### 更新 Hooks

定期更新 pre-commit hooks 版本：
```bash
pre-commit autoupdate
```

## GitHub Actions CI/CD

### 工作流程

位置：`.github/workflows/python-ci.yml`

### 触发条件

- **Push 到 main/develop 分支**
- **Pull Request 到 main/develop 分支**
- 仅当 Python 相关文件变更时触发

### CI 任务

#### 1. Lint（代码检查）
- Python 版本：3.11
- 检查项目：
  - Black 格式检查
  - Ruff 代码检查
  - 导入顺序检查
  - Mypy 类型检查

#### 2. Test（测试）
- 运行单元测试和集成测试
- 使用 Docker 服务：
  - PostgreSQL 16
  - Neo4j 5
  - Redis 7
- 生成测试覆盖率报告
- 上传到 Codecov

#### 3. Security（安全扫描）
- Trivy 漏洞扫描
- 检查 CRITICAL 和 HIGH 级别漏洞
- 上传结果到 GitHub Security

### 本地模拟 CI

在本地运行与 CI 相同的检查：

```bash
# 激活虚拟环境
source .venv/bin/activate

# 格式检查
black --check apps/backend/

# 代码检查
ruff check apps/backend/

# 导入顺序
ruff check --select I apps/backend/

# 类型检查
mypy apps/backend/src/ --ignore-missing-imports

# 运行测试
cd apps/backend
python -m pytest tests/ -v --cov=src
```

## 最佳实践

### 开发流程

1. **开发前**：
   ```bash
   git pull origin develop
   pre-commit install
   ```

2. **提交代码**：
   ```bash
   git add .
   git commit -m "feat: 新功能"  # pre-commit 自动运行
   ```

3. **如果 pre-commit 失败**：
   - 查看错误信息
   - 多数问题会自动修复
   - 重新 `git add` 修复的文件
   - 再次提交

### 常见问题

#### Q: pre-commit 运行很慢？
A: 首次运行需要下载依赖。后续只检查变更的文件，会很快。

#### Q: 如何只运行特定的 hook？
```bash
pre-commit run ruff --all-files
pre-commit run mypy --all-files
```

#### Q: CI 失败但本地通过？
A: 确保：
- 使用相同的 Python 版本（3.11）
- 依赖是最新的：`uv sync --dev`
- 运行 `pre-commit run --all-files`

#### Q: 如何调试 CI 失败？
1. 查看 GitHub Actions 日志
2. 本地复现：使用上面的"本地模拟 CI"命令
3. 检查环境差异（环境变量、数据库版本等）

## 扩展配置

### 添加新的 pre-commit hook

编辑 `.pre-commit-config.yaml`：
```yaml
- repo: https://github.com/new-hook-repo
  rev: v1.0.0
  hooks:
    - id: new-hook
      args: [--some-arg]
```

### 添加新的 CI 步骤

编辑 `.github/workflows/python-ci.yml`，在适当的 job 中添加步骤。

### 配置通知

在 GitHub 仓库设置中配置：
- Pull Request 检查
- 分支保护规则
- Slack/Email 通知

## 相关文件

- `.pre-commit-config.yaml` - Pre-commit 配置
- `.github/workflows/python-ci.yml` - CI/CD 工作流
- `pyproject.toml` - Python 工具配置（ruff、black、mypy、bandit）
- `.dockerignore` - Docker 构建忽略文件

## 参考链接

- [Pre-commit 官方文档](https://pre-commit.com/)
- [GitHub Actions 文档](https://docs.github.com/actions)
- [Ruff 文档](https://docs.astral.sh/ruff/)
- [Mypy 文档](https://mypy.readthedocs.io/)