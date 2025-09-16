import { API_BASE_URL } from '@/config/api'
import { parseApiError, handleNetworkError, logError } from '@/utils/errorHandler'
import type { ApiResponse } from '@/types'
import { authService } from './auth'

// API 请求配置接口
interface RequestConfig extends RequestInit {
  timeout?: number
  retries?: number
  retryDelay?: number
}

// API请求基础配置
class ApiService {
  private baseURL: string
  private defaultTimeout = 30000 // 30秒
  private requestInterceptors: ((config: RequestConfig) => RequestConfig)[] = []
  private responseInterceptors: ((response: Response) => Response)[] = []

  constructor(baseURL: string = API_BASE_URL) {
    this.baseURL = baseURL

    // 添加认证拦截器
    this.addRequestInterceptor((config) => {
      const token = authService.getAccessToken()
      if (token) {
        config.headers = {
          ...config.headers,
          Authorization: `Bearer ${token}`,
        }
      }
      return config
    })
  }

  // 添加请求拦截器
  addRequestInterceptor(interceptor: (config: RequestConfig) => RequestConfig) {
    this.requestInterceptors.push(interceptor)
  }

  // 添加响应拦截器
  addResponseInterceptor(interceptor: (response: Response) => Response) {
    this.responseInterceptors.push(interceptor)
  }

  private async request<T>(endpoint: string, options: RequestConfig = {}): Promise<T> {
    // 先复制一份配置
    let config = { ...options }

    // 先应用请求拦截器（例如附加 Authorization 头）
    for (const interceptor of this.requestInterceptors) {
      config = interceptor(config)
    }

    // 再从拦截后的配置里解构参数，确保拦截器注入的 headers 不会丢失
    const {
      timeout = this.defaultTimeout,
      retries = 0,
      retryDelay = 1000,
      ...fetchOptions
    } = config

    const url = `${this.baseURL}${endpoint}`

    // 创建 AbortController 用于超时控制
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), timeout)

    try {
      let response = await fetch(url, {
        ...fetchOptions,
        signal: controller.signal,
        headers: {
          'Content-Type': 'application/json',
          ...fetchOptions.headers,
        },
      })

      // 应用响应拦截器
      for (const interceptor of this.responseInterceptors) {
        response = interceptor(response)
      }

      clearTimeout(timeoutId)

      // 尝试解析响应体
      let data: unknown
      const contentType = response.headers.get('content-type')
      if (contentType && contentType.includes('application/json')) {
        data = await response.json()
      } else {
        data = await response.text()
      }

      // 处理错误响应
      if (!response.ok) {
        const error = parseApiError(response, data)
        logError(error, { endpoint, method: fetchOptions.method })
        throw error
      }

      // 如果响应是标准的 API 响应格式
      if (data && typeof data === 'object' && 'success' in data) {
        const apiResponse = data as ApiResponse<T>
        if (!apiResponse.success && apiResponse.error) {
          const error = parseApiError(response, apiResponse)
          logError(error, { endpoint, method: fetchOptions.method })
          throw error
        }
        return apiResponse.data as T
      }

      // 直接返回数据
      return data as T
    } catch (error: unknown) {
      clearTimeout(timeoutId)

      // 处理网络错误
      if (error instanceof Error && (error.name === 'AbortError' || error.name === 'TypeError')) {
        const appError = handleNetworkError(error)
        logError(appError, { endpoint, method: fetchOptions.method })

        // 重试逻辑
        if (retries > 0 && !error.name.includes('Abort')) {
          await new Promise((resolve) => setTimeout(resolve, retryDelay))
          return this.request<T>(endpoint, { ...options, retries: retries - 1 })
        }

        throw appError
      }

      // 重新抛出应用错误
      throw error
    }
  }

  async get<T>(endpoint: string, config?: Omit<RequestConfig, 'method' | 'body'>): Promise<T> {
    return this.request<T>(endpoint, { ...config, method: 'GET' })
  }

  async post<T>(
    endpoint: string,
    data?: unknown,
    config?: Omit<RequestConfig, 'method' | 'body'>,
  ): Promise<T> {
    return this.request<T>(endpoint, {
      ...config,
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    })
  }

  async put<T>(
    endpoint: string,
    data?: unknown,
    config?: Omit<RequestConfig, 'method' | 'body'>,
  ): Promise<T> {
    return this.request<T>(endpoint, {
      ...config,
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined,
    })
  }

  async delete<T>(endpoint: string, config?: Omit<RequestConfig, 'method' | 'body'>): Promise<T> {
    return this.request<T>(endpoint, { ...config, method: 'DELETE' })
  }
}

export const apiService = new ApiService()
