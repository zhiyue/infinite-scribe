# TOML 配置加载器最佳实践

## 当前实现分析

### 优点
1. **简单直接** - 代码量少，易于理解和维护
2. **功能完整** - 支持 `${VAR}` 和 `${VAR:-default}` 语法
3. **类型自动转换** - 自动识别布尔值、整数和浮点数
4. **递归处理** - 支持嵌套字典和列表
5. **无额外依赖** - 只使用 Python 标准库
6. **测试覆盖率高** - 所有功能都有单元测试

### 可能的改进点
1. 不支持更复杂的语法（如条件判断、函数调用等）
2. 错误处理可以更详细（如指出哪个变量缺失）
3. 可以添加日志记录功能

## 替代方案对比

### 1. Python 标准库 string.Template
```python
# 文件：toml_loader_stdlib.py
# 优点：无需额外依赖
# 缺点：不支持默认值语法，需要预设默认值
```

**适用场景**：
- 极简需求，不想引入任何依赖
- 配置项较少，可以预设所有默认值

### 2. python-dotenv（项目已使用）
```python
# 文件：toml_loader_dotenv.py
# 优点：项目已经在使用，功能丰富
# 缺点：主要设计用于 .env 文件，不是专门为 TOML 设计
```

**适用场景**：
- 主要使用 .env 文件管理配置
- 需要与 .env 文件保持一致的语法

### 3. 其他第三方库
- **python-decouple**: 专注于配置管理，但主要用于 .env 文件
- **environs**: 基于 marshmallow，提供强类型支持
- **dynaconf**: 功能最全面，但对简单项目来说过于复杂

## 推荐实践

### 1. 保持当前实现
对于 Infinite Scribe 项目，**建议保持当前的自定义实现**，理由：
- ✅ 已经满足所有需求
- ✅ 代码简单，易于维护
- ✅ 无需引入额外依赖
- ✅ 有完整的测试覆盖

### 2. 配置文件组织
```toml
# config.toml - 主配置文件
[service]
name = "infinite-scribe"
env = "${NODE_ENV:-development}"

[database]
host = "${DATABASE__POSTGRES_HOST:-localhost}"
port = "${DATABASE__POSTGRES_PORT:-5432}"

# config.local.toml - 本地开发配置（不纳入版本控制）
[database]
password = "${DATABASE__POSTGRES_PASSWORD}"  # 敏感信息
```

### 3. 环境变量命名规范
- 使用大写字母和下划线：`DATABASE__POSTGRES_HOST`
- 使用双下划线表示嵌套：`AUTH__JWT_SECRET_KEY`
- 为不同环境添加前缀：`DEV_`, `PROD_`, `TEST_`

### 4. 默认值策略
```toml
# 总是为非敏感配置提供默认值
host = "${API_HOST:-0.0.0.0}"
port = "${API_PORT:-8000}"

# 敏感信息不提供默认值，强制从环境变量获取
password = "${DATABASE_PASSWORD}"  # 如果缺失，保持原样
```

### 5. 错误处理增强
如果需要更好的错误处理，可以添加：

```python
def _interpolate_env_vars(value: Any, strict: bool = False) -> Any:
    """增强版插值函数，支持严格模式"""
    if isinstance(value, str):
        # ... 现有代码 ...
        
        if strict and result == match.group(0):
            # 严格模式下，缺失的变量抛出异常
            raise ValueError(f"环境变量未定义: {var_name}")
```

### 6. 日志记录
```python
import logging

logger = logging.getLogger(__name__)

def load_toml_config(config_path: str | Path) -> dict[str, Any]:
    """加载配置并记录日志"""
    logger.info(f"加载配置文件: {config_path}")
    
    # ... 现有代码 ...
    
    logger.debug(f"配置加载完成，共 {len(config_data)} 个顶级配置项")
    return interpolated_config
```

## 测试策略

### 单元测试（已实现）
- ✅ 基本功能测试
- ✅ 类型转换测试
- ✅ 递归处理测试
- ✅ 错误处理测试

### 集成测试（建议添加）
```python
def test_real_config_loading():
    """测试加载实际的配置文件"""
    config = load_toml_config("config.toml")
    
    # 验证必需的配置项
    assert "database" in config
    assert "auth" in config
    assert config["database"]["postgres_host"] is not None
```

## 性能考虑

当前实现的性能是足够的：
- 配置加载通常只在启动时执行一次
- 正则表达式编译可以缓存（如果需要优化）
- 递归深度通常很浅（2-3 层）

## 安全性

1. **避免代码注入**：当前实现不执行任何代码，安全
2. **敏感信息保护**：
   - 不在配置文件中硬编码密码
   - 使用环境变量传递敏感信息
   - 配置文件不包含默认密码

## 总结

当前的 `toml_loader.py` 实现是一个**优秀的解决方案**：
- 简单但功能完整
- 无需额外依赖
- 易于理解和维护
- 有良好的测试覆盖

除非有特殊需求（如需要 Jinja2 模板、远程配置等），否则**不建议**切换到其他库。