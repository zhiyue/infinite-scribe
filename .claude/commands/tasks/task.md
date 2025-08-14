---
description: 任务管理主命令 - 管理开发任务文档
allowed-tools: Bash(echo:*, ls:*)
---

# 任务管理系统

根据 CLAUDE.md 中定义的任务管理规则，使用以下命令管理开发任务：

## 可用命令

### 📝 创建新任务
```
/project:tasks/task-new <任务名称>
```
示例：`/project:tasks/task-new user-authentication`

创建包含以下文件的任务文档结构：
- README.md - 任务概述和上下文
- implementation-plan.md - 实现方案（含 Mermaid 图表）
- todo-list.md - 任务清单和进度跟踪

### 📋 查看所有任务
```
/project:tasks/task-list
```
显示所有任务的列表、进度统计和最近更新

### 🔍 查看特定任务
```
/project:tasks/task-review <任务名称>
```
示例：`/project:tasks/task-review concept-template-model`

查看任务的详细信息，包括：
- 任务概述
- 实现方案
- 当前进度
- 进度记录

### 📊 创建任务总结
```
/project:tasks/task-summary <任务名称>
```
示例：`/project:tasks/task-summary concept-template-model`

为已完成的任务创建总结文档，包含：
- 最终架构（Mermaid 图表）
- 关键决策
- 经验教训
- 后续建议

## 任务管理最佳实践

1. **开始新任务前**：使用 `/project:tasks/task-new` 创建文档结构
2. **开发过程中**：持续更新 todo-list.md 和 progress.md
3. **任务完成后**：使用 `/project:tasks/task-summary` 创建总结
4. **查看历史任务**：使用 `/project:tasks/task-review` 参考以往经验

## 任务文档位置

所有任务文档存储在：`.tasks/`

!`echo "当前任务数量：$(find .tasks -maxdepth 1 -type d 2>/dev/null | grep -v "^.tasks$" | wc -l 2>/dev/null || echo 0)"`