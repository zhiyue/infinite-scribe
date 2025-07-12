/**
 * 重构后的认证服务主类
 * 基于依赖注入实现高内聚低耦合的架构
 */

import type {
  IAuthService,
  ITokenManager,
  IStorageService,
  INavigationService,
  IHttpClient,
  IAuthApiClient,
  AuthServiceConfig,
  AuthDependencies,
} from './types'
import type {
  LoginRequest,
  LoginResponse,
  RegisterRequest,
  RegisterResponse,
  User,
  ChangePasswordRequest,
  ForgotPasswordRequest,
  ResetPasswordRequest,
  UpdateProfileRequest,
  ResendVerificationRequest,
} from '../../types/auth'
import { wrapApiResponse, type ApiSuccessResponse } from '../../utils/api-response'

/**
 * 重构后的认证服务实现
 * 采用依赖注入模式，实现职责分离和高可测试性
 */
export class AuthService implements IAuthService {
  private readonly tokenManager: ITokenManager
  private readonly storageService: IStorageService
  private readonly navigationService: INavigationService
  private readonly httpClient: IHttpClient
  private readonly authApiClient: IAuthApiClient
  private readonly config: AuthServiceConfig

  private refreshPromise: Promise<void> | null = null
  private isInitialized: boolean = false

  constructor(dependencies: AuthDependencies) {
    this.tokenManager = dependencies.tokenManager
    this.storageService = dependencies.storageService
    this.navigationService = dependencies.navigationService
    this.httpClient = dependencies.httpClient
    this.authApiClient = dependencies.authApiClient
    this.config = dependencies.config

    this.initialize()
  }

  /**
   * 用户登录
   */
  async login(credentials: LoginRequest): Promise<ApiSuccessResponse<LoginResponse>> {
    try {
      const response = await this.authApiClient.login(credentials)
      
      // 设置令牌
      this.tokenManager.setTokens(response.access_token, response.refresh_token)
      
      // 如果启用自动刷新，开始调度
      if (this.config.enableAutoRefresh) {
        this.scheduleTokenRefresh()
      }

      return wrapApiResponse<LoginResponse>(response, 'Login successful')
    } catch (error: any) {
      throw this.handleApiError(error)
    }
  }

  /**
   * 用户注册
   */
  async register(data: RegisterRequest): Promise<ApiSuccessResponse<RegisterResponse>> {
    try {
      const response = await this.authApiClient.register(data)
      return wrapApiResponse<RegisterResponse>(response, 'Registration successful')
    } catch (error: any) {
      throw this.handleApiError(error)
    }
  }

  /**
   * 用户登出
   */
  async logout(): Promise<ApiSuccessResponse<void>> {
    try {
      // 取消令牌刷新
      this.tokenManager.cancelRefresh()
      
      // 调用登出 API
      await this.authApiClient.logout()
      
      return wrapApiResponse<void>(undefined, 'Logged out successfully')
    } catch (error) {
      // 即使 API 调用失败，也要清理本地状态
      console.warn('Logout API call failed:', error)
      return wrapApiResponse<void>(undefined, 'Logged out successfully')
    } finally {
      // 清理本地令牌和状态
      this.tokenManager.clearTokens()
    }
  }

  /**
   * 获取当前用户
   */
  async getCurrentUser(): Promise<ApiSuccessResponse<User>> {
    try {
      const user = await this.authApiClient.getCurrentUser()
      return wrapApiResponse<User>(user, 'User profile retrieved successfully')
    } catch (error: any) {
      throw this.handleApiError(error)
    }
  }

  /**
   * 更新用户资料
   */
  async updateProfile(data: UpdateProfileRequest): Promise<ApiSuccessResponse<User>> {
    try {
      const user = await this.authApiClient.updateProfile(data)
      return wrapApiResponse<User>(user, 'Profile updated successfully')
    } catch (error: any) {
      throw this.handleApiError(error)
    }
  }

  /**
   * 修改密码
   */
  async changePassword(data: ChangePasswordRequest): Promise<ApiSuccessResponse<void>> {
    try {
      await this.authApiClient.changePassword(data)
      return wrapApiResponse<void>(undefined, 'Password changed successfully')
    } catch (error: any) {
      throw this.handleApiError(error)
    }
  }

  /**
   * 忘记密码
   */
  async forgotPassword(data: ForgotPasswordRequest): Promise<ApiSuccessResponse<void>> {
    try {
      await this.authApiClient.forgotPassword(data)
      return wrapApiResponse<void>(undefined, 'Password reset email sent')
    } catch (error: any) {
      throw this.handleApiError(error)
    }
  }

  /**
   * 重置密码
   */
  async resetPassword(data: ResetPasswordRequest): Promise<ApiSuccessResponse<void>> {
    try {
      await this.authApiClient.resetPassword(data)
      return wrapApiResponse<void>(undefined, 'Password reset successfully')
    } catch (error: any) {
      throw this.handleApiError(error)
    }
  }

  /**
   * 邮箱验证
   */
  async verifyEmail(token: string): Promise<ApiSuccessResponse<void>> {
    try {
      await this.authApiClient.verifyEmail(token)
      return wrapApiResponse<void>(undefined, 'Email verified successfully')
    } catch (error: any) {
      throw this.handleApiError(error)
    }
  }

  /**
   * 重发验证邮件
   */
  async resendVerification(data: ResendVerificationRequest): Promise<ApiSuccessResponse<void>> {
    try {
      await this.authApiClient.resendVerification(data)
      return wrapApiResponse<void>(undefined, 'Verification email resent')
    } catch (error: any) {
      throw this.handleApiError(error)
    }
  }

  /**
   * 获取访问令牌
   */
  getAccessToken(): string | null {
    return this.tokenManager.getAccessToken()
  }

  /**
   * 检查是否已认证
   */
  isAuthenticated(): boolean {
    return this.tokenManager.hasValidAccessToken()
  }

  /**
   * 手动刷新令牌
   */
  async refreshTokens(): Promise<void> {
    await this.performTokenRefresh()
  }

  /**
   * 初始化服务
   * @private
   */
  private initialize(): void {
    if (this.isInitialized) {
      return
    }

    try {
      // 设置 HTTP 拦截器
      this.setupHttpInterceptors()

      // 如果有有效令牌且启用自动刷新，开始调度
      if (this.isAuthenticated() && this.config.enableAutoRefresh) {
        this.scheduleTokenRefresh()
      }

      this.isInitialized = true
      if (this.config.enableDebugLogging) {
        console.debug('AuthService initialized successfully')
      }
    } catch (error) {
      console.error('Failed to initialize AuthService:', error)
    }
  }

  /**
   * 设置 HTTP 拦截器
   * @private
   */
  private setupHttpInterceptors(): void {
    // 请求拦截器 - 添加授权头
    this.httpClient.addRequestInterceptor(
      (config) => {
        const token = this.tokenManager.getAccessToken()
        if (token) {
          config.headers = config.headers || {}
          config.headers.Authorization = `Bearer ${token}`
        }
        return config
      },
      (error) => Promise.reject(error),
    )

    // 响应拦截器 - 处理 401 错误和令牌刷新
    this.httpClient.addResponseInterceptor(
      (response) => response,
      async (error) => {
        const originalRequest = error.config

        // 如果没有配置信息，直接返回错误
        if (!originalRequest) {
          throw error
        }

        // 不要对认证端点进行令牌刷新
        const isAuthEndpoint = this.isAuthEndpoint(originalRequest?.url)

        if (
          error.response?.status === 401 &&
          !originalRequest._retry &&
          !isAuthEndpoint &&
          this.isAuthenticated()
        ) {
          originalRequest._retry = true

          try {
            await this.performTokenRefresh()
            
            // 重试原始请求
            const token = this.tokenManager.getAccessToken()
            if (token) {
              originalRequest.headers.Authorization = `Bearer ${token}`
              return this.httpClient.get(originalRequest.url, originalRequest)
            }
          } catch (refreshError) {
            // 刷新失败，清理状态并重定向到登录页
            this.handleRefreshFailure()
            return Promise.reject(refreshError)
          }
        }

        return Promise.reject(error)
      },
    )
  }

  /**
   * 判断是否是认证端点
   * @private
   */
  private isAuthEndpoint(url?: string): boolean {
    if (!url) return false
    
    const authEndpoints = ['/login', '/register', '/refresh', '/logout']
    return authEndpoints.some(endpoint => url.includes(endpoint))
  }

  /**
   * 调度令牌刷新
   * @private
   */
  private scheduleTokenRefresh(): void {
    this.tokenManager.scheduleRefresh(() => this.performTokenRefresh())
  }

  /**
   * 执行令牌刷新
   * @private
   */
  private async performTokenRefresh(): Promise<void> {
    // 防止并发刷新请求
    if (this.refreshPromise) {
      return this.refreshPromise
    }

    this.refreshPromise = this.executeTokenRefresh()
    
    try {
      await this.refreshPromise
    } finally {
      this.refreshPromise = null
    }
  }

  /**
   * 执行实际的令牌刷新逻辑
   * @private
   */
  private async executeTokenRefresh(): Promise<void> {
    try {
      if (this.config.enableDebugLogging) {
        console.debug('Refreshing access token...')
      }
      
      const refreshToken = this.tokenManager.getRefreshToken()
      const response = await this.authApiClient.refreshToken(refreshToken || undefined)
      
      // 更新令牌
      this.tokenManager.setTokens(response.access_token, response.refresh_token)
      
      if (this.config.enableDebugLogging) {
        console.debug('Token refresh successful')
      }
    } catch (error) {
      console.error('Token refresh failed:', error)
      this.handleRefreshFailure()
      throw error
    }
  }

  /**
   * 处理令牌刷新失败
   * @private
   */
  private handleRefreshFailure(): void {
    // 清理令牌和状态
    this.tokenManager.clearTokens()
    
    // 重定向到登录页面
    this.navigationService.redirectTo(this.config.loginPath)
  }

  /**
   * 统一 API 错误处理
   * @private
   */
  private handleApiError(error: any): Error {
    // 保持与原 AuthService 的错误格式兼容
    return error
  }

  /**
   * 获取服务状态摘要（用于调试）
   */
  getServiceStatus(): {
    isInitialized: boolean
    isAuthenticated: boolean
    tokenInfo: ReturnType<ITokenManager['getTokenSummary']>
    config: AuthServiceConfig
  } {
    return {
      isInitialized: this.isInitialized,
      isAuthenticated: this.isAuthenticated(),
      tokenInfo: this.tokenManager.getTokenSummary(),
      config: { ...this.config },
    }
  }

  /**
   * 销毁服务，清理资源
   */
  destroy(): void {
    // 取消令牌刷新
    this.tokenManager.cancelRefresh()
    
    // 清理 HTTP 拦截器
    this.httpClient.clearAllInterceptors?.()
    
    // 销毁 TokenManager
    if (this.tokenManager.destroy && typeof this.tokenManager.destroy === 'function') {
      this.tokenManager.destroy()
    }
    
    this.isInitialized = false
    if (this.config.enableDebugLogging) {
      console.debug('AuthService destroyed')
    }
  }

  /**
   * 强制令牌过期（测试专用）
   */
  forceTokenExpiry(): void {
    if (process.env.NODE_ENV === 'development' || process.env.NODE_ENV === 'test') {
      this.tokenManager.clearTokens()
    }
  }

  /**
   * 获取扩展的认证功能（如会话管理、2FA等）
   */
  getExtendedApi(): IAuthApiClient {
    return this.authApiClient
  }
}