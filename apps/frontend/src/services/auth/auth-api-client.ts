/**
 * 认证 API 客户端实现
 * 负责所有认证相关的 HTTP 请求操作
 */

import type {
  IAuthApiClient,
  IHttpClient,
  AuthServiceConfig,
} from './types'
import type {
  LoginRequest,
  LoginResponse,
  RegisterRequest,
  RegisterResponse,
  TokenResponse,
  User,
  ChangePasswordRequest,
  ForgotPasswordRequest,
  ResetPasswordRequest,
  UpdateProfileRequest,
  ResendVerificationRequest,
} from '../../types/auth'

/**
 * 认证 API 客户端实现
 */
export class AuthApiClient implements IAuthApiClient {
  constructor(
    private readonly httpClient: IHttpClient,
    private readonly config: AuthServiceConfig,
  ) {
    this.setupHttpClient()
  }

  /**
   * 用户登录
   */
  async login(credentials: LoginRequest): Promise<LoginResponse> {
    try {
      const response = await this.httpClient.post<LoginResponse>(
        '/login',
        credentials,
        {
          withCredentials: this.config.useHttpOnlyCookies,
        },
      )

      if (!response.data) {
        throw new Error('Invalid login response')
      }

      return response.data
    } catch (error) {
      throw this.handleApiError(error, 'Login failed')
    }
  }

  /**
   * 用户注册
   */
  async register(data: RegisterRequest): Promise<RegisterResponse> {
    try {
      const response = await this.httpClient.post<RegisterResponse>('/register', data)

      if (!response.data) {
        throw new Error('Invalid registration response')
      }

      return response.data
    } catch (error) {
      throw this.handleApiError(error, 'Registration failed')
    }
  }

  /**
   * 用户登出
   */
  async logout(): Promise<void> {
    try {
      await this.httpClient.post('/logout', {}, {
        withCredentials: this.config.useHttpOnlyCookies,
      })
    } catch (error) {
      // 登出失败不阻断流程，但记录错误
      console.warn('Logout API call failed:', error)
      throw this.handleApiError(error, 'Logout failed')
    }
  }

  /**
   * 刷新令牌
   */
  async refreshToken(refreshToken?: string): Promise<TokenResponse> {
    try {
      const requestData = this.config.useHttpOnlyCookies 
        ? {} // 使用 httpOnly cookies，不需要发送 refresh token
        : { refresh_token: refreshToken }

      const response = await this.httpClient.post<TokenResponse>(
        '/refresh',
        requestData,
        {
          withCredentials: this.config.useHttpOnlyCookies,
        },
      )

      if (!response.data) {
        throw new Error('Invalid token refresh response')
      }

      return response.data
    } catch (error) {
      throw this.handleApiError(error, 'Token refresh failed')
    }
  }

  /**
   * 获取当前用户信息
   */
  async getCurrentUser(): Promise<User> {
    try {
      const response = await this.httpClient.get<User>('/me')

      if (!response.data) {
        throw new Error('Invalid user response')
      }

      return response.data
    } catch (error) {
      throw this.handleApiError(error, 'Failed to get user info')
    }
  }

  /**
   * 更新用户资料
   */
  async updateProfile(data: UpdateProfileRequest): Promise<User> {
    try {
      const response = await this.httpClient.put<User>('/me', data)

      if (!response.data) {
        throw new Error('Invalid profile update response')
      }

      return response.data
    } catch (error) {
      throw this.handleApiError(error, 'Profile update failed')
    }
  }

  /**
   * 修改密码
   */
  async changePassword(data: ChangePasswordRequest): Promise<void> {
    try {
      await this.httpClient.post('/change-password', data)
    } catch (error) {
      throw this.handleApiError(error, 'Password change failed')
    }
  }

  /**
   * 忘记密码
   */
  async forgotPassword(data: ForgotPasswordRequest): Promise<void> {
    try {
      await this.httpClient.post('/forgot-password', data)
    } catch (error) {
      throw this.handleApiError(error, 'Forgot password request failed')
    }
  }

  /**
   * 重置密码
   */
  async resetPassword(data: ResetPasswordRequest): Promise<void> {
    try {
      await this.httpClient.post('/reset-password', data)
    } catch (error) {
      throw this.handleApiError(error, 'Password reset failed')
    }
  }

  /**
   * 邮箱验证
   */
  async verifyEmail(token: string): Promise<void> {
    try {
      await this.httpClient.get(`/verify-email?token=${encodeURIComponent(token)}`)
    } catch (error) {
      throw this.handleApiError(error, 'Email verification failed')
    }
  }

  /**
   * 重发验证邮件
   */
  async resendVerification(data: ResendVerificationRequest): Promise<void> {
    try {
      await this.httpClient.post('/resend-verification', data)
    } catch (error) {
      throw this.handleApiError(error, 'Resend verification failed')
    }
  }

  /**
   * 设置 HTTP 客户端配置
   * @private
   */
  private setupHttpClient(): void {
    // 设置基础 URL
    if (this.httpClient.setBaseURL) {
      const authApiUrl = `${this.config.apiBaseUrl}${this.config.authApiPrefix}`
      this.httpClient.setBaseURL(authApiUrl)
    }

    // 设置超时
    if (this.httpClient.setTimeout) {
      this.httpClient.setTimeout(this.config.timeout)
    }

    // 设置默认请求头
    this.httpClient.setDefaultHeader('Content-Type', 'application/json')
  }

  /**
   * 统一 API 错误处理
   * @private
   */
  private handleApiError(error: any, defaultMessage: string): Error {
    // 构建错误对象，保持与原 AuthService 的兼容性
    const apiError = {
      detail: defaultMessage,
      status_code: 0,
    } as any

    if (error.response?.data) {
      // 处理嵌套的 detail 对象
      if (typeof error.response.data.detail === 'object' && error.response.data.detail?.message) {
        apiError.detail = error.response.data.detail.message
      } else if (typeof error.response.data.detail === 'string') {
        apiError.detail = error.response.data.detail
      } else if (error.response.data.message) {
        apiError.detail = error.response.data.message
      }
      
      apiError.status_code = error.response.status
      apiError.retry_after = error.response.data.retry_after
    } else if (error.request) {
      apiError.detail = 'Network error - please check your connection'
      apiError.status_code = 0
    } else {
      apiError.detail = error.message || defaultMessage
      apiError.status_code = 0
    }

    // 将原始错误附加到 ApiError 上，以便组件可以访问响应状态
    apiError.response = error.response

    const finalError = new Error(apiError.detail)
    Object.assign(finalError, apiError)

    return finalError
  }

  /**
   * 获取 API 健康状态
   */
  async getHealthStatus(): Promise<{ status: string; timestamp: string }> {
    try {
      const response = await this.httpClient.get<{ status: string; timestamp: string }>('/health')
      return response.data
    } catch (error) {
      throw this.handleApiError(error, 'Health check failed')
    }
  }

  /**
   * 获取 API 版本信息
   */
  async getApiVersion(): Promise<{ version: string; build: string }> {
    try {
      const response = await this.httpClient.get<{ version: string; build: string }>('/version')
      return response.data
    } catch (error) {
      throw this.handleApiError(error, 'Version check failed')
    }
  }

  /**
   * 批量验证邮箱地址
   */
  async validateEmails(emails: string[]): Promise<{ valid: string[]; invalid: string[] }> {
    try {
      const response = await this.httpClient.post<{ valid: string[]; invalid: string[] }>(
        '/validate-emails',
        { emails },
      )
      return response.data
    } catch (error) {
      throw this.handleApiError(error, 'Email validation failed')
    }
  }

  /**
   * 获取用户会话列表
   */
  async getUserSessions(): Promise<Array<{
    id: string
    ip_address: string
    user_agent: string
    created_at: string
    last_activity: string
    is_current: boolean
  }>> {
    try {
      const response = await this.httpClient.get('/sessions')
      return response.data
    } catch (error) {
      throw this.handleApiError(error, 'Failed to get user sessions')
    }
  }

  /**
   * 撤销用户会话
   */
  async revokeSession(sessionId: string): Promise<void> {
    try {
      await this.httpClient.delete(`/sessions/${sessionId}`)
    } catch (error) {
      throw this.handleApiError(error, 'Failed to revoke session')
    }
  }

  /**
   * 撤销所有其他会话
   */
  async revokeAllOtherSessions(): Promise<void> {
    try {
      await this.httpClient.post('/sessions/revoke-others')
    } catch (error) {
      throw this.handleApiError(error, 'Failed to revoke other sessions')
    }
  }

  /**
   * 启用两因素认证
   */
  async enableTwoFactor(): Promise<{ secret: string; qr_code: string }> {
    try {
      const response = await this.httpClient.post<{ secret: string; qr_code: string }>('/2fa/enable')
      return response.data
    } catch (error) {
      throw this.handleApiError(error, 'Failed to enable 2FA')
    }
  }

  /**
   * 确认两因素认证
   */
  async confirmTwoFactor(code: string): Promise<{ backup_codes: string[] }> {
    try {
      const response = await this.httpClient.post<{ backup_codes: string[] }>('/2fa/confirm', { code })
      return response.data
    } catch (error) {
      throw this.handleApiError(error, 'Failed to confirm 2FA')
    }
  }

  /**
   * 禁用两因素认证
   */
  async disableTwoFactor(code: string): Promise<void> {
    try {
      await this.httpClient.post('/2fa/disable', { code })
    } catch (error) {
      throw this.handleApiError(error, 'Failed to disable 2FA')
    }
  }

  /**
   * 生成新的备份代码
   */
  async generateBackupCodes(): Promise<{ backup_codes: string[] }> {
    try {
      const response = await this.httpClient.post<{ backup_codes: string[] }>('/2fa/backup-codes')
      return response.data
    } catch (error) {
      throw this.handleApiError(error, 'Failed to generate backup codes')
    }
  }
}