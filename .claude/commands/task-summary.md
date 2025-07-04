---
description: 为完成的任务创建总结文档
allowed-tools: Write, Read, Bash(cat:*, ls:*)
---

## 创建任务总结

任务名称：$ARGUMENTS

### 检查任务是否存在

!`if [ -d "docs/development/tasks/$ARGUMENTS" ]; then echo "✓ 任务目录存在"; else echo "✗ 错误：任务目录不存在"; fi`

### 当前任务状态

!`if [ -f "docs/development/tasks/$ARGUMENTS/todo-list.md" ]; then echo "=== TODO 列表状态 ==="; cat "docs/development/tasks/$ARGUMENTS/todo-list.md" | grep -E "^#|^\-"; fi`

## 创建总结文档

我将为任务 `$ARGUMENTS` 创建 summary.md 文档，包含：

1. **实现概述** - 简要描述最终的实现方案
2. **最终架构** - 使用 Mermaid 图表描述最终实现
   - 实现架构图
   - 数据流图
   - 类图（如适用）
3. **关键决策** - 记录重要的技术决策和理由
4. **经验教训** - 遇到的问题、解决方案和改进建议
5. **性能指标** - 如果适用，记录性能改进数据
6. **后续建议** - 未来可能的优化或扩展方向

请确认任务已完成，我将基于任务的实现情况创建详细的总结文档。

### 需要的信息

为了创建高质量的总结，请提供：
- 最终实现的架构描述
- 遇到的主要问题和解决方案
- 关键的技术决策
- 可以改进的地方
- 任何性能或质量指标