# 类型检查配置指南

本项目同时配置了 mypy 和 pyright，以获得最佳的开发体验和代码质量保证。

## 🎯 配置策略

### 1. **开发时使用 Pyright (VSCode)**
- 更快的实时检查
- 更好的 IDE 集成
- 更智能的类型推断

### 2. **CI/CD 使用 Mypy**
- 更成熟的生态系统
- 更严格的检查
- 与 pre-commit 集成

## 📝 配置文件说明

### pyrightconfig.json
```json
{
  // 注意：不要添加 "$schema" 字段，可能导致 "unknown config option" 错误
  "typeCheckingMode": "basic",  // 与 mypy 保持一致的宽松度
  "reportMissingImports": "none",  // 与 mypy ignore_missing_imports 对应
  "pythonVersion": "3.11",  // 与 mypy python_version 一致
}
```

### pyproject.toml (mypy 配置)
```toml
[tool.mypy]
python_version = "3.11"
ignore_missing_imports = true  # 对应 pyright 的 reportMissingImports
strict_optional = true
check_untyped_defs = true  # 对应 pyright 的 basic 模式
```

### .vscode/settings.json
- 使用 "basic" 模式而非 "strict"，与 mypy 配置保持一致
- 禁用 mypy 的 VSCode 集成，避免重复检查
- 使用 Ruff 作为主要的 linter/formatter

## 🔧 类型检查等级对照

| Mypy 设置 | Pyright 等效设置 |
|-----------|-----------------|
| `ignore_missing_imports = true` | `"reportMissingImports": "none"` |
| `check_untyped_defs = true` | `"typeCheckingMode": "basic"` |
| `disallow_untyped_defs = false` | 不设置 `reportUntypedFunctionDecorator` |
| `strict_optional = true` | 默认行为 |
| `warn_redundant_casts = true` | `"reportUnnecessaryCast": "warning"` |
| `warn_unused_ignores = true` | `"reportUnnecessaryTypeIgnoreComment": "warning"` |

## 💡 使用建议

### 处理类型冲突

当 mypy 和 pyright 报告不同的错误时：

1. **LiteralString 问题** (如 neo4j Query)
   ```python
   # pyright 会报错，mypy 可能不会
   Query(dynamic_string)  # Error: Expected LiteralString
   
   # 解决方案 1：避免使用需要 LiteralString 的 API
   session.run(query_string)  # 直接传递字符串
   
   # 解决方案 2：如果必须使用，添加类型忽略
   Query(dynamic_string)  # type: ignore[arg-type]
   ```

2. **联合类型推断差异**
   ```python
   def process(x: int | None) -> int:
       if x:  # pyright 更智能，知道 x 可能是 0
           return x
       return 0
   ```

3. **类型收窄差异**
   ```python
   # 使用类型守卫明确类型
   from typing import TypeGuard
   
   def is_not_none(x: T | None) -> TypeGuard[T]:
       return x is not None
   ```

## 🚀 工作流程

### 开发阶段
1. VSCode 使用 Pylance (基于 pyright) 提供实时反馈
2. 保存时自动运行 Ruff 格式化和 import 排序
3. 类型提示和自动补全由 pyright 提供

### 提交阶段
1. pre-commit 运行 mypy 检查
2. 确保代码通过更严格的 mypy 检查
3. CI 流水线也会运行相同的检查

### 调试类型错误
```bash
# 手动运行 mypy
mypy apps/backend/src/

# 手动运行 pyright
npx pyright apps/backend/src/

# 查看详细的类型推断
mypy --reveal-type apps/backend/src/api/main.py
```

## 🔍 常见问题

### Q: 出现 "unknown config option: $schema" 错误怎么办？
A: 这是因为某些 Python 工具不识别 JSON Schema 的 `$schema` 字段。解决方法：
1. 从 `pyrightconfig.json` 中删除 `$schema` 字段
2. Pyright 仍然会正常工作，不需要这个字段

### Q: 出现 "stubPath file:///...typings is not a valid directory" 错误怎么办？
A: 这是因为配置了 `stubPath` 但目录不存在。解决方法：
1. 如果使用 pip/uv 安装的类型存根（如 types-redis），删除 `stubPath` 配置
2. 如果需要自定义类型存根，创建 `typings` 目录：`mkdir typings`
3. 本项目已通过 uv 安装了所需的类型存根，不需要 stubPath

### Q: 为什么使用 basic 模式而不是 strict？
A: 为了与现有的 mypy 配置保持一致。项目当前的 mypy 配置相对宽松，使用 pyright 的 strict 模式会产生大量新的错误。

### Q: 如何处理只有 pyright 报告的错误？
A: 优先修复错误。如果确实是误报或者修复成本过高，可以：
1. 添加 `# type: ignore` 注释
2. 在 pyrightconfig.json 中调整特定规则
3. 使用更明确的类型注解帮助类型检查器

### Q: 如何逐步提高类型检查严格度？
A: 建议步骤：
1. 先修复所有 basic 模式的错误
2. 逐个启用 pyright 的检查规则
3. 同步更新 mypy 配置
4. 最终迁移到 strict 模式

## 📚 参考资源

- [Pyright 配置文档](https://github.com/microsoft/pyright/blob/main/docs/configuration.md)
- [Mypy 配置文档](https://mypy.readthedocs.io/en/stable/config_file.html)
- [类型检查最佳实践](https://typing.readthedocs.io/en/latest/source/best_practices.html)