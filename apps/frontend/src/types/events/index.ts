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
 * 错误级别枚举（对应后端 ErrorLevel）
 */
export enum ErrorLevel {
  WARNING = 'warning',
  ERROR = 'error',
  CRITICAL = 'critical',
}

/**
 * SSE 消息格式（对应后端 SSEMessage，遵循 W3C 规范）
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
 * 创建 SSE 消息的工厂函数（对应后端 create_sse_message）
 */
export function createSSEMessage({
  event,
  data,
  id,
  retry,
  scope = EventScope.USER,
  version = '1.0',
}: {
  event: string
  data: Record<string, any>
  id?: string
  retry?: number
  scope?: EventScope
  version?: string
}): SSEMessage {
  return {
    event,
    data,
    id,
    retry,
    scope,
    version,
  }
}
