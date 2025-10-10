/**
 * 认证服务架构重构 - 核心接口和类型定义
 * 实现依赖注入和职责分离的设计模式
 */

import type { AxiosRequestConfig, AxiosResponse } from 'axios'
import type {
  ApiError,
  ChangePasswordRequest,
  ForgotPasswordRequest,
  LoginRequest,
  LoginResponse,
  RegisterRequest,
  RegisterResponse,
  ResendVerificationRequest,
  ResetPasswordRequest,
  TokenResponse,
  UpdateProfileRequest,
  User,
} from '../../types/auth'
import type { ApiSuccessResponse } from '../../utils/api-response'

/**
 * 存储服务接口 - 抽象本地存储操作
 */
export interface IStorageService {
  /**
   * 获取存储的值
   */
  getItem(key: string): string | null

  /**
   * 设置存储的值
   */
  setItem(key: string, value: string): void

  /**
   * 移除存储的值
   */
  removeItem(key: string): void

  /**
   * 清空所有存储
   */
  clear(): void
}

/**
 * 导航服务接口 - 抽象路由跳转操作
 */
export interface INavigationService {
  /**
   * 重定向到指定路径
   */
  redirectTo(path: string): void

  /**
   * 获取当前路径
   */
  getCurrentPath(): string

  /**
   * 替换当前路径（不产生历史记录）
   */
  replace(path: string): void

  /**
   * 获取当前 URL 查询参数
   */
  getSearchParams(): URLSearchParams
}

/**
 * HTTP 客户端接口 - 抽象 HTTP 请求操作
 */
export interface IHttpClient {
  /**
   * GET 请求
   */
  get<T = any>(url: string, config?: AxiosRequestConfig): Promise<AxiosResponse<T>>

  /**
   * POST 请求
   */
  post<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<AxiosResponse<T>>

  /**
   * PUT 请求
   */
  put<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<AxiosResponse<T>>

  /**
   * PATCH 请求
   */
  patch<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<AxiosResponse<T>>

  /**
   * DELETE 请求
   */
  delete<T = any>(url: string, config?: AxiosRequestConfig): Promise<AxiosResponse<T>>

  /**
   * 设置默认请求头
   */
  setDefaultHeader(key: string, value: string): void

  /**
   * 移除默认请求头
   */
  removeDefaultHeader(key: string): void

  /**
   * 添加请求拦截器
   */
  addRequestInterceptor(
    onFulfilled?: (config: AxiosRequestConfig) => AxiosRequestConfig | Promise<AxiosRequestConfig>,
    onRejected?: (error: any) => any,
  ): number

  /**
   * 添加响应拦截器
   */
  addResponseInterceptor(
    onFulfilled?: (response: AxiosResponse) => AxiosResponse | Promise<AxiosResponse>,
    onRejected?: (error: any) => any,
  ): number

  /**
   * 移除拦截器
   */
  removeInterceptor(type: 'request' | 'response', id: number): void

  /**
   * 设置基础 URL
   */
  setBaseURL(baseURL: string): void

  /**
   * 设置超时时间
   */
  setTimeout(timeout: number): void

  /**
   * 清除所有拦截器
   */
  clearAllInterceptors(): void
}

/**
 * Token 管理器接口 - 负责 Token 的生命周期管理
 */
export interface ITokenManager {
  /**
   * 获取访问令牌
   */
  getAccessToken(): string | null

  /**
   * 获取刷新令牌
   */
  getRefreshToken(): string | null

  /**
   * 设置令牌对
   */
  setTokens(accessToken: string, refreshToken?: string): void

  /**
   * 清空所有令牌
   */
  clearTokens(): void

  /**
   * 检查令牌是否过期
   */
  isTokenExpired(token?: string): boolean

  /**
   * 获取令牌过期时间
   */
  getTokenExpiration(token?: string): Date | null

  /**
   * 计划令牌刷新
   */
  scheduleRefresh(callback: () => Promise<void>): void

  /**
   * 取消令牌刷新计划
   */
  cancelRefresh(): void

  /**
   * 检查是否有有效的访问令牌
   */
  hasValidAccessToken(): boolean

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
  }

  /**
   * 销毁令牌管理器（清理资源）
   */
  destroy(): void
}

/**
 * 认证 API 客户端接口 - 负责认证相关的 API 调用
 */
export interface IAuthApiClient {
  /**
   * 用户登录
   */
  login(credentials: LoginRequest): Promise<LoginResponse>

  /**
   * 用户注册
   */
  register(data: RegisterRequest): Promise<RegisterResponse>

  /**
   * 用户登出
   */
  logout(): Promise<void>

  /**
   * 刷新令牌
   */
  refreshToken(refreshToken?: string): Promise<TokenResponse>

  /**
   * 获取当前用户信息
   */
  getCurrentUser(): Promise<User>

  /**
   * 更新用户资料
   */
  updateProfile(data: UpdateProfileRequest): Promise<User>

  /**
   * 修改密码
   */
  changePassword(data: ChangePasswordRequest): Promise<void>

  /**
   * 忘记密码
   */
  forgotPassword(data: ForgotPasswordRequest): Promise<void>

  /**
   * 重置密码
   */
  resetPassword(data: ResetPasswordRequest): Promise<void>

  /**
   * 邮箱验证
   */
  verifyEmail(token: string): Promise<void>

  /**
   * 重发验证邮件
   */
  resendVerification(data: ResendVerificationRequest): Promise<void>
}

/**
 * 认证服务配置
 */
export interface AuthServiceConfig {
  /**
   * API 基础 URL
   */
  apiBaseUrl: string

  /**
   * 认证 API 前缀
   */
  authApiPrefix: string

  /**
   * 访问令牌存储键
   */
  accessTokenKey: string

  /**
   * 刷新令牌存储键（如果不使用 httpOnly cookie）
   */
  refreshTokenKey?: string

  /**
   * 是否使用 httpOnly cookies 存储刷新令牌
   */
  useHttpOnlyCookies: boolean

  /**
   * 登录页面路径
   */
  loginPath: string

  /**
   * 令牌刷新提前时间（分钟）
   */
  refreshBufferMinutes: number

  /**
   * 是否启用自动令牌刷新
   */
  enableAutoRefresh: boolean

  /**
   * 请求超时时间（毫秒）
   */
  timeout: number

  /**
   * 是否启用内部调试日志
   */
  enableDebugLogging?: boolean
}

/**
 * 依赖注入容器 - 包含所有认证服务依赖
 */
export interface AuthDependencies {
  /**
   * 存储服务
   */
  storageService: IStorageService

  /**
   * 导航服务
   */
  navigationService: INavigationService

  /**
   * HTTP 客户端
   */
  httpClient: IHttpClient

  /**
   * Token 管理器
   */
  tokenManager: ITokenManager

  /**
   * 认证 API 客户端
   */
  authApiClient: IAuthApiClient

  /**
   * 配置对象
   */
  config: AuthServiceConfig
}

/**
 * 认证服务主接口 - 对外暴露的认证功能
 */
export interface IAuthService {
  /**
   * 用户登录
   */
  login(credentials: LoginRequest): Promise<ApiSuccessResponse<LoginResponse>>

  /**
   * 用户注册
   */
  register(data: RegisterRequest): Promise<ApiSuccessResponse<RegisterResponse>>

  /**
   * 用户登出
   */
  logout(): Promise<ApiSuccessResponse<void>>

  /**
   * 获取当前用户
   */
  getCurrentUser(): Promise<ApiSuccessResponse<User>>

  /**
   * 更新用户资料
   */
  updateProfile(data: UpdateProfileRequest): Promise<ApiSuccessResponse<User>>

  /**
   * 修改密码
   */
  changePassword(data: ChangePasswordRequest): Promise<ApiSuccessResponse<void>>

  /**
   * 忘记密码
   */
  forgotPassword(data: ForgotPasswordRequest): Promise<ApiSuccessResponse<void>>

  /**
   * 重置密码
   */
  resetPassword(data: ResetPasswordRequest): Promise<ApiSuccessResponse<void>>

  /**
   * 邮箱验证
   */
  verifyEmail(token: string): Promise<ApiSuccessResponse<void>>

  /**
   * 重发验证邮件
   */
  resendVerification(data: ResendVerificationRequest): Promise<ApiSuccessResponse<void>>

  /**
   * 获取访问令牌
   */
  getAccessToken(): string | null

  /**
   * 检查是否已认证
   */
  isAuthenticated(): boolean

  /**
   * 手动刷新令牌
   */
  refreshTokens(): Promise<void>

  /**
   * 获取内部HTTP客户端（用于其他服务）
   * 该客户端已配置认证拦截器，可以用于其他API调用
   */
  getHttpClient(): IHttpClient
}

/**
 * 工厂函数配置项
 */
export interface AuthServiceFactoryOptions {
  /**
   * 认证服务配置
   */
  config?: Partial<AuthServiceConfig>

  /**
   * 自定义存储服务
   */
  storageService?: IStorageService

  /**
   * 自定义导航服务
   */
  navigationService?: INavigationService

  /**
   * 自定义 HTTP 客户端
   */
  httpClient?: IHttpClient

  /**
   * 是否启用开发模式日志
   */
  enableDebugLogging?: boolean
}

/**
 * 错误处理器类型
 */
export type ErrorHandler = (error: ApiError) => ApiError

/**
 * 令牌刷新回调类型
 */
export type TokenRefreshCallback = () => Promise<void>

/**
 * 认证状态变化监听器类型
 */
export type AuthStateChangeListener = (isAuthenticated: boolean, user: User | null) => void

/**
 * 事件类型枚举
 */
export enum AuthEventType {
  LOGIN = 'login',
  LOGOUT = 'logout',
  TOKEN_REFRESH = 'token_refresh',
  TOKEN_EXPIRED = 'token_expired',
  AUTH_ERROR = 'auth_error',
}

/**
 * 认证事件接口
 */
export interface AuthEvent {
  type: AuthEventType
  payload?: any
  timestamp: Date
}

/**
 * 事件监听器类型
 */
export type AuthEventListener = (event: AuthEvent) => void
