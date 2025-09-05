/**
 * API 请求和响应类型定义
 * 用于前后端 API 通信
 */

import { GenesisMode } from '../enums'
import type { Chapter, GenesisSession, Novel, WorkflowRun } from '../models/entities'

/**
 * 统一API响应格式 - 匹配后端 ApiResponse<T>
 */
export interface ApiResponse<T = unknown> {
  /** 响应状态码: 0=成功, 非0=错误 */
  code: number
  /** 响应消息 */
  msg: string
  /** 响应数据 */
  data?: T | null
}

/**
 * 分页信息 - 匹配后端 PaginationInfo
 */
export interface PaginationInfo {
  /** 当前页码 */
  page: number
  /** 每页大小 */
  page_size: number
  /** 总记录数 */
  total: number
  /** 总页数 */
  total_pages: number
}

/**
 * 分页数据响应 - 匹配后端 PaginatedResponse<T>
 */
export interface PaginatedResponse<T> {
  /** 数据项目列表 */
  items: T[]
  /** 分页信息 */
  pagination: PaginationInfo
}

/**
 * 统一分页API响应格式 - 匹配后端 PaginatedApiResponse<T>
 */
export interface PaginatedApiResponse<T> extends ApiResponse<PaginatedResponse<T>> {}

/**
 * 分页查询参数
 */
export interface PaginationParams {
  page?: number
  pageSize?: number
}

// ===== 小说相关 API =====

/**
 * 创建小说请求 - POST /api/v1/novels
 */
export interface CreateNovelRequest {
  title: string
  description: string
  tags?: string[]
  coverImage?: string
  genre?: string
  language?: string
}

/**
 * 更新小说请求 - PUT /api/v1/novels/{id}
 */
export interface UpdateNovelRequest {
  title?: string
  description?: string
  status?: Novel['status']
  tags?: string[]
  coverImage?: string
  genre?: string
  language?: string
}

/**
 * 小说列表查询参数 - GET /api/v1/novels
 * 使用camelCase风格，后端会通过alias映射到snake_case
 */
export interface NovelQueryParams {
  page?: number
  pageSize?: number
  /** 状态过滤 - 对应后端 status_filter */
  status?: Novel['status']
  /** 搜索关键词 - 在title和theme中搜索 */
  search?: string
  /** 排序字段 */
  sortBy?: 'created_at' | 'updated_at' | 'title' | 'target_chapters'
  /** 排序方向 */
  sortOrder?: 'asc' | 'desc'
}

// 小说列表响应现在使用 PaginatedApiResponse<Novel> 格式

// ===== 章节相关 API =====

// 章节列表响应现在使用 ApiResponse<Chapter[]> 格式

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

// 角色列表响应现在使用 ApiResponse<Character[]> 格式

/**
 * 创建角色请求
 */
export interface CreateCharacterRequest {
  novel_id: string
  name: string
  role?: 'protagonist' | 'antagonist' | 'supporting' | 'minor'
  description?: string
  background_story?: string
  personality_traits?: string[]
  goals?: string[]
  age?: number
  gender?: string
  appearance?: string
  personality?: string
  background?: string
  relationships?: string[]
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
export interface UpdateWorldviewEntryRequest
  extends Omit<CreateWorldviewEntryRequest, 'novel_id'> {}

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

// 小说统计信息响应现在使用 ApiResponse<NovelStats> 格式

/**
 * 小说统计信息
 */
export interface NovelStats {
  totalWords: number
  totalChapters: number
  averageChapterLength: number
  lastUpdated: string
  readingTime: number // 预计阅读时间（分钟）
  completionRate: number // 完成度百分比
  dailyProgress?: {
    date: string
    wordsAdded: number
  }[]
  weeklyProgress?: {
    week: string
    wordsAdded: number
    chaptersAdded: number
  }[]
  monthlyProgress?: {
    month: string
    wordsAdded: number
    chaptersAdded: number
  }[]
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
