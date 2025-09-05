/**
 * API 响应格式统一化工具
 *
 * 处理后端返回的不同格式，确保前端获得一致的响应结构
 */

// 通用成功响应接口
export interface ApiSuccessResponse<T = unknown> {
  success: true
  data: T
  message?: string
}

// 通用错误响应接口
export interface ApiErrorResponse {
  success: false
  error: string
  status_code?: number
  details?: Record<string, unknown>
}

// 统一的 API 响应类型
export type ApiResponse<T = unknown> = ApiSuccessResponse<T> | ApiErrorResponse

/**
 * 检查响应是否已经包含 success 字段
 */
function hasSuccessField(response: unknown): response is { success: boolean } {
  return response !== null && typeof response === 'object' && 'success' in response
}

/**
 * 包装 API 响应为统一格式
 *
 * @param response - 原始响应数据
 * @param defaultMessage - 默认成功消息
 * @returns 统一格式的响应
 */
export function wrapApiResponse<T>(
  response: unknown,
  defaultMessage?: string,
): ApiSuccessResponse<T> {
  // 如果响应已经有 success 字段且为 true，直接返回
  if (hasSuccessField(response) && (response as { success: boolean }).success === true) {
    const responseObj = response as { success: true; data?: T; message?: string }
    // 对于 login/register 等响应，数据在响应本身
    // 对于其他响应，可能需要提取 data 字段
    const data = responseObj.data || (response as T)
    return {
      success: true,
      data,
      message: responseObj.message || defaultMessage,
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
export function wrapApiError(error: unknown): ApiErrorResponse {
  // 如果已经是 ApiError 格式
  if (error && typeof error === 'object' && 'detail' in error) {
    const apiError = error as {
      detail: string
      status_code?: number
      response?: { data?: { details?: Record<string, unknown> } }
    }
    return {
      success: false,
      error: apiError.detail,
      status_code: apiError.status_code,
      details: apiError.response?.data?.details,
    }
  }

  // 如果是标准错误响应格式
  if (hasSuccessField(error) && (error as { success: boolean }).success === false) {
    const errorObj = error as {
      success: false
      error?: string
      message?: string
      status_code?: number
      details?: Record<string, unknown>
    }
    return {
      success: false,
      error: errorObj.error || errorObj.message || 'Unknown error',
      status_code: errorObj.status_code,
      details: errorObj.details,
    }
  }

  // 其他错误格式
  const errorObj = error as { message?: string; error?: string; status_code?: number }
  return {
    success: false,
    error: errorObj.message || errorObj.error || 'An unexpected error occurred',
    status_code: errorObj.status_code || 0,
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
