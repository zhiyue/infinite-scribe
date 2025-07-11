import type { ApiError } from '@/types'

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
}

// 自定义错误类
export class AppError extends Error implements ApiError {
  code: string
  statusCode?: number
  details?: unknown

  constructor(code: string, message?: string, statusCode?: number, details?: unknown) {
    super(message || errorMessages[code as ErrorCode] || '未知错误')
    this.name = 'AppError'
    this.code = code
    this.statusCode = statusCode
    this.details = details
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

// 解析 API 响应错误
export function parseApiError(response: Response, data?: unknown): AppError {
  const errorCode = httpStatusToErrorCode[response.status] || ErrorCode.UNKNOWN_ERROR

  // 尝试从响应数据中获取错误信息
  if (data && typeof data === 'object' && 'error' in data) {
    const errorData = data.error as {
      code?: string
      message?: string
      details?: unknown
    }
    return new AppError(
      errorData.code || errorCode,
      errorData.message,
      response.status,
      errorData.details,
    )
  }

  return new AppError(errorCode, undefined, response.status)
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
  // 如果已经是 AppError，直接返回
  if (error instanceof AppError) {
    return error
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
    default:
      return error.message || '操作失败，请稍后重试'
  }
}
