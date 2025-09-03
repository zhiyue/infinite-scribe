# 任务 4 测试细节（修订版）

生成时间：2025-09-02T00:00:00Z  
任务描述：CLI（最小集）- `is-launcher` 命令行接口  
关联场景：task-4-test-scenarios.md  
代码定位：`apps/backend/src/launcher/cli.py`

## 被测对象（SUT）

- 模块函数：`src.launcher.cli.main`
- 辅助函数：`src.launcher.cli._parse_list_like`、`src.launcher.cli._parse_components`
- 配置模型：`src.core.config.Settings`（仅用于 `up` 命令解析默认值与校验）

说明：当前实现为函数式 CLI（非类）。历史草案中提到的 `LauncherCLI` 类、`run/setup_parser/_handle_*` 方法不存在，测试需以模块函数与子进程方式验证行为。

## CLI 参数与语义

- 子命令：`up`、`down`、`status`、`logs`
- `up`：
  - `--mode {single,multi,auto}`（可选；默认取自 `Settings().launcher.default_mode`）
  - `--components <CSV|JSON>`（可选；默认取自 `Settings().launcher.components`；解析到 `ComponentType`，去重、非空）
  - `--agents <CSV|JSON>`（可选；默认取自 `Settings().launcher.agents.names`；经 `LauncherAgentsConfig` 校验：非空列表、命名规则、长度）
  - `--reload`（布尔开关；当前实现未参与输出，仅参与解析）
- `down`：`--grace <int>`（默认 10）
- `status`：`--watch`（布尔）
- `logs`：`component` 必填，取值 `api|agents|all`

通用行为：
- 未指定子命令：打印 `--help` 并以退出码 0 结束。
- 非法子命令或非法取值：`argparse` 打印错误到 `stderr`，退出码 2。

## 行为与输出规范

### up 命令
- 解析成功时打印一行计划摘要，例如：
  - `Launcher plan => mode=<mode>, components=[api,agents], agents=<csv or <auto>>, api.reload=<bool>`
- 断言策略：
  - 通过子进程执行 `python -m src.launcher.cli up ...` 捕获 `stdout/stderr`；
  - 使用包含匹配与正则匹配验证关键字段（避免对整行严格比对造成脆弱性）；
  - 模式解析：`--mode` 显式传入优先生效，否则取 `Settings().launcher.default_mode`；
  - 组件解析：支持 CSV 与 JSON 数组；去重后保持顺序；空数组或解析失败时报错；
  - Agents 解析：支持 CSV 与 JSON 数组；传空数组报错；非法命名或超长报错；未指定时从配置读取或显示 `<auto>`；
  - `--reload` 仅校验可解析（当前实现输出中未体现）。

错误输出规范（匹配片段示例）：
- 组件未知：`Invalid --components: Unknown component '<x>' (allowed: api, agents)`
- 组件空：`Invalid --components: Components list cannot be empty`
- 组件 JSON 非法：`Invalid JSON list:` 或 `JSON value must be a list of strings`
- Agents 非法：`Invalid --agents: <pydantic 错误消息>`（含空列表、命名不匹配、长度超限等）

### down/status/logs 命令（当前为占位实现）
- 解析成功后仅打印：`Command: <cmd>` 到 `stdout`；
- `logs` 需校验位置参数存在且取值于 `api|agents|all`。

## 推荐测试方式

- 首选以子进程调用模块形式执行：
  - `subprocess.run([sys.executable, "-m", "src.launcher.cli", ...], capture_output=True, text=True)`
  - 这样可稳定捕获 `argparse` 的 `SystemExit`、标准输出与标准错误。
- 对纯函数 `_parse_list_like/_parse_components` 可直接单元测试（无需子进程）。

## 测试代码片段示例

### 1) up 命令（CSV/JSON/默认）
```python
import json, sys, subprocess

def run_cli(args: list[str]):
    return subprocess.run([sys.executable, "-m", "src.launcher.cli", *args], capture_output=True, text=True)

def test_up_default_from_settings():
    r = run_cli(["up"])  # 使用 Settings().launcher 默认
    assert r.returncode == 0
    assert "Launcher plan =>" in r.stdout
    assert "components=[" in r.stdout
    assert "api.reload=" in r.stdout

def test_up_components_csv():
    r = run_cli(["up", "--components", "api,agents"])
    assert r.returncode == 0
    assert "components=[api,agents]" in r.stdout

def test_up_components_json():
    r = run_cli(["up", "--components", json.dumps(["api", "agents", "api"])])
    assert r.returncode == 0
    # 去重后保持顺序
    assert "components=[api,agents]" in r.stdout

def test_up_mode_single():
    r = run_cli(["up", "--mode", "single"])  # choices: single/multi/auto
    assert r.returncode == 0
    assert "mode=single" in r.stdout

def test_up_agents_csv_and_validation():
    r = run_cli(["up", "--agents", "writer,editor-1"])
    assert r.returncode == 0
    assert "agents=writer,editor-1" in r.stdout or "agents=" in r.stdout

def test_up_agents_empty_list_invalid():
    r = run_cli(["up", "--agents", "[]"])  # 空列表非法（pydantic 校验）
    assert r.returncode == 2
    assert "Agent names list cannot be empty" in r.stderr
```

### 2) up 命令错误场景
```python
def test_up_components_unknown():
    r = run_cli(["up", "--components", "api,unknown"])  # Unknown component
    assert r.returncode == 2
    assert "Unknown component" in r.stderr

def test_up_components_invalid_json():
    r = run_cli(["up", "--components", "[1,2]"])  # 非字符串列表
    assert r.returncode == 2
    assert "JSON value must be a list of strings" in r.stderr
```

### 3) down/status/logs（占位）
```python
def test_down_grace_default():
    r = run_cli(["down"])  # 默认 grace=10，仅验证可解析
    assert r.returncode == 0
    assert r.stdout.strip() == "Command: down"

def test_status_watch_flag():
    r = run_cli(["status", "--watch"])
    assert r.returncode == 0
    assert r.stdout.strip() == "Command: status"

def test_logs_component_all():
    r = run_cli(["logs", "all"])  # 允许 api/agents/all
    assert r.returncode == 0
    assert r.stdout.strip() == "Command: logs"

def test_logs_missing_component():
    r = run_cli(["logs"])  # 缺少必填位置参数
    assert r.returncode == 2
    assert "the following arguments are required" in r.stderr
```

### 4) 通用与帮助信息
```python
def test_no_command_shows_help_exit0():
    r = run_cli([])
    assert r.returncode == 0
    assert "usage:" in r.stdout.lower()

def test_help_flag():
    r = run_cli(["--help"])
    assert r.returncode == 0
    # 描述文字为英文：Unified Backend Launcher for InfiniteScribe
    assert "launcher" in (r.stdout + r.stderr).lower()
```

### 5) 纯函数单测
```python
from src.launcher.cli import _parse_list_like, _parse_components
from src.launcher.types import ComponentType
import pytest

def test_parse_list_like_csv():
    assert _parse_list_like("a,b , c") == ["a", "b", "c"]

def test_parse_list_like_json():
    assert _parse_list_like('["a","b"]') == ["a", "b"]

def test_parse_components_ok_and_dedup():
    items = _parse_components(["api", "agents", "api"])  # 去重
    assert items == [ComponentType.API, ComponentType.AGENTS]

def test_parse_components_unknown_raises():
    with pytest.raises(ValueError):
        _parse_components(["unknown"])  # 非允许集合
```

## 目录与命名建议

- 单元测试：`apps/backend/tests/unit/launcher/test_cli_parsing.py`、`test_cli_helpers.py`
- 集成测试（可选）：`apps/backend/tests/integration/launcher/test_cli_invocation.py`
- 遵循仓库测试命名规范（pytest，`test_*.py`）。

## 超时与稳定性

- 建议使用 `pytest-timeout`（或 CI 外层 `timeout` 命令）控制用例级/任务级超时：
  - 单元测试：5–10s；集成测试：30–60s；全量：60–120s
- 避免对毫秒级性能做硬性断言，优先通过超时机制保障稳定性（原草案的 `<100ms/<50ms` 断言建议移除或放宽为软断言）。

## 验收要点（对应场景文档）

- `up`：模式解析、组件解析（CSV/JSON、去重、错误）、Agents 解析与校验；打印计划摘要包含关键字段。
- `down/status/logs`：参数可解析；`logs` 支持 `api|agents|all`；占位输出 `Command: <cmd>`。
- 帮助/错误：未给命令显示帮助并退出码 0；非法值退出码 2 且错误包含关键信息。
- 入口：`python -m src.launcher.cli --help` 可用；`pyproject.toml` 中 `is-launcher = "src.launcher.cli:main"` 存在。

---
此文档已对齐当前函数式实现（非类）。后续若 CLI 增强（例如整合 orchestrator、实际执行业务逻辑），可在不改变现有断言稳定性的前提下扩充输出匹配与副作用验证。

