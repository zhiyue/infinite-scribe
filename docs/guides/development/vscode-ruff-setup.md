# VSCode Ruff 格式化工具设置指南

## 🔧 解决 "Extension 'Ruff' is configured as formatter but it cannot format 'Python'-files" 错误

### 问题原因

这个错误通常出现在以下情况：

1. **Ruff 扩展未安装或版本过旧**
2. **Python 扩展与 Ruff 扩展的配置冲突**
3. **Ruff 可执行文件路径未正确配置**
4. **格式化器 ID 配置错误**

### 解决步骤

#### 1. 安装或更新 Ruff 扩展

在 VSCode 中：
1. 打开扩展面板 (Ctrl+Shift+X)
2. 搜索 "Ruff" (发布者: Charlie Marsh)
3. 确保安装的是 `charliermarsh.ruff` 扩展
4. 安装或更新到最新版本
5. 重新加载 VSCode

#### 2. 确保 Ruff 已在项目中安装

```bash
# 验证 ruff 安装
source .venv/bin/activate
ruff --version  # 应该显示版本号

# 如果未安装
uv add --dev ruff
```

#### 3. 更新 VSCode 设置

已更新的 `.vscode/settings.json` 包含：

```json
{
    // Ruff 配置
    "ruff.enable": true,
    "ruff.lint.enable": true,
    "ruff.format.enable": true,
    "ruff.organizeImports": true,
    "ruff.path": ["${workspaceFolder}/.venv/bin/ruff"],
    
    // Python 文件格式化配置
    "[python]": {
        "editor.defaultFormatter": "charliermarsh.ruff",
        "editor.formatOnSave": true
    }
}
```

#### 4. 其他可能的解决方案

如果问题仍然存在，尝试：

##### 方案 A: 手动选择格式化器
1. 打开任意 Python 文件
2. 右键点击 → "使用...格式化文档"
3. 选择 "Ruff" 作为默认格式化器
4. VSCode 会自动更新设置

##### 方案 B: 使用命令面板配置
```
Ctrl+Shift+P → "Format Document With..."
选择 "Configure Default Formatter..."
选择 "Ruff"
```

##### 方案 C: 检查扩展冲突
```bash
# 禁用可能冲突的扩展：
- Black Formatter
- autopep8
- yapf
```

##### 方案 D: 完全重置 Python 格式化设置
```json
{
    "python.formatting.provider": "none",
    "python.linting.enabled": false,
    "[python]": {
        "editor.defaultFormatter": "charliermarsh.ruff",
        "editor.formatOnSave": true
    }
}
```

### 验证配置

1. **测试格式化功能**：
   - 打开一个 Python 文件
   - 按 Shift+Alt+F (Windows/Linux) 或 Shift+Option+F (Mac)
   - 应该看到 Ruff 格式化生效

2. **查看输出面板**：
   - 查看 → 输出 → 选择 "Ruff"
   - 检查是否有错误信息

3. **检查状态栏**：
   - VSCode 状态栏应显示 "Ruff" 作为格式化器

### Ruff 的优势

Ruff 作为格式化工具的优势：
- ⚡ **速度极快**：比 Black 快 10-100 倍
- 🔧 **多合一**：同时提供 linting 和 formatting
- 📦 **兼容性好**：与 Black 的格式化规则兼容
- 🎯 **配置简单**：通过 `pyproject.toml` 统一配置

### 项目中的 Ruff 配置

在 `pyproject.toml` 中：

```toml
[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP", "B", "C4", "SIM", "RUF"]
ignore = ["E501", "B008", "RUF012"]

# Ruff 的格式化功能默认启用，兼容 Black 的风格
```

### 常见问题排查

1. **确认扩展状态**：
   ```bash
   # 在 VSCode 命令面板 (Ctrl+Shift+P)
   > Developer: Show Running Extensions
   # 确保 Ruff 扩展在运行中
   ```

2. **重新加载窗口**：
   ```bash
   # 命令面板
   > Developer: Reload Window
   ```

3. **清除缓存**：
   ```bash
   rm -rf .ruff_cache
   ```

4. **查看扩展日志**：
   - 帮助 → 切换开发人员工具
   - 控制台中查看是否有 Ruff 相关错误

### 备选方案：使用 Black 格式化器

如果 Ruff 格式化器仍有问题，可以临时使用 Black：

1. **安装 Black 扩展**：
   - 扩展 ID: `ms-python.black-formatter`

2. **更新设置**：
   ```json
   "[python]": {
       "editor.defaultFormatter": "ms-python.black-formatter"
   }
   ```

3. **保持 Ruff 作为 Linter**：
   ```json
   "ruff.lint.enable": true,
   "ruff.format.enable": false  // 禁用格式化功能
   ```

### 快速验证脚本

运行验证脚本检查 Ruff 设置：

```bash
./scripts/dev/verify-ruff.sh
```

这个脚本会：
- ✅ 检查 Ruff 是否正确安装
- ✅ 测试格式化功能
- ✅ 测试 linting 功能
- ✅ 验证配置文件
- ✅ 提供 VSCode 设置建议

通过以上步骤，应该能解决 Ruff 格式化器的配置问题。