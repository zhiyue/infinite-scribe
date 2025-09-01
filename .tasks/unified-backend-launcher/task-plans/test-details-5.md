# 任务 5 测试细节

**生成时间**：2025-01-09T22:15:00+08:00  
**任务描述**：适配器层 - 实现ApiAdapter和AgentsAdapter，支持单进程和多进程运行模式  
**关联场景**：task-5-test-scenarios.md

## 被测对象（SUT）

### 主要被测类

- **被测试的类叫** `BaseAdapter`。它的构造函数接受 `str name, Dict[str, Any] config` 作为参数；
- **BaseAdapter** 是抽象基类，定义了 `start()`, `stop(timeout: int)`, `health_check()` 抽象方法；
- **验证时**，通过检查 `status` 属性和方法返回值，完成验证

- **被测试的类叫** `ApiAdapter`。它的构造函数接受 `Dict[str, Any] config` 作为配置参数；
- **ApiAdapter** 的 `start()` 方法返回 `bool` 作为结果，支持单进程和多进程两种模式；
- **验证时**，通过检查 `status` 状态变化和 Mock 对象调用，完成验证

- **被测试的类叫** `AgentsAdapter`。它的构造函数接受 `Dict[str, Any] config` 作为配置参数；
- **AgentsAdapter** 的 `start()` 方法返回 `bool` 作为结果，接受 `Optional[List[str]] agents` 作为Agent列表；
- **验证时**，通过检查内部 `AgentLauncher` 实例的状态和方法调用，完成验证

## 详细规格

### 类继承结构
```python
# 类型定义
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from enum import Enum

class ComponentStatus(Enum):
    INIT = "init"
    STARTING = "starting"
    RUNNING = "running"
    DEGRADED = "degraded"
    STOPPING = "stopping" 
    STOPPED = "stopped"
    ERROR = "error"

# 基类定义
class BaseAdapter(ABC):
    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        self.status = ComponentStatus.INIT
        self._process: Optional[Any] = None
    
    @abstractmethod
    async def start(self) -> bool: pass
    
    @abstractmethod
    async def stop(self, timeout: int = 30) -> bool: pass
    
    @abstractmethod  
    async def health_check(self) -> Dict[str, Any]: pass
    
    def get_status(self) -> ComponentStatus:
        return self.status
```

### ApiAdapter 类定义
```python
import asyncio
import uvicorn
import os
from .base import BaseAdapter

class ApiAdapter(BaseAdapter):
    def __init__(self, config: Dict[str, Any]):
        super().__init__("api", config)
        self.mode = config.get("mode", "single")
        self.host = config.get("host", "127.0.0.1")
        self.port = config.get("port", 8000)
        self.app = config.get("app", "src.api.main:app")
        self._server: Optional[uvicorn.Server] = None
        self._process: Optional[asyncio.subprocess.Process] = None
    
    async def start(self) -> bool: pass
    async def stop(self, timeout: int = 30) -> bool: pass
    async def health_check(self) -> Dict[str, Any]: pass
    async def _start_single_mode(self) -> None: pass
    async def _start_multi_mode(self) -> None: pass
    async def _stop_process(self, timeout: int) -> None: pass
```

### AgentsAdapter 类定义
```python
from ...agents.launcher import AgentLauncher
from .base import BaseAdapter

class AgentsAdapter(BaseAdapter):
    def __init__(self, config: Dict[str, Any]):
        super().__init__("agents", config)
        self.agent_names: Optional[List[str]] = config.get("agents")
        self._launcher: Optional[AgentLauncher] = None
    
    async def start(self) -> bool: pass
    async def stop(self, timeout: int = 30) -> bool: pass
    async def health_check(self) -> Dict[str, Any]: pass
```

## 依赖注入

### BaseAdapter 依赖
| 依赖名称 | 类型 | 用途 | Mock策略 |
|---------|------|------|----------|
| name | str | 适配器标识 | 直接传入字符串 |
| config | Dict[str, Any] | 配置参数 | 构造测试字典 |

### ApiAdapter 依赖
| 依赖名称 | 类型 | 用途 | Mock策略 |
|---------|------|------|----------|
| uvicorn.Server | class | 单进程模式HTTP服务器 | patch + Mock实例 |
| asyncio.create_subprocess_exec | function | 多进程模式子进程 | patch + Mock返回值 |
| os.setsid | function | 进程组管理 | patch |
| structlog.get_logger | function | 日志记录 | patch |

### AgentsAdapter 依赖  
| 依赖名称 | 类型 | 用途 | Mock策略 |
|---------|------|------|----------|
| AgentLauncher | class | Agent管理器 | Mock实例 + AsyncMock方法 |
| structlog.get_logger | function | 日志记录 | patch |

## 方法规格

### BaseAdapter 方法

#### `__init__(name: str, config: Dict[str, Any])`
- **参数**：
  - `name: str` - 适配器名称标识
  - `config: Dict[str, Any]` - 配置字典
- **副作用**：设置实例属性，初始状态为INIT
- **验证点**：`self.name`, `self.config`, `self.status`

#### `start() -> bool` (抽象方法)
- **返回值**：`bool` - 启动是否成功
- **异常**：`NotImplementedError` - 抽象方法未实现

#### `get_status() -> ComponentStatus`
- **返回值**：`ComponentStatus` - 当前组件状态
- **验证点**：返回值等于 `self.status`

### ApiAdapter 方法

#### `start() -> bool`
- **参数**：无
- **返回值**：`bool` - 启动是否成功  
- **副作用**：状态变化 INIT -> STARTING -> RUNNING/ERROR
- **异常**：内部捕获，错误时返回False
- **验证点**：返回值、状态变化、依赖方法调用

#### `stop(timeout: int = 30) -> bool`
- **参数**：
  - `timeout: int` - 停止超时时间（秒）
- **返回值**：`bool` - 停止是否成功
- **副作用**：状态变化 RUNNING -> STOPPING -> STOPPED
- **验证点**：返回值、进程终止调用、状态变化

#### `health_check() -> Dict[str, Any]`
- **返回值**：`Dict[str, Any]` - 健康检查结果
- **验证点**：包含status和mode字段

### AgentsAdapter 方法

#### `start() -> bool` 
- **参数**：无
- **返回值**：`bool` - 启动是否成功
- **副作用**：创建AgentLauncher实例，加载和启动agents
- **验证点**：AgentLauncher方法调用、状态变化

#### `stop(timeout: int = 30) -> bool`
- **参数**：
  - `timeout: int` - 停止超时时间（秒）
- **返回值**：`bool` - 停止是否成功  
- **副作用**：调用AgentLauncher.stop_all()
- **验证点**：AgentLauncher.stop_all调用、状态变化

## 测试实现模板

### BaseAdapter 测试结构
```python
import pytest
from unittest.mock import Mock
from launcher.adapters.base import BaseAdapter
from launcher.types import ComponentStatus

class TestAdapter(BaseAdapter):
    """测试用的具体适配器实现"""
    async def start(self) -> bool:
        return True
    
    async def stop(self, timeout: int = 30) -> bool:
        return True
    
    async def health_check(self) -> Dict[str, Any]:
        return {"status": "healthy"}

class TestBaseAdapter:
    def test_adapter_init(self):
        """测试适配器初始化"""
        # Arrange
        name = "test"
        config = {"key": "value"}
        
        # Act
        adapter = TestAdapter(name, config)
        
        # Assert
        assert adapter.name == name
        assert adapter.config == config
        assert adapter.status == ComponentStatus.INIT
    
    def test_abstract_method_enforcement(self):
        """测试抽象方法强制实现"""
        # Act & Assert
        with pytest.raises(TypeError):
            BaseAdapter("test", {})
```

### ApiAdapter 测试结构  
```python
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, call
from launcher.adapters.api import ApiAdapter
from launcher.types import ComponentStatus

class TestApiAdapter:
    @pytest.fixture
    def single_mode_config(self):
        return {
            "mode": "single",
            "host": "127.0.0.1",
            "port": 8000,
            "app": "src.api.main:app"
        }
    
    @pytest.fixture
    def multi_mode_config(self):
        return {
            "mode": "multi",
            "host": "127.0.0.1", 
            "port": 8001
        }
    
    @pytest.mark.asyncio
    async def test_single_mode_start_success(self, single_mode_config):
        """测试单进程模式启动成功"""
        # Arrange
        adapter = ApiAdapter(single_mode_config)
        
        with patch('uvicorn.Server') as mock_server_class:
            mock_server = Mock()
            mock_server.startup = AsyncMock()
            mock_server.serve = AsyncMock()
            mock_server_class.return_value = mock_server
            
            with patch('asyncio.create_task') as mock_create_task:
                # Act
                result = await adapter.start()
                
                # Assert
                assert result is True
                assert adapter.status == ComponentStatus.RUNNING
                mock_server_class.assert_called_once()
                mock_server.startup.assert_called_once()
                mock_create_task.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_multi_mode_start_success(self, multi_mode_config):
        """测试多进程模式启动成功"""
        # Arrange  
        adapter = ApiAdapter(multi_mode_config)
        mock_process = Mock()
        mock_process.returncode = None
        
        with patch('asyncio.create_subprocess_exec') as mock_subprocess:
            mock_subprocess.return_value = mock_process
            with patch('asyncio.sleep'):
                # Act
                result = await adapter.start()
                
                # Assert
                assert result is True
                assert adapter.status == ComponentStatus.RUNNING
                assert adapter._process == mock_process
                mock_subprocess.assert_called_once()
                
    @pytest.mark.asyncio
    async def test_stop_with_timeout(self, multi_mode_config):
        """测试停止超时处理"""
        # Arrange
        adapter = ApiAdapter(multi_mode_config)
        mock_process = Mock()
        mock_process.terminate = AsyncMock()
        mock_process.wait = AsyncMock(side_effect=asyncio.TimeoutError)
        mock_process.kill = AsyncMock()
        adapter._process = mock_process
        
        # Act
        result = await adapter.stop(timeout=5)
        
        # Assert
        assert result is True
        mock_process.terminate.assert_called_once()
        mock_process.kill.assert_called_once()
```

### AgentsAdapter 测试结构
```python
import pytest
from unittest.mock import Mock, patch, AsyncMock
from launcher.adapters.agents import AgentsAdapter
from launcher.types import ComponentStatus

class TestAgentsAdapter:
    @pytest.fixture
    def agents_config(self):
        return {"agents": ["worldsmith", "writer"]}
    
    @pytest.mark.asyncio 
    async def test_start_with_specific_agents(self, agents_config):
        """测试启动指定agents"""
        # Arrange
        adapter = AgentsAdapter(agents_config)
        
        with patch('launcher.adapters.agents.AgentLauncher') as mock_launcher_class:
            mock_launcher = Mock()
            mock_launcher.load_agents = Mock()
            mock_launcher.setup_signal_handlers = Mock()
            mock_launcher.start_all = AsyncMock()
            mock_launcher_class.return_value = mock_launcher
            
            # Act
            result = await adapter.start()
            
            # Assert
            assert result is True
            assert adapter.status == ComponentStatus.RUNNING
            mock_launcher_class.assert_called_once()
            mock_launcher.setup_signal_handlers.assert_called_once()
            mock_launcher.load_agents.assert_called_once_with(["worldsmith", "writer"])
            mock_launcher.start_all.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_stop_success(self, agents_config):
        """测试停止agents成功"""
        # Arrange
        adapter = AgentsAdapter(agents_config)
        mock_launcher = Mock()
        mock_launcher.stop_all = AsyncMock()
        adapter._launcher = mock_launcher
        
        # Act
        result = await adapter.stop()
        
        # Assert
        assert result is True
        assert adapter.status == ComponentStatus.STOPPED
        mock_launcher.stop_all.assert_called_once()
```

## 断言策略

### 基本断言
- **相等性**：`assert adapter.name == "api"`
- **真值性**：`assert result is True`  
- **状态检查**：`assert adapter.status == ComponentStatus.RUNNING`

### Mock验证断言
- **调用次数**：`mock_method.assert_called_once()`
- **调用参数**：`mock_method.assert_called_once_with(expected_args)`
- **调用顺序**：`mock_method.assert_has_calls([call(arg1), call(arg2)])`

### 异步断言
- **异步方法**：使用 `@pytest.mark.asyncio` 和 `await`
- **异步Mock**：使用 `AsyncMock()` 替代 `Mock()`
- **超时测试**：使用 `asyncio.TimeoutError` 模拟超时

### 异常断言
- **抽象方法**：`with pytest.raises(TypeError)`
- **配置错误**：`with pytest.raises(ValueError)`
- **运行时错误**：检查返回值为False和状态为ERROR

## 测试数据工厂

### 有效配置数据
```python
def create_valid_api_config(mode: str = "single") -> Dict[str, Any]:
    return {
        "mode": mode,
        "host": "127.0.0.1",
        "port": 8000 if mode == "single" else 8001,
        "app": "src.api.main:app"
    }

def create_valid_agents_config(agents: List[str] = None) -> Dict[str, Any]:
    config = {}
    if agents:
        config["agents"] = agents
    return config
```

### 无效配置数据
```python
def create_invalid_api_config() -> Dict[str, Any]:
    return {
        "mode": "invalid_mode",
        "port": "not_a_number"
    }

def create_empty_config() -> Dict[str, Any]:
    return {}
```

### Mock对象工厂
```python
def create_mock_uvicorn_server() -> Mock:
    server = Mock()
    server.startup = AsyncMock()
    server.serve = AsyncMock()
    server.shutdown = AsyncMock()
    return server

def create_mock_process() -> Mock:
    process = Mock()
    process.terminate = AsyncMock()
    process.kill = AsyncMock()
    process.wait = AsyncMock()
    process.returncode = 0
    return process

def create_mock_agent_launcher() -> Mock:
    launcher = Mock()
    launcher.load_agents = Mock()
    launcher.setup_signal_handlers = Mock()
    launcher.start_all = AsyncMock()
    launcher.stop_all = AsyncMock()
    launcher.agents = {"worldsmith": Mock(), "writer": Mock()}
    launcher.running = True
    return launcher
```

## 边界条件测试

### 配置边界
- **空配置**：`{}`
- **部分配置**：只包含mode
- **无效值**：无效的mode、端口号

### 状态边界
- **重复启动**：已运行状态下再次启动
- **重复停止**：已停止状态下再次停止
- **异常状态**：ERROR状态的处理

### 时间边界
- **超时边界**：timeout=0, timeout=1, timeout=很大值
- **启动时间**：模拟启动慢的情况

## 验证清单

- [ ] 所有测试场景都有对应的测试方法
- [ ] SUT 的构造函数参数明确且可测试
- [ ] 核心方法签名完整并有具体实现
- [ ] 断言方式具体可执行
- [ ] Mock 策略清晰且符合项目实践
- [ ] 测试数据工厂提供完整的数据支持
- [ ] 边界条件覆盖充分
- [ ] 异步测试正确使用 pytest-asyncio

---
*此文档由 spec-task:impl-test-detail 生成，作为任务5测试实现的技术规格*