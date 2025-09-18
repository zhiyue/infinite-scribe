import type { ApiError } from '../types/auth'

// 错误类型枚举
export enum ErrorCode {
  // 客户端错误
  BAD_REQUEST = 'BAD_REQUEST',
  UNAUTHORIZED = 'UNAUTHORIZED',
  FORBIDDEN = 'FORBIDDEN',
  NOT_FOUND = 'NOT_FOUND',
  VALIDATION_ERROR = 'VALIDATION_ERROR',

  // 服务端错误
  INTERNAL_SERVER_ERROR = 'INTERNAL_SERVER_ERROR',
  SERVICE_UNAVAILABLE = 'SERVICE_UNAVAILABLE',
  GATEWAY_TIMEOUT = 'GATEWAY_TIMEOUT',

  // 网络错误
  NETWORK_ERROR = 'NETWORK_ERROR',
  TIMEOUT_ERROR = 'TIMEOUT_ERROR',

  // 业务错误
  BUSINESS_ERROR = 'BUSINESS_ERROR',
  UNKNOWN_ERROR = 'UNKNOWN_ERROR',

  // Genesis 特定错误
  STAGE_CONFIG_INCOMPLETE = 'STAGE_CONFIG_INCOMPLETE',
  STAGE_VALIDATION_ERROR = 'STAGE_VALIDATION_ERROR',
}

// 错误消息映射
const errorMessages: Record<ErrorCode, string> = {
  [ErrorCode.BAD_REQUEST]: '请求参数错误',
  [ErrorCode.UNAUTHORIZED]: '未登录或登录已过期',
  [ErrorCode.FORBIDDEN]: '没有权限访问该资源',
  [ErrorCode.NOT_FOUND]: '请求的资源不存在',
  [ErrorCode.VALIDATION_ERROR]: '数据验证失败',
  [ErrorCode.INTERNAL_SERVER_ERROR]: '服务器内部错误',
  [ErrorCode.SERVICE_UNAVAILABLE]: '服务暂时不可用',
  [ErrorCode.GATEWAY_TIMEOUT]: '网关超时',
  [ErrorCode.NETWORK_ERROR]: '网络连接失败',
  [ErrorCode.TIMEOUT_ERROR]: '请求超时',
  [ErrorCode.BUSINESS_ERROR]: '业务处理失败',
  [ErrorCode.UNKNOWN_ERROR]: '未知错误',
  [ErrorCode.STAGE_CONFIG_INCOMPLETE]: '当前阶段配置不完整',
  [ErrorCode.STAGE_VALIDATION_ERROR]: '阶段切换验证失败',
}

// Genesis 错误接口
export interface GenesisErrorDetail {
  type: string
  message: string
  user_message: string
  action_required: string
  missing_fields?: string[]
}

// 自定义错误类
export class AppError extends Error implements ApiError {
  detail: string
  status_code?: number
  retry_after?: number
  code: string
  statusCode?: number
  details?: unknown
  // Genesis 特定错误信息
  genesisError?: GenesisErrorDetail

  constructor(code: string, message?: string, statusCode?: number, details?: unknown, genesisError?: GenesisErrorDetail) {
    super(message || errorMessages[code as ErrorCode] || '未知错误')
    this.name = 'AppError'
    this.code = code
    this.detail = message || errorMessages[code as ErrorCode] || '未知错误'
    this.statusCode = statusCode
    this.status_code = statusCode
    this.details = details
    this.genesisError = genesisError
  }

  toString(): string {
    return `${this.name}(${this.code}): ${this.message}`
  }

  // 确保 valueOf 也返回有意义的值
  valueOf(): string {
    return this.toString()
  }

  // 重写 Symbol.toStringTag
  get [Symbol.toStringTag](): string {
    return 'AppError'
  }

  toJSON() {
    return {
      name: this.name,
      code: this.code,
      message: this.message,
      detail: this.detail,
      statusCode: this.statusCode,
      genesisError: this.genesisError,
      details: this.details
    }
  }
}

// HTTP 状态码到错误码的映射
const httpStatusToErrorCode: Record<number, ErrorCode> = {
  400: ErrorCode.BAD_REQUEST,
  401: ErrorCode.UNAUTHORIZED,
  403: ErrorCode.FORBIDDEN,
  404: ErrorCode.NOT_FOUND,
  422: ErrorCode.VALIDATION_ERROR,
  500: ErrorCode.INTERNAL_SERVER_ERROR,
  502: ErrorCode.SERVICE_UNAVAILABLE,
  503: ErrorCode.SERVICE_UNAVAILABLE,
  504: ErrorCode.GATEWAY_TIMEOUT,
}

// 缓存正则表达式以提升性能
const MISSING_FIELDS_REGEX = /Required fields are missing - (.+?)\./

// 解析 API 响应错误
export function parseApiError(response: Response, data?: unknown): AppError {
  const isDev = import.meta.env.DEV
  if (isDev) {
    console.log('[parseApiError] Parsing error response:', response.status, data)
  }

  const defaultErrorCode = httpStatusToErrorCode[response.status] || ErrorCode.UNKNOWN_ERROR

  // 尝试从响应数据中获取错误信息
  if (data && typeof data === 'object') {
    // 检查是否是 Genesis 特定的结构化错误 (HTTPException with detail object)
    if ('detail' in data && typeof data.detail === 'object' && data.detail !== null) {
      const detail = data.detail as any

      // 检查是否是 Genesis 错误格式
      if ('type' in detail && 'user_message' in detail && 'action_required' in detail) {
        // 快速解析缺失字段（使用缓存的正则表达式）
        let missing_fields: string[] = []
        if (detail.message && typeof detail.message === 'string') {
          const match = detail.message.match(MISSING_FIELDS_REGEX)
          if (match) {
            missing_fields = match[1].split(', ').map(field => field.trim())
          }
        }

        const genesisError: GenesisErrorDetail = {
          type: detail.type,
          message: detail.message || '',
          user_message: detail.user_message,
          action_required: detail.action_required,
          missing_fields: detail.missing_fields || missing_fields
        }

        // 根据错误类型映射到适当的错误码
        const errorCode = detail.type === 'stage_config_incomplete'
          ? ErrorCode.STAGE_CONFIG_INCOMPLETE
          : detail.type === 'stage_validation_error'
          ? ErrorCode.STAGE_VALIDATION_ERROR
          : defaultErrorCode

        return new AppError(
          errorCode,
          genesisError.user_message, // 使用用户友好的消息
          response.status,
          detail,
          genesisError
        )
      }

      // 检查传统的 detail 字符串格式
      if (typeof data.detail === 'string') {
        return new AppError(defaultErrorCode, data.detail, response.status)
      }
    }

    // 检查传统的 error 字段
    if ('error' in data) {
      const errorData = data.error as {
        code?: string
        message?: string
        details?: unknown
      }
      return new AppError(
        errorData.code || defaultErrorCode,
        errorData.message,
        response.status,
        errorData.details,
      )
    }
  }

  return new AppError(defaultErrorCode, undefined, response.status)
}

// 处理网络错误
export function handleNetworkError(error: unknown): AppError {
  if (error instanceof Error) {
    if (error.name === 'AbortError') {
      return new AppError(ErrorCode.TIMEOUT_ERROR, '请求已取消')
    }

    if (error.name === 'TypeError' && error.message.includes('fetch')) {
      return new AppError(ErrorCode.NETWORK_ERROR, '网络连接失败，请检查网络设置')
    }

    return new AppError(ErrorCode.UNKNOWN_ERROR, error.message)
  }

  return new AppError(ErrorCode.UNKNOWN_ERROR, String(error))
}

// 统一错误处理函数
export function handleError(error: unknown): AppError {
  const isDev = import.meta.env.DEV
  if (isDev) {
    console.log('[handleError] Processing error:', error)
  }

  // 如果已经是 AppError，直接返回
  if (error instanceof AppError) {
    return error
  }

  // 检查是否是 Axios 错误（有 response 属性的）
  if (error && typeof error === 'object' && 'response' in error) {
    const axiosError = error as any

    if (axiosError.response) {
      // 创建一个假的 Response 对象来兼容 parseApiError
      const fakeResponse = {
        status: axiosError.response.status,
        statusText: axiosError.response.statusText || 'Unknown'
      } as Response

      return parseApiError(fakeResponse, axiosError.response.data)
    }
  }

  // 处理其他类型的错误
  if (error instanceof Error) {
    return handleNetworkError(error)
  }

  // 处理未知错误
  return new AppError(ErrorCode.UNKNOWN_ERROR, String(error))
}

// 错误日志记录
export function logError(error: AppError, context?: unknown): void {
  console.error('应用错误:', {
    code: error.code,
    message: error.message,
    statusCode: error.statusCode,
    details: error.details,
    context,
    timestamp: new Date().toISOString(),
  })
}

// 用户友好的错误消息
export function getUserFriendlyMessage(error: AppError): string {
  // 如果有 Genesis 特定的错误，优先使用其用户友好消息
  if (error.genesisError?.user_message) {
    return error.genesisError.user_message
  }

  // 对于某些错误，返回更友好的消息
  switch (error.code as ErrorCode) {
    case ErrorCode.NETWORK_ERROR:
      return '网络连接失败，请检查您的网络设置'
    case ErrorCode.TIMEOUT_ERROR:
      return '请求超时，请稍后重试'
    case ErrorCode.UNAUTHORIZED:
      return '您需要登录才能访问此功能'
    case ErrorCode.SERVICE_UNAVAILABLE:
      return '服务暂时不可用，请稍后再试'
    case ErrorCode.STAGE_CONFIG_INCOMPLETE:
      return error.message || '当前阶段配置不完整，请先完成必填字段的配置'
    case ErrorCode.STAGE_VALIDATION_ERROR:
      return error.message || '阶段切换验证失败，请检查当前阶段状态'
    default:
      return error.message || '操作失败，请稍后重试'
  }
}

// 获取错误的操作建议
export function getErrorActionSuggestion(error: AppError): string | null {
  if (error.genesisError?.action_required) {
    switch (error.genesisError.action_required) {
      case 'complete_current_stage_config':
        return '请前往阶段配置页面完成必填字段的设置'
      case 'check_stage_status':
        return '请检查当前阶段的状态和配置'
      default:
        return null
    }
  }
  return null
}

// 检查是否是需要用户操作的错误
export function isUserActionRequired(error: AppError): boolean {
  return !!(error.genesisError?.action_required)
}
