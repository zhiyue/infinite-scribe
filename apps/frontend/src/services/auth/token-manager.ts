/**
 * Token 管理器实现
 * 负责 JWT Token 的生命周期管理，包括存储、验证、刷新调度等
 */

import type { IStorageService, ITokenManager, TokenRefreshCallback } from './types'

/**
 * JWT Token 解析结果
 */
interface JwtPayload {
  exp?: number // 过期时间（Unix 时间戳）
  iat?: number // 签发时间（Unix 时间戳）
  sub?: string // 主题（通常是用户ID）
  [key: string]: any
}

/**
 * Token 管理器实现类
 */
export class TokenManager implements ITokenManager {
  private refreshTimer: NodeJS.Timeout | null = null
  private refreshCallback: TokenRefreshCallback | null = null
  private isRefreshing = false // 防止递归刷新

  constructor(
    private readonly storageService: IStorageService,
    private readonly accessTokenKey = 'access_token',
    private readonly refreshTokenKey?: string, // 如果为空则使用 httpOnly cookies
    private readonly refreshBufferMinutes = 5, // 提前5分钟刷新
  ) {}

  /**
   * 获取访问令牌
   */
  getAccessToken(): string | null {
    try {
      return this.storageService.getItem(this.accessTokenKey)
    } catch (error) {
      console.warn('Failed to get access token from storage:', error)
      return null
    }
  }

  /**
   * 获取刷新令牌
   */
  getRefreshToken(): string | null {
    if (!this.refreshTokenKey) {
      // 使用 httpOnly cookies，无法从客户端访问
      return null
    }
    try {
      return this.storageService.getItem(this.refreshTokenKey)
    } catch (error) {
      console.warn('Failed to get refresh token from storage:', error)
      return null
    }
  }

  /**
   * 设置令牌对
   */
  setTokens(accessToken: string, refreshToken?: string): void {
    // 存储访问令牌
    this.storageService.setItem(this.accessTokenKey, accessToken)

    // 如果配置了刷新令牌存储且提供了刷新令牌，则存储
    if (this.refreshTokenKey && refreshToken) {
      this.storageService.setItem(this.refreshTokenKey, refreshToken)
    }

    // 注意：不在这里自动重新调度刷新，避免在刷新回调中调用setTokens时造成无限循环
    // 调度刷新应该由外部在合适的时机调用scheduleRefresh
  }

  /**
   * 清空所有令牌
   */
  clearTokens(): void {
    this.storageService.removeItem(this.accessTokenKey)

    if (this.refreshTokenKey) {
      this.storageService.removeItem(this.refreshTokenKey)
    }

    this.cancelRefresh()
    this.isRefreshing = false // 重置刷新状态
  }

  /**
   * 检查令牌是否过期
   */
  isTokenExpired(token?: string): boolean {
    const targetToken = token || this.getAccessToken()

    if (!targetToken) {
      return true
    }

    const expiration = this.getTokenExpiration(targetToken)
    if (!expiration) {
      // 无法解析过期时间，认为已过期
      return true
    }

    // 检查是否已过期
    return Date.now() >= expiration.getTime()
  }

  /**
   * 获取令牌过期时间
   */
  getTokenExpiration(token?: string): Date | null {
    const targetToken = token || this.getAccessToken()

    if (!targetToken) {
      return null
    }

    try {
      const payload = this.parseJwtPayload(targetToken)

      if (!payload.exp) {
        return null
      }

      // JWT exp 是 Unix 时间戳（秒），需要转换为毫秒
      return new Date(payload.exp * 1000)
    } catch (error) {
      console.warn('Failed to parse JWT token:', error)
      return null
    }
  }

  /**
   * 计划令牌刷新
   */
  scheduleRefresh(callback: TokenRefreshCallback): void {
    this.refreshCallback = callback
    this.cancelRefresh() // 取消之前的定时器

    const accessToken = this.getAccessToken()
    if (!accessToken) {
      return
    }

    const expiration = this.getTokenExpiration(accessToken)
    if (!expiration) {
      return
    }

    // 计算刷新时间（提前指定分钟数刷新）
    const refreshTime = expiration.getTime() - this.refreshBufferMinutes * 60 * 1000
    const delay = refreshTime - Date.now()

    // 如果已经需要刷新或即将过期，立即刷新
    if (delay <= 0) {
      this.executeRefresh()
      return
    }

    // 设置定时器
    this.refreshTimer = setTimeout(() => {
      this.executeRefresh()
    }, delay)

    console.debug(`Token refresh scheduled in ${Math.round(delay / 1000)} seconds`)
  }

  /**
   * 取消令牌刷新计划
   */
  cancelRefresh(): void {
    if (this.refreshTimer) {
      clearTimeout(this.refreshTimer)
      this.refreshTimer = null
    }
  }

  /**
   * 检查是否有有效的访问令牌
   */
  hasValidAccessToken(): boolean {
    const accessToken = this.getAccessToken()
    return accessToken !== null && !this.isTokenExpired(accessToken)
  }

  /**
   * 解析 JWT Payload
   * @private
   */
  private parseJwtPayload(token: string): JwtPayload {
    try {
      // JWT 格式：header.payload.signature
      const parts = token.split('.')
      if (parts.length !== 3) {
        throw new Error('Invalid JWT format')
      }

      // Base64URL 解码 payload
      const payload = parts[1]
      const decodedPayload = this.base64UrlDecode(payload)

      return JSON.parse(decodedPayload)
    } catch (error) {
      throw new Error(`Failed to parse JWT payload: ${error}`)
    }
  }

  /**
   * Base64URL 解码
   * @private
   */
  private base64UrlDecode(str: string): string {
    // Base64URL 转 Base64
    let base64 = str.replace(/-/g, '+').replace(/_/g, '/')

    // 补齐 padding
    while (base64.length % 4) {
      base64 += '='
    }

    try {
      // 解码 Base64
      return atob(base64)
    } catch (error) {
      throw new Error('Invalid Base64URL encoding')
    }
  }

  /**
   * 执行令牌刷新
   * @private
   */
  private async executeRefresh(): Promise<void> {
    if (!this.refreshCallback) {
      console.warn('No refresh callback configured')
      return
    }

    if (this.isRefreshing) {
      console.debug('Token refresh already in progress, skipping')
      return
    }

    this.isRefreshing = true

    try {
      console.debug('Executing token refresh')
      await this.refreshCallback()

      // 刷新成功后重新调度下一次刷新
      // 检查是否有新的有效令牌
      const currentToken = this.getAccessToken()
      if (currentToken && !this.isTokenExpired(currentToken)) {
        // 重新调度下一次刷新
        this.scheduleRefresh(this.refreshCallback)
      }
    } catch (error) {
      console.error('Token refresh failed:', error)
      // 刷新失败，清除令牌
      this.clearTokens()
    } finally {
      this.isRefreshing = false
    }
  }

  /**
   * 获取令牌剩余有效时间（秒）
   */
  getTokenTimeToExpiry(token?: string): number | null {
    const expiration = this.getTokenExpiration(token)
    if (!expiration) {
      return null
    }

    const remaining = expiration.getTime() - Date.now()
    return Math.max(0, Math.floor(remaining / 1000))
  }

  /**
   * 检查令牌是否即将过期
   */
  isTokenExpiringSoon(token?: string, bufferMinutes: number = this.refreshBufferMinutes): boolean {
    const expiration = this.getTokenExpiration(token)
    if (!expiration) {
      return true
    }

    const bufferTime = bufferMinutes * 60 * 1000
    return Date.now() >= expiration.getTime() - bufferTime
  }

  /**
   * 获取令牌信息摘要（用于调试）
   */
  getTokenSummary(): {
    hasAccessToken: boolean
    hasRefreshToken: boolean
    accessTokenExpiry: Date | null
    isAccessTokenValid: boolean
    isAccessTokenExpiringSoon: boolean
    timeToRefresh: number | null
  } {
    const accessToken = this.getAccessToken()
    const refreshToken = this.getRefreshToken()
    const accessTokenExpiry = this.getTokenExpiration(accessToken || undefined)

    return {
      hasAccessToken: !!accessToken,
      hasRefreshToken: !!refreshToken,
      accessTokenExpiry,
      isAccessTokenValid: this.hasValidAccessToken(),
      isAccessTokenExpiringSoon: this.isTokenExpiringSoon(accessToken || undefined),
      timeToRefresh: this.getTokenTimeToExpiry(accessToken || undefined),
    }
  }

  /**
   * 销毁管理器，清理资源
   */
  destroy(): void {
    this.cancelRefresh()
    this.refreshCallback = null
  }
}
