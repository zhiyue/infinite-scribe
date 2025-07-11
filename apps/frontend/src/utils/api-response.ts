/**
 * API 响应格式统一化工具
 *
 * 处理后端返回的不同格式，确保前端获得一致的响应结构
 */

import type { ApiError } from '../types/auth'

// 通用成功响应接口
export interface ApiSuccessResponse<T = any> {
  success: true
  data: T
  message?: string
}

// 通用错误响应接口
export interface ApiErrorResponse {
  success: false
  error: string
  status_code?: number
  details?: Record<string, any>
}

// 统一的 API 响应类型
export type ApiResponse<T = any> = ApiSuccessResponse<T> | ApiErrorResponse

/**
 * 检查响应是否已经包含 success 字段
 */
function hasSuccessField(response: any): boolean {
  return response && typeof response === 'object' && 'success' in response
}

/**
 * 包装 API 响应为统一格式
 *
 * @param response - 原始响应数据
 * @param defaultMessage - 默认成功消息
 * @returns 统一格式的响应
 */
export function wrapApiResponse<T>(response: any, defaultMessage?: string): ApiSuccessResponse<T> {
  // 如果响应已经有 success 字段且为 true，直接返回
  if (hasSuccessField(response) && response.success === true) {
    // 对于 login/register 等响应，数据在响应本身
    // 对于其他响应，可能需要提取 data 字段
    const data = response.data || response
    return {
      success: true,
      data: data as T,
      message: response.message || defaultMessage,
    }
  }

  // 对于没有 success 字段的响应（如 /me 端点），包装为统一格式
  return {
    success: true,
    data: response as T,
    message: defaultMessage,
  }
}

/**
 * 处理 API 错误为统一格式
 *
 * @param error - 原始错误
 * @returns 统一格式的错误响应
 */
export function wrapApiError(error: ApiError | any): ApiErrorResponse {
  // 如果已经是 ApiError 格式
  if (error.detail) {
    return {
      success: false,
      error: error.detail,
      status_code: error.status_code,
      details: error.response?.data?.details,
    }
  }

  // 如果是标准错误响应格式
  if (hasSuccessField(error) && error.success === false) {
    return {
      success: false,
      error: error.error || error.message || 'Unknown error',
      status_code: error.status_code,
      details: error.details,
    }
  }

  // 其他错误格式
  return {
    success: false,
    error: error.message || error.error || 'An unexpected error occurred',
    status_code: error.status_code || 0,
  }
}

/**
 * 解析 API 响应数据
 *
 * 用于从统一响应格式中提取实际数据
 */
export function unwrapApiResponse<T>(response: ApiSuccessResponse<T>): T {
  return response.data
}

/**
 * 类型守卫：检查是否为成功响应
 */
export function isApiSuccess<T>(response: ApiResponse<T>): response is ApiSuccessResponse<T> {
  return response.success === true
}

/**
 * 类型守卫：检查是否为错误响应
 */
export function isApiError(response: ApiResponse): response is ApiErrorResponse {
  return response.success === false
}
