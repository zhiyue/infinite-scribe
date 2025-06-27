# Pyright VSCode 配置修复记录

## 修复的问题

### 1. "unknown config option: $schema"
**原因**: VSCode Python 插件不识别 JSON Schema 的 `$schema` 字段

**解决方案**: 从 `pyrightconfig.json` 中删除 `$schema` 字段

### 2. "stubPath file:///...typings is not a valid directory"
**原因**: 配置了 `stubPath: "typings"` 但该目录不存在

**解决方案**: 删除 `stubPath` 配置，因为项目使用 uv 管理类型存根

## 当前类型存根管理

项目通过 uv 安装了以下类型存根包：
- `types-redis` - Redis 类型定义
- `types-pyyaml` - PyYAML 类型定义
- `types-cffi` - CFFI 类型定义（依赖）
- `types-pyopenssl` - PyOpenSSL 类型定义（依赖）
- `types-setuptools` - Setuptools 类型定义（依赖）

这些类型存根安装在虚拟环境中，pyright 会自动发现并使用它们。

## 最终配置

`pyrightconfig.json` 关键配置：
```json
{
  // 不包含 $schema 和 stubPath
  "useLibraryCodeForTypes": true,  // 使用库代码进行类型推断
  "typeCheckingMode": "basic",      // 与 mypy 保持一致
}
```

## 验证步骤

```bash
# 验证 pyright 工作正常
npx pyright apps/backend/src/

# 验证 mypy 工作正常
mypy apps/backend/src/

# 查看已安装的类型存根
uv pip list | grep "types-"
```

通过这些修复，VSCode 中的 Python 类型检查现在可以正常工作，没有任何配置错误提示。