# Story 2.2: 基于命令的创世API和事务性发件箱

## 概述

本Story实现了基于命令模式的API端点和事务性发件箱模式，确保命令处理、领域事件生成和Kafka事件发布的原子性。

## 架构设计

### 核心原则
- **高内聚低耦合**: 每个模块专注于单一职责
- **事务性保证**: 确保数据一致性
- **幂等性**: 防止重复命令处理
- **可靠事件发布**: 使用事务性发件箱模式

### 组件架构

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   API Gateway   │───▶│ Command Service │───▶│ Event Publisher │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Genesis Routes  │    │   Database      │    │  Event Outbox   │
└─────────────────┘    │  (PostgreSQL)   │    └─────────────────┘
                       └─────────────────┘             │
                                                       ▼
                                              ┌─────────────────┐
                                              │ Message Relay   │
                                              │    Service      │
                                              └─────────────────┘
                                                       │
                                                       ▼
                                              ┌─────────────────┐
                                              │     Kafka       │
                                              └─────────────────┘
```

## 文件结构

### 核心服务层 (High Cohesion)
```
src/
├── core/
│   ├── database.py           # 数据库连接管理 (80行)
│   └── messaging.py          # Kafka连接管理 (100行)
├── models/
│   └── api.py               # API请求/响应模型 (70行)
├── common/services/
│   ├── command_service.py    # 命令处理服务 (350行)
│   └── event_publisher.py    # 事件发布服务 (150行)
├── api/routes/v1/
│   └── genesis.py           # Genesis API路由 (200行)
└── agents/message_relay/
    └── main.py              # 消息中继服务 (300行)
```

### 测试层 (Comprehensive Coverage)
```
tests/
├── unit/                    # 单元测试 (85%+ 覆盖率)
│   ├── api/
│   │   └── test_genesis_commands.py         (400行)
│   ├── services/
│   │   ├── test_command_service.py          (200行)
│   │   ├── test_command_database_operations.py (350行)
│   │   └── test_event_publisher.py          (350行)
│   └── agents/
│       └── test_message_relay.py            (350行)
└── integration/             # 集成测试
    ├── test_command_to_event_flow.py        (400行)
    └── test_message_relay.py               (350行)
```

## TDD实现流程

### 1. 红灯阶段 (Test First)
- 编写失败的单元测试
- 验证测试确实失败
- 明确功能需求

### 2. 绿灯阶段 (Make It Work)
- 编写最小化实现
- 使测试通过
- 不过度设计

### 3. 重构阶段 (Make It Clean)
- 优化代码结构
- 消除重复
- 保持测试通过

## 关键实现特性

### 命令处理流程

1. **API层**: 接收命令请求，路由到相应处理器
2. **验证层**: JWT认证，命令类型验证
3. **服务层**: 事务性处理命令
4. **数据层**: 原子写入三张表

### 事务性保证

```sql
BEGIN TRANSACTION;
-- 1. 插入command_inbox (幂等性检查)
-- 2. 插入domain_events (事件溯源)
-- 3. 插入event_outbox (可靠发布)
COMMIT;
```

### 幂等性实现

- 使用`command_inbox`表的唯一约束
- 基于`(session_id, command_type)`的复合索引
- 返回409 Conflict状态码

### 重试机制

- 指数退避策略: 1s → 2s → 4s
- 最大重试次数: 3次
- 失败后标记为FAILED状态

## API规范

### 命令端点

```http
POST /api/v1/genesis/sessions/{session_id}/commands
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "command_type": "RequestConceptGeneration",
  "payload": {
    "theme_preferences": ["科幻", "悬疑"],
    "style_preferences": ["快节奏", "第一人称"]
  }
}
```

### 响应格式

**成功响应 (200/202):**
```json
{
  "command_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "COMPLETED",
  "message": "Command processed successfully"
}
```

**重复命令 (409):**
```json
{
  "error_code": "DUPLICATE_COMMAND",
  "message": "Command already processing",
  "duplicate_command_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

## 事件命名规范

遵循官方动词表，格式: `Genesis.Session.<ActionInPastTense>`

- `Genesis.Session.Requested` (RequestConceptGeneration)
- `Genesis.Session.Confirmed` (ConfirmStage)
- `Genesis.Session.Submitted` (SubmitFeedback)

## 测试策略

### 单元测试覆盖

- **命令处理**: 成功/失败/重复场景
- **事件发布**: 验证/序列化/错误处理
- **API路由**: 认证/路由/错误处理
- **消息中继**: 轮询/发布/重试逻辑

### 集成测试覆盖

- **端到端流程**: 命令→事件→Kafka
- **事务性验证**: 原子性保证
- **错误恢复**: 失败场景处理
- **真实环境**: TestContainers

### 测试命令

```bash
# 单元测试
pytest apps/backend/tests/unit/ -v --cov=apps/backend/src

# 集成测试
pytest apps/backend/tests/integration/ -v

# 完整测试套件
pytest apps/backend/tests/ --cov=apps/backend/src --cov-report=html
```

## 部署配置

### 环境变量

```bash
# 数据库
POSTGRES_HOST=192.168.2.201
POSTGRES_PORT=5432
POSTGRES_DB=infinite_scribe

# Kafka
KAFKA_HOST=localhost
KAFKA_PORT=9092

# Message Relay
SERVICE_TYPE=message-relay
RELAY_POLL_INTERVAL=5
RELAY_BATCH_SIZE=100
```

### 服务启动

```bash
# API Gateway
python -m src.api.main

# Message Relay Service
SERVICE_TYPE=message-relay python -m src.agents.message_relay.main
```

## 性能指标

- **吞吐量**: 支持每秒100+命令请求
- **延迟**: API响应 < 100ms
- **可靠性**: 99.9%事件投递成功率
- **一致性**: ACID事务保证

## 监控和告警

### 关键指标

- 命令处理成功率
- 事件发布延迟
- 重试队列长度
- 数据库连接池状态

### 日志级别

- INFO: 正常操作
- WARNING: 重试事件
- ERROR: 处理失败
- DEBUG: 详细跟踪

## 代码质量标准

- **文件大小**: ≤ 400行
- **测试覆盖率**: ≥ 85%
- **圈复杂度**: ≤ 10
- **函数长度**: ≤ 50行

## 故障处理

### 常见问题

1. **重复命令**: 检查幂等性键
2. **事件堆积**: 检查Message Relay状态
3. **数据库锁**: 监控事务时长
4. **Kafka连接**: 验证网络连通性

### 恢复策略

1. **重启服务**: 自动恢复机制
2. **手动重试**: 更新event_outbox状态
3. **数据修复**: 基于事件溯源重建

## 未来优化

- 分片策略优化
- 异步命令处理
- 事件版本管理
- 性能监控增强

---

**开发完成**: ✅ 所有验收标准已满足  
**测试覆盖**: ✅ 85%+ 单元测试覆盖率  
**集成测试**: ✅ TestContainers验证  
**代码规范**: ✅ 高内聚低耦合设计