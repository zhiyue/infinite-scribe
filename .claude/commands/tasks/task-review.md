---
description: 查看特定任务的详细信息
allowed-tools: Read, Bash(cat:*, ls:*, head:*, tail:*)
---

## 任务详情查看

任务名称：$ARGUMENTS

### 任务目录检查

!`if [ -d ".tasks/$ARGUMENTS" ]; then echo "✓ 任务存在"; ls -la ".tasks/$ARGUMENTS/"; else echo "✗ 任务不存在"; exit 1; fi`

### 任务概述 (README.md)

!`if [ -f ".tasks/$ARGUMENTS/README.md" ]; then cat ".tasks/$ARGUMENTS/README.md"; else echo "README.md 不存在"; fi`

### 实现方案概览 (implementation-plan.md)

!`if [ -f ".tasks/$ARGUMENTS/implementation-plan.md" ]; then echo "=== 实现方案 ==="; head -n 50 ".tasks/$ARGUMENTS/implementation-plan.md" | grep -E "^#|^##|^###" | head -20; echo ""; echo "查看完整实现方案请使用 Read 工具"; else echo "implementation-plan.md 不存在"; fi`

### 当前进度 (todo-list.md)

!`if [ -f ".tasks/$ARGUMENTS/todo-list.md" ]; then cat ".tasks/$ARGUMENTS/todo-list.md"; else echo "todo-list.md 不存在"; fi`

### 进度记录 (progress.md)

!`if [ -f ".tasks/$ARGUMENTS/progress.md" ]; then echo "=== 最新进度 ==="; tail -n 30 ".tasks/$ARGUMENTS/progress.md"; else echo "progress.md 不存在（可选文件）"; fi`

### 任务总结 (summary.md)

!`if [ -f ".tasks/$ARGUMENTS/summary.md" ]; then echo "=== 任务已完成，查看总结 ==="; head -n 50 ".tasks/$ARGUMENTS/summary.md"; echo ""; echo "查看完整总结请使用 Read 工具"; else echo "summary.md 不存在（任务可能尚未完成）"; fi`

## 可用操作

- 继续未完成的任务
- 查看完整的实现方案或总结
- 更新任务进度
- 创建任务总结（使用 `/project:tasks/task-summary $ARGUMENTS`）