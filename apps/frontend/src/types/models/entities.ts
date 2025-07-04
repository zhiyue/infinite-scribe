/**
 * 核心实体类型定义
 * 对应后端数据库模型
 */

import type { BaseDBModel, AuditFields, UUIDString, ISODateString } from './base'
import {
  AgentType,
  NovelStatus,
  ChapterStatus,
  GenesisStatus,
  GenesisStage,
  WorkflowStatus,
  ActivityStatus,
  EventStatus,
  OperationType
} from '../enums'

/**
 * 小说表接口
 * 对应 NovelModel
 */
export interface Novel extends BaseDBModel, AuditFields {
  /** 小说标题 */
  title: string
  /** 小说主题 */
  theme?: string
  /** 写作风格 */
  writing_style?: string
  /** 当前状态 */
  status: NovelStatus
  /** 目标章节数 */
  target_chapters: number
  /** 已完成章节数 */
  completed_chapters: number
}

/**
 * 章节表接口
 * 对应 ChapterModel
 */
export interface Chapter extends BaseDBModel, AuditFields {
  /** 所属小说的ID */
  novel_id: UUIDString
  /** 章节序号 */
  chapter_number: number
  /** 章节标题 */
  title?: string
  /** 章节当前状态 */
  status: ChapterStatus
  /** 指向当前已发布版本的ID */
  published_version_id?: UUIDString
}

/**
 * 章节版本表接口
 * 对应 ChapterVersionModel
 */
export interface ChapterVersion extends BaseDBModel {
  /** 关联的章节ID */
  chapter_id: UUIDString
  /** 版本号，从1开始递增 */
  readonly version_number: number
  /** 指向Minio中该版本内容的URL */
  content_url: string
  /** 该版本的字数 */
  word_count?: number
  /** 创建此版本的Agent类型 */
  readonly created_by_agent_type: AgentType
  /** 修改原因 */
  change_reason?: string
  /** 指向上一个版本的ID */
  parent_version_id?: UUIDString
  /** 版本相关的额外元数据 */
  metadata?: Record<string, any>
  /** 版本创建时间 */
  readonly created_at: ISODateString
}

/**
 * 角色表接口
 * 对应 CharacterModel
 */
export interface Character extends BaseDBModel, AuditFields {
  /** 所属小说的ID */
  novel_id: UUIDString
  /** 角色名称 */
  name: string
  /** 角色定位 */
  role?: string
  /** 角色外貌、性格等简述 */
  description?: string
  /** 角色背景故事 */
  background_story?: string
  /** 性格特点列表 */
  personality_traits?: string[]
  /** 角色的主要目标列表 */
  goals?: string[]
}

/**
 * 世界观条目表接口
 * 对应 WorldviewEntryModel
 */
export interface WorldviewEntry extends BaseDBModel, AuditFields {
  /** 所属小说的ID */
  novel_id: UUIDString
  /** 条目类型 */
  entry_type: string
  /** 条目名称 */
  name: string
  /** 详细描述 */
  description?: string
  /** 标签，用于分类和检索 */
  tags?: string[]
}

/**
 * 故事弧表接口
 * 对应 StoryArcModel
 */
export interface StoryArc extends BaseDBModel, AuditFields {
  /** 所属小说的ID */
  novel_id: UUIDString
  /** 故事弧标题 */
  title: string
  /** 故事弧摘要 */
  summary?: string
  /** 开始章节号 */
  start_chapter_number?: number
  /** 结束章节号 */
  end_chapter_number?: number
  /** 状态 */
  status: string
}

/**
 * 评审记录表接口
 * 对应 ReviewModel
 */
export interface Review extends BaseDBModel {
  /** 关联的章节ID */
  chapter_id: UUIDString
  /** 评审针对的具体章节版本ID */
  chapter_version_id: UUIDString
  /** 关联的工作流运行ID */
  workflow_run_id?: UUIDString
  /** 执行评审的Agent类型 */
  readonly agent_type: AgentType
  /** 评审类型 */
  review_type: string
  /** 评论家评分 */
  score?: number
  /** 评论家评语 */
  comment?: string
  /** 事实核查员判断是否一致 */
  is_consistent?: boolean
  /** 事实核查员发现的问题列表 */
  issues_found?: string[]
  /** 评审创建时间 */
  readonly created_at: ISODateString
}

/**
 * 大纲表接口
 * 对应 OutlineModel
 */
export interface Outline extends BaseDBModel, AuditFields {
  /** 关联的章节ID */
  chapter_id: UUIDString
  /** 大纲文本内容 */
  content: string
  /** 指向Minio中存储的大纲文件URL */
  content_url?: string
  /** 额外的结构化元数据 */
  metadata?: Record<string, any>
}

/**
 * 场景卡表接口
 * 对应 SceneCardModel
 */
export interface SceneCard extends BaseDBModel, AuditFields {
  /** 所属小说ID */
  novel_id: UUIDString
  /** 所属章节ID */
  chapter_id: UUIDString
  /** 关联的大纲ID */
  outline_id: UUIDString
  /** 场景在章节内的序号 */
  scene_number: number
  /** 视角角色ID */
  pov_character_id?: UUIDString
  /** 场景的详细设计 */
  content: Record<string, any>
}

/**
 * 角色互动表接口
 * 对应 CharacterInteractionModel
 */
export interface CharacterInteraction extends BaseDBModel, AuditFields {
  /** 所属小说ID */
  novel_id: UUIDString
  /** 所属章节ID */
  chapter_id: UUIDString
  /** 关联的场景卡ID */
  scene_card_id: UUIDString
  /** 互动类型 */
  interaction_type?: string
  /** 互动的详细内容 */
  content: Record<string, any>
}

/**
 * 工作流运行表接口
 * 对应 WorkflowRunModel
 */
export interface WorkflowRun extends BaseDBModel {
  /** 关联的小说ID */
  novel_id: UUIDString
  /** 工作流类型 */
  workflow_type: string
  /** 工作流当前状态 */
  status: WorkflowStatus
  /** 启动工作流时传入的参数 */
  parameters?: Record<string, any>
  /** 开始时间 */
  started_at: ISODateString
  /** 完成时间 */
  completed_at?: ISODateString
  /** 错误详情 */
  error_details?: Record<string, any>
}

/**
 * Agent活动表接口（分区表）
 * 对应 AgentActivityModel
 */
export interface AgentActivity extends BaseDBModel {
  /** 关联的工作流运行ID */
  workflow_run_id?: UUIDString
  /** 关联的小说ID */
  novel_id: UUIDString
  /** 活动操作的目标实体ID */
  target_entity_id?: UUIDString
  /** 目标实体类型 */
  target_entity_type?: string
  /** 执行活动的Agent类型 */
  agent_type?: AgentType
  /** 活动类型 */
  activity_type: string
  /** 活动状态 */
  status: ActivityStatus
  /** 活动的输入数据摘要 */
  input_data?: Record<string, any>
  /** 活动的输出数据摘要 */
  output_data?: Record<string, any>
  /** 错误详情 */
  error_details?: Record<string, any>
  /** 开始时间 */
  started_at: ISODateString
  /** 完成时间 */
  completed_at?: ISODateString
  /** 调用LLM消耗的Token数 */
  llm_tokens_used?: number
  /** 调用LLM的估算成本 */
  llm_cost_estimate?: number
  /** 重试次数 */
  retry_count: number
}

/**
 * 事件表接口
 * 对应 EventModel
 */
export interface Event extends BaseDBModel {
  /** 事件类型 */
  event_type: string
  /** 关联的小说ID */
  novel_id?: UUIDString
  /** 关联的工作流运行ID */
  workflow_run_id?: UUIDString
  /** 事件的完整载荷 */
  payload: Record<string, any>
  /** 事件处理状态 */
  status: EventStatus
  /** 处理此事件的Agent类型 */
  processed_by_agent_type?: AgentType
  /** 事件创建时间 */
  created_at: ISODateString
  /** 事件处理完成时间 */
  processed_at?: ISODateString
  /** 错误详情 */
  error_details?: Record<string, any>
}

/**
 * Agent配置表接口
 * 对应 AgentConfigurationModel
 */
export interface AgentConfiguration extends BaseDBModel {
  /** 关联的小说ID，null表示全局配置 */
  novel_id?: UUIDString
  /** 配置作用的Agent类型 */
  agent_type?: AgentType
  /** 配置项名称 */
  config_key: string
  /** 配置项的值 */
  config_value: Record<string, any> | string | number
  /** 是否启用此配置 */
  is_active: boolean
  /** 创建时间 */
  created_at: ISODateString
  /** 最后更新时间 */
  updated_at: ISODateString
}

/**
 * 创世会话表接口
 * 对应 GenesisSessionModel
 */
export interface GenesisSession extends BaseDBModel, AuditFields {
  /** 关联的小说ID */
  novel_id: UUIDString
  /** 用户ID */
  user_id?: UUIDString
  /** 会话状态 */
  status: GenesisStatus
  /** 当前阶段 */
  current_stage: GenesisStage
  /** 初始用户输入 */
  initial_user_input?: Record<string, any>
  /** 最终设置 */
  final_settings?: Record<string, any>
}

/**
 * 创世步骤表接口
 * 对应 GenesisStepModel
 */
export interface GenesisStep extends BaseDBModel {
  /** 所属会话ID */
  session_id: UUIDString
  /** 所属阶段 */
  readonly stage: GenesisStage
  /** 迭代次数 */
  readonly iteration_count: number
  /** AI提示词 */
  ai_prompt?: string
  /** AI输出 */
  ai_output: Record<string, any>
  /** 用户反馈 */
  user_feedback?: string
  /** 是否已确认 */
  is_confirmed: boolean
  /** 创建时间 */
  readonly created_at: ISODateString
}

/**
 * 审计日志表接口
 * 对应 AuditLogModel
 */
export interface AuditLog extends BaseDBModel {
  /** 发生变更的表名 */
  table_name: string
  /** 发生变更的记录ID */
  record_id: UUIDString
  /** 操作类型 */
  operation: OperationType
  /** 执行变更的Agent类型 */
  changed_by_agent_type?: AgentType
  /** 变更发生时间 */
  changed_at: ISODateString
  /** 旧值 */
  old_values?: Record<string, any>
  /** 新值 */
  new_values?: Record<string, any>
}