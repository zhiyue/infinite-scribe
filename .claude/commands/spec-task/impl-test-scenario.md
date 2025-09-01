---
description: Generate concise, testable TDD scenarios and datasets
allowed-tools: Bash, Read, Write, Edit, MultiEdit, Update, Glob, Grep, LS
argument-hint: <feature-name> [--task <id>] [-y] [--overwrite]
---

# 测试驱动场景生成（impl-test-scenario）

以测试驱动开发（TDD）为指导，先产出可测的测试场景、关联需求与测试数据，保持简洁清晰，便于 `impl` 阶段直接据此编写测试（RED）。

## 参数：$ARGUMENTS

- **feature-name**（必填）：功能名称（对应 `.tasks/<feature-name>/`）
- **--task <id>**（可选）：仅为指定任务生成测试场景（如 `1.1`）；省略则生成 feature 级场景
- **-y**（可选）：自动批准生成的测试场景
- **--overwrite**（可选）：存在同名文件时覆盖；默认提供交互式选项

## 必要文件检查

- 规范元数据：`.tasks/$ARGUMENTS/spec.json`（若缺失则提示先运行前置规范命令）
- 用于提取上下文（至少存在其一）：
  - 任务：`.tasks/$ARGUMENTS/tasks.md`
  - 需求：`.tasks/$ARGUMENTS/requirements.md`
  - 低层设计：`.tasks/$ARGUMENTS/design-lld.md`

## 输出路径与命名

生成目录：`.tasks/{feature}/task-plans/`

- Feature 级：`test-scenarios.md`
- Task 级：`task-<id>-test-scenarios.md`（如 `task-1.1-test-scenarios.md`）

若文件已存在且未指定 `--overwrite`，提供选项：
- **[o] 覆盖**：替换现有内容
- **[a] 追加**：在原有基础上追加新场景
- **[c] 取消**：保持现状，退出

## 内容要求（保持简洁，可直接转化为测试）

以编号条目列出场景；每个场景包含三项，均为单行或短代码块：

```
1. <场景名称>

- 场景描述：<一句话说明验证目标>
- 测试数据：`<可直接用于测试的输入>` 或代码块
- 预期结果：`<断言/输出的简洁表示>` 或代码块
```

可选附加（如需要）：
- 关联任务：`<id>`（如 `1.1`）
- 关联需求：`<EARS或FR/NFR标识>`

## 示例

需求为 ArgParser。

输出（节选）：

```
1. 布尔标志测试

- 场景描述：测试解析程序是否可以正确处理布尔标志。
- 测试数据：`-l -p 8080`
- 预期结果：`{"l": true}`
```

## 生成步骤

1. 载入 `.tasks/{feature}/tasks.md`（若存在），识别所选任务或功能域的关键行为；无则回退 `requirements.md`/`design-lld.md`
2. 为每个关键行为生成 3–7 个精炼场景（正向、边界、错误、空值/默认、组合）
3. 为每个场景补充最小可运行的测试数据与可断言的预期结果
4. 将内容写入上述输出路径

## 元数据更新（spec.json）

在 `.tasks/{feature}/spec.json` 中追加/更新：

```json
{
  "test_scenarios": {
    "generated": true,
    "approved": false,
    "generated_at": "{timestamp}",
    "feature_level": { "file": "task-plans/test-scenarios.md", "count": {n} },
    "tasks": {
      "{task_id}": { "file": "task-plans/task-{task_id}-test-scenarios.md", "count": {m}, "approved": false }
    }
  }
}
```

若使用 `-y`，对应 `approved` 置为 `true`。

## 与 impl 命令的协作

- impl 在执行指定任务时，优先读取：
  1) `.tasks/{feature}/task-plans/task-<id>-test-scenarios.md`
  2) `.tasks/{feature}/task-plans/test-scenarios.md`
- 若存在相应场景，RED 阶段直接据此编写测试用例；否则按既有流程进行

## 使用示例

```bash
# 为整个功能生成测试场景
/spec-task:impl-test-scenario user-auth -y

# 仅为任务 1.1 生成场景（推荐在实现前）
/spec-task:impl-test-scenario user-auth --task 1.1 -y

# 覆盖已有任务级场景
/spec-task:impl-test-scenario user-auth --task 2.3 --overwrite -y

# 随后在实施时将被优先使用
/spec-task:impl user-auth 1.1
```

---
*此命令用于以最小而完整的测试场景推动 TDD，实现快速落地与一致断言。*

