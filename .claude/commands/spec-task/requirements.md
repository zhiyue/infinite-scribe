---
description: Generate comprehensive requirements for a specification
allowed-tools:
  Bash, Glob, Grep, LS, Read, Write, Edit, MultiEdit, Update, WebSearch,
  WebFetch
argument-hint: <feature-name>
---

# 需求生成

为功能生成系统需求：**$ARGUMENTS**

## 上下文验证

### 现有规范上下文

- 当前规范目录：!`ls -la .tasks/$ARGUMENTS/`
- **产品需求文档**：@.tasks/$ARGUMENTS/prd.md
- 当前需求：@.tasks/$ARGUMENTS/requirements.md
- 规范元数据：@.tasks/$ARGUMENTS/spec.json

## 任务：基于 PRD 生成系统需求

基于已批准的 PRD 用户故事，生成一组系统需求（使用 EARS 格式）。每个用户故事都应派生出相应的功能需求（FR）和非功能需求（NFR）。

**重要**：首先验证 PRD 已经生成并批准。如果 PRD 尚未生成，提示用户先运行
`/spec-task:prd {feature-name}`。

在这个阶段不要专注于代码探索。相反，专注于从 PRD 推导出可验证的系统需求。

### 需求生成指南

1. **基于 PRD 推导**：每个 Story 至少派生一个 FR，关键质量目标派生 NFR
2. **使用 EARS 格式**：所有验收标准必须使用正确的 EARS 语法
3. **建立追踪性**：明确标注每个 FR/NFR 源自哪个 Story ID
4. **定义可测阈值**：NFR 必须包含具体的度量指标和阈值
5. **保持工程视角**：从 PRD 的业务需求转换为可验证的技术需求

### 1. EARS 格式需求

**EARS（需求语法简易方法）** 是验收标准的强制格式：

**主要 EARS 模式：**

- WHEN [事件/条件] THEN [系统] SHALL [响应]
- IF [前置条件/状态] THEN [系统] SHALL [响应]
- WHILE [持续条件] THE [系统] SHALL [持续行为]
- WHERE [位置/上下文/触发器] THE [系统] SHALL [上下文行为]

**组合模式：**

- WHEN [事件] AND [附加条件] THEN [系统] SHALL [响应]
- IF [条件] AND [附加条件] THEN [系统] SHALL [响应]

### 2. 需求文档结构

根据 spec.json 中指定的语言生成 requirements.md（检查
`@.tasks/$ARGUMENTS/spec.json` 中的 "language" 字段）：

```markdown
# Requirements Document

## Introduction

[清晰的介绍，总结功能及其业务价值]

## Functional Requirements

### FR-001: [主要功能区域]

**源自 Story:** STORY-XXX

#### Acceptance Criteria

此部分应包含 EARS 需求

1. WHEN [事件] THEN [系统] SHALL [响应]
2. IF [前置条件] THEN [系统] SHALL [响应]
3. WHILE [持续条件] THE [系统] SHALL [持续行为]
4. WHERE [位置/上下文/触发器] THE [系统] SHALL [上下文行为]

### FR-002: [下一个主要功能区域]

**源自 Story:** STORY-XXX

1. WHEN [事件] THEN [系统] SHALL [响应]
2. WHEN [事件] AND [条件] THEN [系统] SHALL [响应]

### FR-003: [其他主要区域]

[为所有主要功能区域继续此模式]

## Non-Functional Requirements (NFR)

### NFR-001: 性能需求

**源自 Story:** STORY-XXX

- **延迟**: P95 < Xs
- **吞吐量**: >= X req/s
- **并发**: >= X 并发用户

### NFR-002: 可靠性需求

**源自 Story:** STORY-XXX

- **可用性**: >= X%
- **恢复时间**: < X 分钟

## Traceability Matrix

| Story ID  | Requirements    | Priority |
| --------- | --------------- | -------- |
| STORY-001 | FR-001, NFR-001 | P1       |
| STORY-002 | FR-002, FR-003  | P2       |
| STORY-003 | NFR-002         | P1       |

## ADR Candidates (Placeholder)

<!-- ADR 候选项将在下一步通过 /spec-task:adr-draft 命令生成 -->
<!-- 识别的架构决策点将在此处列出，并创建对应的 ADR 草稿文件 -->
```

### 3. 更新元数据

更新 spec.json：

```json
{
  "phase": "requirements-generated",
  "approvals": {
    "requirements": {
      "generated": true,
      "approved": false
    }
  }
}
```

### 4. 仅生成文档

仅生成需求文档内容。不要在实际文档文件中包含任何审查或批准说明。

---

## 下一阶段：交互式审批

生成 requirements.md 后，审查需求并选择：

**如果需求看起来不错：**

1. 运行 `/spec-task:adr-draft $ARGUMENTS` 生成 ADR 草稿
2. 运行 `/spec-task:adr-review $ARGUMENTS` 评审并决策 ADR
3. 所有关键 ADR 接受后，运行 `/spec-task:design-hld $ARGUMENTS -y`
   继续到高层设计阶段

**如果需求需要修改：** 请求更改，然后在修改后重新运行此命令

`-y` 标志自动批准需求并直接生成设计，在保持审查强制执行的同时简化工作流程。

## 执行说明

1. **检查 spec.json 中的语言** - 使用元数据中指定的语言
2. **生成初始需求** - 基于功能想法，不先进行连续提问
3. **应用 EARS 格式** - 对所有验收标准使用正确的 EARS 语法模式
4. **专注核心功能** - 从基本功能和用户工作流开始
5. **清晰的结构** - 将相关功能分组为逻辑需求区域
6. **使需求可测试** - 每个验收标准都应该是可验证的
7. **更新跟踪元数据** - 完成后更新

生成的需求应为设计阶段提供坚实的基础，重点关注功能想法中的核心功能。

---

## EARS 格式详解

### 基本模式

#### 1. WHEN 模式（事件触发）

```
WHEN [用户点击登录按钮]
THEN [系统] SHALL [验证用户凭证]
```

用于：响应特定事件或用户操作

#### 2. IF 模式（条件判断）

```
IF [用户未登录]
THEN [系统] SHALL [重定向到登录页面]
```

用于：基于系统状态的条件行为

#### 3. WHILE 模式（持续状态）

```
WHILE [用户会话活跃]
THE [系统] SHALL [每5分钟刷新认证令牌]
```

用于：在特定条件期间的持续行为

#### 4. WHERE 模式（上下文相关）

```
WHERE [用户在移动设备上]
THE [系统] SHALL [显示响应式界面]
```

用于：基于环境或上下文的行为

### 复合模式

#### 5. 多条件组合

```
WHEN [用户提交表单] AND [所有字段有效]
THEN [系统] SHALL [保存数据并显示成功消息]
```

#### 6. 嵌套条件

```
IF [用户是管理员] AND [在工作时间]
THEN [系统] SHALL [允许访问管理面板]
```

---

## 需求质量检查清单

### ✅ 完整性

- [ ] 涵盖所有核心用户场景
- [ ] 包含正常和异常路径
- [ ] 定义边界条件

### ✅ 清晰度

- [ ] 使用明确的语言
- [ ] 避免歧义
- [ ] 术语定义一致

### ✅ 可测试性

- [ ] 每个需求都可验证
- [ ] 有明确的通过/失败标准
- [ ] 可量化的指标

### ✅ 一致性

- [ ] 需求之间无冲突
- [ ] 遵循统一的格式
- [ ] 与系统约束一致

### ✅ 可追踪性

- [ ] 需求有唯一标识
- [ ] 可映射到用户故事
- [ ] 支持变更跟踪

---

## 常见需求模式示例

### 用户认证

```markdown
### Requirement: 用户登录

**User Story:** As a 用户, I want 安全登录, so that 我可以访问个人数据

#### Acceptance Criteria

1. WHEN 用户输入有效凭证 THEN 系统 SHALL 创建会话并重定向到仪表板
2. WHEN 用户输入无效凭证 THEN 系统 SHALL 显示错误消息
3. IF 用户连续3次登录失败 THEN 系统 SHALL 锁定账户15分钟
4. WHILE 用户会话活跃 THE 系统 SHALL 保持认证状态
```

### 数据验证

```markdown
### Requirement: 表单验证

**User Story:** As a 用户, I want 实时表单验证, so that 我可以立即纠正错误

#### Acceptance Criteria

1. WHEN 用户离开必填字段为空 THEN 系统 SHALL 显示字段级错误
2. WHILE 用户输入 THE 系统 SHALL 提供实时格式反馈
3. IF 所有字段有效 THEN 系统 SHALL 启用提交按钮
```

### 性能需求

```markdown
### Requirement: 响应时间

**User Story:** As a 用户, I want 快速页面加载, so that 我有流畅的体验

#### Acceptance Criteria

1. WHERE 用户在4G网络 THE 系统 SHALL 在2秒内加载页面
2. WHEN 服务器负载正常 THEN API响应 SHALL 在500毫秒内返回
3. WHILE 处理大数据集 THE 系统 SHALL 显示进度指示器
```

---

## 工作流程集成

```mermaid
graph LR
    A[初始化规范] --> B[生成需求]
    B --> C{需求审查}
    C -->|批准| D[生成设计]
    C -->|修改| B
    D --> E{设计审查}
    E -->|批准| F[生成任务]
    E -->|修改| D
    F --> G[实施准备]
```

---

## 最佳实践

### 1. 迭代优化

- 从核心功能开始
- 逐步添加细节
- 频繁获取反馈

### 2. 用户参与

- 让利益相关者参与审查
- 使用他们的语言
- 验证业务价值

### 3. 技术可行性

- 考虑技术约束
- 与架构保持一致
- 评估实施复杂度

### 4. 维护性

- 保持需求模块化
- 支持独立更新
- 记录依赖关系

---

## 故障排除

### 问题：需求过于技术化

**解决方案**：使用业务语言，专注于"什么"而不是"如何"

### 问题：需求不明确

**解决方案**：添加具体示例和边界条件

### 问题：需求冲突

**解决方案**：创建优先级矩阵，与利益相关者澄清

### 问题：需求范围蔓延

**解决方案**：定义MVP，将额外功能标记为未来阶段
