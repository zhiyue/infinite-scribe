# 命令与事件设计文档索引

基于 `events.md` 文档的事件命名契约，创世阶段的命令和事件数据结构设计分为以下模块：

## 📋 文档目录

### 核心设计文档
- **[命令类型定义](command-types.md)** - 统一的命令类型命名约定和枚举定义
- **[事件类型定义](event-types.md)** - 领域事件类型命名约定和映射关系
- **[数据库表结构](database-schemas.md)** - Command_Box、Domain_Events、Event_Outbox 表设计

### 实现细节文档
- **[数据示例](data-examples.md)** - 完整的创世阶段数据流示例
- **[序列化实现](serialization-implementation.md)** - Python 枚举和序列化器实现
- **[一致性保证](consistency-guidelines.md)** - 命名一致性和数据流保证原则

## 🎯 快速导航

### 按业务阶段查找
- **Stage 0 (创意种子)**: 查看 [data-examples.md](data-examples.md#初始灵感阶段)
- **Stage 1 (立意主题)**: 查看 [data-examples.md](data-examples.md#立意主题阶段)
- **通用命令事件**: 查看 [command-types.md](command-types.md#通用命令) 和 [event-types.md](event-types.md#通用事件)

### 按技术层面查找
- **表结构设计**: [database-schemas.md](database-schemas.md)
- **代码实现**: [serialization-implementation.md](serialization-implementation.md)
- **数据格式**: [data-examples.md](data-examples.md)

### 按问题域查找
- **命名规范**: [command-types.md](command-types.md#命名格式) 和 [event-types.md](event-types.md#命名格式)
- **映射关系**: [event-types.md](event-types.md#命令到事件映射)
- **数据一致性**: [consistency-guidelines.md](consistency-guidelines.md)

## 🔗 相关文档

- **[events.md](events.md)** - 事件设计详细实现（上游设计文档）
- **[data-models.md](data-models.md)** - 完整数据模型设计
- **[eventbridge.md](eventbridge.md)** - 事件桥接架构

## 📝 使用说明

1. **新增命令/事件类型**：先更新 [command-types.md](command-types.md) 或 [event-types.md](event-types.md)，然后更新 [serialization-implementation.md](serialization-implementation.md) 中的枚举
2. **修改表结构**：在 [database-schemas.md](database-schemas.md) 中修改，并更新相关的数据示例
3. **添加新的数据示例**：在 [data-examples.md](data-examples.md) 中按阶段组织
4. **一致性检查**：参考 [consistency-guidelines.md](consistency-guidelines.md) 确保符合设计原则

## 📅 文档维护

- **维护频率**: 每次命令/事件类型变更时更新
- **负责人**: 后端开发团队
- **审核**: 架构师审核一致性