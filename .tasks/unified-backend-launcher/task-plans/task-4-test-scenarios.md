# Task 4 测试场景 - CLI（最小集，修订版）

生成时间：2025-09-02T00:00:00Z  
关联任务：4  
关联需求：FR-001, FR-002, NFR-003  
测试场景数量：28

说明：本场景集已对齐函数式实现（`apps/backend/src/launcher/cli.py`）。输出断言以包含/正则方式验证关键字段，避免对整行输出的脆弱匹配。

## 基础与帮助

1) 未指定命令显示帮助并退出码 0  
- 命令：`python -m src.launcher.cli`  
- 预期：`returncode=0`，`stdout` 包含 `usage:`

2) `--help` 显示帮助  
- 命令：`python -m src.launcher.cli --help`  
- 预期：`returncode=0`，输出包含 `launcher` 关键词

3) 非法子命令报错  
- 命令：`python -m src.launcher.cli invalid_cmd`  
- 预期：`returncode=2`，`stderr` 包含 `invalid choice`

## Up 命令

4) 默认启动（取自 Settings）  
- 命令：`python -m src.launcher.cli up`  
- 预期：`returncode=0`，`stdout` 含 `Launcher plan =>`、`components=[`、`api.reload=`

5) 显式模式 single  
- 命令：`... up --mode single`  
- 预期：`returncode=0`，`stdout` 含 `mode=single`

6) 显式模式 multi  
- 命令：`... up --mode multi`  
- 预期：`returncode=0`，`stdout` 含 `mode=multi`

7) 显式模式 auto  
- 命令：`... up --mode auto`  
- 预期：`returncode=0`，`stdout` 含 `mode=auto`

8) 无效模式报错  
- 命令：`... up --mode invalid`  
- 预期：`returncode=2`，`stderr` 含 `invalid choice`

9) components=CSV（api,agents）  
- 命令：`... up --components api,agents`  
- 预期：`returncode=0`，`stdout` 含 `components=[api,agents]`

10) components=JSON 去重并保持顺序  
- 命令：`... up --components ["api","agents","api"]`  
- 预期：`returncode=0`，`stdout` 含 `components=[api,agents]`

11) components=空字符串触发空列表错误  
- 命令：`... up --components ""`  
- 预期：`returncode=2`，`stderr` 含 `Components list cannot be empty`

12) components=非法 JSON  
- 命令：`... up --components [1,2]`  
- 预期：`returncode=2`，`stderr` 含 `JSON value must be a list of strings`

13) components=包含未知项  
- 命令：`... up --components api,unknown`  
- 预期：`returncode=2`，`stderr` 含 `Unknown component`

14) agents=CSV  
- 命令：`... up --agents writer,editor-1`  
- 预期：`returncode=0`，`stdout` 包含 `agents=` 片段

15) agents=JSON  
- 命令：`... up --agents ["writer","editor-1"]`  
- 预期：`returncode=0`，`stdout` 包含 `agents=` 片段

16) agents=空 JSON 列表报错  
- 命令：`... up --agents []`  
- 预期：`returncode=2`，`stderr` 含 `Agent names list cannot be empty`

17) agents=非法命名报错  
- 命令：`... up --agents writer,invalid name`（含空格）  
- 预期：`returncode=2`，`stderr` 含 `Invalid agent name`

18) 未指定 agents 使用配置默认  
- 命令：`... up`  
- 预期：`returncode=0`，若配置为 `None`，则 `stdout` 含 `agents=<auto>`

19) reload 开关可解析  
- 命令：`... up --reload`  
- 预期：`returncode=0`（当前实现输出不包含 reload 字段，仅校验不报错）

## Down 命令（占位）

20) 基本 down  
- 命令：`... down`  
- 预期：`returncode=0`，`stdout` 为 `Command: down`

21) down 自定义 grace  
- 命令：`... down --grace 15`  
- 预期：`returncode=0`，`stdout` 为 `Command: down`

## Status 命令（占位）

22) 基本 status  
- 命令：`... status`  
- 预期：`returncode=0`，`stdout` 为 `Command: status`

23) status --watch  
- 命令：`... status --watch`  
- 预期：`returncode=0`，`stdout` 为 `Command: status`

## Logs 命令（占位）

24) logs api  
- 命令：`... logs api`  
- 预期：`returncode=0`，`stdout` 为 `Command: logs`

25) logs agents  
- 命令：`... logs agents`  
- 预期：`returncode=0`，`stdout` 为 `Command: logs`

26) logs all  
- 命令：`... logs all`  
- 预期：`returncode=0`，`stdout` 为 `Command: logs`

27) logs 缺少 component  
- 命令：`... logs`  
- 预期：`returncode=2`，`stderr` 含 `the following arguments are required`

28) logs 非法 component  
- 命令：`... logs invalid`  
- 预期：`returncode=2`，`stderr` 含 `invalid choice`

## 集成与入口

- `python -m src.launcher.cli --help` 可成功执行并返回 0；
- `pyproject.toml` 存在入口：`is-launcher = "src.launcher.cli:main"`；
- 若安装为控制台脚本，`is-launcher --help` 可用（CI 可选验证）。

## 验收标准映射

- FR-001：场景 4–19（模式、组件、agents 参数解析与错误处理）
- FR-002：场景 9–10, 13–16（选择性服务控制/过滤能力）
- NFR-003：通过 pytest-timeout/外层 `timeout` 控制总时长，避免微基准的脆弱性

## 说明与注意

- 所有断言使用包含匹配或正则匹配关键片段（如 `mode=single`、`components=[api,agents]`），避免依赖完整输出字符串；
- `down/status/logs` 当前为占位实现，仅验证解析与占位输出；
- 建议在 `apps/backend/tests/unit/launcher/` 下组织用例；
- 超时策略参考仓库指南：单测 5–10s、集成 30–60s、全量 60–120s（可在 CI 外层包裹 `timeout`）。

