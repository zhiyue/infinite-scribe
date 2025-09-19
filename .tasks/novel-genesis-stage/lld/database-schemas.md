# 数据库表结构设计

## 表概览

创世阶段的命令和事件存储涉及三个核心表：

1. **command_box** - 命令存储和处理状态管理
2. **domain_events** - 领域事件持久化存储
3. **event_outbox** - 事件发布队列管理

## Command_Box 表

### 表结构

```sql
CREATE TABLE command_box (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    command_id UUID NOT NULL UNIQUE,               -- 命令唯一标识
    command_type VARCHAR(255) NOT NULL,            -- 点式命名：Command.Genesis.Session.Start
    aggregate_id UUID NOT NULL,                    -- session_id 或 novel_id
    aggregate_type VARCHAR(100) NOT NULL,          -- "GenesisSession"
    payload JSONB NOT NULL,                        -- 命令具体内容
    correlation_id UUID,                           -- 流程关联ID
    causation_id UUID,                             -- 触发此命令的事件ID
    user_id UUID NOT NULL,                         -- 用户ID
    status VARCHAR(50) NOT NULL DEFAULT 'PENDING', -- PENDING/PROCESSING/COMPLETED/FAILED
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    processed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,                            -- 错误信息
    retry_count INTEGER DEFAULT 0,                 -- 重试次数
    metadata JSONB DEFAULT '{}'::jsonb,            -- 扩展元数据

    -- 检查约束
    CONSTRAINT chk_command_status CHECK (status IN ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED')),
    CONSTRAINT chk_retry_count CHECK (retry_count >= 0)
);
```

### 索引优化

```sql
-- 状态查询索引（处理队列）
CREATE INDEX idx_command_box_status ON command_box (status);

-- 聚合查询索引（按会话查询命令）
CREATE INDEX idx_command_box_aggregate ON command_box (aggregate_id, aggregate_type);

-- 关联查询索引（事件链追踪）
CREATE INDEX idx_command_box_correlation ON command_box (correlation_id);

-- 时间排序索引（创建时间）
CREATE INDEX idx_command_box_created ON command_box (created_at);

-- 命令类型查询索引
CREATE INDEX idx_command_box_command_type ON command_box (command_type);

-- 用户查询索引
CREATE INDEX idx_command_box_user ON command_box (user_id);

-- 复合索引：状态+创建时间（处理队列优化）
CREATE INDEX idx_command_box_status_created ON command_box (status, created_at);
```

### 字段说明

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| command_id | UUID | 命令全局唯一标识 | `cmd-123` |
| command_type | VARCHAR(255) | 点式命名的命令类型 | `Command.Genesis.Session.Start` |
| aggregate_id | UUID | 聚合根ID（通常是session_id） | `session-456` |
| aggregate_type | VARCHAR(100) | 聚合根类型 | `GenesisSession` |
| payload | JSONB | 命令参数和数据 | `{"user_input": "..."}` |
| correlation_id | UUID | 流程跟踪ID | `flow-001` |
| causation_id | UUID | 触发该命令的事件ID | `event-123` |
| status | VARCHAR(50) | 处理状态 | `PENDING/PROCESSING/COMPLETED/FAILED` |

## Domain_Events 表

### 表结构

```sql
CREATE TABLE domain_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id UUID NOT NULL UNIQUE,                 -- 事件唯一标识
    event_type VARCHAR(255) NOT NULL,              -- 点式命名：Genesis.Session.Started
    aggregate_id UUID NOT NULL,                    -- session_id
    aggregate_type VARCHAR(100) NOT NULL,          -- "GenesisSession"
    aggregate_version INTEGER NOT NULL,            -- 聚合版本号
    payload JSONB NOT NULL,                        -- 事件具体内容
    correlation_id UUID,                           -- 流程关联ID
    causation_id UUID,                             -- 触发此事件的命令/事件ID
    user_id UUID,                                  -- 用户ID
    occurred_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb,            -- 扩展元数据

    -- 检查约束
    CONSTRAINT chk_aggregate_version CHECK (aggregate_version > 0)
);
```

### 索引优化

```sql
-- 聚合查询索引（事件溯源）
CREATE INDEX idx_domain_events_aggregate ON domain_events (aggregate_id, aggregate_type);

-- 事件类型查询索引
CREATE INDEX idx_domain_events_type ON domain_events (event_type);

-- 关联查询索引（事件链追踪）
CREATE INDEX idx_domain_events_correlation ON domain_events (correlation_id);

-- 时间排序索引
CREATE INDEX idx_domain_events_occurred ON domain_events (occurred_at);

-- 因果关系查询索引
CREATE INDEX idx_domain_events_causation ON domain_events (causation_id);

-- 用户查询索引
CREATE INDEX idx_domain_events_user ON domain_events (user_id);

-- 聚合版本唯一性约束
CREATE UNIQUE INDEX idx_domain_events_aggregate_version ON domain_events (aggregate_id, aggregate_version);

-- 复合索引：聚合+时间（事件历史查询）
CREATE INDEX idx_domain_events_aggregate_time ON domain_events (aggregate_id, occurred_at);
```

### 字段说明

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| event_id | UUID | 事件全局唯一标识 | `event-456` |
| event_type | VARCHAR(255) | 点式命名的事件类型 | `Genesis.Session.Started` |
| aggregate_id | UUID | 聚合根ID | `session-456` |
| aggregate_version | INTEGER | 聚合版本号（乐观锁） | `1, 2, 3...` |
| payload | JSONB | 事件数据内容 | `{"session_id": "...", "content": {...}}` |
| correlation_id | UUID | 流程跟踪ID | `flow-001` |
| causation_id | UUID | 触发该事件的命令/事件ID | `cmd-123` |
| occurred_at | TIMESTAMPTZ | 事件发生时间 | `2024-01-15T10:30:00Z` |

## Event_Outbox 表

### 表结构

```sql
CREATE TABLE event_outbox (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id UUID NOT NULL,                       -- 引用 domain_events.event_id
    topic VARCHAR(255) NOT NULL,                  -- Kafka topic: "genesis.session.events"
    partition_key VARCHAR(255),                   -- session_id 用于分区
    headers JSONB NOT NULL,                       -- 包含 event_type 等元数据
    payload JSONB NOT NULL,                       -- 完整事件数据
    status VARCHAR(50) NOT NULL DEFAULT 'PENDING', -- PENDING/PUBLISHED/FAILED
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    published_at TIMESTAMP WITH TIME ZONE,
    retry_count INTEGER DEFAULT 0,                -- 重试次数
    error_message TEXT,                           -- 错误信息

    -- 检查约束
    CONSTRAINT chk_outbox_status CHECK (status IN ('PENDING', 'PUBLISHED', 'FAILED')),
    CONSTRAINT chk_outbox_retry_count CHECK (retry_count >= 0)
);
```

### 索引优化

```sql
-- 状态查询索引（发布队列）
CREATE INDEX idx_event_outbox_status ON event_outbox (status);

-- Topic查询索引
CREATE INDEX idx_event_outbox_topic ON event_outbox (topic);

-- 时间排序索引
CREATE INDEX idx_event_outbox_created ON event_outbox (created_at);

-- 分区键索引（Kafka分区优化）
CREATE INDEX idx_event_outbox_partition ON event_outbox (partition_key);

-- 事件ID索引（关联查询）
CREATE INDEX idx_event_outbox_event_id ON event_outbox (event_id);

-- 复合索引：状态+创建时间（发布队列优化）
CREATE INDEX idx_event_outbox_status_created ON event_outbox (status, created_at);

-- 外键约束
ALTER TABLE event_outbox
ADD CONSTRAINT fk_event_outbox_event_id
FOREIGN KEY (event_id) REFERENCES domain_events(event_id);
```

### 字段说明

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| event_id | UUID | 关联的领域事件ID | `event-456` |
| topic | VARCHAR(255) | Kafka Topic名称 | `genesis.session.events` |
| partition_key | VARCHAR(255) | 分区键（保证顺序） | `session-456` |
| headers | JSONB | Kafka消息头（路由信息） | `{"event_type": "...", "correlation_id": "..."}` |
| payload | JSONB | 完整的事件数据 | `{完整的domain_events记录}` |
| status | VARCHAR(50) | 发布状态 | `PENDING/PUBLISHED/FAILED` |

## 数据清理策略

### 命令清理

```sql
-- 清理30天前的已完成命令
DELETE FROM command_box
WHERE status = 'COMPLETED'
  AND processed_at < NOW() - INTERVAL '30 days';

-- 清理90天前的失败命令（保留时间更长用于调试）
DELETE FROM command_box
WHERE status = 'FAILED'
  AND created_at < NOW() - INTERVAL '90 days';
```

### 事件清理

```sql
-- 事件存储期更长，用于审计和回放
-- 清理1年前的事件（根据业务需求调整）
DELETE FROM domain_events
WHERE occurred_at < NOW() - INTERVAL '1 year';
```

### Outbox清理

```sql
-- 清理7天前的已发布事件
DELETE FROM event_outbox
WHERE status = 'PUBLISHED'
  AND published_at < NOW() - INTERVAL '7 days';

-- 清理30天前的失败事件
DELETE FROM event_outbox
WHERE status = 'FAILED'
  AND created_at < NOW() - INTERVAL '30 days';
```

## 性能优化建议

### 分区策略

```sql
-- 按时间分区 domain_events 表（可选，大数据量时考虑）
CREATE TABLE domain_events_2024_01 PARTITION OF domain_events
FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');

-- 按状态分区 command_box 表（可选）
CREATE TABLE command_box_pending PARTITION OF command_box
FOR VALUES IN ('PENDING', 'PROCESSING');
```

### 监控查询

```sql
-- 监控待处理命令数量
SELECT status, COUNT(*)
FROM command_box
GROUP BY status;

-- 监控事件发布延迟
SELECT topic,
       AVG(EXTRACT(EPOCH FROM (published_at - created_at))) as avg_delay_seconds
FROM event_outbox
WHERE status = 'PUBLISHED'
  AND created_at > NOW() - INTERVAL '1 hour'
GROUP BY topic;

-- 监控重试情况
SELECT command_type,
       AVG(retry_count) as avg_retries,
       MAX(retry_count) as max_retries
FROM command_box
WHERE status = 'FAILED'
GROUP BY command_type;
```

## 备份与恢复

### 备份策略

```bash
# 完整备份（包含索引）
pg_dump -h localhost -U postgres -d infinite_scribe \
  -t command_box -t domain_events -t event_outbox \
  --create --clean --if-exists > genesis_events_backup.sql

# 仅数据备份
pg_dump -h localhost -U postgres -d infinite_scribe \
  -t command_box -t domain_events -t event_outbox \
  --data-only > genesis_events_data.sql
```

### 恢复策略

```bash
# 恢复表结构和数据
psql -h localhost -U postgres -d infinite_scribe < genesis_events_backup.sql

# 仅恢复数据
psql -h localhost -U postgres -d infinite_scribe < genesis_events_data.sql
```