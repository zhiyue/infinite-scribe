# 一致性保证与最佳实践

本文档定义了创世阶段命令和事件系统的一致性保证原则和最佳实践。

## 命名一致性原则

### 1. 统一前缀规范

```yaml
领域分离:
  - 命令前缀: "Command.Genesis.Session.*"
  - 事件前缀: "Genesis.Session.*"
  - 能力事件: "Outliner.*", "Worldbuilder.*", "Character.*" 等

示例:
  ✅ 正确: "Command.Genesis.Session.Start" → "Genesis.Session.Started"
  ❌ 错误: "StartGenesisSession" → "GenesisSessionStarted"
```

### 2. 语态区分规范

```yaml
命令语态:
  - 使用祈使语态: Request, Confirm, Update, Create, Start, Finish
  - 表示意图和指令: "请求做某事", "确认某事"

事件语态:
  - 使用过去式: Requested, Confirmed, Updated, Created, Started, Finished
  - 表示已发生的事实: "某事已发生"

映射示例:
  Request → Requested
  Confirm → Confirmed
  Update → Updated
  Create → Created
```

### 3. 分层命名规范

```yaml
三层结构:
  Domain.AggregateRoot.Entity.Action

具体应用:
  - 一级域: Genesis (创世域)
  - 二级聚合: Session (会话聚合根)
  - 三级实体: Theme, World, Character, Plot (可选)
  - 四级动作: Requested, Proposed, Confirmed

示例:
  Genesis.Session.Theme.Requested     # 主题层级
  Genesis.Session.Character.Proposed  # 角色层级
  Genesis.Session.Started             # 会话层级
```

## 数据流一致性保证

### 1. 原子性保证

```python
# 命令处理的原子性
async def handle_command(command: DomainCommand) -> List[DomainEvent]:
    """命令处理必须在同一事务中完成"""
    async with database.transaction():
        try:
            # 1. 验证命令
            validate_command(command)

            # 2. 处理业务逻辑
            events = process_business_logic(command)

            # 3. 保存事件到domain_events表
            for event in events:
                await save_domain_event(event)

            # 4. 更新command_box状态
            await update_command_status(command.command_id, "COMPLETED")

            # 5. 添加到event_outbox
            for event in events:
                await add_to_outbox(event)

            return events

        except Exception as e:
            # 事务回滚，确保数据一致性
            await update_command_status(command.command_id, "FAILED", str(e))
            raise
```

### 2. 顺序性保证

```python
# 使用聚合版本号确保事件顺序
class AggregateVersionManager:
    async def get_next_version(self, aggregate_id: str) -> int:
        """获取下一个聚合版本号"""
        current_version = await self.get_current_version(aggregate_id)
        return current_version + 1

    async def save_event_with_version(self, event: DomainEvent) -> bool:
        """保存事件并检查版本冲突"""
        try:
            # 使用数据库唯一约束确保版本唯一性
            await self.db.execute(
                "INSERT INTO domain_events (aggregate_id, aggregate_version, ...) VALUES (%s, %s, ...)",
                (event.aggregate_id, event.aggregate_version, ...)
            )
            return True
        except UniqueViolationError:
            # 版本冲突，需要重试
            raise VersionConflictError(f"Version conflict for aggregate {event.aggregate_id}")
```

### 3. 幂等性保证

```python
# 命令幂等性处理
class CommandIdempotencyManager:
    async def is_command_already_processed(self, command_id: str) -> bool:
        """检查命令是否已被处理"""
        result = await self.db.fetch_one(
            "SELECT status FROM command_box WHERE command_id = %s",
            (command_id,)
        )
        return result and result["status"] in ["COMPLETED", "PROCESSING"]

    async def handle_duplicate_command(self, command: DomainCommand):
        """处理重复命令"""
        existing_status = await self.get_command_status(command.command_id)

        if existing_status == "COMPLETED":
            # 返回已有的事件结果
            return await self.get_events_by_causation_id(command.command_id)
        elif existing_status == "PROCESSING":
            # 等待处理完成
            raise CommandStillProcessingError("Command is still being processed")
        elif existing_status == "FAILED":
            # 允许重试失败的命令
            return await self.retry_failed_command(command)
```

## 链路追踪保证

### 1. Correlation ID 管理

```python
class CorrelationManager:
    """关联ID管理器"""

    def generate_correlation_id(self) -> str:
        """生成新的关联ID"""
        return f"flow-{uuid.uuid4()}"

    def propagate_correlation_id(self, source_event: DomainEvent, target_command: DomainCommand):
        """传播关联ID"""
        target_command.correlation_id = source_event.correlation_id
        target_command.causation_id = source_event.event_id

    async def trace_event_chain(self, correlation_id: str) -> List[Dict]:
        """追踪完整的事件链"""
        query = """
        SELECT 'COMMAND' as type, command_id as id, command_type as event_type,
               status, created_at, causation_id
        FROM command_box WHERE correlation_id = %s
        UNION ALL
        SELECT 'EVENT' as type, event_id as id, event_type,
               'COMPLETED' as status, occurred_at, causation_id
        FROM domain_events WHERE correlation_id = %s
        ORDER BY created_at
        """
        return await self.db.fetch_all(query, (correlation_id, correlation_id))
```

### 2. Causation Chain 验证

```python
class CausationValidator:
    """因果关系验证器"""

    async def validate_causation_chain(self, correlation_id: str) -> bool:
        """验证因果链的完整性"""
        events = await self.get_events_by_correlation(correlation_id)
        commands = await self.get_commands_by_correlation(correlation_id)

        # 检查每个事件的causation_id是否指向有效的命令
        for event in events:
            if event.causation_id:
                causation_found = any(
                    cmd.command_id == event.causation_id for cmd in commands
                ) or any(
                    evt.event_id == event.causation_id for evt in events
                )
                if not causation_found:
                    return False

        return True

    def find_orphaned_events(self, events: List[DomainEvent]) -> List[DomainEvent]:
        """查找孤立事件（无因果关系）"""
        return [evt for evt in events if not evt.causation_id and evt.event_type != GenesisEventType.SESSION_STARTED]
```

## 错误处理与恢复

### 1. 命令重试机制

```python
class CommandRetryManager:
    """命令重试管理器"""

    MAX_RETRIES = 3
    RETRY_DELAYS = [1, 5, 15]  # 指数退避 (秒)

    async def should_retry_command(self, command_id: str) -> bool:
        """判断命令是否应该重试"""
        command_record = await self.get_command_record(command_id)

        return (
            command_record["status"] == "FAILED" and
            command_record["retry_count"] < self.MAX_RETRIES and
            self.is_retryable_error(command_record["error_message"])
        )

    def is_retryable_error(self, error_message: str) -> bool:
        """判断错误是否可重试"""
        non_retryable_patterns = [
            "Invalid payload",
            "Command validation failed",
            "Aggregate not found",
            "Permission denied"
        ]
        return not any(pattern in error_message for pattern in non_retryable_patterns)

    async def schedule_retry(self, command_id: str):
        """安排命令重试"""
        command_record = await self.get_command_record(command_id)
        retry_count = command_record["retry_count"]

        if retry_count < self.MAX_RETRIES:
            delay = self.RETRY_DELAYS[min(retry_count, len(self.RETRY_DELAYS) - 1)]
            next_retry_at = datetime.utcnow() + timedelta(seconds=delay)

            await self.update_command_retry_info(command_id, retry_count + 1, next_retry_at)
```

### 2. 事件发布重试

```python
class EventOutboxManager:
    """事件发件箱管理器"""

    async def process_pending_events(self):
        """处理待发布事件"""
        pending_events = await self.get_pending_outbox_events()

        for outbox_record in pending_events:
            try:
                await self.publish_to_kafka(outbox_record)
                await self.mark_as_published(outbox_record["id"])
            except Exception as e:
                await self.handle_publish_failure(outbox_record["id"], str(e))

    async def handle_publish_failure(self, outbox_id: str, error_message: str):
        """处理发布失败"""
        outbox_record = await self.get_outbox_record(outbox_id)
        retry_count = outbox_record["retry_count"]

        if retry_count < 5:  # 最多重试5次
            await self.update_outbox_status(outbox_id, "PENDING", retry_count + 1)
        else:
            await self.update_outbox_status(outbox_id, "FAILED", retry_count, error_message)
            await self.alert_dead_letter_event(outbox_id)
```

## 数据一致性检查

### 1. 完整性检查

```python
class ConsistencyChecker:
    """一致性检查器"""

    async def check_command_event_consistency(self, time_window_hours: int = 24) -> Dict[str, Any]:
        """检查命令事件一致性"""
        since = datetime.utcnow() - timedelta(hours=time_window_hours)

        # 1. 检查已完成命令是否都有对应事件
        completed_commands = await self.get_completed_commands_since(since)
        orphaned_commands = []

        for cmd in completed_commands:
            expected_event_type = get_result_event_type(cmd["command_type"])
            if expected_event_type:
                event_exists = await self.event_exists(cmd["command_id"], expected_event_type)
                if not event_exists:
                    orphaned_commands.append(cmd)

        # 2. 检查事件是否都在outbox中
        events = await self.get_events_since(since)
        missing_outbox = []

        for event in events:
            outbox_exists = await self.outbox_exists(event["event_id"])
            if not outbox_exists:
                missing_outbox.append(event)

        return {
            "orphaned_commands": orphaned_commands,
            "missing_outbox_events": missing_outbox,
            "total_commands": len(completed_commands),
            "total_events": len(events)
        }

    async def check_aggregate_version_gaps(self) -> List[Dict]:
        """检查聚合版本号是否有间隙"""
        query = """
        WITH version_gaps AS (
            SELECT aggregate_id,
                   aggregate_version,
                   LAG(aggregate_version) OVER (PARTITION BY aggregate_id ORDER BY aggregate_version) as prev_version
            FROM domain_events
        )
        SELECT aggregate_id, aggregate_version, prev_version
        FROM version_gaps
        WHERE aggregate_version != prev_version + 1 AND prev_version IS NOT NULL
        """
        return await self.db.fetch_all(query)
```

### 2. 自动修复机制

```python
class AutoRepairManager:
    """自动修复管理器"""

    async def repair_missing_outbox_events(self):
        """修复缺失的outbox事件"""
        events_without_outbox = await self.find_events_without_outbox()

        for event in events_without_outbox:
            try:
                # 重新添加到outbox
                await self.add_event_to_outbox(event)
                logger.info(f"Repaired missing outbox for event {event['event_id']}")
            except Exception as e:
                logger.error(f"Failed to repair outbox for event {event['event_id']}: {e}")

    async def repair_orphaned_commands(self):
        """修复孤立命令（有命令但无对应事件）"""
        orphaned = await self.find_orphaned_commands()

        for command in orphaned:
            if command["status"] == "COMPLETED" and not await self.has_corresponding_event(command):
                # 标记为需要重新处理
                await self.update_command_status(command["command_id"], "PENDING")
                logger.info(f"Marked orphaned command {command['command_id']} for reprocessing")
```

## 监控与告警

### 1. 关键指标监控

```python
class MetricsCollector:
    """指标收集器"""

    async def collect_command_metrics(self) -> Dict[str, Any]:
        """收集命令相关指标"""
        return {
            "pending_commands": await self.count_commands_by_status("PENDING"),
            "processing_commands": await self.count_commands_by_status("PROCESSING"),
            "failed_commands": await self.count_commands_by_status("FAILED"),
            "avg_processing_time": await self.get_avg_processing_time(),
            "retry_rate": await self.get_retry_rate(),
            "commands_by_type": await self.get_commands_by_type_stats()
        }

    async def collect_event_metrics(self) -> Dict[str, Any]:
        """收集事件相关指标"""
        return {
            "events_per_hour": await self.get_events_per_hour(),
            "pending_outbox": await self.count_outbox_by_status("PENDING"),
            "failed_outbox": await self.count_outbox_by_status("FAILED"),
            "avg_publish_delay": await self.get_avg_publish_delay(),
            "events_by_type": await self.get_events_by_type_stats()
        }
```

### 2. 告警规则

```yaml
# 告警配置示例
alerts:
  high_pending_commands:
    condition: "pending_commands > 100"
    severity: "warning"
    message: "待处理命令数量过多"

  command_processing_timeout:
    condition: "avg_processing_time > 30000"  # 30秒
    severity: "critical"
    message: "命令处理时间过长"

  high_failure_rate:
    condition: "retry_rate > 0.1"  # 10%
    severity: "warning"
    message: "命令失败率过高"

  outbox_publish_delay:
    condition: "avg_publish_delay > 5000"  # 5秒
    severity: "warning"
    message: "事件发布延迟过高"

  version_gap_detected:
    condition: "aggregate_version_gaps > 0"
    severity: "critical"
    message: "检测到聚合版本号间隙"
```

## 最佳实践总结

### 1. 设计原则

1. **单一职责**: 每个命令/事件只负责一个明确的业务动作
2. **幂等性**: 相同命令多次执行结果一致
3. **原子性**: 命令处理要么全部成功，要么全部失败
4. **可追溯性**: 完整的correlation_id和causation_id链路

### 2. 实现原则

1. **统一命名**: 严格遵循点式命名约定
2. **版本控制**: 使用aggregate_version确保事件顺序
3. **错误处理**: 区分可重试和不可重试错误
4. **监控告警**: 关键指标的实时监控和告警

### 3. 运维原则

1. **定期检查**: 自动化的一致性检查
2. **自动修复**: 常见问题的自动修复机制
3. **性能优化**: 基于监控数据的持续优化
4. **容量规划**: 基于业务增长的容量预估

这套一致性保证机制确保了创世阶段命令事件系统的稳定性和可靠性。