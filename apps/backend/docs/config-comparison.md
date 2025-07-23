# 配置管理方案对比

## 当前实现 vs 最佳实践

### 1. 自定义 TOML 加载器（当前实现）

**优点：**
- ✅ 简单直接，代码量少
- ✅ 完全控制插值逻辑
- ✅ 无额外依赖
- ✅ 与 pydantic-settings 集成良好

**缺点：**
- ❌ 需要自己维护代码
- ❌ 功能有限（只支持基本的 ${VAR:-default} 语法）
- ❌ 没有验证机制
- ❌ 不支持多环境配置
- ❌ 缺少高级特性（如加密、远程配置等）

### 2. Dynaconf（推荐方案）

**优点：**
- ✅ 功能丰富的环境变量插值（@format, @jinja）
- ✅ 内置多环境支持（development, production, testing）
- ✅ 强大的验证器系统
- ✅ 支持密钥文件（.secrets.toml）
- ✅ 支持远程配置（Redis, Vault 等）
- ✅ 活跃维护，社区支持好
- ✅ 支持热重载

**缺点：**
- ❌ 额外依赖
- ❌ 学习曲线稍陡
- ❌ 配置语法与标准 TOML 略有不同

**安装：**
```bash
pip install dynaconf
```

**配置示例：**
```toml
[default]
database_url = "@format postgresql://{env[DB_USER]}:{env[DB_PASSWORD]}@{env[DB_HOST]}/{env[DB_NAME]}"
api_key = "@jinja {{ env.API_KEY | default('dev-key') }}"

[production]
debug = false
```

### 3. pydantic-settings + python-dotenv（简化方案）

**优点：**
- ✅ 已经在项目中使用
- ✅ 类型安全
- ✅ 与 FastAPI 完美集成
- ✅ 简单易用

**缺点：**
- ❌ TOML 支持有限
- ❌ 不支持环境变量插值
- ❌ 多环境配置需要手动实现

**使用方式：**
```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        toml_file="config.toml",  # 基础 TOML 支持
    )
```

## 推荐策略

### 对于 Infinite Scribe 项目

考虑到项目的复杂性和需求，我推荐：

1. **短期（保持现状）**：继续使用当前的自定义实现
   - 已经能满足基本需求
   - 避免引入破坏性变更
   - 代码简单，易于理解

2. **中期（逐步迁移）**：迁移到 Dynaconf
   - 当需要多环境配置时
   - 当需要更复杂的配置管理时
   - 当需要配置验证和热重载时

3. **长期（最佳实践）**：Dynaconf + Pydantic 混合使用
   - Dynaconf 负责配置加载和环境变量插值
   - Pydantic 负责类型验证和数据模型

## 迁移指南

如果决定迁移到 Dynaconf：

1. **安装依赖**
   ```bash
   uv add dynaconf
   ```

2. **更新配置文件**
   - 将 `${VAR:-default}` 替换为 `@format {env[VAR]|default}`
   - 添加环境特定的配置节

3. **更新配置类**
   - 使用 `config_dynaconf.py` 中的实现
   - 保持与现有代码的兼容性

4. **测试**
   - 确保所有环境变量正确加载
   - 验证多环境配置工作正常

## 总结

- **如果项目简单**：继续使用当前实现
- **如果需要高级功能**：迁移到 Dynaconf
- **如果只需要类型安全**：使用 pydantic-settings 的基础功能

每种方案都有其适用场景，选择最适合项目需求的即可。