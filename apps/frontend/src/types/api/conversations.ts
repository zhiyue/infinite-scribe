/**
 * Conversation API 类型定义
 * 对话管理相关的所有类型定义
 */

// ===== 基础枚举类型 =====

/**
 * 对话范围类型
 */
export type ScopeType = 'GENESIS' | 'CHAPTER' | 'REVIEW' | 'PLANNING' | 'WORLDBUILDING'

/**
 * 会话状态
 */
export type SessionStatus =
  | 'ACTIVE'
  | 'PROCESSING'
  | 'COMPLETED'
  | 'FAILED'
  | 'ABANDONED'
  | 'PAUSED'

/**
 * 对话角色
 */
export type DialogueRole = 'user' | 'assistant' | 'system' | 'tool'

// ===== Session 相关类型 =====

/**
 * 会话列表查询参数 - GET /api/v1/conversations/sessions
 */
export interface SessionListParams {
  /** 范围类型 */
  scope_type: ScopeType
  /** 范围ID */
  scope_id: string
  /** 状态过滤 */
  status?: SessionStatus
  /** 限制数量（1-200，默认50） */
  limit?: number
  /** 偏移量（默认0） */
  offset?: number
}

/**
 * 创建会话请求 - POST /api/v1/conversations/sessions
 */
export interface CreateSessionRequest {
  /** 会话范围类型 */
  scope_type: ScopeType
  /** 范围ID（如 novel_id） */
  scope_id: string
  /** 初始阶段 */
  stage?: string
  /** 初始状态 */
  initial_state?: Record<string, any>
}

/**
 * 更新会话请求 - PATCH /api/v1/conversations/sessions/{session_id}
 */
export interface UpdateSessionRequest {
  /** 会话状态 */
  status?: SessionStatus
  /** 当前阶段 */
  stage?: string
  /** 状态数据 */
  state?: Record<string, any>
}

/**
 * 会话响应
 */
export interface SessionResponse {
  /** 会话ID */
  id: string
  /** 范围类型 */
  scope_type: ScopeType
  /** 范围ID */
  scope_id: string
  /** 会话状态 */
  status: SessionStatus
  /** 当前阶段 */
  stage?: string
  /** 状态数据 */
  state: Record<string, any>
  /** 版本号（用于乐观锁） */
  version: number
  /** 创建时间 */
  created_at: string
  /** 更新时间 */
  updated_at: string
  /** 关联的小说ID */
  novel_id?: string
}

// ===== Round 相关类型 =====

/**
 * 创建轮次请求 - POST /api/v1/conversations/sessions/{session_id}/rounds
 */
export interface RoundCreateRequest {
  /** 角色 */
  role: DialogueRole
  /** 输入内容 */
  input: Record<string, any>
  /** 模型名称 */
  model?: string
  /** 关联ID */
  correlation_id?: string
}

/**
 * 轮次响应
 */
export interface RoundResponse {
  /** 会话ID */
  session_id: string
  /** 轮次路径（如 "1", "2.1", "2.1.1"） */
  round_path: string
  /** 角色 */
  role: DialogueRole
  /** 输入内容 */
  input: Record<string, any>
  /** 输出内容 */
  output?: Record<string, any>
  /** 模型名称 */
  model?: string
  /** 关联ID */
  correlation_id?: string
  /** 创建时间 */
  created_at: string
}

/**
 * 轮次查询参数 - GET /api/v1/conversations/sessions/{session_id}/rounds
 */
export interface RoundQueryParams {
  /** 游标（round_path） */
  after?: string
  /** 限制数量（1-200，默认50） */
  limit?: number
  /** 排序方向 */
  order?: 'asc' | 'desc'
  /** 角色过滤 */
  role?: DialogueRole
}

// ===== Command 相关类型 =====

/**
 * 命令请求 - POST /api/v1/conversations/sessions/{session_id}/commands
 */
export interface CommandRequest {
  /** 命令类型 */
  type: string
  /** 命令载荷 */
  payload?: Record<string, any>
}

/**
 * 命令接受响应
 */
export interface CommandAcceptedResponse {
  /** 是否接受 */
  accepted: boolean
  /** 命令ID */
  command_id: string
}

/**
 * 命令状态响应 - GET /api/v1/conversations/sessions/{session_id}/commands/{cmd_id}
 */
export interface CommandStatusResponse {
  /** 命令ID */
  command_id: string
  /** 命令类型 */
  type: string
  /** 命令状态 */
  status: string
  /** 提交时间 */
  submitted_at: string
  /** 关联ID */
  correlation_id: string
}

// ===== Stage 相关类型 =====

/**
 * 设置阶段请求 - PUT /api/v1/conversations/sessions/{session_id}/stage
 */
export interface SetStageRequest {
  /** 阶段名称 */
  stage: string
}

/**
 * 阶段响应
 */
export interface StageResponse {
  /** 当前阶段 */
  stage: string
  /** 更新时间 */
  updated_at: string
}

// ===== Content 相关类型 =====

/**
 * 内容响应 - GET /api/v1/conversations/sessions/{session_id}/content
 */
export interface ContentResponse {
  /** 聚合状态 */
  state: Record<string, any>
  /** 元数据 */
  meta: {
    /** 更新时间 */
    updated_at: string
  }
}

/**
 * 内容搜索请求 - POST /api/v1/conversations/sessions/{session_id}/content/search
 */
export interface ContentSearchRequest {
  /** 搜索查询 */
  query?: string
  /** 阶段过滤 */
  stage?: string
  /** 类型过滤 */
  type?: string
  /** 页码 */
  page?: number
  /** 每页数量 */
  limit?: number
}

/**
 * 内容搜索结果项
 */
export interface ContentSearchItem {
  /** 项目ID */
  id: string
  /** 内容类型 */
  type: string
  /** 阶段 */
  stage: string
  /** 内容 */
  content: Record<string, any>
  /** 高亮片段 */
  highlight?: string
  /** 相关性得分 */
  score?: number
}

// ===== Quality 相关类型 =====

/**
 * 质量评分响应 - GET /api/v1/conversations/sessions/{session_id}/quality
 */
export interface QualityScoreResponse {
  /** 质量得分 */
  score: number
  /** 更新时间 */
  updated_at: string
}

// ===== Version 相关类型 =====

/**
 * 创建版本请求 - POST /api/v1/conversations/sessions/{session_id}/versions
 */
export interface VersionCreateRequest {
  /** 基础版本号 */
  base_version: number
  /** 版本标签 */
  label: string
  /** 版本描述 */
  description?: string
}

/**
 * 合并版本请求 - PUT /api/v1/conversations/sessions/{session_id}/versions/merge
 */
export interface VersionMergeRequest {
  /** 源版本 */
  source: string
  /** 目标版本 */
  target: string
  /** 合并策略 */
  strategy?: string
}

/**
 * 版本信息
 */
export interface VersionInfo {
  /** 版本号 */
  version: number
  /** 版本标签 */
  label: string
  /** 版本描述 */
  description?: string
  /** 创建时间 */
  created_at: string
  /** 创建者 */
  created_by: string
}

// ===== 消息别名类型 =====

/**
 * 消息请求（轮次创建的别名）
 * POST /api/v1/conversations/sessions/{session_id}/messages
 */
export interface MessageRequest extends Omit<RoundCreateRequest, 'role'> {
  /** 角色默认为 'user' */
  role?: DialogueRole
}

// ===== 通用请求头类型 =====

/**
 * 对话API请求头
 */
export interface ConversationHeaders {
  /** 关联ID（用于请求追踪） */
  'X-Correlation-Id'?: string
  /** 幂等键（用于POST请求） */
  'Idempotency-Key'?: string
  /** 版本检查（用于乐观并发控制） */
  'If-Match'?: string
}
