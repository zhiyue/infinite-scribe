---
description: 开始或继续开发特定任务，自动加载上下文并更新进度
allowed-tools: Read, Write, Edit, TodoWrite, Bash(cat:*, grep:*, date:*)
---

## 开发任务：$ARGUMENTS

### 任务上下文加载

#### 任务概述
@docs/development/tasks/$ARGUMENTS/README.md

#### 实现方案
@docs/development/tasks/$ARGUMENTS/implementation-plan.md

#### 当前进度
!`if [ -f "docs/development/tasks/$ARGUMENTS/todo-list.md" ]; then echo "=== TODO 状态 ==="; cat "docs/development/tasks/$ARGUMENTS/todo-list.md"; else echo "错误：任务不存在或 todo-list.md 缺失"; exit 1; fi`

#### 最近进度记录
!`if [ -f "docs/development/tasks/$ARGUMENTS/progress.md" ]; then echo "=== 最近进度 ==="; tail -n 20 "docs/development/tasks/$ARGUMENTS/progress.md"; else echo "暂无进度记录"; fi`

### 开发指引

基于上述任务上下文，我将：

1. **理解任务目标**：根据 README 和实现方案了解任务需求
2. **检查当前进度**：查看 todo-list 中的待办事项
3. **继续开发工作**：实现待办事项中的功能
4. **更新任务状态**：
   - 将进行中的任务标记在 todo-list
   - 完成后更新 todo-list 状态
   - 在 progress.md 中记录进度

### 自动进度跟踪

我会在开发过程中：
- 使用 TodoWrite 工具跟踪当前工作项
- 完成每个功能后更新 todo-list.md
- 定期在 progress.md 中添加进度记录

### 任务完成后

当所有待办事项完成后，我会提醒您：
- 使用 `/project:task-summary $ARGUMENTS` 创建任务总结
- 记录关键决策和经验教训

现在让我开始处理任务 "$ARGUMENTS" 的待办事项...