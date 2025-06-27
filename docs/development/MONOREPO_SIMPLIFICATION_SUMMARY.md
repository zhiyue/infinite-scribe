# Python Monorepo 简化总结

## 从复杂到简单的演进

### v1: 独立虚拟环境（过于复杂）
- 每个服务独立的 pyproject.toml
- 每个服务独立的虚拟环境
- 问题：管理困难，IDE配置复杂

### v2: 统一开发，独立部署（仍然复杂）
- 根目录统一虚拟环境用于开发
- 每个服务保留 pyproject.toml 用于部署
- 问题：需要维护多个 pyproject.toml 文件，同步困难

### v3: 完全统一（最终方案）✅
- **一个 pyproject.toml**：根目录管理所有依赖
- **一个虚拟环境**：所有开发和部署使用相同配置
- **极简管理**：不需要同步多个文件

## 最终方案优势

1. **极简配置**
   - 只维护一个 pyproject.toml
   - 新依赖只需要在一个地方添加
   - 不存在版本不一致的问题

2. **开发便利**
   - `uv sync --dev` 一次性安装所有依赖
   - 所有服务在同一个环境中运行
   - IDE配置简单，只需要一个解释器

3. **部署一致**
   - Docker 使用根目录的 pyproject.toml
   - 开发和生产环境依赖完全一致
   - 减少"在我机器上能跑"的问题

4. **维护简单**
   - 升级依赖只需要修改一个文件
   - 依赖冲突立即发现
   - 团队协作更顺畅

## 实施步骤

1. 创建根目录 `pyproject.toml`（已完成）
2. 创建开发脚本 `scripts/development/dev.py`（已完成）
3. 更新所有文档引用（已完成）
4. 删除服务目录下的 pyproject.toml（下一步）

## 注意事项

- 所有 Python 依赖都在根目录管理
- Docker 构建使用根目录作为上下文
- 确保 uv.lock 文件提交到版本控制
- 使用 `uv sync --frozen` 确保依赖版本一致性

## 相关文档

- [快速入门](python-dev-quickstart.md)
- [详细指南](python-monorepo-setup-v3.md)
- [Story 1.3](../stories/1.3.story.md)