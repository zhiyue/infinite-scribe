# Monorepo Python 配置更新总结

## 更新背景

用户反馈维护多个 pyproject.toml 文件太麻烦，需要简化为只使用根目录的一个配置文件。

## 主要更改

### 1. 创建统一的依赖配置

**文件**: `/pyproject.toml`
- 包含所有服务的依赖
- 统一的开发工具配置（ruff, black, pytest, mypy）
- 完整的项目元数据

### 2. 创建开发辅助脚本

**文件**: `/scripts/dev.py`
- 运行服务：`python scripts/dev.py run api-gateway`
- 运行测试：`python scripts/dev.py test`
- 代码检查：`python scripts/dev.py lint`
- 格式化：`python scripts/dev.py format`
- 更多功能：install, clean, docker-build

### 3. 创建 Python 版本文件

**文件**: `/.python-version`
- 指定 Python 3.11

### 4. 创建 VS Code 配置

**文件**: `/.vscode/settings.json`
- 配置 Python 解释器路径
- 设置代码分析路径
- 配置自动格式化

### 5. 更新文档

#### 新建文档
- `/docs/development/python-monorepo-setup-v3.md` - 简化版配置指南
- `/docs/development/MONOREPO_SIMPLIFICATION_SUMMARY.md` - 演进历史总结

#### 更新文档
- `docs/development/python-dev-quickstart.md` - 更新为最新简化流程
- `/docs/stories/1.3.story.md` - 更新技术约束说明
- `/docs/architecture/source-tree.md` - 更新目录结构说明

## 关键决策

1. **统一依赖管理**
   - 所有服务共享一个 pyproject.toml
   - 开发和部署使用相同配置
   - 不再需要服务级别的 pyproject.toml

2. **简化 Docker 构建**
   - Docker 使用根目录的 pyproject.toml
   - 构建上下文设为根目录
   - 多阶段构建优化镜像大小

3. **开发体验优化**
   - 一次 `uv sync --dev` 安装所有依赖
   - 统一的虚拟环境
   - 简单的 IDE 配置

## 下一步建议

1. **清理旧文件**
   - 删除 `python-monorepo-setup.md` 和 `python-monorepo-setup-v2.md`
   - 确保没有遗留的服务级 pyproject.toml

2. **团队沟通**
   - 通知团队新的开发流程
   - 更新开发者文档
   - 确保 CI/CD 配置更新

3. **验证部署**
   - 测试 Docker 构建流程
   - 验证开发服务器部署
   - 确保所有服务正常运行

## 影响分析

- ✅ 开发体验大幅简化
- ✅ 依赖管理更容易
- ✅ 减少配置文件维护成本
- ⚠️ 所有服务共享依赖可能导致包体积增大
- ⚠️ 需要更新现有 CI/CD 流程

## 结论

这次简化大大降低了 Python monorepo 的复杂度，让开发者可以专注于业务逻辑而不是配置管理。