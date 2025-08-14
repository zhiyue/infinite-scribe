---
description: 创建新的开发任务文档结构
allowed-tools: Write, Bash(mkdir:*, ls:*, tree:*)
---

## 任务信息

请提供以下信息来创建新任务：
- 任务名称（用于目录名，使用小写字母和连字符，如 user-authentication）
- 任务标题（中文描述）
- 任务背景（为什么需要这个任务）
- 任务目标（明确的目标）
- 相关文件（主要涉及的文件和模块）

## 当前任务列表

!`ls -la .tasks/ 2>/dev/null || echo "任务目录尚未创建"`

## 创建任务

我将帮您创建以下任务文档结构：

1. 在 `.tasks/$ARGUMENTS` 下创建任务目录
2. 创建 README.md - 任务概述和上下文
3. 创建 implementation-plan.md - 详细的实现方案（包含 Mermaid 图表）
4. 创建 todo-list.md - 任务清单和进度跟踪
5. 可选创建 progress.md - 实施进度记录

任务文档将遵循 CLAUDE.md 中定义的任务管理规则，确保包含必要的 Mermaid 图表和结构化内容。

请提供任务信息，我将为您创建完整的任务文档结构。