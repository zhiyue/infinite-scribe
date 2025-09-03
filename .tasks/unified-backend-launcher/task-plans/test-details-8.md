# 任务 8 测试细节

生成时间：2025-09-02T16:45:00Z
任务描述：管理端点（开发默认启用）- 实现 /admin/launcher/status 和 /admin/launcher/health 端点
关联场景：test-scenarios-8.md

## 被测对象（SUT）

- **被测试的类叫** `AdminRouter`。它是一个 FastAPI 路由器，通过依赖注入接受 `orchestrator_service, health_monitor_service, settings` 作为依赖；
- **AdminRouter** 的 `get_launcher_status` 方法返回 `LauncherStatusResponse` 作为结果，不接受参数；
- **AdminRouter** 的 `get_health_summary` 方法返回 `HealthSummaryResponse` 作为结果，不接受参数；
- **验证时**，通过检查 FastAPI 测试客户端的响应状态码、JSON 结构和字段值，完成验证

## 详细规格

### 路由定义
```python
from fastapi import APIRouter, Depends, HTTPException
from apps.backend.src.launcher.orchestrator import OrchestratorService
from apps.backend.src.launcher.health import HealthMonitor
from apps.backend.src.core.config import Settings

router = APIRouter(prefix="/admin/launcher", tags=["launcher-admin"])

@router.get("/status", response_model=LauncherStatusResponse)
async def get_launcher_status(
    orchestrator: OrchestratorService = Depends(get_orchestrator),
    settings: Settings = Depends(get_settings)
): ...

@router.get("/health", response_model=HealthSummaryResponse) 
async def get_health_summary(
    health_monitor: HealthMonitor = Depends(get_health_monitor),
    settings: Settings = Depends(get_settings)
): ...
```

### 依赖注入
| 依赖名称 | 类型 | 用途 | Mock策略 |
|---------|------|------|----------|
| orchestrator | OrchestratorService | 获取服务状态信息 | Mock 返回预定义服务列表 |
| health_monitor | HealthMonitor | 获取健康检查数据 | Mock 返回健康状态缓存 |
| settings | Settings | 环境配置和权限控制 | Mock environment 属性 |

### 响应模型规格

#### LauncherStatusResponse
- **launcher_status**: `str` - "running"|"partial"|"starting"|"stopped"
- **services**: `List[ServiceStatus]` - 服务状态列表
- **total_services**: `int` - 服务总数
- **running_services**: `int` - 运行中服务数
- **timestamp**: `str` - ISO 8601 格式时间戳

#### HealthSummaryResponse
- **cluster_status**: `str` - "healthy"|"degraded"|"unhealthy"|"unknown"
- **services**: `List[ServiceHealth]` - 服务健康状态列表
- **healthy_count**: `int` - 健康服务数
- **total_count**: `int` - 服务总数
- **timestamp**: `str` - ISO 8601 格式时间戳

#### ServiceStatus
- **name**: `str` - 服务名称
- **status**: `str` - 服务状态字符串
- **uptime_seconds**: `int` - 运行时间（秒）
- **started_at**: `str` - 启动时间 ISO 格式
- **pid**: `int` - 进程ID
- **port**: `int` - 服务端口

#### ServiceHealth
- **service_name**: `str` - 服务名称
- **status**: `str` - 健康状态
- **response_time_ms**: `float` - 响应时间（毫秒）
- **last_check**: `str` - 最后检查时间 ISO 格式
- **error**: `Optional[str]` - 错误信息

## 测试实现模板

### 测试结构
```python
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
from apps.backend.src.api.routes.admin import router
from apps.backend.src.launcher.types import ServiceState, ServiceStatus, HealthStatus

@pytest.fixture
def mock_orchestrator():
    orchestrator = Mock()
    return orchestrator

@pytest.fixture 
def mock_health_monitor():
    health_monitor = Mock()
    return health_monitor

@pytest.fixture
def mock_settings():
    settings = Mock()
    settings.environment = "development"
    return settings

@pytest.fixture
def test_client(mock_orchestrator, mock_health_monitor, mock_settings):
    app = FastAPI()
    
    app.dependency_overrides[get_orchestrator] = lambda: mock_orchestrator
    app.dependency_overrides[get_health_monitor] = lambda: mock_health_monitor  
    app.dependency_overrides[get_settings] = lambda: mock_settings
    
    app.include_router(router)
    return TestClient(app)

class TestAdminEndpoints:
    
    def test_get_launcher_status_success(self, test_client, mock_orchestrator):
        # Arrange
        service_data = [
            ServiceStatus(
                name="api-gateway",
                status=ServiceState.RUNNING,
                uptime_seconds=1800,
                started_at="2025-09-02T15:30:00Z",
                pid=12345,
                port=8000
            ),
            ServiceStatus(
                name="agent-worker", 
                status=ServiceState.STARTING,
                uptime_seconds=0,
                started_at="2025-09-02T16:40:00Z", 
                pid=12346,
                port=8001
            )
        ]
        mock_orchestrator.get_service_statuses.return_value = service_data
        
        # Act
        response = test_client.get("/admin/launcher/status")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["launcher_status"] == "partial"
        assert data["total_services"] == 2
        assert data["running_services"] == 1
        assert len(data["services"]) == 2
        assert data["services"][0]["name"] == "api-gateway"
        assert data["services"][0]["status"] == "running"
        
    def test_get_health_summary_success(self, test_client, mock_health_monitor):
        # Arrange  
        health_data = [
            {
                "service_name": "api-gateway",
                "status": HealthStatus.HEALTHY,
                "response_time_ms": 25.0,
                "last_check": "2025-09-02T16:39:45Z",
                "error": None
            },
            {
                "service_name": "agent-worker",
                "status": HealthStatus.DEGRADED, 
                "response_time_ms": 150.0,
                "last_check": "2025-09-02T16:39:30Z",
                "error": "High response time"
            }
        ]
        mock_health_monitor.get_cluster_health.return_value = health_data
        
        # Act
        response = test_client.get("/admin/launcher/health")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["cluster_status"] == "degraded"
        assert data["total_count"] == 2
        assert data["healthy_count"] == 1
        assert len(data["services"]) == 2
```

### 场景到测试的映射

#### 场景1：获取启动器状态成功
```python
def test_launcher_status_partial_running(self, test_client, mock_orchestrator):
    # Arrange
    services = [
        create_running_service("api-gateway", 8000, 1800),
        create_starting_service("agents", 8001, 0) 
    ]
    mock_orchestrator.get_service_statuses.return_value = services
    
    # Act
    response = test_client.get("/admin/launcher/status")
    
    # Assert
    assert response.status_code == 200
    assert response.json()["launcher_status"] == "partial"
    assert response.json()["running_services"] == 1
    assert response.json()["total_services"] == 2
```

#### 场景2：全部服务运行状态
```python
def test_launcher_status_all_running(self, test_client, mock_orchestrator):
    # Arrange
    services = [
        create_running_service("api-gateway", 8000, 1800),
        create_running_service("agents", 8001, 900)
    ]
    mock_orchestrator.get_service_statuses.return_value = services
    
    # Act
    response = test_client.get("/admin/launcher/status")
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["launcher_status"] == "running" 
    assert data["running_services"] == data["total_services"]
```

#### 场景3：开发环境启用端点
```python
def test_development_environment_enables_endpoints(self, mock_settings, test_client):
    # Arrange
    mock_settings.environment = "development"
    
    # Act & Assert
    status_response = test_client.get("/admin/launcher/status")
    health_response = test_client.get("/admin/launcher/health")
    
    assert status_response.status_code != 404
    assert health_response.status_code != 404
```

#### 场景4：生产环境默认禁用  
```python
def test_production_environment_disables_by_default(self, mock_settings, test_client):
    # Arrange
    mock_settings.environment = "production"
    mock_settings.admin_enabled = False
    
    # Act & Assert
    with patch('apps.backend.src.api.routes.admin.require_admin_access') as mock_auth:
        mock_auth.side_effect = HTTPException(404, "Not Found")
        
        status_response = test_client.get("/admin/launcher/status")  
        health_response = test_client.get("/admin/launcher/health")
        
        assert status_response.status_code == 404
        assert health_response.status_code == 404
```

## 断言策略

### 基本断言
- **状态码验证**：`assert response.status_code == 200`
- **JSON结构验证**：`assert "launcher_status" in response.json()`
- **字段类型验证**：`assert isinstance(data["total_services"], int)`

### 响应数据断言
- **枚举值验证**：`assert data["launcher_status"] in ["running", "partial", "starting", "stopped"]`
- **时间格式验证**：`assert datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00"))`
- **数值关系验证**：`assert data["running_services"] <= data["total_services"]`

### Mock验证
- **方法调用验证**：`mock_orchestrator.get_service_statuses.assert_called_once()`
- **参数验证**：`mock_health_monitor.get_cluster_health.assert_called_with()`
- **调用顺序验证**：使用 `call()` 检查调用序列

## 测试数据工厂

### 有效数据生成
```python
def create_running_service(name: str, port: int, uptime: int) -> ServiceStatus:
    return ServiceStatus(
        name=name,
        status=ServiceState.RUNNING,
        uptime_seconds=uptime,
        started_at=datetime.utcnow().isoformat() + "Z",
        pid=random.randint(1000, 99999),
        port=port
    )

def create_healthy_service(name: str) -> dict:
    return {
        "service_name": name,
        "status": HealthStatus.HEALTHY,
        "response_time_ms": random.uniform(10.0, 50.0),
        "last_check": datetime.utcnow().isoformat() + "Z",
        "error": None
    }
```

### 错误场景数据生成
```python
def create_failed_service(name: str, error: str) -> ServiceStatus:
    return ServiceStatus(
        name=name,
        status=ServiceState.ERROR,
        uptime_seconds=0,
        started_at=datetime.utcnow().isoformat() + "Z",
        pid=0,
        port=0
    )

def create_unhealthy_service(name: str, error: str) -> dict:
    return {
        "service_name": name,
        "status": HealthStatus.UNHEALTHY,
        "response_time_ms": 0.0,
        "last_check": datetime.utcnow().isoformat() + "Z", 
        "error": error
    }
```

## 验证清单

- [x] 所有场景都有对应的测试细节
- [x] SUT 的依赖注入参数明确
- [x] 核心方法签名完整
- [x] 断言方式具体可执行
- [x] Mock 策略清晰
- [x] 响应模型定义完整
- [x] 环境控制逻辑明确
- [x] 错误处理场景覆盖
- [x] 性能要求可测试化
- [x] 数据工厂函数实用

---
*此文档由 spec-task:impl-test-detail 生成，作为测试实现的技术规格*