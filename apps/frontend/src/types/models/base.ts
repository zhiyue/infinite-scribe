/**
 * 基础模型类型定义
 * 包含所有模型的通用接口和类型别名
 */

import { AgentType } from '../enums'

/**
 * ISO8601 格式的日期时间字符串
 * @example "2025-07-02T10:00:00Z"
 */
export type ISODateString = string

/**
 * UUID 字符串类型
 * @example "550e8400-e29b-41d4-a716-446655440000"
 */
export type UUIDString = string

/**
 * 带元数据的通用接口
 * 提供类型安全的元数据支持
 */
export interface WithMetadata<T = Record<string, any>> {
  /** 类型安全的元数据 */
  metadata?: T
}

/**
 * 基础数据库模型接口
 * 所有数据库模型的通用属性
 */
export interface BaseDBModel {
  /** 主键ID */
  readonly id: UUIDString
}

/**
 * 审计字段接口
 * 包含版本控制和创建/更新信息
 */
export interface AuditFields {
  /** 乐观锁版本号 */
  readonly version: number
  /** 创建此记录的Agent类型 */
  readonly created_by_agent_type?: AgentType
  /** 最后更新此记录的Agent类型 */
  updated_by_agent_type?: AgentType
  /** 创建时间 */
  readonly created_at: ISODateString
  /** 最后更新时间 */
  updated_at: ISODateString
}

/**
 * 基础API模型接口
 * 用于API请求和响应的通用属性
 */
export interface BaseAPIModel {
  // API模型的通用字段将在此定义
}

/**
 * 基础事件接口
 * 事件系统的通用属性
 */
export interface BaseEvent {
  /** 事件ID */
  event_id: UUIDString
  /** 事件类型 */
  event_type: string
  /** 时间戳 */
  timestamp: ISODateString
  /** 源Agent */
  source_agent: string
  /** 关联小说ID */
  novel_id: UUIDString
  /** 关联ID */
  correlation_id?: string
}

/**
 * 所有模型名称的联合类型
 */
export type ModelName =
  | 'Novel'
  | 'Chapter'
  | 'ChapterVersion'
  | 'Character'
  | 'WorldviewEntry'
  | 'StoryArc'
  | 'Review'
  | 'Outline'
  | 'SceneCard'
  | 'CharacterInteraction'
  | 'WorkflowRun'
  | 'AgentActivity'
  | 'Event'
  | 'AgentConfiguration'
  | 'GenesisSession'
  | 'GenesisStep'
  | 'AuditLog'

/**
 * 模型关系映射类型
 * 用于理解表间关系
 */
export type ModelRelationships = Record<
  ModelName,
  {
    children: readonly ModelName[]
    foreign_keys: readonly string[]
  }
>

/**
 * 常量导出
 */
export const VERSION = '0.1.0'

/**
 * 模型关系映射常量
 * 类型安全的关系定义
 */
export const MODEL_RELATIONSHIPS = {
  Novel: {
    children: [
      'Chapter',
      'Character',
      'WorldviewEntry',
      'StoryArc',
      'GenesisSession',
      'SceneCard',
      'CharacterInteraction',
    ] as const satisfies readonly ModelName[],
    foreign_keys: [] as const,
  },
  Chapter: {
    children: ['ChapterVersion', 'Outline', 'SceneCard'] as const satisfies readonly ModelName[],
    foreign_keys: ['novel_id'] as const,
  },
  ChapterVersion: {
    children: ['Review'] as const satisfies readonly ModelName[],
    foreign_keys: ['chapter_id', 'parent_version_id'] as const,
  },
  Character: {
    children: [] as const satisfies readonly ModelName[],
    foreign_keys: ['novel_id'] as const,
  },
  WorldviewEntry: {
    children: [] as const satisfies readonly ModelName[],
    foreign_keys: ['novel_id'] as const,
  },
  StoryArc: {
    children: [] as const satisfies readonly ModelName[],
    foreign_keys: ['novel_id'] as const,
  },
  GenesisSession: {
    children: ['GenesisStep'] as const satisfies readonly ModelName[],
    foreign_keys: ['novel_id'] as const,
  },
  GenesisStep: {
    children: [] as const satisfies readonly ModelName[],
    foreign_keys: ['session_id'] as const,
  },
  Outline: {
    children: ['SceneCard'] as const satisfies readonly ModelName[],
    foreign_keys: ['chapter_id'] as const,
  },
  SceneCard: {
    children: ['CharacterInteraction'] as const satisfies readonly ModelName[],
    foreign_keys: ['novel_id', 'chapter_id', 'outline_id', 'pov_character_id'] as const,
  },
  CharacterInteraction: {
    children: [] as const satisfies readonly ModelName[],
    foreign_keys: ['novel_id', 'chapter_id', 'scene_card_id'] as const,
  },
  Review: {
    children: [] as const satisfies readonly ModelName[],
    foreign_keys: ['chapter_id', 'chapter_version_id'] as const,
  },
  WorkflowRun: {
    children: [] as const satisfies readonly ModelName[],
    foreign_keys: ['novel_id'] as const,
  },
  AgentActivity: {
    children: [] as const satisfies readonly ModelName[],
    foreign_keys: ['workflow_run_id', 'novel_id', 'target_entity_id'] as const,
  },
  Event: {
    children: [] as const satisfies readonly ModelName[],
    foreign_keys: ['novel_id', 'workflow_run_id'] as const,
  },
  AgentConfiguration: {
    children: [] as const satisfies readonly ModelName[],
    foreign_keys: ['novel_id', 'agent_type'] as const,
  },
  AuditLog: {
    children: [] as const satisfies readonly ModelName[],
    foreign_keys: ['record_id'] as const,
  },
} as const satisfies ModelRelationships
