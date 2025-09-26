/**
 * 事件类型定义
 * 对应后端的事件系统
 */

import type { BaseEvent } from '../models/base'

/**
 * 基础事件类型
 * 所有具体事件类型都应该扩展此接口
 */
export type { BaseEvent }

/**
 * 事件作用域枚举（对应后端 EventScope）
 */
export enum EventScope {
  USER = 'user',
  SESSION = 'session',
  NOVEL = 'novel',
  GLOBAL = 'global',
}

/**
 * Orchestrator 消息类型（对应后端 MessageType）
 */
export type MessageType =
  | 'Character.Design.Generated'
  | 'Character.Generated'
  | 'Outliner.Theme.Generated'
  | 'Theme.Generated'
  | 'Review.Quality.Evaluated'
  | 'Review.Quality.Result'
  | 'Review.Consistency.Checked'
  | 'Consistency.Checked'
  | 'Character.Design.GenerationRequested'
  | 'Outliner.Theme.GenerationRequested'
  | 'Review.Quality.EvaluationRequested'

/**
 * Orchestrator 事件动作类型（对应后端 EventActionType）
 */
export type EventActionType =
  | 'Character.Proposed'
  | 'Theme.Proposed'
  | 'Character.Confirmed'
  | 'Theme.Confirmed'
  | 'Character.Failed'
  | 'Theme.Failed'
  | 'Character.RegenerationRequested'
  | 'Theme.RegenerationRequested'
  | 'Stage.Confirmed'
  | 'Stage.Failed'

/**
 * Orchestrator 目标类型（对应后端 TargetType）
 */
export type TargetType = 'character' | 'theme' | 'content'

/**
 * Orchestrator 作用域类型（对应后端 ScopeType）
 */
export type OrchestratorScopeType = 'GENESIS'

/**
 * 错误级别枚举（对应后端 ErrorLevel）
 */
export enum ErrorLevel {
  WARNING = 'warning',
  ERROR = 'error',
  CRITICAL = 'critical',
}

/**
 * 统一事件元数据模型（对应后端 EventMetadata）
 * 定义了事件系统中所有元数据的标准结构，用于：
 * - 事件标识和分类
 * - 业务流程关联和追踪
 * - 技术调用链监控
 * - 系统间数据传递
 */
export interface EventMetadata {
  // === 核心标识字段 ===
  /** 事件唯一标识符，通常为UUID格式
   * 用途：事件去重、引用、审计追踪
   * 示例：'550e8400-e29b-41d4-a716-446655440000'
   */
  event_id?: string | null

  /** 事件类型标识，遵循层次化命名约定
   * 格式：Domain.Aggregate.Action（如：Genesis.Character.Generated）
   * 用途：事件分类、路由、处理器匹配
   * 注意：统一使用event_type而不是type，避免关键字冲突
   */
  event_type?: string | null

  /** 聚合根类型，DDD概念中的聚合标识
   * 格式：通常为单个名词（如：Genesis、Character、Session）
   * 用途：数据分区、事件分组、业务边界定义
   */
  aggregate_type?: string | null

  /** 聚合根实例ID，通常对应具体的业务实体
   * 格式：UUID或业务ID（如：session_id、user_id）
   * 用途：事件与具体业务实体关联、数据分片
   */
  aggregate_id?: string | null

  // === 业务关联字段 ===
  /** 业务流程关联ID，用于串联完整的业务操作
   *
   * 作用域：单一业务请求的完整生命周期
   * 用途：
   * - 业务流程追踪（如：从用户请求到最终响应）
   * - 事件幂等性保证（correlation_id + event_type去重）
   * - 跨服务的业务操作关联
   *
   * 示例：'user-char-gen-20241201-001'
   * 生命周期：用户发起请求 → 多个领域事件 → 业务完成
   */
  correlation_id?: string | null

  /** 因果关系ID，指向触发当前事件的上游事件
   *
   * 用途：
   * - 事件链追踪（Event A → Event B → Event C）
   * - 调试复杂业务流程
   * - 审计和回溯分析
   *
   * 示例：当前事件由event_id='abc-123'的事件触发，则causation_id='abc-123'
   * 注意：形成有向无环图(DAG)，避免循环引用
   */
  causation_id?: string | null

  // === 时间字段 ===
  /** 事件创建时间戳，ISO 8601格式
   *
   * 格式：'2024-12-01T10:30:00.123Z'
   * 用途：
   * - 事件排序和时间线重建
   * - 性能分析和SLA监控
   * - 数据归档和清理策略
   *
   * 注意：建议使用UTC时间避免时区问题
   */
  created_at?: string | null

  // === 版本字段 ===
  /** 事件schema版本号，用于事件结构演进
   *
   * 用途：
   * - 事件格式向后兼容
   * - 系统升级和迁移
   * - 反序列化版本控制
   *
   * 示例：v1=1, v2=2（递增整数）
   */
  event_version?: number | null

  /** 字符串版本标识，兼容现有系统的version字段
   *
   * 格式：'v1', 'v2.1', '1.0.0'等
   * 用途：与外部系统集成时的版本兼容
   * 注意：建议新系统使用event_version（整数），此字段用于过渡
   */
  version?: string | null

  // === 分布式追踪字段 ===
  /** 分布式追踪ID，用于跨服务调用链监控
   *
   * 作用域：完整的技术调用链（可能跨越多个业务操作）
   * 用途：
   * - 性能监控和APM
   * - 错误排查和调试
   * - 系统观测性(Observability)
   * - 调用链分析
   *
   * 示例：'jaeger-trace-550e8400e29b41d4a716446655440000'
   * 传播：通过HTTP Headers、消息队列属性等技术手段
   *
   * 与correlation_id区别：
   * - trace_id：技术维度，关注系统调用
   * - correlation_id：业务维度，关注业务流程
   */
  trace_id?: string | null

  /** 调用链段标识，标识trace中的具体操作段
   *
   * 用途：
   * - 细粒度的调用监控
   * - 性能瓶颈定位
   * - 调用链可视化
   *
   * 示例：'span-abc123def456'
   * 关系：trace_id包含多个span_id，形成调用树
   */
  span_id?: string | null

  /** 事件来源标识，标识产生事件的系统或组件
   *
   * 用途：
   * - 事件溯源和审计
   * - 系统间集成调试
   * - 权限和安全控制
   *
   * 示例：'orchestrator', 'api-gateway', 'character-service'
   * 建议：使用标准化的服务名称
   */
  source?: string | null

  // === 扩展元数据 ===
  /** 通用元数据字典，存储额外的上下文信息
   *
   * 用途：
   * - 存储不适合标准字段的附加信息
   * - 系统特定的扩展数据
   * - 临时性的调试信息
   *
   * 示例：
   * {
   *   'user_id': 'user-123',
   *   'session_type': 'character_generation',
   *   'experiment_id': 'exp-001',
   *   'custom_tags': ['priority:high', 'region:us-west']
   * }
   *
   * 注意：
   * - 避免存储敏感信息（密码、token等）
   * - 保持结构简单，便于序列化
   * - 考虑大小限制，避免存储大对象
   */
  metadata?: Record<string, any>
}

/**
 * SSE 消息格式（对应后端 SSEMessage，遵循 W3C 规范）
 * 增强版本，包含完整的事件元数据
 */
export interface SSEMessage {
  /** 事件类型，使用 domain.action-past 格式 */
  event: string
  /** 事件数据 */
  data: Record<string, any>
  /** 事件 ID，格式：{source}:{partition}:{offset} */
  id?: string
  /** 重连延迟（毫秒） */
  retry?: number
  /** 事件作用域 */
  scope: EventScope
  /** 事件版本，用于兼容性 */
  version: string
  /** 完整的事件元数据（新增，对应后端 EventMetadata） */
  metadata?: EventMetadata
}

/**
 * SSE 事件类型（兼容性接口）
 * @deprecated 使用 SSEMessage 替代
 */
export interface SSEEvent<T = any> {
  /** 事件类型 */
  type: string
  /** 事件数据 */
  data: T
  /** 事件ID */
  id?: string
  /** 重试时间（毫秒） */
  retry?: number
  /** 事件作用域 */
  scope?: EventScope
  /** 事件版本 */
  version?: string
}

/**
 * SSE 连接配置接口
 */
export interface SSEConnectionConfig {
  /** 重连间隔（毫秒） */
  reconnectInterval?: number
  /** 最大重连次数 */
  maxReconnectAttempts?: number
  /** 连接超时（毫秒） */
  connectionTimeout?: number
  /** 是否启用自动重连 */
  enableReconnect?: boolean
}

/**
 * SSE 事件监听器配置
 */
export interface SSEListenerConfig {
  /** 是否只监听一次 */
  once?: boolean
  /** 事件过滤器 */
  filter?: (event: SSEEvent) => boolean
  /** 错误处理器 */
  onError?: (error: Error) => void
}

/**
 * 任务进度事件（对应后端 TaskProgressEvent）
 */
export interface TaskProgressEvent {
  event: 'task.progress-updated'
  data: {
    task_id: string
    progress: number
    message?: string
    estimated_remaining?: number
  }
}

/**
 * 任务状态变更事件（对应后端 TaskStatusChangeEvent）
 */
export interface TaskStatusChangeEvent {
  event: 'task.status-changed'
  data: {
    task_id: string
    old_status: string
    new_status: string
    timestamp: string
    reason?: string
  }
}

/**
 * 系统通知事件（对应后端 SystemNotificationEvent）
 */
export interface SystemNotificationEvent {
  event: 'system.notification-sent'
  data: {
    level: 'info' | 'warning' | 'error'
    title: string
    message: string
    action_required: boolean
    action_url?: string
  }
}

/**
 * 内容更新事件（对应后端 ContentUpdateEvent）
 */
export interface ContentUpdateEvent {
  event: 'content.updated'
  data: {
    entity_type: string
    entity_id: string
    action: 'created' | 'updated' | 'deleted'
    summary?: string
    changed_fields?: string[]
  }
}

/**
 * SSE 错误事件（对应后端 SSEErrorEvent）
 */
export interface SSEErrorEvent {
  event: 'sse.error-occurred'
  data: {
    level: ErrorLevel
    code: string
    message: string
    correlation_id?: string
    retry_after?: number
  }
}

/**
 * 小说创建事件（对应后端 NovelCreatedEvent）
 */
export interface NovelCreatedEvent {
  event: 'novel.created'
  data: {
    id: string
    title: string
    theme?: string
    status: string
    created_at: string
  }
}

/**
 * 小说状态变更事件（对应后端 NovelStatusChangedEvent）
 */
export interface NovelStatusChangedEvent {
  event: 'novel.status-changed'
  data: {
    novel_id: string
    old_status: string
    new_status: string
    changed_at: string
  }
}

/**
 * 章节草稿创建事件（对应后端 ChapterDraftCreatedEvent）
 */
export interface ChapterDraftCreatedEvent {
  event: 'chapter.draft-created'
  data: {
    chapter_id: string
    chapter_number: number
    title?: string
    novel_id: string
  }
}

/**
 * 章节状态变更事件（对应后端 ChapterStatusChangedEvent）
 */
export interface ChapterStatusChangedEvent {
  event: 'chapter.status-changed'
  data: {
    chapter_id: string
    old_status: string
    new_status: string
    novel_id: string
  }
}

/**
 * 创世步骤完成事件（对应后端 GenesisStepCompletedEvent）
 */
export interface GenesisStepCompletedEvent {
  event: 'genesis.step-completed'
  data: {
    session_id: string
    stage: string
    iteration: number
    is_confirmed: boolean
    summary?: string
  }
}

/**
 * 创世步骤失败事件（对应后端 GenesisStepFailedEvent）
 */
export interface GenesisStepFailedEvent {
  event: 'genesis.step-failed'
  data: {
    session_id: string
    stage: string
    iteration: number
    error_message?: string
    retry_count?: number
  }
}

/**
 * 创世会话完成事件（对应后端 GenesisSessionCompletedEvent）
 */
export interface GenesisSessionCompletedEvent {
  event: 'genesis.session-completed'
  data: {
    session_id: string
    novel_id: string
    status: string
    completion_time: string
  }
}

/**
 * 创世会话失败事件（对应后端 GenesisSessionFailedEvent）
 */
export interface GenesisSessionFailedEvent {
  event: 'genesis.session-failed'
  data: {
    session_id: string
    novel_id?: string
    error_message: string
    failure_stage?: string
  }
}

/**
 * 工作流状态变更事件（对应后端 WorkflowStatusChangedEvent）
 */
export interface WorkflowStatusChangedEvent {
  event: 'workflow.status-changed'
  data: {
    workflow_id: string
    workflow_type: string
    old_status: string
    new_status: string
    novel_id: string
  }
}

/**
 * 兼容性事件类型（保持向后兼容）
 */
export interface LegacyChapterUpdatedEvent extends BaseEvent {
  event_type: 'chapter.updated'
  payload: {
    chapter_id: string
    novel_id: string
    chapter_number: number
    status: string
  }
}

export interface LegacyWorkflowStartedEvent extends BaseEvent {
  event_type: 'workflow.started'
  payload: {
    workflow_run_id: string
    workflow_type: string
    novel_id: string
  }
}

export interface LegacyWorkflowCompletedEvent extends BaseEvent {
  event_type: 'workflow.completed'
  payload: {
    workflow_run_id: string
    workflow_type: string
    novel_id: string
    status: 'COMPLETED' | 'FAILED'
    error_details?: any
  }
}

export interface LegacyAgentActivityEvent extends BaseEvent {
  event_type: 'agent.activity'
  payload: {
    activity_id: string
    agent_type: string
    activity_type: string
    status: string
    novel_id: string
  }
}

export interface LegacyGenesisProgressEvent extends BaseEvent {
  event_type: 'genesis.progress'
  payload: {
    session_id: string
    novel_id: string
    stage: string
    status: string
    progress?: number
  }
}

/**
 * 所有后端事件类型的联合类型
 */
export type BackendSSEEvent =
  | TaskProgressEvent
  | TaskStatusChangeEvent
  | SystemNotificationEvent
  | ContentUpdateEvent
  | SSEErrorEvent
  | NovelCreatedEvent
  | NovelStatusChangedEvent
  | ChapterDraftCreatedEvent
  | ChapterStatusChangedEvent
  | GenesisStepCompletedEvent
  | GenesisStepFailedEvent
  | GenesisSessionCompletedEvent
  | GenesisSessionFailedEvent
  | WorkflowStatusChangedEvent

/**
 * 兼容性事件类型联合（保持向后兼容）
 */
export type DomainEvent =
  | NovelCreatedEvent
  | LegacyChapterUpdatedEvent
  | LegacyWorkflowStartedEvent
  | LegacyWorkflowCompletedEvent
  | LegacyAgentActivityEvent
  | LegacyGenesisProgressEvent

/**
 * 后端事件类型枚举（对应后端实现）
 */
export enum BackendEventType {
  // 任务相关事件
  TASK_PROGRESS_UPDATED = 'task.progress-updated',
  TASK_STATUS_CHANGED = 'task.status-changed',

  // 系统相关事件
  SYSTEM_NOTIFICATION_SENT = 'system.notification-sent',
  SSE_ERROR_OCCURRED = 'sse.error-occurred',

  // 内容相关事件
  CONTENT_UPDATED = 'content.updated',

  // 小说相关事件
  NOVEL_CREATED = 'novel.created',
  NOVEL_STATUS_CHANGED = 'novel.status-changed',

  // 章节相关事件
  CHAPTER_DRAFT_CREATED = 'chapter.draft-created',
  CHAPTER_STATUS_CHANGED = 'chapter.status-changed',

  // 创世相关事件
  GENESIS_STEP_COMPLETED = 'genesis.step-completed',
  GENESIS_STEP_FAILED = 'genesis.step-failed',
  GENESIS_SESSION_COMPLETED = 'genesis.session-completed',
  GENESIS_SESSION_FAILED = 'genesis.session-failed',

  // 工作流相关事件
  WORKFLOW_STATUS_CHANGED = 'workflow.status-changed',
}

/**
 * 兼容性事件类型枚举（保持向后兼容）
 */
export enum EventType {
  NOVEL_CREATED = 'novel.created',
  CHAPTER_UPDATED = 'chapter.updated',
  WORKFLOW_STARTED = 'workflow.started',
  WORKFLOW_COMPLETED = 'workflow.completed',
  AGENT_ACTIVITY = 'agent.activity',
  GENESIS_PROGRESS = 'genesis.progress',
}

/**
 * 创建事件元数据的工厂函数（对应后端 EventMetadata）
 */
export function createEventMetadata({
  event_id,
  event_type,
  aggregate_type,
  aggregate_id,
  correlation_id,
  causation_id,
  created_at,
  event_version,
  version,
  trace_id,
  span_id,
  source,
  metadata = {},
}: Partial<EventMetadata> = {}): EventMetadata {
  return {
    event_id,
    event_type,
    aggregate_type,
    aggregate_id,
    correlation_id,
    causation_id,
    created_at,
    event_version,
    version,
    trace_id,
    span_id,
    source,
    metadata,
  }
}

/**
 * 创建 SSE 消息的工厂函数（对应后端 create_sse_message）
 * 增强版本，支持完整的事件元数据
 */
export function createSSEMessage({
  event,
  data,
  id,
  retry,
  scope = EventScope.USER,
  version = '1.0',
  metadata,
}: {
  event: string
  data: Record<string, any>
  id?: string
  retry?: number
  scope?: EventScope
  version?: string
  metadata?: EventMetadata
}): SSEMessage {
  return {
    event,
    data,
    id,
    retry,
    scope,
    version,
    metadata,
  }
}

/**
 * 从 SSE 消息中提取事件元数据
 */
export function extractEventMetadata(message: SSEMessage): EventMetadata | null {
  return message.metadata || null
}

/**
 * 检查 SSE 消息是否包含完整的事件元数据
 */
export function hasEventMetadata(message: SSEMessage): boolean {
  return !!message.metadata && Object.keys(message.metadata).length > 0
}

/**
 * 获取事件的关联 ID（correlation_id），用于业务流程追踪
 */
export function getCorrelationId(message: SSEMessage): string | null {
  return message.metadata?.correlation_id || null
}

/**
 * 获取事件的因果关系 ID（causation_id），用于事件链追踪
 */
export function getCausationId(message: SSEMessage): string | null {
  return message.metadata?.causation_id || null
}

/**
 * 获取事件的分布式追踪 ID（trace_id），用于调用链监控
 */
export function getTraceId(message: SSEMessage): string | null {
  return message.metadata?.trace_id || null
}

/**
 * 获取事件来源（source），用于事件溯源
 */
export function getEventSource(message: SSEMessage): string | null {
  return message.metadata?.source || null
}

/**
 * 检查事件是否来自特定源
 */
export function isFromSource(message: SSEMessage, source: string): boolean {
  return getEventSource(message) === source
}

/**
 * 检查事件是否来自 Orchestrator
 */
export function isFromOrchestrator(message: SSEMessage): boolean {
  return isFromSource(message, 'orchestrator')
}

/**
 * 检查事件是否属于特定聚合类型
 */
export function isFromAggregateType(message: SSEMessage, aggregateType: string): boolean {
  return message.metadata?.aggregate_type === aggregateType
}

/**
 * 检查事件是否属于 Genesis 聚合
 */
export function isGenesisEvent(message: SSEMessage): boolean {
  return isFromAggregateType(message, 'Genesis')
}

/**
 * 创建带有完整元数据的 Genesis 相关事件
 */
export function createGenesisEvent({
  event,
  data,
  session_id,
  correlation_id,
  causation_id,
  source = 'orchestrator',
}: {
  event: string
  data: Record<string, any>
  session_id: string
  correlation_id?: string
  causation_id?: string
  source?: string
}): SSEMessage {
  const metadata = createEventMetadata({
    event_id: `genesis-${Date.now()}-${Math.random().toString(36).slice(2)}`,
    event_type: event,
    aggregate_type: 'Genesis',
    aggregate_id: session_id,
    correlation_id,
    causation_id,
    created_at: new Date().toISOString(),
    event_version: 1,
    version: '1.0',
    source,
    metadata: {
      session_id,
      scope_type: 'GENESIS' as OrchestratorScopeType,
    },
  })

  return createSSEMessage({
    event,
    data,
    scope: EventScope.SESSION,
    version: '1.0',
    metadata,
  })
}
