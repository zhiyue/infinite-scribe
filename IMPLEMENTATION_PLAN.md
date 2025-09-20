---

# Event Handlers Refactoring Plan

## Goal

重构
`apps/backend/src/agents/orchestrator/event_handlers.py`，解决设计模式问题、硬编码问题和可读性问题。

## Current Problems Analysis

### 1. 设计模式问题

- **违反单一职责原则**: `CapabilityEventHandlers` 处理多种不同类型的事件
- **违反开闭原则**: 添加新事件类型需要修改现有代码
- **缺乏策略模式**: 使用硬编码条件语句处理不同事件

### 2. 硬编码问题

- 质量阈值: `7.5`
- 最大尝试次数: `3`
- 事件类型字符串: `"Character.Design.Generated"`, `"Theme.Generated"`
- 事件动作字符串: `"Character.Proposed"`, `"Theme.Proposed"`
- 任务前缀: `"Character.Design.Generation"`, `"Outliner.Theme.Generation"`

### 3. 代码重复问题

- 重复的字典构建代码 (domain_event, task_completion)
- 相似的条件判断逻辑
- 重复的 EventAction 创建代码

### 4. 可读性问题

- 方法过长 (60-70 行)
- 深层嵌套的条件语句
- 参数过多 (7-8 个参数)

## Refactoring Strategy

### 采用的设计模式

1. **命令模式 (Command Pattern)**
   - 为每种事件类型创建独立的命令处理器
   - 封装事件处理逻辑，便于扩展和测试
   - 符合单一职责原则

2. **建造者模式 (Builder Pattern)**
   - `EventActionBuilder` 统一构建复杂的 `EventAction` 对象
   - 消除重复的字典构建代码
   - 提供流畅的 API

3. **工厂模式 (Factory Pattern)**
   - `EventCommandFactory` 根据事件类型选择合适的命令处理器
   - 符合开闭原则，便于添加新事件类型

4. **配置驱动 (Configuration Driven)**
   - `EventHandlerConfig` 统一管理所有硬编码常量
   - 单一来源原则 (Single Source of Truth)

### 重构后的架构

```
EventHandlerConfig          # 配置类 - 管理所有常量
│
├── EventActionBuilder     # 建造者 - 构建 EventAction
│
├── EventCommand           # 命令接口
│   ├── GenerationCompletedCommand
│   ├── QualityReviewCommand
│   └── ConsistencyCheckCommand
│
├── EventCommandFactory    # 工厂 - 选择命令处理器
│
└── CapabilityEventHandlers # 重构后的主处理器
```

## Event Handler Refactoring Stages

### Stage R1: 基础设施搭建

**Goal**: 创建配置类和建造者模式基础设施
**Success Criteria**:
- [x] `EventHandlerConfig` 配置类创建完成，集成 Settings 系统
- [x] `EventActionBuilder` 建造者类创建完成
- [x] 所有硬编码常量移到配置类
**Tests**: 配置类和建造者类的单元测试
**Status**: Complete

### Stage R2: 命令模式实现

**Goal**: 实现命令模式的事件处理器
**Success Criteria**:
- [x] `EventCommand` 抽象基类定义
- [x] `GenerationCompletedCommand` 实现 (70 行，使用配置和建造者)
- [x] `QualityReviewCommand` 实现 (60 行，消除硬编码)
- [x] `ConsistencyCheckCommand` 实现 (35 行，简洁实现)
**Tests**: 每个命令类的单元测试，验证事件处理逻辑正确性
**Status**: Complete

### Stage R3: 工厂模式实现

**Goal**: 实现工厂模式选择命令处理器
**Success Criteria**:
- [x] `EventCommandFactory` 工厂类实现
- [x] 支持根据事件类型自动选择命令
- [x] 工厂类支持扩展新命令类型
- [x] 提供统一的 `handle_event` 接口
**Tests**: 工厂类选择逻辑测试，未知事件类型处理测试
**Status**: Complete

### Stage R4: 主处理器重构

**Goal**: 重构主事件处理器使用新架构
**Success Criteria**:
- [x] 重构 `CapabilityEventHandlers` 使用命令模式
- [x] 消除原有的长方法和重复代码 (从 60-70 行减少到 20 行)
- [x] 保持向后兼容的 API (静态方法保留，新增实例方法)
**Tests**: 集成测试验证重构前后行为一致
**Status**: Complete

### Stage R5: 测试和验证

**Goal**: 验证重构正确性和兼容性
**Success Criteria**:
- [x] 核心功能测试通过 (orchestrator agent 测试全部通过)
- [ ] 兼容性测试修复 (capability event processor 测试需要适配)
- [x] 代码重复显著减少
- [x] 硬编码问题完全解决
**Tests**: 完整的测试套件验证
**Status**: In Progress (核心功能完成，兼容性修复待处理)

## Implementation Notes

### 复用现有类型系统

- 使用 `types.py` 中已定义的 `MessageType`, `EventActionType`
- 使用 `mapping.py` 中的 `normalize_task_type()` 函数
- 不重复定义已有的类型和常量

### 保持向后兼容

- 保持现有 API 签名不变
- 确保重构后行为与原有逻辑一致
- 逐步迁移，支持平滑过渡
