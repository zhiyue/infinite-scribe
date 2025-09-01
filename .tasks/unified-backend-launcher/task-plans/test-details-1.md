# 任务 1 测试细节

生成时间：2025-09-01T23:10:00Z
任务描述：创建 launcher 模块的目录结构与骨架文件
关联场景：task-1-test-scenarios.md
关联需求：FR-001（统一管理）；关联决策：ADR-005（CLI 架构）

## 被测对象（SUT）

### 核心模块结构

- **被测试的模块是** `src.launcher`。它包含启动器的所有核心组件；
- **CLI入口点** `src.launcher.cli.main` 函数不接受参数，作为console_scripts入口；
- **验证时**，通过检查文件存在性、模块可导入性和类定义完整性，完成验证

## 详细规格

### 测试运行上下文

- 工作目录：apps/backend（pytest 已配置 pythonpath 指向当前目录与 src）
- 路径断言统一使用 `Path("src/launcher")` 前缀

### 模块层级结构
```
src/launcher/
├── __init__.py          # 模块初始化，暴露版本号
├── cli.py               # CLI入口点，包含main()函数
├── orchestrator.py      # 服务编排器类
├── health.py            # 健康监控类
├── types.py             # 类型定义
├── errors.py            # 异常定义
└── adapters/
    ├── __init__.py      # 适配器模块初始化
    ├── api.py           # API适配器类
    └── agents.py        # Agents适配器类
```

### 类定义规格

#### Orchestrator类
```python
class Orchestrator:
    """Service orchestrator for managing backend components"""
    
    def __init__(self):
        """Initialize the orchestrator"""
        pass
    
    async def orchestrate_startup(self, target_services: Optional[List[str]] = None) -> bool:
        """Orchestrate service startup"""
        pass
    
    async def orchestrate_shutdown(self, target_services: Optional[List[str]] = None) -> bool:
        """Orchestrate service shutdown"""
        pass
```

#### HealthMonitor类
```python
class HealthMonitor:
    """Monitor health of launched services"""
    
    def __init__(self):
        """Initialize the health monitor"""
        pass
    
    async def check_health(self, service_name: str) -> bool:
        """Check health of a specific service"""
        pass
```

#### ApiAdapter类
```python
class ApiAdapter:
    """Adapter for managing API Gateway service"""
    
    async def start(self, host: str, port: int, reload: bool, mode: str) -> bool:
        """Start the API Gateway service"""
        pass
    
    async def stop(self, grace: int = 10) -> bool:
        """Stop the API Gateway service"""
        pass
    
    def status(self) -> str:
        """Get current status"""
        pass
```

#### AgentsAdapter类
```python
class AgentsAdapter:
    """Adapter for managing AI agents"""
    
    def __init__(self):
        """Initialize the agents adapter"""
        self._launcher = None
    
    def load(self, agent_names: Optional[List[str]] = None) -> None:
        """Load specified agents"""
        pass
    
    async def start(self) -> bool:
        """Start loaded agents"""
        pass
    
    async def stop(self, grace: int = 10) -> bool:
        """Stop all agents"""
        pass
```

### 异常类定义
```python
class LauncherError(Exception):
    """Base exception for launcher errors"""
    pass

class DependencyNotReadyError(LauncherError):
    """Raised when a dependency is not ready"""
    pass

class ServiceStartupError(LauncherError):
    """Raised when a service fails to start"""
    pass
```

### CLI入口点规格
```python
def main():
    """Main entry point for is-launcher command"""
    # Will be implemented to parse arguments and invoke launcher
    pass
```

## 测试实现模板

### 目录结构测试
```python
import pytest
from pathlib import Path

class TestDirectoryStructure:
    """Test launcher directory structure"""
    
    def test_launcher_directory_exists(self):
        """Test that launcher main directory exists"""
        launcher_path = Path("src/launcher")
        assert launcher_path.exists()
        assert launcher_path.is_dir()
    
    def test_adapters_subdirectory_exists(self):
        """Test that adapters subdirectory exists"""
        adapters_path = Path("src/launcher/adapters")
        assert adapters_path.exists()
        assert adapters_path.is_dir()
```

### 模块文件测试
```python
class TestModuleFiles:
    """Test module file existence"""
    
    def test_core_module_files_exist(self):
        """Test all core module files are created"""
        launcher_path = Path("src/launcher")
        required_files = [
            "__init__.py", "cli.py", "orchestrator.py",
            "health.py", "types.py", "errors.py"
        ]
        
        for file_name in required_files:
            file_path = launcher_path / file_name
            assert file_path.exists(), f"Missing: {file_name}"
            assert file_path.is_file()
    
    def test_adapter_files_exist(self):
        """Test adapter module files exist"""
        adapters_path = Path("src/launcher/adapters")
        required_files = ["__init__.py", "api.py", "agents.py"]
        
        for file_name in required_files:
            file_path = adapters_path / file_name
            assert file_path.exists(), f"Missing adapter: {file_name}"
```

### 导入测试
```python
class TestModuleImports:
    """Test module imports"""
    
    def test_cli_module_importable(self):
        """Test CLI module can be imported"""
        import src.launcher.cli
        assert hasattr(src.launcher.cli, 'main')
        assert callable(src.launcher.cli.main)
    
    def test_orchestrator_class_exists(self):
        """Test Orchestrator class is defined"""
        from src.launcher.orchestrator import Orchestrator
        assert isinstance(Orchestrator, type)
        assert hasattr(Orchestrator, 'orchestrate_startup')
        assert hasattr(Orchestrator, 'orchestrate_shutdown')
    
    def test_health_monitor_class_exists(self):
        """Test HealthMonitor class is defined"""
        from src.launcher.health import HealthMonitor
        assert isinstance(HealthMonitor, type)
        assert hasattr(HealthMonitor, 'check_health')
    
    def test_api_adapter_class_exists(self):
        """Test ApiAdapter class is defined"""
        from src.launcher.adapters.api import ApiAdapter
        assert isinstance(ApiAdapter, type)
        assert hasattr(ApiAdapter, 'start')
        assert hasattr(ApiAdapter, 'stop')
        assert hasattr(ApiAdapter, 'status')
    
    def test_agents_adapter_class_exists(self):
        """Test AgentsAdapter class is defined"""
        from src.launcher.adapters.agents import AgentsAdapter
        assert isinstance(AgentsAdapter, type)
        assert hasattr(AgentsAdapter, 'load')
        assert hasattr(AgentsAdapter, 'start')
        assert hasattr(AgentsAdapter, 'stop')
```

### 异常类测试
```python
class TestExceptionClasses:
    """Test exception class definitions"""
    
    def test_launcher_error_defined(self):
        """Test LauncherError base exception"""
        from src.launcher.errors import LauncherError
        assert issubclass(LauncherError, Exception)
        
        # Test instantiation
        error = LauncherError("Test error")
        assert str(error) == "Test error"
    
    def test_derived_exceptions(self):
        """Test derived exception classes"""
        from src.launcher.errors import (
            DependencyNotReadyError,
            ServiceStartupError
        )
        
        assert issubclass(DependencyNotReadyError, LauncherError)
        assert issubclass(ServiceStartupError, LauncherError)
```

### CLI入口点测试
```python
import subprocess
import tomllib

class TestCLIEntryPoint:
    """Test CLI entry point registration"""
    
    def test_pyproject_entry_point_registered(self):
        """Test CLI entry point in pyproject.toml"""
        with open("apps/backend/pyproject.toml", "rb") as f:
            config = tomllib.load(f)
        
        assert "project" in config
        assert "scripts" in config["project"]
        assert "is-launcher" in config["project"]["scripts"]
        assert config["project"]["scripts"]["is-launcher"] == "src.launcher.cli:main"
    
    def test_cli_help_command(self):
        """Test CLI help command executes"""
        import sys
        result = subprocess.run(
            [sys.executable, "-m", "src.launcher.cli", "--help"],
            capture_output=True,
            text=True,
            cwd="apps/backend"
        )
        assert result.returncode == 0
```

### 版本信息测试
```python
class TestVersionInfo:
    """Test module version information"""
    
    def test_module_has_version(self):
        """Test launcher module has version info"""
        import src.launcher
        assert hasattr(src.launcher, '__version__')
        assert isinstance(src.launcher.__version__, str)
        assert len(src.launcher.__version__) > 0
```

## 断言策略

### 文件系统断言
- **存在性**：`assert path.exists()`
- **类型检查**：`assert path.is_dir()` 或 `assert path.is_file()`
- **权限检查（可选）**：在非 Windows 平台可验证基本可读权限，例如 `(path.stat().st_mode & 0o444) != 0`

### 模块导入断言
- **可导入性**：`import module` 不抛出 ImportError
- **属性存在**：`assert hasattr(module, 'attribute')`
- **类型检查**：`assert isinstance(Class, type)`
- **可调用性**：`assert callable(function)`

### 类定义断言
- **继承关系**：`assert issubclass(Child, Parent)`
- **方法存在**：`assert hasattr(instance, 'method')`
- **签名匹配**：使用 `inspect.signature()` 验证

### 配置文件断言
- **键存在**：`assert key in config`
- **值匹配**：`assert config[key] == expected_value`

## 测试数据工厂

### 路径生成器
```python
def get_launcher_path() -> Path:
    """Get launcher module path"""
    return Path("src/launcher")

def get_module_files() -> List[str]:
    """Get list of required module files"""
    return [
        "__init__.py", "cli.py", "orchestrator.py",
        "health.py", "types.py", "errors.py"
    ]

def get_adapter_files() -> List[str]:
    """Get list of required adapter files"""
    return ["__init__.py", "api.py", "agents.py"]
```

### 骨架代码生成器
```python
def create_skeleton_class(class_name: str, base_class: str = None) -> str:
    """Generate skeleton class code"""
    base = f"({base_class})" if base_class else ""
    return f'''"""Module for {class_name}"""

class {class_name}{base}:
    """{class_name} implementation"""
    
    def __init__(self):
        """Initialize {class_name}"""
        pass
'''
```

## 验证清单

- [x] 所有15个测试场景都有对应的测试细节
- [x] 文件结构测试覆盖所有必需文件
- [x] 类定义包含必要的方法签名
- [x] 异常类继承关系正确
- [x] CLI入口点配置完整
- [x] 导入测试覆盖所有模块
- [x] 断言方式具体可执行
- [x] 测试数据工厂可复用

## 实施顺序建议

1. **创建目录结构** - 使用 `mkdir -p` 命令
2. **创建骨架文件** - 使用模板生成基本结构
3. **实现类定义** - 添加必要的方法签名
4. **配置入口点** - 更新 pyproject.toml
5. **运行测试验证** - 执行所有测试确保通过

---
*此文档由 spec-task:impl-test-detail 生成，作为任务1测试实现的技术规格*
