/**
 * 认证API服务
 * 使用认证服务的HTTP客户端，确保自动包含认证头
 */

import { authService } from './auth'
import type { IHttpClient } from './auth/types'
import type { ApiResponse } from '@/types'
import { API_BASE_URL } from '@/config/api'

/**
 * 认证API服务类
 * 使用认证服务内部的HTTP客户端，确保所有请求都包含正确的认证头
 */
class AuthenticatedApiService {
  private httpClient: IHttpClient

  constructor() {
    // 从认证服务获取已配置认证拦截器的HTTP客户端
    this.httpClient = authService.getHttpClient()
  }

  /**
   * GET 请求
   */
  async get<T>(endpoint: string): Promise<T> {
    const fullUrl = this.buildUrl(endpoint)
    const response = await this.httpClient.get<T>(fullUrl)
    return this.extractData(response)
  }

  /**
   * POST 请求
   */
  async post<T>(endpoint: string, data?: unknown): Promise<T> {
    const fullUrl = this.buildUrl(endpoint)
    const response = await this.httpClient.post<T>(fullUrl, data)
    return this.extractData(response)
  }

  /**
   * PUT 请求
   */
  async put<T>(endpoint: string, data?: unknown): Promise<T> {
    const fullUrl = this.buildUrl(endpoint)
    const response = await this.httpClient.put<T>(fullUrl, data)
    return this.extractData(response)
  }

  /**
   * DELETE 请求
   */
  async delete<T>(endpoint: string): Promise<T> {
    const fullUrl = this.buildUrl(endpoint)
    const response = await this.httpClient.delete<T>(fullUrl)
    return this.extractData(response)
  }

  /**
   * 构建完整URL
   * @private
   */
  private buildUrl(endpoint: string): string {
    if (endpoint.startsWith('http://') || endpoint.startsWith('https://')) {
      return endpoint
    }
    
    // 确保endpoint以/开头
    const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`
    return `${API_BASE_URL}${cleanEndpoint}`
  }

  /**
   * 从响应中提取数据
   * @private
   */
  private extractData<T>(response: any): T {
    // 如果响应有data字段，返回data
    if (response && typeof response === 'object' && 'data' in response) {
      return response.data
    }
    
    // 否则返回整个响应
    return response
  }
}

// 导出单例实例
export const authenticatedApiService = new AuthenticatedApiService()
export default authenticatedApiService