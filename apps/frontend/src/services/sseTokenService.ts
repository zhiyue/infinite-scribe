/**
 * SSE Token Service
 * 负责获取和管理SSE连接专用的token
 */

import { apiService } from './api'
import { authService } from './auth'

export interface SSETokenResponse {
  sse_token: string
  expires_at: string
  token_type: 'sse'
}

class SSETokenService {
  private currentToken: string | null = null
  private tokenExpiry: Date | null = null

  /**
   * 获取有效的SSE token
   * 如果当前token即将过期（15秒内），则获取新的token
   * 调整为更激进的刷新策略以适应60秒的短期过期时间
   */
  async getValidSSEToken(): Promise<string> {
    console.log('[SSE Token] 检查当前SSE token状态', {
      hasToken: !!this.currentToken,
      tokenExpiry: this.tokenExpiry?.toISOString(),
      willExpireSoon: this.willExpireSoon(),
    })

    // 如果没有token或即将过期，获取新的
    if (!this.currentToken || this.willExpireSoon()) {
      console.log('[SSE Token] 需要获取新的SSE token')
      await this.refreshToken()
    }

    console.log('[SSE Token] ✅ 返回有效的SSE token')
    return this.currentToken!
  }

  /**
   * 刷新SSE token
   */
  async refreshToken(): Promise<void> {
    try {
      console.log('[SSE Token] 🔄 正在获取新的SSE token...')

      // 检查当前认证状态
      const currentToken = authService.getAccessToken()
      console.log('[SSE Token] 认证状态检查:', {
        hasAccessToken: !!currentToken,
        tokenLength: currentToken ? currentToken.length : 0,
        tokenPrefix: currentToken ? currentToken.substring(0, 20) + '...' : 'none',
      })

      const response = await apiService.post<SSETokenResponse>('/api/v1/auth/sse-token')

      this.currentToken = response.sse_token
      this.tokenExpiry = new Date(response.expires_at)

      console.log('[SSE Token] ✅ SSE token获取成功', {
        tokenLength: this.currentToken.length,
        expiresAt: this.tokenExpiry.toISOString(),
        tokenType: response.token_type,
      })
    } catch (error) {
      console.error('[SSE Token] ❌ 获取SSE token失败:', {
        error: error,
        errorMessage: error instanceof Error ? error.message : 'Unknown error',
        errorType: error instanceof Error ? error.constructor.name : typeof error,
      })

      // 检查是否是认证错误
      if (error instanceof Error && error.message.includes('Not authenticated')) {
        console.warn('[SSE Token] 🔒 认证失败 - 用户可能未登录或token已过期')
      }

      this.currentToken = null
      this.tokenExpiry = null
      throw error
    }
  }

  /**
   * 清除当前token
   */
  clearToken(): void {
    console.log('[SSE Token] 🗑️ 清除SSE token')
    this.currentToken = null
    this.tokenExpiry = null
  }

  /**
   * 检查token是否即将过期（15秒内）
   * 调整为更激进的阈值以适应60秒的短期过期时间
   */
  private willExpireSoon(): boolean {
    if (!this.tokenExpiry) return true

    const now = new Date()
    const fifteenSecondsFromNow = new Date(now.getTime() + 15 * 1000)

    const willExpire = this.tokenExpiry <= fifteenSecondsFromNow

    if (willExpire) {
      console.log('[SSE Token] ⏰ Token即将过期', {
        expiresAt: this.tokenExpiry.toISOString(),
        timeUntilExpiry: this.tokenExpiry.getTime() - now.getTime(),
      })
    }

    return willExpire
  }

  /**
   * 主动检查并刷新token（用于长连接维护）
   * 为了应对60秒的短期过期，在长期SSE连接中定期调用此方法
   */
  async maintainTokenFreshness(): Promise<boolean> {
    try {
      const tokenInfo = this.getTokenInfo()
      console.log('[SSE Token] 🔄 主动维护token新鲜度', tokenInfo)

      if (this.willExpireSoon()) {
        console.log('[SSE Token] 🔄 主动刷新即将过期的token')
        await this.refreshToken()
        return true // Token was refreshed
      }

      return false // Token was still fresh
    } catch (error) {
      console.error('[SSE Token] ❌ 主动token维护失败:', error)
      return false
    }
  }

  /**
   * 获取token信息（用于调试）
   */
  getTokenInfo() {
    return {
      hasToken: !!this.currentToken,
      tokenExpiry: this.tokenExpiry?.toISOString(),
      willExpireSoon: this.willExpireSoon(),
      timeUntilExpiry: this.tokenExpiry ? this.tokenExpiry.getTime() - Date.now() : null,
    }
  }
}

// 导出单例实例
export const sseTokenService = new SSETokenService()
export { SSETokenService }
