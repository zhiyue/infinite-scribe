---
description:
  Generate implementation plan with technical research and API documentation
allowed-tools:
  Bash, Glob, Grep, LS, Read, Write, Edit, MultiEdit, Update, WebSearch,
  WebFetch, TodoWrite, Task, Agent
argument-hint: <feature-name> [-y] [--refresh]
---

# 实施规划与技术预研

为功能生成技术实施规划和API参考文档：**$ARGUMENTS**

## 说明

此命令是**可选的预研工具**，通过 context7 工具在实施前进行集中的技术研究，获取准确的库文档和API接口，减少实施过程中的重复查询和技术阻塞。

## 参数解析

- **feature-name**: 功能名称
- **-y**: 可选，自动批准生成的规划
- **--refresh**: 可选，忽略已有缓存，重新抓取文档

## 先决条件验证

### 必需文件检查

功能名称：!`echo "$ARGUMENTS" | awk '{print $1}' | head -1`

- 任务文档：!`ls -la .tasks/$ARGUMENTS/tasks.md 2>/dev/null || echo "Tasks not found - run spec-task:tasks first"`
- 低层设计：!`ls -la .tasks/$ARGUMENTS/lld/ 2>/dev/null || echo "LLD directory not found"`
- 规范元数据：!`cat .tasks/$ARGUMENTS/spec.json 2>/dev/null | grep "tasks_approved" || echo "Tasks not approved"`

### 现有规划检查

- 检查是否已存在：@.tasks/$ARGUMENTS/impl-plan.md
- 如果存在且未使用 --refresh，提示选项：
  - **[o] 覆盖**：重新生成全新的规划
  - **[u] 更新**：基于现有内容更新
  - **[c] 取消**：保留现有规划

## 任务：生成技术实施规划

### 1. 技术栈分析

从设计文档中提取技术依赖：

#### 1.1 扫描技术组件

从 `.tasks/$ARGUMENTS/lld/` 目录中的设计文档识别：

- 编程语言和版本要求
- 框架和主要库（FastAPI、SQLAlchemy、React、Vue等）
- 数据库和存储系统（PostgreSQL、Redis、Neo4j等）
- 第三方服务和API（OpenAI、Claude、Stripe等）
- 开发工具和构建系统

#### 1.2 依赖关系映射

创建依赖矩阵：

- 直接依赖（项目直接使用）
- 传递依赖（库的依赖）
- 版本兼容性要求
- 已知的版本冲突

### 2. API 文档研究

#### 2.1 库文档收集

对每个识别的库执行深度研究：

**使用 context7 工具获取准确的库文档**：

- 通过 context7 查询库的最新接口和方法签名
- 获取官方文档中的使用示例和最佳实践
- 收集库的错误处理模式和异常类型
- 识别常见陷阱、限制和性能考虑
- 检查版本兼容性和破坏性变更历史

**补充使用 WebFetch 和 Task 代理**：

- 当 context7 未覆盖某些库时，使用 WebFetch 获取官方文档
- 对于复杂的研究任务，使用 Task 代理并行收集信息

#### 2.2 创建技术参考缓存

建立参考文档目录结构：

```
.tasks/{feature-name}/references/
├── libraries/
│   ├── {library-name}/
│   │   ├── api.md          # API 接口文档
│   │   ├── examples.md     # 代码示例
│   │   └── gotchas.md      # 注意事项
├── patterns/
│   └── {pattern-name}.md   # 设计模式示例
└── snippets/
    └── {functionality}.md   # 可重用代码片段
```

### 3. 实施计划生成

#### 3.1 技术可行性验证

验证每个任务的技术可行性：

- API 可用性确认
- 性能要求可达性
- 安全要求满足度
- 扩展性考虑

#### 3.2 生成 impl-plan.md

创建结构化的实施规划文档：

````markdown
# 实施规划与研究手册

生成时间：{timestamp} 功能名称：{feature-name} 状态：{approved/pending}

## 执行摘要

- 范围：{实施范围描述}
- 关键假设：{版本、环境、依赖假设}
- 主要风险：{技术风险摘要}

## 技术栈清单

### 核心依赖

| 库/框架 | 版本      | 用途      | 文档链接   | 稳定性      |
| ------- | --------- | --------- | ---------- | ----------- |
| {lib}   | {version} | {purpose} | {docs_url} | {stability} |

### API 兼容性矩阵

| 库组合          | 兼容性  | 注意事项 |
| --------------- | ------- | -------- |
| {lib1} + {lib2} | ✅ 兼容 | {notes}  |

## API 速查表

### {Library Name}

#### 核心模块

```{language}
// 导入方式
import { Module } from '{library}'
```
````

#### 关键接口

```{language}
// 方法签名
function methodName(param1: Type1, param2?: Type2): ReturnType
```

#### 典型用法

```{language}
// 初始化
const instance = new Module({
  option1: value1,
  option2: value2
})

// 常见操作
instance.method(args)
```

#### 错误处理

```{language}
try {
  // 操作
} catch (SpecificError) {
  // 处理特定错误
}
```

## 任务到技术映射

### 任务 {number}: {任务描述}

**关联库**：{libraries}

**Context7 查询结果**：

- 接口签名：{从context7获取的准确签名}
- 版本信息：{context7确认的稳定版本}
- 最佳实践：{context7推荐的使用模式}

**TDD 实施计划**：

1. **红灯阶段（测试先行）**：

   ```{language}
   // 测试：{test_description}
   test('{test_name}', () => {
     // 断言期望行为
   })
   ```

2. **绿灯阶段（最小实现）**：

   ```{language}
   // 最小代码使测试通过
   {minimal_implementation}
   ```

3. **重构阶段（优化）**：
   - 提取公共逻辑
   - 应用设计模式
   - 优化性能

**验收断言清单**：

- [ ] 正常路径：{description}
- [ ] 边界条件：{description}
- [ ] 错误处理：{description}
- [ ] 性能要求：{description}

**依赖前置**：

- 需要任务 {prerequisite_task} 完成的 {output}

[继续其他任务...]

## 技术风险与缓解

### 已识别风险

1. **{风险名称}**
   - 描述：{description}
   - 概率：{高/中/低}
   - 影响：{impact}
   - 缓解策略：{mitigation}
   - Spike建议：{spike_if_needed}

2. **版本兼容性风险**
   - 库版本锁定策略
   - 回退方案

## 实施顺序优化

基于技术依赖的建议顺序：

1. {task} - 原因：{无外部依赖，可独立完成}
2. {task} - 原因：{依赖task1的输出}
3. {task} - 原因：{需要task2的基础设施}

## 测试策略

### 单元测试

- 覆盖率目标：>80%
- 测试框架：{framework}
- Mock策略：{approach}

### 集成测试

- 关键路径：{paths}
- 测试环境：{environment}
- 数据准备：{approach}

## 参考文档索引

### 库文档缓存

- [{library}] API文档：`references/libraries/{library}/api.md`
- [{library}] 示例代码：`references/libraries/{library}/examples.md`
- [{library}] 常见问题：`references/libraries/{library}/gotchas.md`

### 设计模式

- [{pattern}]：`references/patterns/{pattern}.md`

### 代码片段

- [{functionality}]：`references/snippets/{functionality}.md`

## 版本锁定建议

### package.json (前端)

```json
{
  "dependencies": {
    "{package}": "{exact-version}"
  }
}
```

### pyproject.toml (后端)

```toml
[tool.poetry.dependencies]
{package} = "^{version}"
```

## 环境配置要求

### 环境变量

```bash
# 必需配置
{ENV_VAR}={description}

# 可选配置
{OPT_VAR}={default_value}
```

### 外部服务

- {service}: {endpoint_url}
- 认证方式：{auth_method}
- 速率限制：{rate_limit}

## 质量门控

实施前检查清单：

- [ ] 所有库版本已确定
- [ ] API文档已收集完整
- [ ] 测试策略已明确
- [ ] 风险已识别并有缓解方案
- [ ] 依赖顺序已优化

## 批准状态

- [ ] 技术栈已验证
- [ ] API文档已收集
- [ ] TDD计划已制定
- [ ] 风险已评估
- [ ] 准备进入实施

---

_此文档由 spec-task:impl-plan 生成，作为实施阶段的技术参考_

````

### 4. 更新元数据

#### 4.1 更新 spec.json

添加或更新实施规划状态：
```json
{
  "phase": "impl-plan-generated",
  "impl_plan": {
    "generated": true,
    "approved": false,  // 如果使用 -y 则设为 true
    "generated_at": "{timestamp}",
    "libraries": [{detected_libraries}],
    "dependencies_count": {count},
    "risks_identified": {count},
    "cached_references": {count}
  }
}
````

#### 4.2 生成执行摘要

输出简洁的状态报告：

```
✅ 实施规划已生成

📊 分析结果：
- 技术依赖：{n} 个库/框架
- Context7 查询：{c} 个库文档已获取
- API文档：{m} 个接口已研究
- 技术风险：{r} 个已识别
- 参考文档：{d} 个已缓存
- TDD计划：{t} 个任务已规划

📁 生成的文件：
- impl-plan.md：主规划文档
- references/：API参考缓存目录（含context7查询结果）

🎯 下一步：
1. 审查规划：查看 .tasks/{feature}/impl-plan.md
2. 批准规划：在spec.json中设置approved=true
3. 开始实施：/spec-task:impl {feature}

💡 提示：
- Context7 查询结果已缓存，减少实施阶段的重复查询
- 使用 --refresh 强制重新查询 context7 和更新缓存
- 规划已批准后，impl命令将自动使用缓存的参考文档
```

## 高级功能

### 1. 增量更新模式

如果规划已存在且选择更新：

- 保留已验证的API信息
- 仅更新变更的依赖
- 追加新识别的风险
- 保持已批准的部分

### 2. 智能缓存策略

优化API查询：

- 优先使用本地缓存的 context7 查询结果（除非使用--refresh）
- 批量向 context7 查询相关库的API
- 并行获取多个库文档（context7 + WebFetch 组合）
- 标记过期的缓存（超过30天）
- Context7 查询结果单独标记，便于追踪来源

### 3. 依赖版本检查

自动检查：

- 最新稳定版本
- 安全漏洞警告（通过CVE数据库）
- 废弃API警告
- 许可证兼容性

### 4. Spike建议生成

对高风险或不确定的技术点：

- 自动生成Spike任务建议
- 估算验证时间
- 提供验证方案

## 与impl命令的协作

生成的规划将被 `/spec-task:impl` 命令使用：

1. **当规划已批准**（impl_plan.approved=true）：
   - impl优先使用缓存的 context7 查询结果
   - 避免实施阶段重复调用 context7
   - 提供一致且准确的API接口参考
   - 加速TDD实施过程

2. **当规划未生成或未批准**：
   - impl仍可正常工作
   - 按需即时调用 context7 查询API文档
   - 提示建议先运行impl-plan以预缓存文档

## 错误处理

### 常见问题

1. **任务未批准**：

   ```
   ❌ 任务尚未批准
   请先运行：/spec-task:tasks {feature} -y
   ```

2. **API文档不可用**：

   ```
   ⚠️ 无法获取 {library} 文档
   - 已标记为待研究
   - 备选资源：{alternative_sources}
   ```

3. **版本冲突检测**：
   ```
   ⚠️ 版本冲突：{lib1} v{x} 与 {lib2} v{y} 不兼容
   建议：{resolution}
   ```

## 使用示例

```bash
# 生成新的实施规划（将通过 context7 查询库文档）
/spec-task:impl-plan user-auth

# 自动批准规划
/spec-task:impl-plan user-auth -y

# 强制刷新（重新查询 context7 获取最新API文档）
/spec-task:impl-plan user-auth --refresh

# 更新现有规划（保留context7缓存，仅更新变化部分）
/spec-task:impl-plan user-auth  # 选择 [u] 更新
```

## 最佳实践

1. **时机选择**：在tasks批准后、impl开始前运行
2. **团队协作**：生成的参考文档可在团队间共享
3. **版本控制**：将规划和references纳入git
4. **定期更新**：每2-4周运行--refresh更新缓存
5. **风险管理**：高风险项先做Spike验证

## 重要说明

1. **可选但推荐**：此命令不是必需的，但能显著提高实施效率
2. **Context7 优先**：始终优先使用 context7 获取准确的库文档
3. **缓存有效期**：API文档缓存30天后建议重新查询 context7 更新
4. **离线支持**：context7 查询结果缓存后可离线使用
5. **质量保证**：规划审批是可选的质量门控
6. **准确性保障**：context7 提供的接口签名和示例是实施的权威参考

此命令通过 context7 进行集中的技术研究和文档缓存，为高效的TDD实施提供坚实基础，确保使用正确的API接口，减少实施阶段的不确定性和返工。
