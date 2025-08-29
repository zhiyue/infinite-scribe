---
description: Initialize a new specification with detailed project description and requirements
allowed-tools: Bash, Read, Write, Glob
---

# 规范初始化

基于提供的项目描述初始化新规范：

**项目描述**: `$ARGUMENTS`

## 任务：初始化规范结构

**范围**：此命令基于提供的详细项目描述初始化目录结构和元数据。

### 1. 生成功能名称

从项目描述（`$ARGUMENTS`）创建一个简洁、描述性的功能名称。

**检查现有的 `.tasks/` 目录以确保生成的功能名称是唯一的。如果存在冲突，添加数字后缀（例如：feature-name-2）。**

### 2. 创建规范目录

创建 `.tasks/{generated-feature-name}/` 目录，包含模板文件：

- `requirements.md` - 用户故事的空模板
- `design.md` - 技术设计的空模板
- `tasks.md` - 实施任务的空模板
- `spec.json` - 元数据和审批追踪

### 3. 初始化 spec.json 元数据

创建包含审批追踪的初始元数据：

```json
{
  "feature_name": "{generated-feature-name}",
  "created_at": "current_timestamp",
  "updated_at": "current_timestamp",
  "language": "chinese",
  "phase": "initialized",
  "approvals": {
    "requirements": {
      "generated": false,
      "approved": false
    },
    "design": {
      "generated": false,
      "approved": false
    },
    "tasks": {
      "generated": false,
      "approved": false
    }
  },
  "ready_for_implementation": false
}
```

### 4. 创建包含项目上下文的模板文件

#### requirements.md（模板）

```markdown
# Requirements Document

## Overview

<!-- 项目概述将在 /spec-task:requirements 阶段生成 -->

## Project Description (User Input)

$ARGUMENTS

## Requirements

<!-- 详细的用户故事将在 /spec-task:requirements 阶段生成 -->
```

#### design.md（空模板）

```markdown
# Design Document

## Overview

<!-- 技术设计将在需求审批后生成 -->
```

#### tasks.md（空模板）

```markdown
# Implementation Plan

<!-- 实施任务将在设计审批后生成 -->
```

### 5. 更新 CLAUDE.md 引用

将新规范添加到活动规范列表中，包含生成的功能名称和简要描述。

## 初始化后的下一步

遵循规范驱动的开发工作流：

1. `/spec-task:requirements {feature-name}` - 生成需求
2. `/spec-task:design {feature-name}` - 生成设计（交互式审批）
3. `/spec-task:tasks {feature-name}` - 生成任务（交互式审批）

## 输出格式

初始化后，提供：

1. 生成的功能名称及其理由
2. 简要的项目摘要
3. 创建的文件路径
4. 下一条命令：`/spec-task:requirements {feature-name}`

---

## 工作流程图示

```
初始化 → 需求生成 → 设计生成 → 任务生成 → 实施准备就绪
         ↓           ↓          ↓
       [审批]      [审批]     [审批]
```

## 注意事项

- **唯一性检查**：确保功能名称在系统中是唯一的
- **模板结构**：所有模板文件都遵循标准化格式
- **审批流程**：每个阶段都需要明确的审批才能继续
- **元数据追踪**：`spec.json` 文件追踪整个生命周期的状态

---

## 规范生命周期

### 阶段 1：初始化（Initialization）

- 创建目录结构
- 生成模板文件
- 初始化元数据

### 阶段 2：需求定义（Requirements Definition）

- 分析项目描述
- 生成用户故事
- 定义验收标准

### 阶段 3：技术设计（Technical Design）

- 架构设计
- 技术栈选择
- 接口定义

### 阶段 4：任务分解（Task Breakdown）

- 实施计划
- 任务优先级
- 依赖关系

### 阶段 5：实施就绪（Ready for Implementation）

- 所有文档已审批
- 任务已分配
- 开发环境准备完成

---

## 命令示例

### 初始化新规范

```bash
/spec-task:init "创建一个用户管理系统，支持注册、登录和权限管理"
```

### 生成需求文档

```bash
/spec-task:requirements user-management
```

### 生成技术设计

```bash
/spec-task:design user-management
```

### 生成实施任务

```bash
/spec-task:tasks user-management
```

---

## 文件结构示例

```
.
└── specs/
    └── user-management/
        ├── requirements.md   # 需求文档
        ├── design.md        # 设计文档
        ├── tasks.md         # 任务计划
        └── spec.json        # 元数据和状态追踪
```

---

## 最佳实践

1. **清晰的功能命名**
   - 使用描述性名称
   - 避免使用特殊字符
   - 保持简洁明了

2. **渐进式审批**
   - 每个阶段完成后进行审批
   - 确保前置条件满足
   - 记录审批决策

3. **文档维护**
   - 保持文档同步更新
   - 记录变更历史
   - 维护版本控制

4. **团队协作**
   - 明确责任分工
   - 定期评审进度
   - 及时沟通问题

---

## 常见问题（FAQ）

### Q: 如何处理功能名称冲突？

A: 系统会自动检测冲突并添加数字后缀（如 feature-name-2）。

### Q: 可以修改已生成的文档吗？

A: 可以，但建议在相应的审批阶段之前完成修改。

### Q: 如何撤销初始化？

A: 可以手动删除 `.tasks/{feature-name}/` 目录。

### Q: 支持哪些语言？

A: 默认支持中文（Chinese），可以在 spec.json 中修改。
