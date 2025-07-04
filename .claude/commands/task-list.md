---
description: 列出所有开发任务及其状态
allowed-tools: Bash(ls:*, tree:*, find:*, grep:*)
---

## 任务列表

### 所有任务概览

!`tree docs/development/tasks/ -d -L 1 2>/dev/null || echo "尚未创建任何任务"`

### 任务详情

!`find docs/development/tasks -name "README.md" -type f 2>/dev/null | while read -r file; do echo ""; echo "=== $(dirname "$file" | sed 's|docs/development/tasks/||') ==="; head -n 20 "$file" | grep -E "^#|^##|任务背景|目标" | head -n 10; done`

### 任务进度统计

!`find docs/development/tasks -name "todo-list.md" -type f 2>/dev/null | while read -r file; do echo ""; echo "=== $(dirname "$file" | sed 's|docs/development/tasks/||') ==="; grep -c "\[x\]" "$file" 2>/dev/null && echo "已完成项" || echo "0 已完成项"; grep -c "\[ \]" "$file" 2>/dev/null && echo "待办项" || echo "0 待办项"; done`

### 最近更新的任务

!`find docs/development/tasks -type f -name "*.md" -mtime -7 2>/dev/null | head -10 | while read -r file; do echo "$(date -r "$file" "+%Y-%m-%d %H:%M") - $(echo "$file" | sed 's|docs/development/tasks/||')"; done | sort -r`

## 使用其他任务命令

- `/project:task-new <任务名>` - 创建新任务
- `/project:task-summary <任务名>` - 为任务创建总结
- `/project:task-review <任务名>` - 查看特定任务详情