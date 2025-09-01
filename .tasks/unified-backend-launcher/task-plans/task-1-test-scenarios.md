# 测试场景 - 任务 1：目录与骨架

生成时间：2025-09-01T23:05:00Z
任务：创建 launcher 模块的目录结构与骨架文件
关联需求：FR-001（统一管理）；关联决策：ADR-005（CLI 架构）

## 测试场景

### 1. 目录结构创建测试

- 场景描述：验证launcher主目录及子目录是否正确创建
- 测试数据：`Path("src/launcher")`（测试运行目录为 apps/backend）
- 预期结果：`path.exists() and path.is_dir()`
- 关联任务：1

### 2. 适配器子目录测试

- 场景描述：验证adapters子目录是否存在
- 测试数据：`Path("src/launcher/adapters")`
- 预期结果：`path.exists() and path.is_dir()`
- 关联任务：1

### 3. 核心模块文件存在性测试

- 场景描述：验证所有核心模块文件是否创建
- 测试数据：`["__init__.py", "cli.py", "orchestrator.py", "health.py", "types.py", "errors.py"]`
- 预期结果：`all(Path(f"apps/backend/src/launcher/{f}").exists())`
 （Note：测试代码中请使用 `Path("src/launcher") / f`）
- 关联任务：1

### 4. CLI模块可导入测试

- 场景描述：验证cli模块是否可正常导入
- 测试数据：`import src.launcher.cli`
- 预期结果：`hasattr(src.launcher.cli, 'main')`
- 关联任务：1

### 5. 适配器文件完整性测试

- 场景描述：验证适配器目录下所有必需文件存在
- 测试数据：`["__init__.py", "api.py", "agents.py"]`
- 预期结果：`all(Path(f"apps/backend/src/launcher/adapters/{f}").exists())`
- 关联任务：1

### 6. Orchestrator类存在性测试

- 场景描述：验证Orchestrator类是否定义
- 测试数据：`from src.launcher.orchestrator import Orchestrator`
- 预期结果：`isinstance(Orchestrator, type)`
- 关联任务：1

### 7. HealthMonitor类存在性测试

- 场景描述：验证HealthMonitor类是否定义
- 测试数据：`from src.launcher.health import HealthMonitor`
- 预期结果：`isinstance(HealthMonitor, type)`
- 关联任务：1

### 8. ApiAdapter类存在性测试

- 场景描述：验证ApiAdapter类是否定义
- 测试数据：`from src.launcher.adapters.api import ApiAdapter`
- 预期结果：`isinstance(ApiAdapter, type)`
- 关联任务：1

### 9. AgentsAdapter类存在性测试

- 场景描述：验证AgentsAdapter类是否定义
- 测试数据：`from src.launcher.adapters.agents import AgentsAdapter`
- 预期结果：`isinstance(AgentsAdapter, type)`
- 关联任务：1

### 10. LauncherError异常类测试

- 场景描述：验证自定义异常类是否正确定义
- 测试数据：`from src.launcher.errors import LauncherError`
- 预期结果：`issubclass(LauncherError, Exception)`
- 关联任务：1

### 11. CLI入口点注册测试

- 场景描述：验证 pyproject.toml 中 CLI 入口点是否注册（PEP 621 `project.scripts`）
- 测试数据：使用 `tomllib.load(open("apps/backend/pyproject.toml", "rb"))`
- 预期结果：`config["project"]["scripts"].get("is-launcher") == "src.launcher.cli:main"`
- 关联任务：1

### 12. 模块版本信息测试

- 场景描述：验证launcher模块包含版本信息
- 测试数据：`import src.launcher`
- 预期结果：`hasattr(src.launcher, '__version__')`
- 关联任务：1

### 13. CLI help命令测试

- 场景描述：验证 CLI help 命令可正常执行
- 测试数据：`subprocess.run([sys.executable, "-m", "src.launcher.cli", "--help"], cwd="apps/backend")`
- 预期结果：`returncode == 0`
- 关联任务：1

### 14. 文件权限测试（可选）

- 场景描述：验证创建的 Python 文件具备基本可读权限（跨平台差异较大，建议可选）
- 测试数据：`Path("src/launcher/cli.py").stat()`
- 预期结果：在非 Windows 平台，`(st_mode & 0o444) != 0`
- 关联任务：1（可选）

### 15. 模块初始化导入测试

- 场景描述：验证__init__.py正确暴露必要的组件
- 测试数据：`from src.launcher import *`
- 预期结果：`no ImportError raised`
- 关联任务：1

---
*此文档由 spec-task:impl-test-scenario 生成，用于任务1的TDD测试驱动开发*
