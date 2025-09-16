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
 * SSE 事件类型
 * 用于服务器发送事件
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
 * 小说创建事件
 */
export interface NovelCreatedEvent extends BaseEvent {
  event_type: 'novel.created'
  payload: {
    novel_id: string
    title: string
    user_id?: string
  }
}

/**
 * 章节更新事件
 */
export interface ChapterUpdatedEvent extends BaseEvent {
  event_type: 'chapter.updated'
  payload: {
    chapter_id: string
    novel_id: string
    chapter_number: number
    status: string
  }
}

/**
 * 工作流开始事件
 */
export interface WorkflowStartedEvent extends BaseEvent {
  event_type: 'workflow.started'
  payload: {
    workflow_run_id: string
    workflow_type: string
    novel_id: string
  }
}

/**
 * 工作流完成事件
 */
export interface WorkflowCompletedEvent extends BaseEvent {
  event_type: 'workflow.completed'
  payload: {
    workflow_run_id: string
    workflow_type: string
    novel_id: string
    status: 'COMPLETED' | 'FAILED'
    error_details?: any
  }
}

/**
 * Agent 活动事件
 */
export interface AgentActivityEvent extends BaseEvent {
  event_type: 'agent.activity'
  payload: {
    activity_id: string
    agent_type: string
    activity_type: string
    status: string
    novel_id: string
  }
}

/**
 * 创世流程事件
 */
export interface GenesisProgressEvent extends BaseEvent {
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
 * 所有事件类型的联合类型
 */
export type DomainEvent =
  | NovelCreatedEvent
  | ChapterUpdatedEvent
  | WorkflowStartedEvent
  | WorkflowCompletedEvent
  | AgentActivityEvent
  | GenesisProgressEvent

/**
 * 事件类型枚举
 */
export enum EventType {
  NOVEL_CREATED = 'novel.created',
  CHAPTER_UPDATED = 'chapter.updated',
  WORKFLOW_STARTED = 'workflow.started',
  WORKFLOW_COMPLETED = 'workflow.completed',
  AGENT_ACTIVITY = 'agent.activity',
  GENESIS_PROGRESS = 'genesis.progress',
}
