/**
 * 认证服务工厂函数
 * 负责创建和配置认证服务及其所有依赖
 */

import type {
  IAuthService,
  IStorageService,
  INavigationService,
  IHttpClient,
  ITokenManager,
  IAuthApiClient,
  AuthServiceConfig,
  AuthDependencies,
  AuthServiceFactoryOptions,
} from './types'

import { AuthService } from './auth-service'
import { TokenManager } from './token-manager'
import { AuthApiClient } from './auth-api-client'
import { createStorageService, MemoryStorageService } from './storage'
import { createAutoNavigationService, MockNavigationService } from './navigation'
import { createAutoHttpClient, MockHttpClient } from './http-client'

/**
 * 默认认证服务配置
 */
const DEFAULT_CONFIG: AuthServiceConfig = {
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  authApiPrefix: '/api/v1/auth',
  accessTokenKey: 'access_token',
  refreshTokenKey: undefined, // 默认使用 httpOnly cookies
  useHttpOnlyCookies: true,
  loginPath: '/login',
  refreshBufferMinutes: 5,
  enableAutoRefresh: true,
  timeout: 10000,
  enableDebugLogging: false, // 默认禁用内部调试日志
}

/**
 * 环境特定配置
 */
const ENVIRONMENT_CONFIGS: Record<string, Partial<AuthServiceConfig>> = {
  development: {
    enableAutoRefresh: true,
    refreshBufferMinutes: 2, // 开发环境更频繁的刷新
    timeout: 15000, // 开发环境更长的超时时间
    enableDebugLogging: true, // 开发环境启用调试日志
  },
  test: {
    enableAutoRefresh: false, // 测试环境禁用自动刷新
    useHttpOnlyCookies: false, // 测试环境使用 localStorage
    refreshTokenKey: 'refresh_token',
    timeout: 5000, // 测试环境更短的超时时间
    enableDebugLogging: false, // 测试环境禁用调试日志
  },
  production: {
    enableAutoRefresh: true,
    useHttpOnlyCookies: true,
    refreshBufferMinutes: 5,
    timeout: 10000,
    enableDebugLogging: false, // 生产环境禁用调试日志
  },
}

/**
 * 创建认证服务配置
 */
function createAuthServiceConfig(
  customConfig?: Partial<AuthServiceConfig>,
  environment?: string,
): AuthServiceConfig {
  const env = environment || import.meta.env.MODE || 'development'
  const envConfig = ENVIRONMENT_CONFIGS[env] || {}
  
  return {
    ...DEFAULT_CONFIG,
    ...envConfig,
    ...customConfig,
  }
}

/**
 * 创建存储服务
 */
function createAuthStorageService(
  customService?: IStorageService,
  config?: AuthServiceConfig,
): IStorageService {
  if (customService) {
    return customService
  }

  // 根据配置选择存储类型
  const storageType = config?.useHttpOnlyCookies ? 'localStorage' : 'localStorage'
  return createStorageService(storageType, 'auth_')
}

/**
 * 创建导航服务
 */
function createAuthNavigationService(
  customService?: INavigationService,
): INavigationService {
  if (customService) {
    return customService
  }

  return createAutoNavigationService()
}

/**
 * 创建 HTTP 客户端
 */
function createAuthHttpClient(
  customClient?: IHttpClient,
  config?: AuthServiceConfig,
): IHttpClient {
  if (customClient) {
    return customClient
  }

  return createAutoHttpClient({
    baseURL: config ? `${config.apiBaseUrl}${config.authApiPrefix}` : undefined,
    timeout: config?.timeout,
    withCredentials: config?.useHttpOnlyCookies,
  })
}

/**
 * 创建 Token 管理器
 */
function createAuthTokenManager(
  storageService: IStorageService,
  config: AuthServiceConfig,
): ITokenManager {
  return new TokenManager(
    storageService,
    config.accessTokenKey,
    config.refreshTokenKey,
    config.refreshBufferMinutes,
  )
}

/**
 * 创建认证 API 客户端
 */
function createAuthApiClient(
  httpClient: IHttpClient,
  config: AuthServiceConfig,
): IAuthApiClient {
  return new AuthApiClient(httpClient, config)
}

/**
 * 创建完整的认证服务
 */
export function createAuthService(options: AuthServiceFactoryOptions = {}): IAuthService {
  try {
    // 创建配置
    const config = createAuthServiceConfig({
      ...options.config,
      // 如果工厂指定了调试日志，则设置到配置中
      enableDebugLogging: options.enableDebugLogging ?? options.config?.enableDebugLogging,
    })

    // 创建各个服务实例
    const storageService = createAuthStorageService(options.storageService, config)
    const navigationService = createAuthNavigationService(options.navigationService)
    const httpClient = createAuthHttpClient(options.httpClient, config)
    
    // 创建核心管理器和 API 客户端
    const tokenManager = createAuthTokenManager(storageService, config)
    const authApiClient = createAuthApiClient(httpClient, config)

    // 组装依赖容器
    const dependencies: AuthDependencies = {
      storageService,
      navigationService,
      httpClient,
      tokenManager,
      authApiClient,
      config,
    }

    // 创建认证服务实例
    const authService = new AuthService(dependencies)

    if (options.enableDebugLogging) {
      console.debug('AuthService created with config:', config)
      console.debug('AuthService status:', authService.getServiceStatus())
    }

    return authService
  } catch (error) {
    console.error('Failed to create AuthService:', error)
    throw new Error(`AuthService factory failed: ${error}`)
  }
}

/**
 * 创建测试用的认证服务
 */
export function createTestAuthService(options: {
  mockResponses?: Record<string, any>
  config?: Partial<AuthServiceConfig>
  enableLogging?: boolean
} = {}): IAuthService {
  // 创建测试专用的服务实例
  const storageService = new MemoryStorageService('test_auth_')
  const navigationService = new MockNavigationService('/test')
  const httpClient = new MockHttpClient()

  // 设置模拟响应
  if (options.mockResponses) {
    Object.entries(options.mockResponses).forEach(([key, response]) => {
      const [method, url] = key.split(' ')
      httpClient.setMockResponse(method, url, response)
    })
  }

  // 测试环境配置
  const testConfig: Partial<AuthServiceConfig> = {
    enableAutoRefresh: false,
    useHttpOnlyCookies: false,
    refreshTokenKey: 'refresh_token',
    timeout: 5000,
    ...options.config,
  }

  return createAuthService({
    config: testConfig,
    storageService,
    navigationService,
    httpClient,
    enableDebugLogging: options.enableLogging,
  })
}

/**
 * 创建开发环境的认证服务
 */
export function createDevelopmentAuthService(
  customConfig?: Partial<AuthServiceConfig>,
): IAuthService {
  return createAuthService({
    config: {
      // 开发环境特定配置
      enableAutoRefresh: true,
      refreshBufferMinutes: 2,
      timeout: 15000,
      // 自定义配置覆盖默认配置
      ...customConfig,
    },
    enableDebugLogging: true,
  })
}

/**
 * 创建生产环境的认证服务
 */
export function createProductionAuthService(
  customConfig?: Partial<AuthServiceConfig>,
): IAuthService {
  return createAuthService({
    config: {
      // 生产环境特定配置
      enableAutoRefresh: true,
      useHttpOnlyCookies: true,
      refreshBufferMinutes: 5,
      timeout: 10000,
      // 自定义配置覆盖默认配置
      ...customConfig,
    },
    enableDebugLogging: false,
  })
}

/**
 * 环境自适应工厂函数
 */
export function createEnvironmentAuthService(
  environment?: string,
  customConfig?: Partial<AuthServiceConfig>,
): IAuthService {
  const env = environment || import.meta.env.MODE || 'development'

  switch (env) {
    case 'development':
      return createDevelopmentAuthService(customConfig)
    case 'production':
      return createProductionAuthService(customConfig)
    case 'test':
      return createTestAuthService({ config: customConfig })
    default:
      console.warn(`Unknown environment: ${env}, using development config`)
      return createDevelopmentAuthService(customConfig)
  }
}

/**
 * 验证服务配置
 */
export function validateAuthServiceConfig(config: AuthServiceConfig): {
  isValid: boolean
  errors: string[]
  warnings: string[]
} {
  const errors: string[] = []
  const warnings: string[] = []

  // 必需字段验证
  if (!config.apiBaseUrl) {
    errors.push('apiBaseUrl is required')
  }

  if (!config.authApiPrefix) {
    errors.push('authApiPrefix is required')
  }

  if (!config.accessTokenKey) {
    errors.push('accessTokenKey is required')
  }

  if (!config.loginPath) {
    errors.push('loginPath is required')
  }

  // 配置逻辑验证
  if (config.useHttpOnlyCookies && config.refreshTokenKey) {
    warnings.push('refreshTokenKey is ignored when useHttpOnlyCookies is true')
  }

  if (!config.useHttpOnlyCookies && !config.refreshTokenKey) {
    errors.push('refreshTokenKey is required when useHttpOnlyCookies is false')
  }

  if (config.refreshBufferMinutes < 1) {
    warnings.push('refreshBufferMinutes should be at least 1 minute')
  }

  if (config.timeout < 1000) {
    warnings.push('timeout should be at least 1000ms')
  }

  // URL 格式验证
  try {
    new URL(config.apiBaseUrl)
  } catch {
    errors.push('apiBaseUrl must be a valid URL')
  }

  return {
    isValid: errors.length === 0,
    errors,
    warnings,
  }
}

/**
 * 获取默认配置
 */
export function getDefaultAuthServiceConfig(): AuthServiceConfig {
  return { ...DEFAULT_CONFIG }
}

/**
 * 获取环境配置
 */
export function getEnvironmentConfig(environment: string): Partial<AuthServiceConfig> {
  return { ...(ENVIRONMENT_CONFIGS[environment] || {}) }
}

/**
 * 创建自定义认证服务构建器
 */
export class AuthServiceBuilder {
  private config: Partial<AuthServiceConfig> = {}
  private storageService?: IStorageService
  private navigationService?: INavigationService
  private httpClient?: IHttpClient
  private enableDebugLogging: boolean = false

  withConfig(config: Partial<AuthServiceConfig>): AuthServiceBuilder {
    this.config = { ...this.config, ...config }
    return this
  }

  withStorageService(service: IStorageService): AuthServiceBuilder {
    this.storageService = service
    return this
  }

  withNavigationService(service: INavigationService): AuthServiceBuilder {
    this.navigationService = service
    return this
  }

  withHttpClient(client: IHttpClient): AuthServiceBuilder {
    this.httpClient = client
    return this
  }

  withDebugLogging(enable: boolean = true): AuthServiceBuilder {
    this.enableDebugLogging = enable
    return this
  }

  build(): IAuthService {
    return createAuthService({
      config: this.config,
      storageService: this.storageService,
      navigationService: this.navigationService,
      httpClient: this.httpClient,
      enableDebugLogging: this.enableDebugLogging,
    })
  }
}

/**
 * 创建认证服务构建器实例
 */
export function authServiceBuilder(): AuthServiceBuilder {
  return new AuthServiceBuilder()
}