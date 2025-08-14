# Kafka → SSE 事件映射文档

## 概述

本文档定义了 Kafka 事件到 SSE（Server-Sent Events）事件的映射规则，确保前后端对事件格式和语义的理解一致。

## 事件命名规范

### SSE 事件命名约定
- 格式：`domain.action-past`
- 域名使用小写
- 动作使用过去时
- 使用连字符分隔多个单词
- 示例：`task.progress-updated`, `novel.status-changed`

### 事件作用域（scope）
- `user` - 仅推送给特定用户的事件
- `session` - 推送给特定会话的事件
- `novel` - 推送给订阅特定小说的用户
- `global` - 系统级广播事件

## 映射规则表

| Kafka Event Type | SSE Event | 作用域 | 过滤条件 | 数据转换规则 |
|-----------------|-----------|--------|---------|-------------|
| NovelCreatedEvent | novel.created | user | user_id | 保留：{id, title, theme, status, created_at}<br>移除：内部字段 |
| NovelStatusChangedEvent | novel.status-changed | novel | novel_id | {novel_id, old_status, new_status, changed_at} |
| ChapterDraftCreatedEvent | chapter.draft-created | novel | novel_id | {chapter_id, chapter_number, title, novel_id} |
| ChapterStatusChangedEvent | chapter.status-changed | novel | novel_id, chapter_id | {chapter_id, old_status, new_status} |
| ChapterVersionPublishedEvent | chapter.version-published | novel | novel_id | {chapter_id, version_number, word_count} |
| CharacterCreatedEvent | character.created | novel | novel_id | {character_id, name, role, novel_id} |
| CharacterUpdatedEvent | character.updated | novel | novel_id | {character_id, updated_fields, novel_id} |
| WorldviewEntryCreatedEvent | worldview.entry-created | novel | novel_id | {entry_id, entry_type, name, novel_id} |
| GenesisStepCompletedEvent | genesis.step-completed | session | session_id | {session_id, stage, iteration, is_confirmed} |
| GenesisSessionCompletedEvent | genesis.session-completed | user | user_id, session_id | {session_id, novel_id, final_settings} |
| WorkflowStartedEvent | workflow.started | novel | novel_id | {workflow_id, workflow_type, novel_id} |
| WorkflowStatusChangedEvent | workflow.status-changed | novel | novel_id | {workflow_id, old_status, new_status} |
| WorkflowCompletedEvent | workflow.completed | novel | novel_id | {workflow_id, status, duration, result_summary} |
| TaskCreatedEvent | task.created | user | user_id | {task_id, task_type, description} |
| TaskProgressUpdateEvent | task.progress-updated | user | task_id, user_id | {task_id, progress, message, estimated_remaining} |
| TaskStatusChangedEvent | task.status-changed | user | task_id, user_id | {task_id, old_status, new_status} |
| AgentActivityStartedEvent | agent.activity-started | novel | novel_id | {activity_id, agent_type, activity_type} |
| AgentActivityCompletedEvent | agent.activity-completed | novel | novel_id | {activity_id, status, duration} |
| SystemNotificationEvent | system.notification | global | - | {level, title, message, action_required} |
| SystemMaintenanceEvent | system.maintenance-scheduled | global | - | {start_time, end_time, affected_services} |

## 数据转换详细规则

### 1. 通用转换规则
- 移除所有内部 ID（除了必要的关联 ID）
- 移除敏感信息（如内部配置、密钥等）
- 时间戳统一转换为 ISO 8601 格式
- 大对象（如完整内容）替换为摘要或 URL

### 2. 权限过滤规则
```python
def check_event_permission(event: KafkaEvent, user_context: UserContext) -> bool:
    """检查用户是否有权限接收此事件"""
    if event.scope == "global":
        return True
    elif event.scope == "user":
        return event.user_id == user_context.user_id
    elif event.scope == "session":
        return event.session_id == user_context.session_id
    elif event.scope == "novel":
        return user_context.has_access_to_novel(event.novel_id)
    return False
```

### 3. 数据精简示例
```python
# Kafka 事件（完整数据）
{
    "event_id": "550e8400-e29b-41d4-a716-446655440000",
    "event_type": "NovelCreatedEvent",
    "timestamp": "2025-01-04T10:30:00Z",
    "source_agent": "worldsmith",
    "novel_id": "123e4567-e89b-12d3-a456-426614174000",
    "novel_data": {
        "id": "123e4567-e89b-12d3-a456-426614174000",
        "title": "星际迷航",
        "theme": "科幻冒险",
        "writing_style": "硬科幻",
        "status": "GENESIS",
        "target_chapters": 30,
        "completed_chapters": 0,
        "created_by_agent_type": "worldsmith",
        "version": 1,
        "created_at": "2025-01-04T10:30:00Z",
        "updated_at": "2025-01-04T10:30:00Z"
    }
}

# SSE 事件（精简后）
{
    "event": "novel.created",
    "data": {
        "id": "123e4567-e89b-12d3-a456-426614174000",
        "title": "星际迷航",
        "theme": "科幻冒险",
        "status": "GENESIS",
        "created_at": "2025-01-04T10:30:00Z"
    },
    "id": "kafka:0:12345",
    "scope": "user"
}
```

## 错误事件

### SSE 错误事件格式
```typescript
interface SSEErrorEvent {
    level: "warning" | "error" | "critical";
    code: string;  // 错误码，如 "AUTH_EXPIRED", "RATE_LIMIT_EXCEEDED"
    message: string;  // 用户友好的错误信息
    correlation_id?: string;  // 关联的请求或任务 ID
    retry_after?: number;  // 建议重试时间（秒）
}
```

### 错误码定义
| 错误码 | 说明 | 处理建议 |
|-------|------|---------|
| AUTH_EXPIRED | 认证过期 | 客户端应重新认证 |
| RATE_LIMIT_EXCEEDED | 超过速率限制 | 等待 retry_after 秒后重试 |
| SUBSCRIPTION_INVALID | 订阅无效 | 检查订阅参数 |
| PERMISSION_DENIED | 权限不足 | 无法接收该事件 |
| SERVER_OVERLOAD | 服务器过载 | 降级到轮询模式 |

## 版本管理

### 事件版本控制
- 每个 SSE 事件包含 `version` 字段
- 当前版本：`1.0`
- 向后兼容原则：新增字段不影响旧版本客户端
- 重大变更需要新的事件类型

### 版本迁移策略
```javascript
// 客户端版本兼容处理
function handleSSEEvent(event) {
    const version = event.data._version || "1.0";
    
    switch(version) {
        case "1.0":
            return handleV1Event(event);
        case "2.0":
            return handleV2Event(event);
        default:
            console.warn(`Unknown event version: ${version}`);
            return handleV1Event(event); // 降级处理
    }
}
```

## 性能考虑

### 事件大小限制
- 单个 SSE 事件数据部分不超过 64KB
- 超大内容使用引用 + 按需加载
- 批量数据使用分页事件

### 事件频率控制
- 同类事件合并：进度更新最多 1 次/秒
- 使用事件优先级：高优先级事件优先发送
- 背压控制：队列满时丢弃低优先级事件

## 最佳实践

1. **事件设计原则**
   - 事件应该是自包含的，不依赖外部状态
   - 使用明确的事件类型，避免通用事件
   - 包含足够的上下文信息

2. **前端处理建议**
   - 使用 TypeScript 类型确保类型安全
   - 实现事件去重（基于 event id）
   - 处理乱序事件（基于 timestamp）

3. **监控和调试**
   - 记录所有事件的发送和接收
   - 监控事件延迟和丢失率
   - 提供事件追踪工具