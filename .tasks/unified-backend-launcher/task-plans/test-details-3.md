# 任务 3 测试细节

生成时间：2025-09-01T23:35:00Z  
任务描述：启动器配置模型 - 定义LauncherConfigModel并集成现有配置系统  
关联场景：task-3-test-scenarios.md  
关联需求：FR-006, NFR-004  

## 被测对象（SUT）

- **被测试的类叫** `LauncherConfigModel`。它的构造函数接受 `default_mode, components, health_interval, api, agents` 作为可选参数；
- **LauncherConfigModel** 的 `model_validate` 方法返回 `LauncherConfigModel` 作为验证结果，接受 `Dict[str, Any] data` 作为参数；
- **LauncherConfigModel** 的 `model_dump` 方法返回 `Dict[str, Any]` 作为序列化结果，不接受参数；
- **验证时**，通过访问模型属性和调用pydantic验证方法，完成验证

## 详细规格

### 核心类定义

#### 枚举类型
```python
# src/launcher/types.py
from enum import Enum

class LaunchMode(Enum):
    """启动模式枚举"""
    SINGLE = "single"  # 单进程模式
    MULTI = "multi"    # 多进程模式  
    AUTO = "auto"      # 自动推荐模式
```

#### 配置模型类
```python
# src/launcher/config.py
from typing import Optional
from pydantic import BaseModel, Field, field_validator
from .types import LaunchMode
import re

class LauncherApiConfig(BaseModel):
    """启动器API配置"""
    host: str = Field(default="0.0.0.0", description="API服务器绑定地址")
    port: int = Field(default=8000, ge=1024, le=65535, description="API服务器端口")
    reload: bool = Field(default=False, description="开发模式热重载")

class LauncherAgentsConfig(BaseModel):
    """启动器Agents配置"""
    names: Optional[List[str]] = Field(default=None, description="启动的Agent名称列表")
    
    @field_validator('names')
    @classmethod
    def validate_agent_names(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is not None:
            if len(v) == 0:
                raise ValueError("Agent names list cannot be empty")
            
            pattern = re.compile(r'^[a-zA-Z0-9_-]+$')
            for name in v:
                if not pattern.match(name):
                    raise ValueError(f"Invalid agent name: {name}")
                if len(name) > 50:
                    raise ValueError(f"Agent name too long: {name}")
        return v

class LauncherConfigModel(BaseModel):
    """启动器主配置模型"""
    default_mode: LaunchMode = Field(default=LaunchMode.SINGLE, description="默认启动模式")
    components: list[str] = Field(default_factory=lambda: ["api", "agents"], description="启动的组件列表")
    health_interval: float = Field(
        default=1.0, 
        ge=0.1, 
        le=60.0, 
        description="健康检查间隔（秒）"
    )
    api: LauncherApiConfig = Field(default_factory=LauncherApiConfig, description="API配置")
    agents: LauncherAgentsConfig = Field(default_factory=LauncherAgentsConfig, description="Agents配置")
    
    @field_validator('components')
    @classmethod
    def validate_components(cls, v: list[str]) -> list[str]:
        if len(v) == 0:
            raise ValueError("Components list cannot be empty")
        if len(set(v)) != len(v):
            raise ValueError("Duplicate components are not allowed")
        allowed = {"api", "agents"}
        for item in v:
            if item not in allowed:
                raise ValueError(f"Unsupported component: {item}")
        return v
```

#### 集成配置类
```python
# src/core/config.py (修改部分)
from src.launcher.config import LauncherConfigModel

class Settings(BaseSettings):
    # ... 现有字段 ...
    
    # 新增启动器配置
    launcher: LauncherConfigModel = Field(default_factory=LauncherConfigModel, description="启动器配置")
    
    # ... 其他现有内容 ...
```

### 依赖注入

| 依赖名称 | 类型 | 用途 | Mock策略 |
|---------|------|------|----------|
| pydantic.BaseModel | Class | 配置模型基类 | 使用真实实现，无需Mock |
| pydantic.Field | Function | 字段定义和验证 | 使用真实实现 |  
| pydantic.field_validator | Decorator | 自定义验证器 | 使用真实实现 |
| typing模块 | Module | 类型注解 | 使用真实实现 |
| enum.Enum | Class | 枚举基类 | 使用真实实现 |
| re.compile | Function | 正则表达式 | 使用真实实现 |

### 方法规格

#### LauncherConfigModel.__init__
- **参数**：
  - `default_mode: LaunchMode` - 默认启动模式（可选，默认SINGLE）
  - `components: List[ComponentType]` - 组件列表（可选，默认[API, AGENTS]）
  - `health_interval: float` - 健康检查间隔（可选，默认1.0秒）
  - `api: LauncherApiConfig` - API配置（可选，使用默认值）
  - `agents: LauncherAgentsConfig` - Agents配置（可选，使用默认值）
- **返回值**：`LauncherConfigModel` - 配置模型实例
- **异常**：
  - `ValidationError` - 当字段验证失败时抛出

#### LauncherConfigModel.model_validate
- **参数**：
  - `data: Dict[str, Any]` - 待验证的配置字典
- **返回值**：`LauncherConfigModel` - 验证后的配置模型实例
- **异常**：
  - `ValidationError` - 当配置数据格式不正确时抛出

#### LauncherConfigModel.model_dump
- **参数**：无
- **返回值**：`Dict[str, Any]` - 配置的字典表示
- **异常**：无

#### LauncherAgentsConfig.validate_agent_names
- **参数**：
  - `v: Optional[List[str]]` - Agent名称列表
- **返回值**：`Optional[List[str]]` - 验证后的名称列表
- **异常**：
  - `ValueError` - 当名称格式不正确、列表为空或名称过长时抛出

## 测试实现模板

### 测试结构
```python
# tests/unit/launcher/test_config_models.py
import pytest
from pydantic import ValidationError
from src.launcher.types import LaunchMode
from src.launcher.config import LauncherApiConfig, LauncherAgentsConfig, LauncherConfigModel

class TestLaunchMode:
    """测试启动模式枚举"""
    
    def test_enum_values(self):
        """测试枚举值正确性"""
        assert LaunchMode.SINGLE.value == "single"
        assert LaunchMode.MULTI.value == "multi"
        assert LaunchMode.AUTO.value == "auto"
    
    def test_enum_string_type(self):
        """测试枚举值为字符串类型"""
        for mode in LaunchMode:
            assert isinstance(mode.value, str)

class TestComponentsField:
    """测试组件列表字段"""

    def test_allowed_values(self):
        config = LauncherConfigModel(components=["api"]) 
        assert config.components == ["api"]

    def test_default_values(self):
        config = LauncherConfigModel()
        assert config.components == ["api", "agents"]

    def test_reject_invalid_value(self):
        with pytest.raises(ValidationError):
            LauncherConfigModel(components=["invalid"])  # 不支持的组件

    def test_reject_duplicates(self):
        with pytest.raises(ValidationError):
            LauncherConfigModel(components=["api", "api"])  # 重复

class TestLauncherApiConfig:
    """测试API配置模型"""
    
    def test_default_values(self):
        """测试默认配置值"""
        config = LauncherApiConfig()
        assert config.host == "0.0.0.0"
        assert config.port == 8000
        assert config.reload == False
    
    def test_custom_values(self):
        """测试自定义配置值"""
        config = LauncherApiConfig(host="127.0.0.1", port=9000, reload=True)
        assert config.host == "127.0.0.1"
        assert config.port == 9000
        assert config.reload == True
    
    def test_port_range_validation(self):
        """测试端口范围验证"""
        # 测试最小值边界
        with pytest.raises(ValidationError):
            LauncherApiConfig(port=1023)
        
        # 测试最大值边界
        with pytest.raises(ValidationError):
            LauncherApiConfig(port=65536)
        
        # 测试有效值
        config = LauncherApiConfig(port=8080)
        assert config.port == 8080
    
    def test_field_type_validation(self):
        """测试字段类型验证"""
        with pytest.raises(ValidationError):
            LauncherApiConfig(host=123)
        
        with pytest.raises(ValidationError):
            LauncherApiConfig(port="invalid")
        
        with pytest.raises(ValidationError):
            LauncherApiConfig(reload="yes")

class TestLauncherAgentsConfig:
    """测试Agents配置模型"""
    
    def test_default_values(self):
        """测试默认配置值"""
        config = LauncherAgentsConfig()
        assert config.names is None
    
    def test_valid_names_list(self):
        """测试有效名称列表"""
        names = ["worldsmith", "plotmaster"]
        config = LauncherAgentsConfig(names=names)
        assert config.names == names
        assert len(config.names) == 2
    
    def test_empty_list_rejection(self):
        """测试空列表拒绝"""
        with pytest.raises(ValidationError) as exc_info:
            LauncherAgentsConfig(names=[])
        assert "cannot be empty" in str(exc_info.value)
    
    def test_invalid_name_format_rejection(self):
        """测试无效名称格式拒绝"""
        # 测试特殊字符
        with pytest.raises(ValidationError) as exc_info:
            LauncherAgentsConfig(names=["invalid@name"])
        assert "Invalid agent name" in str(exc_info.value)
        
        # 测试多个无效字符
        with pytest.raises(ValidationError):
            LauncherAgentsConfig(names=["name-with-special#chars"])
    
    def test_name_length_limit(self):
        """测试名称长度限制"""
        long_name = "a" * 51
        with pytest.raises(ValidationError) as exc_info:
            LauncherAgentsConfig(names=[long_name])
        assert "too long" in str(exc_info.value)
        
        # 测试边界值
        valid_name = "a" * 50
        config = LauncherAgentsConfig(names=[valid_name])
        assert config.names == [valid_name]
    
    def test_valid_name_patterns(self):
        """测试有效名称模式"""
        valid_names = [
            "simple-name",
            "name_with_underscore", 
            "name123",
            "Name-With-Caps",
            "a",  # 最短有效名称
            "a" * 50  # 最长有效名称
        ]
        config = LauncherAgentsConfig(names=valid_names)
        assert config.names == valid_names

class TestLauncherConfigModel:
    """测试主配置模型"""
    
    def test_default_values(self):
        """测试默认配置值"""
        config = LauncherConfigModel()
        assert config.default_mode == LaunchMode.SINGLE
        assert config.components == ["api", "agents"]
        assert config.health_interval == 1.0
        assert isinstance(config.api, LauncherApiConfig)
        assert isinstance(config.agents, LauncherAgentsConfig)
    
    def test_custom_values(self):
        """测试自定义配置值"""
        config = LauncherConfigModel(
            default_mode=LaunchMode.MULTI,
            components=["api"],
            health_interval=2.5
        )
        assert config.default_mode == LaunchMode.MULTI
        assert config.components == ["api"]
        assert config.health_interval == 2.5
    
    def test_health_interval_range_validation(self):
        """测试健康检查间隔范围验证"""
        # 测试最小值
        with pytest.raises(ValidationError):
            LauncherConfigModel(health_interval=0.05)
        
        # 测试最大值
        with pytest.raises(ValidationError):
            LauncherConfigModel(health_interval=61.0)
        
        # 测试有效值
        config = LauncherConfigModel(health_interval=30.0)
        assert config.health_interval == 30.0
    
    def test_components_validation(self):
        """测试组件列表验证"""
        # 测试空列表
        with pytest.raises(ValidationError) as exc_info:
            LauncherConfigModel(components=[])
        # 优先检查字段定位，避免依赖具体错误文案
        assert any(e.get("loc") == ("components",) for e in exc_info.value.errors())
        
        # 测试重复组件
        with pytest.raises(ValidationError) as exc_info:
            LauncherConfigModel(components=["api", "api"])
        assert any("Duplicate" in e.get("msg", "") for e in exc_info.value.errors())

        # 测试非法组件
        with pytest.raises(ValidationError) as exc_info:
            LauncherConfigModel(components=["api", "invalid"])
        assert any("Unsupported component" in e.get("msg", "") for e in exc_info.value.errors())
    
    def test_nested_model_access(self):
        """测试嵌套模型访问"""
        config = LauncherConfigModel()
        
        # 测试API配置访问
        assert config.api.host == "0.0.0.0"
        assert config.api.port == 8000
        assert config.api.reload == False
        
        # 测试Agents配置访问
        assert config.agents.names is None
    
    def test_nested_model_customization(self):
        """测试嵌套模型自定义"""
        api_config = LauncherApiConfig(host="127.0.0.1", port=9000)
        agents_config = LauncherAgentsConfig(names=["worldsmith"])
        
        config = LauncherConfigModel(api=api_config, agents=agents_config)
        
        assert config.api.host == "127.0.0.1"
        assert config.api.port == 9000
        assert config.agents.names == ["worldsmith"]
    
    def test_model_serialization(self):
        """测试模型序列化"""
        config = LauncherConfigModel(
            default_mode=LaunchMode.MULTI,
            health_interval=2.0
        )
        
        data = config.model_dump()
        
        assert data["default_mode"] == "multi"
        assert data["health_interval"] == 2.0
        assert "api" in data
        assert "agents" in data
    
    def test_model_deserialization(self):
        """测试模型反序列化"""
        data = {
            "default_mode": "multi",
            "components": ["api", "agents"],
            "health_interval": 2.0,
            "api": {"host": "127.0.0.1", "port": 9000, "reload": True},
            "agents": {"names": ["worldsmith", "plotmaster"]}
        }
        
        config = LauncherConfigModel.model_validate(data)
        
        assert config.default_mode == LaunchMode.MULTI
        assert config.health_interval == 2.0
        assert config.api.host == "127.0.0.1"
        assert config.api.port == 9000
        assert config.agents.names == ["worldsmith", "plotmaster"]

class TestConfigSystemIntegration:
    """测试配置系统集成"""
    
    @pytest.fixture
    def temp_toml_file(self, tmp_path):
        """创建临时TOML配置文件"""
        toml_content = """
[launcher]
default_mode = "multi"
components = ["api", "agents"]
health_interval = 2.0

[launcher.api]
host = "127.0.0.1"
port = 9000
reload = true

[launcher.agents]
names = ["worldsmith", "plotmaster"]
"""
        toml_file = tmp_path / "config.toml"
        toml_file.write_text(toml_content)
        return toml_file
    
    def test_settings_includes_launcher_config(self):
        """测试Settings包含启动器配置"""
        from src.core.config import Settings
        
        settings = Settings()
        assert hasattr(settings, 'launcher')
        assert isinstance(settings.launcher, LauncherConfigModel)
    
    @pytest.mark.timeout(5)
    def test_toml_config_loading(self, temp_toml_file):
        """测试TOML配置加载"""
        from src.core.toml_loader import load_toml_config
        
        config = load_toml_config(temp_toml_file)
        
        assert 'launcher' in config
        assert config['launcher']['default_mode'] == 'multi'
        assert config['launcher']['health_interval'] == 2.0
        assert config['launcher']['api']['host'] == '127.0.0.1'
        assert config['launcher']['api']['port'] == 9000
        assert config['launcher']['agents']['names'] == ["worldsmith", "plotmaster"]
    
    @pytest.mark.timeout(5)
    def test_environment_variable_override(self, monkeypatch):
        """测试环境变量覆盖"""
        from src.core.config import Settings
        
        # 设置环境变量
        monkeypatch.setenv('LAUNCHER__DEFAULT_MODE', 'auto')
        monkeypatch.setenv('LAUNCHER__HEALTH_INTERVAL', '5.0')
        monkeypatch.setenv('LAUNCHER__API__PORT', '9001')
        
        settings = Settings()
        
        assert settings.launcher.default_mode == LaunchMode.AUTO
        assert settings.launcher.health_interval == 5.0
        assert settings.launcher.api.port == 9001

    @pytest.mark.timeout(5)
    def test_environment_variable_list_parsing(self, monkeypatch):
        """测试列表类型环境变量(JSON)解析"""
        from src.core.config import Settings

        monkeypatch.setenv('LAUNCHER__COMPONENTS', '["api"]')
        monkeypatch.setenv('LAUNCHER__AGENTS__NAMES', '["worldsmith","plotmaster"]')

        settings = Settings()

        assert settings.launcher.components == ["api"]
        assert settings.launcher.agents.names == ["worldsmith", "plotmaster"]
    
    @pytest.mark.timeout(10)
    def test_configuration_priority(self, tmp_path, monkeypatch):
        """测试配置优先级：环境变量 > .env > TOML > 默认值（这里验证 环境变量 > TOML）"""
        from src.core.config import Settings

        # 在临时目录创建 TOML 并切换工作目录，让 Settings 的 TomlConfigSettingsSource 读取到
        toml_text = """
[launcher]
[launcher.api]
port = 9000
"""
        (tmp_path / 'config.toml').write_text(toml_text)
        monkeypatch.chdir(tmp_path)

        # 环境变量覆盖 TOML
        monkeypatch.setenv('LAUNCHER__API__PORT', '9001')

        settings = Settings()
        assert settings.launcher.api.port == 9001
```

## 断言策略

### 基本断言
- **相等性**：`assert config.field == expected_value`
- **类型检查**：`assert isinstance(config.field, ExpectedType)`
- **包含性**：`assert expected_item in config.list_field`
- **布尔值**：`assert config.boolean_field == True`

### 复杂对象断言
- **枚举值**：`assert config.mode == LaunchMode.SINGLE`
- **嵌套模型**：`assert isinstance(config.api, LauncherApiConfig)`
- **列表长度**：`assert len(config.components) == 2`
- **字典键值**：`assert "api" in config.model_dump()`

### 异常断言
- **验证错误类型**：`pytest.raises(ValidationError)`
- **字段定位优先**：优先使用 `exc.errors()` 校验 `loc`、`type`、`msg`，减少对具体文案的依赖
- **示例**：`any(e.get("loc") == ("components",) for e in exc.errors())`
- **特定异常类型**：`pytest.raises(ValueError)`（用于自定义 validator 抛出的值错误）

## Timeout 策略

- 默认：在 `apps/backend/pyproject.toml` 中通过 `addopts` 启用 `pytest-timeout`，全局 `--timeout=60 --timeout-method=thread`。
- 用例级：对可能阻塞或偶发慢的测试添加 `@pytest.mark.timeout(N)`，本规范示例已为集成与性能测试分别添加 5s/10s 与亚秒级超时。
- 推荐阈值：
  - 单元测试：5–10 秒
  - 集成测试：30–60 秒（多数场景 5–10 秒即可）
  - 全量测试：60–120 秒（视用例数量）

### Mock验证
- **环境变量Mock**：使用pytest的`monkeypatch.setenv()`
- **文件操作Mock**：使用pytest的`tmp_path` fixture
- **配置加载Mock**：根据需要Mock TOML加载器

## 测试数据工厂

### 有效数据生成
```python
def create_valid_launcher_config() -> dict:
    """生成有效的启动器配置"""
    return {
        "default_mode": "single",
        "components": ["api", "agents"],
        "health_interval": 1.0,
        "api": {
            "host": "0.0.0.0",
            "port": 8000,
            "reload": False
        },
        "agents": {
            "names": ["worldsmith", "plotmaster"]
        }
    }

def create_valid_api_config() -> dict:
    """生成有效的API配置"""
    return {
        "host": "127.0.0.1",
        "port": 9000,
        "reload": True
    }

def create_valid_agents_config() -> dict:
    """生成有效的Agents配置"""
    return {
        "names": ["worldsmith", "plotmaster", "character-creator"]
    }
```

### 无效数据生成
```python
def create_invalid_launcher_config_empty_components() -> dict:
    """生成空组件列表的无效配置"""
    return {
        "default_mode": "single",
        "components": [],
        "health_interval": 1.0
    }

def create_invalid_api_config_bad_port() -> dict:
    """生成无效端口的API配置"""
    return {
        "host": "127.0.0.1",
        "port": 1023,  # 低于最小值
        "reload": False
    }

def create_invalid_agents_config_empty_list() -> dict:
    """生成空列表的Agents配置"""
    return {
        "names": []
    }

def create_invalid_agents_config_bad_names() -> dict:
    """生成无效名称的Agents配置"""
    return {
        "names": ["invalid@name", "name-with-special#chars"]
    }
```

### 边界值数据生成
```python
def create_boundary_health_intervals() -> List[float]:
    """生成健康检查间隔的边界值"""
    return [
        0.05,   # 低于最小值（无效）
        0.1,    # 最小有效值
        1.0,    # 默认值
        60.0,   # 最大有效值
        61.0    # 超过最大值（无效）
    ]

def create_boundary_port_values() -> List[int]:
    """生成端口的边界值"""
    return [
        1023,   # 低于最小值（无效）
        1024,   # 最小有效值
        8000,   # 默认值
        65535,  # 最大有效值
        65536   # 超过最大值（无效）
    ]
```

## 性能测试场景

### 实例化性能测试
```python
import time
import pytest

@pytest.mark.perf
@pytest.mark.timeout(0.3)
def test_config_instantiation_performance():
    """测试配置模型实例化性能"""
    start_time = time.time()
    
    # 创建1000个实例
    configs = []
    for _ in range(1000):
        configs.append(LauncherConfigModel())
    
    end_time = time.time()
    elapsed = end_time - start_time
    
    # 在多数 CI/本地环境下应在 300ms 内，标记为 perf 以便选择性执行
    assert elapsed < 0.3, f"Instantiation took {elapsed:.3f}s, expected < 0.3s"

@pytest.mark.perf
@pytest.mark.timeout(0.15)
def test_serialization_performance():
    """测试序列化性能"""
    config = LauncherConfigModel()
    
    start_time = time.time()
    
    # 序列化1000次
    for _ in range(1000):
        data = config.model_dump()
    
    end_time = time.time()
    elapsed = end_time - start_time
    
    # 在多数 CI/本地环境下应在 150ms 内，标记为 perf 以便选择性执行
    assert elapsed < 0.15, f"Serialization took {elapsed:.3f}s, expected < 0.15s"
```

## 验证清单

- [ ] 所有场景都有对应的测试细节
- [ ] SUT 的构造函数参数明确
- [ ] 核心方法签名完整
- [ ] 断言方式具体可执行
- [ ] Mock 策略清晰
- [ ] 测试数据工厂完整
- [ ] 性能测试覆盖关键场景
- [ ] 边界值测试全面
- [ ] 集成测试包含配置系统
- [ ] 异常处理测试充分
- [ ] ENV/TOML/优先级验证路径与工作目录切换说明明确

---
*此文档由 spec-task:impl-test-detail 生成，作为测试实现的技术规格*
