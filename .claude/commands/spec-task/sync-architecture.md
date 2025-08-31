---
description: Update architecture documentation with approved ADR and HLD content
allowed-tools: Bash, Glob, Grep, LS, Read, Write, Edit, MultiEdit, Update, TodoWrite, Task
argument-hint: [--force] [--dry-run] [feature-name]
---

# 架构文档内容更新

将已批准的 ADR 和 HLD 设计内容更新到架构文档目录的对应文件中：**$ARGUMENTS**

## 参数解析

- **--force**: 可选，即使未完全批准也强制更新内容
- **--dry-run**: 可选，仅显示将要更新的内容而不实际执行
- **feature-name**: 可选，仅更新特定功能的相关内容

## 环境验证

### 源内容检查

- 任务目录：!`ls -la .tasks/ 2>/dev/null || echo "No .tasks directory found"`
- 活动任务：!`find .tasks -name "spec.json" 2>/dev/null | wc -l` 个任务
- HLD 文档：!`find .tasks -name "design*.md" 2>/dev/null | wc -l` 个设计文档

### 目标文档检查

- 架构文档目录：!`ls -la docs/architecture/ 2>/dev/null || echo "No architecture docs"`
- 现有架构文档：
  - @docs/architecture/high-level-architecture.md
  - @docs/architecture/data-models.md
  - @docs/architecture/components.md
  - @docs/architecture/database-schema.md
  - @docs/architecture/rest-api-spec.md
  - @docs/architecture/tech-stack.md

## 任务：更新架构文档内容

### 1. 扫描源设计文档

#### 1.1 查找 ADR 内容

扫描所有已批准的架构决策：
- 位置：`.tasks/*/adr/*.md`
- 查找状态为 `Accepted` 的 ADR
- 提取关键决策内容：
  - 技术选型决策
  - 架构模式选择
  - 集成方案决定
  - 数据模型设计

#### 1.2 查找 HLD 内容

扫描高层设计文档：
- 主要位置：`.tasks/*/design.md`
- 备选位置：`.tasks/*/design-hld.md`

提取设计内容：
- 系统架构图和组件设计
- 数据流和交互模式
- API 设计和接口定义
- 数据模型和关系
- 技术栈更新

### 2. 内容映射分析

#### 2.1 架构决策映射

将 ADR 内容映射到对应的架构文档：

| ADR 内容类型 | 目标文档 | 更新章节 |
|------------|---------|---------|
| 技术选型 | tech-stack.md | 相应技术栈章节 |
| 架构模式 | high-level-architecture.md | 架构原则/模式 |
| 数据存储决策 | database-schema.md | 存储策略章节 |
| API 设计决策 | rest-api-spec.md | API 设计原则 |
| 组件架构 | components.md | 组件设计章节 |

#### 2.2 HLD 内容映射

将 HLD 设计内容映射到架构文档：

| HLD 内容类型 | 目标文档 | 更新章节 |
|------------|---------|---------|
| 系统架构图 | high-level-architecture.md | 系统架构章节 |
| 组件设计 | components.md | 具体组件章节 |
| 数据模型 | data-models.md | 领域模型章节 |
| 数据库设计 | database-schema.md | 表结构章节 |
| API 设计 | rest-api-spec.md | 端点定义章节 |
| 集成方案 | external-apis.md | 集成章节 |

### 3. 内容更新策略

#### 3.1 增量更新模式

对于每个目标文档：

1. **识别更新点**：
   - 查找文档中的标记注释：`<!-- ADR-UPDATE -->` 或 `<!-- HLD-UPDATE -->`
   - 如果没有标记，分析文档结构找到合适的插入点

2. **内容合并**：
   - 保留现有内容的结构
   - 在适当章节添加新内容
   - 标记更新来源：`<!-- Updated from {feature}/ADR-{id} on {date} -->`

3. **冲突处理**：
   - 如果内容冲突，创建新章节：`### {功能名称} 架构更新`
   - 保留原有内容，新内容追加
   - 添加版本标记

#### 3.2 具体更新操作

##### 更新 high-level-architecture.md

```markdown
## 系统架构

[保留现有内容]

### {功能名称} 架构扩展
<!-- Updated from {feature}/design-hld.md on {date} -->

[插入 HLD 中的架构设计内容]

#### 架构决策依据
<!-- Updated from {feature}/adr/ADR-001.md on {date} -->

[插入相关 ADR 决策内容]
```

##### 更新 data-models.md

```markdown
## 领域模型

[保留现有内容]

### {功能名称} 数据模型
<!-- Updated from {feature}/design-hld.md on {date} -->

[插入数据模型设计]

#### 模型设计决策
<!-- Updated from {feature}/adr/ADR-002.md on {date} -->

[插入数据模型相关的 ADR 决策]
```

##### 更新 components.md

```markdown
## 系统组件

[保留现有内容]

### {功能名称} 组件
<!-- Updated from {feature}/design-hld.md on {date} -->

#### 组件职责
[插入组件设计内容]

#### 组件交互
[插入组件交互图和说明]

#### 设计决策
<!-- Updated from {feature}/adr/ADR-003.md on {date} -->
[插入相关架构决策]
```

### 4. 执行更新

#### 4.1 干运行模式 (--dry-run)

如果指定了 --dry-run：
1. 显示将要更新的文件列表
2. 展示每个文件的更新预览（diff 格式）
3. 统计将要添加/修改的行数
4. 不执行实际更新

#### 4.2 实际更新执行

1. **备份原文件**：
   ```bash
   cp docs/architecture/{file}.md docs/architecture/{file}.md.backup.{timestamp}
   ```

2. **执行内容更新**：
   - 读取目标文档
   - 识别插入点
   - 合并新内容
   - 保存更新后的文档

3. **更新索引**：
   - 更新 `docs/architecture/index.md`
   - 添加更新日志条目
   - 记录功能和更新内容的映射

### 5. 生成更新报告

```markdown
# 架构文档更新报告

生成时间：{timestamp}
更新模式：{mode}
功能范围：{feature-name 或 "所有功能"}

## 更新摘要

- 处理的 ADR：{count} 个
- 处理的 HLD：{count} 个
- 更新的文档：{count} 个
- 新增内容行数：{lines} 行

## 文档更新详情

### high-level-architecture.md
- 新增章节：{sections}
- 更新内容：{summary}
- 来源：{source-files}

### data-models.md
- 新增模型：{models}
- 更新内容：{summary}
- 来源：{source-files}

### components.md
- 新增组件：{components}
- 更新内容：{summary}
- 来源：{source-files}

## 跳过的内容

### 未批准的 ADR
- {adr-file}: 状态为 {status}

### 未批准的设计
- {feature}: 设计未完成或未批准

## 建议后续操作

1. 审查更新的内容确保一致性
2. 验证架构文档的完整性
3. 更新相关的实施文档
4. 提交变更到版本控制
```

### 6. 版本控制建议

生成 git 提交建议：
```bash
git add docs/architecture/*.md
git commit -m "docs: update architecture with approved designs

- Updated from {features} ADRs and HLDs
- Added {n} new architectural decisions
- Enhanced {files} documentation files
"
```

## 错误处理

### 常见问题处理

1. **目标文档不存在**：
   - 提示创建新文档
   - 提供文档模板

2. **内容冲突**：
   - 创建独立章节避免覆盖
   - 标记需要人工审查的部分

3. **格式不兼容**：
   - 转换 Mermaid 图表格式
   - 调整 Markdown 标题层级
   - 统一代码块语言标记

## 使用示例

```bash
# 更新所有批准的内容到架构文档
/spec-task:sync-architecture

# 预览将要更新的内容
/spec-task:sync-architecture --dry-run

# 强制更新包括未批准的内容
/spec-task:sync-architecture --force

# 仅更新特定功能的内容
/spec-task:sync-architecture implement-sse

# 组合使用
/spec-task:sync-architecture --dry-run --force user-management
```

## 重要说明

1. **内容审查**：更新前应确保源内容已经过适当审查
2. **增量更新**：本命令采用增量更新，不会删除现有内容
3. **标记追踪**：所有更新都会添加来源标记便于追踪
4. **备份策略**：自动备份确保可以回滚
5. **手动审查**：建议更新后进行人工审查确保文档连贯性

本命令确保架构文档与最新的设计决策保持同步，同时保护现有文档内容的完整性。