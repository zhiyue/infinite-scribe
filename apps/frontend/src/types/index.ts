// 全局类型定义

// API 响应基础类型
export interface ApiResponse<T = any> {
  success: boolean
  data?: T
  error?: {
    code: string
    message: string
    details?: any
  }
  timestamp?: string
}

// 分页相关类型
export interface PaginationParams {
  page: number
  pageSize: number
  total?: number
}

export interface PaginatedResponse<T> {
  items: T[]
  pagination: {
    page: number
    pageSize: number
    total: number
    totalPages: number
  }
}

// 项目相关类型
export interface Project {
  id: string
  title: string
  description: string
  status: 'drafting' | 'reviewing' | 'completed'
  wordCount: number
  chapterCount: number
  lastUpdated: string
  createdAt: string
  author?: string
  tags?: string[]
  coverImage?: string
}

// 章节相关类型
export interface Chapter {
  id: string
  projectId: string
  title: string
  content: string
  order: number
  wordCount: number
  status: 'draft' | 'published'
  createdAt: string
  updatedAt: string
}

// 用户相关类型
export interface User {
  id: string
  username: string
  email: string
  avatar?: string
  role: 'user' | 'admin'
  createdAt: string
  lastLogin?: string
}

// 健康检查相关类型
export interface HealthCheckResponse {
  status: 'healthy' | 'unhealthy'
  timestamp: string
  services?: {
    database?: string
    redis?: string
    kafka?: string
  }
}

// 统计相关类型
export interface Statistics {
  totalProjects: number
  totalWords: number
  totalChapters: number
  recentActivity: ActivityItem[]
}

export interface ActivityItem {
  id: string
  type: 'project_created' | 'chapter_updated' | 'project_completed'
  projectId: string
  projectTitle: string
  timestamp: string
  description?: string
}

// 设置相关类型
export interface UserSettings {
  theme: 'light' | 'dark' | 'system'
  language: 'zh-CN' | 'en-US'
  notifications: {
    email: boolean
    browser: boolean
    updates: boolean
  }
  editor: {
    fontSize: number
    fontFamily: string
    autoSave: boolean
    autoSaveInterval: number // 秒
  }
}

// 表单相关类型
export interface CreateProjectForm {
  title: string
  description: string
  tags?: string[]
  coverImage?: File
}

export interface UpdateProjectForm extends Partial<CreateProjectForm> {
  status?: Project['status']
}

// 错误类型
export interface ApiError extends Error {
  code: string
  statusCode?: number
  details?: any
}