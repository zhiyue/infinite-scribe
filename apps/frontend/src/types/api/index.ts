/**
 * API 请求和响应类型定义
 * 用于前后端 API 通信
 */

import type { 
  Novel, 
  Chapter, 
  // @ts-expect-error - Used in CreateCharacterRequest
  Character, 
  // @ts-expect-error - Used in CreateWorldviewEntryRequest
  WorldviewEntry,
  GenesisSession,
  WorkflowRun 
} from '../models/entities'
import { GenesisMode } from '../enums'

/**
 * API 响应基础类型（已在原 types/index.ts 中定义）
 * 这里重新导出以保持一致性
 */
export interface ApiResponse<T = unknown> {
  success: boolean
  data?: T
  error?: {
    code: string
    message: string
    details?: unknown
  }
  timestamp?: string
}

/**
 * 分页参数（已在原 types/index.ts 中定义）
 */
export interface PaginationParams {
  page: number
  pageSize: number
  total?: number
}

/**
 * 分页响应（已在原 types/index.ts 中定义）
 */
export interface PaginatedResponse<T> {
  items: T[]
  pagination: {
    page: number
    pageSize: number
    total: number
    totalPages: number
  }
}

// ===== 小说相关 API =====

/**
 * 创建小说请求
 */
export interface CreateNovelRequest {
  title: string
  theme?: string
  writing_style?: string
  target_chapters: number
}

/**
 * 更新小说请求
 */
export interface UpdateNovelRequest extends Partial<CreateNovelRequest> {
  status?: Novel['status']
}

/**
 * 小说列表查询参数
 */
export interface NovelListParams extends PaginationParams {
  status?: Novel['status']
  search?: string
  sort_by?: 'created_at' | 'updated_at' | 'title'
  sort_order?: 'asc' | 'desc'
}

// ===== 章节相关 API =====

/**
 * 创建章节请求
 */
export interface CreateChapterRequest {
  novel_id: string
  chapter_number: number
  title?: string
}

/**
 * 更新章节请求
 */
export interface UpdateChapterRequest {
  title?: string
  status?: Chapter['status']
}

/**
 * 章节内容响应
 */
export interface ChapterContentResponse {
  chapter: Chapter
  content: string
  word_count: number
  version_number: number
}

// ===== 角色相关 API =====

/**
 * 创建角色请求
 */
export interface CreateCharacterRequest {
  novel_id: string
  name: string
  role?: string
  description?: string
  background_story?: string
  personality_traits?: string[]
  goals?: string[]
}

/**
 * 更新角色请求
 */
export interface UpdateCharacterRequest extends Omit<CreateCharacterRequest, 'novel_id'> {}

// ===== 世界观相关 API =====

/**
 * 创建世界观条目请求
 */
export interface CreateWorldviewEntryRequest {
  novel_id: string
  entry_type: string
  name: string
  description?: string
  tags?: string[]
}

/**
 * 更新世界观条目请求
 */
export interface UpdateWorldviewEntryRequest extends Omit<CreateWorldviewEntryRequest, 'novel_id'> {}

// ===== 创世流程相关 API =====

/**
 * 开始创世请求
 */
export interface StartGenesisRequest {
  mode: GenesisMode
  initial_input?: {
    theme?: string
    style?: string
    inspiration?: string
  }
}

/**
 * 创世步骤反馈请求
 */
export interface GenesisFeedbackRequest {
  session_id: string
  step_id: string
  feedback?: string
  confirmed: boolean
}

/**
 * 创世会话响应
 */
export interface GenesisSessionResponse extends GenesisSession {
  current_step?: {
    id: string
    stage: string
    ai_output: any
    is_confirmed: boolean
  }
  progress: number
}

// ===== 工作流相关 API =====

/**
 * 启动工作流请求
 */
export interface StartWorkflowRequest {
  novel_id: string
  workflow_type: string
  parameters?: Record<string, any>
}

/**
 * 工作流状态响应
 */
export interface WorkflowStatusResponse extends WorkflowRun {
  activities?: {
    total: number
    completed: number
    failed: number
  }
  estimated_completion?: string
}

// ===== 搜索相关 API =====

/**
 * 全局搜索请求
 */
export interface GlobalSearchRequest {
  query: string
  types?: ('novel' | 'chapter' | 'character' | 'worldview')[]
  limit?: number
}

/**
 * 搜索结果项
 */
export interface SearchResultItem {
  type: 'novel' | 'chapter' | 'character' | 'worldview'
  id: string
  title: string
  description?: string
  highlight?: string
  score: number
}

/**
 * 搜索响应
 */
export interface GlobalSearchResponse {
  results: SearchResultItem[]
  total: number
  took: number
}

// ===== 统计相关 API =====

/**
 * 小说统计信息
 */
export interface NovelStatistics {
  novel_id: string
  total_words: number
  total_chapters: number
  completed_chapters: number
  total_characters: number
  total_worldview_entries: number
  last_activity: string
  creation_progress: number
}

/**
 * 系统统计信息
 */
export interface SystemStatistics {
  total_novels: number
  active_workflows: number
  total_users: number
  storage_used: number
  api_calls_today: number
}