/**
 * HTTP 客户端适配器实现
 * 提供抽象的 HTTP 接口，支持多种 HTTP 库（axios、fetch、mock 等）
 */

import axios, {
  type AxiosError,
  type AxiosInstance,
  type AxiosRequestConfig,
  type AxiosResponse,
  type InternalAxiosRequestConfig,
} from 'axios'
import type { IHttpClient } from './types'

/**
 * 拦截器配置接口
 */
interface InterceptorConfig {
  id: number
  type: 'request' | 'response'
}

/**
 * Axios HTTP 客户端适配器实现
 */
export class AxiosHttpClient implements IHttpClient {
  private readonly axiosInstance: AxiosInstance
  private readonly interceptors: InterceptorConfig[] = []

  constructor(baseConfig?: AxiosRequestConfig) {
    this.axiosInstance = axios.create({
      timeout: 10000, // 默认 10 秒超时
      headers: {
        'Content-Type': 'application/json',
      },
      ...baseConfig,
    })

    // 设置默认的错误处理
    this.setupDefaultErrorHandling()
  }

  /**
   * GET 请求
   */
  async get<T = any>(url: string, config?: AxiosRequestConfig): Promise<AxiosResponse<T>> {
    try {
      return await this.axiosInstance.get<T>(url, config)
    } catch (error) {
      throw this.handleError(error as AxiosError)
    }
  }

  /**
   * POST 请求
   */
  async post<T = any>(
    url: string,
    data?: any,
    config?: AxiosRequestConfig,
  ): Promise<AxiosResponse<T>> {
    try {
      return await this.axiosInstance.post<T>(url, data, config)
    } catch (error) {
      throw this.handleError(error as AxiosError)
    }
  }

  /**
   * PUT 请求
   */
  async put<T = any>(
    url: string,
    data?: any,
    config?: AxiosRequestConfig,
  ): Promise<AxiosResponse<T>> {
    try {
      return await this.axiosInstance.put<T>(url, data, config)
    } catch (error) {
      throw this.handleError(error as AxiosError)
    }
  }

  /**
   * PATCH 请求
   */
  async patch<T = any>(
    url: string,
    data?: any,
    config?: AxiosRequestConfig,
  ): Promise<AxiosResponse<T>> {
    try {
      return await this.axiosInstance.patch<T>(url, data, config)
    } catch (error) {
      throw this.handleError(error as AxiosError)
    }
  }

  /**
   * DELETE 请求
   */
  async delete<T = any>(url: string, config?: AxiosRequestConfig): Promise<AxiosResponse<T>> {
    try {
      return await this.axiosInstance.delete<T>(url, config)
    } catch (error) {
      throw this.handleError(error as AxiosError)
    }
  }

  /**
   * 设置默认请求头
   */
  setDefaultHeader(key: string, value: string): void {
    this.axiosInstance.defaults.headers.common[key] = value
  }

  /**
   * 移除默认请求头
   */
  removeDefaultHeader(key: string): void {
    delete this.axiosInstance.defaults.headers.common[key]
  }

  /**
   * 添加请求拦截器
   */
  addRequestInterceptor(
    onFulfilled?: (config: AxiosRequestConfig) => AxiosRequestConfig | Promise<AxiosRequestConfig>,
    onRejected?: (error: any) => any,
  ): number {
    const id = this.axiosInstance.interceptors.request.use(
      onFulfilled as (
        config: InternalAxiosRequestConfig,
      ) => InternalAxiosRequestConfig | Promise<InternalAxiosRequestConfig>,
      onRejected,
    )

    this.interceptors.push({ id, type: 'request' })
    return id
  }

  /**
   * 添加响应拦截器
   */
  addResponseInterceptor(
    onFulfilled?: (response: AxiosResponse) => AxiosResponse | Promise<AxiosResponse>,
    onRejected?: (error: any) => any,
  ): number {
    const id = this.axiosInstance.interceptors.response.use(onFulfilled, onRejected)

    this.interceptors.push({ id, type: 'response' })
    return id
  }

  /**
   * 移除拦截器
   */
  removeInterceptor(type: 'request' | 'response', id: number): void {
    if (type === 'request') {
      this.axiosInstance.interceptors.request.eject(id)
    } else {
      this.axiosInstance.interceptors.response.eject(id)
    }

    // 从记录中移除
    const index = this.interceptors.findIndex(
      (interceptor) => interceptor.id === id && interceptor.type === type,
    )
    if (index !== -1) {
      this.interceptors.splice(index, 1)
    }
  }

  /**
   * 获取 Axios 实例（用于高级配置）
   */
  getAxiosInstance(): AxiosInstance {
    return this.axiosInstance
  }

  /**
   * 设置基础 URL
   */
  setBaseURL(baseURL: string): void {
    this.axiosInstance.defaults.baseURL = baseURL
  }

  /**
   * 设置超时时间
   */
  setTimeout(timeout: number): void {
    this.axiosInstance.defaults.timeout = timeout
  }

  /**
   * 清除所有拦截器
   */
  clearAllInterceptors(): void {
    // 创建副本以避免在迭代过程中修改数组
    const interceptorsToRemove = [...this.interceptors]
    interceptorsToRemove.forEach(({ id, type }) => {
      this.removeInterceptor(type, id)
    })
  }

  /**
   * 设置默认的错误处理
   * @private
   */
  private setupDefaultErrorHandling(): void {
    // 这里可以添加通用的错误处理逻辑
    // 比如网络错误、超时处理等
  }

  /**
   * 统一错误处理
   * @private
   */
  private handleError(error: AxiosError): Error {
    // 保持原始错误结构，但可以添加额外的处理逻辑
    if (error.response) {
      // 服务器响应了错误状态码
      console.error(`HTTP Error ${error.response.status}:`, error.response.data)
    } else if (error.request) {
      // 请求已发送但没有收到响应
      console.error('Network Error:', error.message)
    } else {
      // 请求配置出错
      console.error('Request Setup Error:', error.message)
    }

    // 返回原始错误以保持兼容性
    return error
  }
}

/**
 * Fetch API HTTP 客户端适配器实现
 * 作为 axios 的轻量级替代方案
 */
export class FetchHttpClient implements IHttpClient {
  private defaultHeaders: Record<string, string> = {
    'Content-Type': 'application/json',
  }
  private baseURL = ''
  private timeout = 10000

  constructor(config?: { baseURL?: string; timeout?: number; headers?: Record<string, string> }) {
    if (config?.baseURL) {
      this.baseURL = config.baseURL
    }
    if (config?.timeout) {
      this.timeout = config.timeout
    }
    if (config?.headers) {
      this.defaultHeaders = { ...this.defaultHeaders, ...config.headers }
    }
  }

  async get<T = any>(url: string, config?: AxiosRequestConfig): Promise<AxiosResponse<T>> {
    return this.request<T>('GET', url, undefined, config)
  }

  async post<T = any>(
    url: string,
    data?: any,
    config?: AxiosRequestConfig,
  ): Promise<AxiosResponse<T>> {
    return this.request<T>('POST', url, data, config)
  }

  async put<T = any>(
    url: string,
    data?: any,
    config?: AxiosRequestConfig,
  ): Promise<AxiosResponse<T>> {
    return this.request<T>('PUT', url, data, config)
  }

  async patch<T = any>(
    url: string,
    data?: any,
    config?: AxiosRequestConfig,
  ): Promise<AxiosResponse<T>> {
    return this.request<T>('PATCH', url, data, config)
  }

  async delete<T = any>(url: string, config?: AxiosRequestConfig): Promise<AxiosResponse<T>> {
    return this.request<T>('DELETE', url, undefined, config)
  }

  setDefaultHeader(key: string, value: string): void {
    this.defaultHeaders[key] = value
  }

  removeDefaultHeader(key: string): void {
    delete this.defaultHeaders[key]
  }

  addRequestInterceptor(): number {
    console.warn('Request interceptors not supported in FetchHttpClient')
    return 0
  }

  addResponseInterceptor(): number {
    console.warn('Response interceptors not supported in FetchHttpClient')
    return 0
  }

  removeInterceptor(): void {
    console.warn('Interceptors not supported in FetchHttpClient')
  }

  setBaseURL(baseURL: string): void {
    this.baseURL = baseURL
  }

  setTimeout(timeout: number): void {
    this.timeout = timeout
  }

  clearAllInterceptors(): void {
    console.warn('Interceptors not supported in FetchHttpClient')
  }

  /**
   * 执行 HTTP 请求
   * @private
   */
  private async request<T>(
    method: string,
    url: string,
    data?: any,
    config?: AxiosRequestConfig,
  ): Promise<AxiosResponse<T>> {
    const fullUrl = this.buildUrl(url)
    const headers = { ...this.defaultHeaders, ...config?.headers }

    const requestConfig: RequestInit = {
      method,
      headers,
      ...config,
    }

    if (data) {
      requestConfig.body = typeof data === 'string' ? data : JSON.stringify(data)
    }

    try {
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), this.timeout)

      const response = await fetch(fullUrl, {
        ...requestConfig,
        signal: controller.signal,
      })

      clearTimeout(timeoutId)

      const responseData = await this.parseResponse<T>(response)

      // 构造类似 axios 的响应格式
      return {
        data: responseData,
        status: response.status,
        statusText: response.statusText,
        headers: this.parseHeaders(response.headers),
        config: config || {},
        request: {},
      } as AxiosResponse<T>
    } catch (error) {
      throw this.handleFetchError(error)
    }
  }

  /**
   * 构建完整 URL
   * @private
   */
  private buildUrl(url: string): string {
    if (url.startsWith('http://') || url.startsWith('https://')) {
      return url
    }

    return this.baseURL + (url.startsWith('/') ? url : `/${url}`)
  }

  /**
   * 解析响应数据
   * @private
   */
  private async parseResponse<T>(response: Response): Promise<T> {
    const contentType = response.headers.get('content-type')

    if (contentType && contentType.includes('application/json')) {
      return await response.json()
    }

    return (await response.text()) as unknown as T
  }

  /**
   * 解析响应头
   * @private
   */
  private parseHeaders(headers: Headers): Record<string, string> {
    const result: Record<string, string> = {}
    headers.forEach((value, key) => {
      result[key] = value
    })
    return result
  }

  /**
   * 处理 fetch 错误
   * @private
   */
  private handleFetchError(error: any): Error {
    if (error.name === 'AbortError') {
      const timeoutError = new Error('Request timeout')
      ;(timeoutError as any).code = 'ECONNABORTED'
      return timeoutError
    }

    return error
  }
}

/**
 * 模拟 HTTP 客户端实现
 * 用于测试环境
 */
export class MockHttpClient implements IHttpClient {
  private responses = new Map<string, any>()
  private defaultHeaders: Record<string, string> = {}
  private delay = 0

  constructor(config?: { delay?: number }) {
    if (config?.delay) {
      this.delay = config.delay
    }
  }

  async get<T = any>(url: string, config?: AxiosRequestConfig): Promise<AxiosResponse<T>> {
    return this.mockRequest<T>('GET', url, undefined, config)
  }

  async post<T = any>(
    url: string,
    data?: any,
    config?: AxiosRequestConfig,
  ): Promise<AxiosResponse<T>> {
    return this.mockRequest<T>('POST', url, data, config)
  }

  async put<T = any>(
    url: string,
    data?: any,
    config?: AxiosRequestConfig,
  ): Promise<AxiosResponse<T>> {
    return this.mockRequest<T>('PUT', url, data, config)
  }

  async patch<T = any>(
    url: string,
    data?: any,
    config?: AxiosRequestConfig,
  ): Promise<AxiosResponse<T>> {
    return this.mockRequest<T>('PATCH', url, data, config)
  }

  async delete<T = any>(url: string, config?: AxiosRequestConfig): Promise<AxiosResponse<T>> {
    return this.mockRequest<T>('DELETE', url, undefined, config)
  }

  setDefaultHeader(key: string, value: string): void {
    this.defaultHeaders[key] = value
  }

  removeDefaultHeader(key: string): void {
    delete this.defaultHeaders[key]
  }

  addRequestInterceptor(): number {
    return 0
  }

  addResponseInterceptor(): number {
    return 0
  }

  removeInterceptor(): void {
    // Mock implementation
  }

  setBaseURL(baseURL: string): void {
    // Mock implementation - not actually used in mock client
  }

  setTimeout(timeout: number): void {
    this.delay = timeout
  }

  clearAllInterceptors(): void {
    // Mock implementation
  }

  /**
   * 设置模拟响应
   */
  setMockResponse(method: string, url: string, response: any): void {
    const key = `${method.toUpperCase()} ${url}`
    this.responses.set(key, response)
  }

  /**
   * 清除所有模拟响应
   */
  clearMockResponses(): void {
    this.responses.clear()
  }

  /**
   * 设置响应延迟
   */
  setDelay(delay: number): void {
    this.delay = delay
  }

  /**
   * 执行模拟请求
   * @private
   */
  private async mockRequest<T>(
    method: string,
    url: string,
    data?: any,
    config?: AxiosRequestConfig,
  ): Promise<AxiosResponse<T>> {
    if (this.delay > 0) {
      await new Promise((resolve) => setTimeout(resolve, this.delay))
    }

    const key = `${method.toUpperCase()} ${url}`
    const mockResponse = this.responses.get(key)

    if (!mockResponse) {
      throw new Error(`No mock response configured for ${key}`)
    }

    // 如果配置的是错误响应
    if (mockResponse.error) {
      throw mockResponse.error
    }

    return {
      data: mockResponse.data || mockResponse,
      status: mockResponse.status || 200,
      statusText: mockResponse.statusText || 'OK',
      headers: mockResponse.headers || {},
      config: config || {},
      request: { method, url, data },
    } as AxiosResponse<T>
  }
}

/**
 * HTTP 客户端工厂函数
 */
export function createHttpClient(
  type: 'axios' | 'fetch' | 'mock' = 'axios',
  config?: any,
): IHttpClient {
  switch (type) {
    case 'axios':
      return new AxiosHttpClient(config)
    case 'fetch':
      return new FetchHttpClient(config)
    case 'mock':
      return new MockHttpClient(config)
    default:
      throw new Error(`Unsupported HTTP client type: ${type}`)
  }
}

/**
 * 自动检测并创建最佳的 HTTP 客户端
 */
export function createAutoHttpClient(config?: AxiosRequestConfig): IHttpClient {
  // 优先使用 axios（如果可用）
  try {
    return new AxiosHttpClient(config)
  } catch {
    // 降级到 fetch
    return new FetchHttpClient(config)
  }
}
