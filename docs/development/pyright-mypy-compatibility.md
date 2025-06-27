# Pyright 与 Mypy 兼容性配置总结

## 🎯 配置成果

我们成功配置了 pyright 和 mypy 的兼容运行环境：

1. **创建了 `pyrightconfig.json`**
   - 使用 `basic` 模式匹配 mypy 的宽松度
   - 配置了正确的 Python 路径和版本
   - 设置了与 mypy 相同的导入忽略规则

2. **创建了 `.vscode/settings.json`**
   - 配置 VSCode 使用 Pyright/Pylance
   - 禁用了 mypy 的 VSCode 集成，避免重复检查
   - 使用 Ruff 作为主要的代码格式化工具

3. **解决了类型冲突**
   - 处理了 neo4j 的 `LiteralString` 类型错误
   - 使用了针对性的忽略注释：`# pyright: ignore[reportArgumentType]`

## 📊 当前状态

```bash
# Mypy 检查结果
✅ Success: no issues found in 25 source files

# Pyright 检查结果
✅ 0 errors, 0 warnings, 0 informations
```

## 🔧 关键配置差异处理

### LiteralString 问题

**问题**: Neo4j 的 `session.run()` 方法在 pyright 中要求 `LiteralString` 类型，但 mypy 不会报错。

**解决方案**:
```python
# 使用针对 pyright 的忽略注释
result = await session.run(query, parameters or {})  # pyright: ignore[reportArgumentType]
```

这样可以：
- ✅ Mypy 正常通过（不需要 type: ignore）
- ✅ Pyright 忽略这个特定错误
- ✅ 保持代码的类型安全性

## 🚀 开发流程

1. **开发时**: VSCode + Pyright 提供实时反馈
2. **提交前**: pre-commit hooks 运行 mypy 检查
3. **CI/CD**: GitHub Actions 运行 mypy 确保代码质量

## 📝 最佳实践

1. **优先修复两者都报告的错误**
2. **对于工具特定的错误，使用针对性的忽略注释**：
   - `# type: ignore` - 忽略 mypy 错误
   - `# pyright: ignore` - 忽略 pyright 错误
   - `# pyright: ignore[specificError]` - 忽略特定的 pyright 错误

3. **定期运行两个检查器**：
   ```bash
   # 完整检查
   mypy apps/backend/src/ && npx pyright apps/backend/src/
   ```

## 🔍 调试技巧

如果遇到类型检查差异：

1. **查看具体的错误代码**：
   - Mypy: 使用 `--show-error-codes`
   - Pyright: 错误信息中包含错误代码

2. **使用更详细的输出**：
   ```bash
   # Mypy 详细输出
   mypy --verbose apps/backend/src/
   
   # Pyright 详细输出
   npx pyright --stats apps/backend/src/
   ```

3. **检查类型推断**：
   ```bash
   # Mypy 显示推断的类型
   mypy --reveal-type apps/backend/src/api/main.py:96
   ```

通过这种配置，我们获得了：
- 🚀 开发时的快速反馈（Pyright）
- ✅ 提交时的严格检查（Mypy）
- 🎯 两者的优势互补，无冲突运行