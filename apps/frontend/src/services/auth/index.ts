/**
 * 认证服务模块统一导出
 * 重构后的高内聚低耦合认证架构
 */

// 核心接口和类型
export type {
  AuthDependencies,
  AuthEvent,
  AuthEventListener,
  // 事件和回调
  AuthEventType,
  // 配置和依赖注入
  AuthServiceConfig,
  AuthServiceFactoryOptions,
  AuthStateChangeListener,
  ErrorHandler,
  IAuthApiClient,
  // 服务接口
  IAuthService,
  IHttpClient,
  INavigationService,
  IStorageService,
  ITokenManager,
  TokenRefreshCallback,
} from './types'

// 核心实现类
export { AuthApiClient } from './auth-api-client'
export { AuthService } from './auth-service'
export { TokenManager } from './token-manager'

// 导入 AuthService 类用于类型守卫
import { AuthService } from './auth-service'
import type { AuthServiceConfig } from './types'

// 存储服务
export {
  createStorageService,
  LocalStorageService,
  MemoryStorageService,
  SessionStorageService,
} from './storage'

// 导航服务
export {
  BrowserNavigationService,
  createAutoNavigationService,
  createNavigationService,
  HistoryNavigationService,
  MockNavigationService,
  NavigationUtils,
} from './navigation'

// HTTP 客户端
export {
  AxiosHttpClient,
  createAutoHttpClient,
  createHttpClient,
  FetchHttpClient,
  MockHttpClient,
} from './http-client'

// 工厂函数
export {
  AuthServiceBuilder,
  authServiceBuilder,
  createAuthService,
  createDevelopmentAuthService,
  createEnvironmentAuthService,
  createProductionAuthService,
  createTestAuthService,
  getDefaultAuthServiceConfig,
  getEnvironmentConfig,
  validateAuthServiceConfig,
} from './factory'

// 导入工厂函数用于内部使用
import {
  createAuthService,
  createDevelopmentAuthService,
  createEnvironmentAuthService,
  createProductionAuthService,
  createTestAuthService,
  validateAuthServiceConfig,
} from './factory'

// 便利的默认导出
export {
  // 快速创建服务的函数
  createAuthService as default,
} from './factory'

/**
 * 版本信息
 */
export const AUTH_SERVICE_VERSION = '2.0.0'

/**
 * 快速开始助手函数
 * 为最常见的使用场景提供简化的接口
 */
export const QuickStart = {
  /**
   * 创建默认认证服务（适用于大多数应用）
   */
  createDefault: (apiBaseUrl?: string) => {
    return createEnvironmentAuthService(undefined, {
      apiBaseUrl: apiBaseUrl || import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
    })
  },

  /**
   * 创建开发环境服务（启用调试和更短的刷新间隔）
   */
  createDev: (apiBaseUrl?: string) => {
    return createDevelopmentAuthService({
      apiBaseUrl: apiBaseUrl || import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
    })
  },

  /**
   * 创建测试服务（使用内存存储和模拟服务）
   */
  createTest: (mockResponses?: Record<string, any>) => {
    return createTestAuthService({
      mockResponses,
      enableLogging: false,
    })
  },

  /**
   * 创建生产环境服务（优化的安全配置）
   */
  createProd: (apiBaseUrl: string) => {
    return createProductionAuthService({
      apiBaseUrl,
    })
  },
}

/**
 * 迁移助手
 * 帮助从旧版 AuthService 迁移到新架构
 */
export const Migration = {
  /**
   * 创建向后兼容的认证服务
   * 保持与原有 API 的完全兼容性
   */
  createCompatible: () => {
    return createAuthService({
      config: {
        // 使用与原服务相同的配置
        apiBaseUrl: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
        authApiPrefix: '/api/v1/auth',
        accessTokenKey: 'access_token',
        useHttpOnlyCookies: true,
        loginPath: '/login',
        enableAutoRefresh: true,
      },
    })
  },

  /**
   * 检查配置兼容性
   */
  checkCompatibility: (config: any) => {
    return validateAuthServiceConfig(config)
  },
}

/**
 * 调试工具
 */
export const Debug = {
  /**
   * 获取服务状态信息
   */
  getServiceStatus: (authService: any) => {
    if ('getServiceStatus' in authService) {
      return authService.getServiceStatus()
    }
    return null
  },

  /**
   * 获取令牌信息
   */
  getTokenInfo: (authService: any) => {
    if ('getServiceStatus' in authService) {
      return authService.getServiceStatus().tokenInfo
    }
    return null
  },

  /**
   * 启用调试日志
   */
  enableLogging: () => {
    if (typeof window !== 'undefined') {
      ;(window as any).__AUTH_DEBUG__ = true
    }
  },

  /**
   * 禁用调试日志
   */
  disableLogging: () => {
    if (typeof window !== 'undefined') {
      ;(window as any).__AUTH_DEBUG__ = false
    }
  },
}

/**
 * 类型守卫
 */
export const TypeGuards = {
  /**
   * 检查是否是新版认证服务
   */
  isNewAuthService: (authService: any): authService is AuthService => {
    return authService && typeof authService.getServiceStatus === 'function'
  },

  /**
   * 检查是否是有效的配置
   */
  isValidConfig: (config: any): config is AuthServiceConfig => {
    return (
      config &&
      typeof config.apiBaseUrl === 'string' &&
      typeof config.authApiPrefix === 'string' &&
      typeof config.accessTokenKey === 'string'
    )
  },
}

/**
 * 使用示例（注释掉的代码，仅作参考）
 */
/*
// 基本使用
import { QuickStart } from './services/auth'
const authService = QuickStart.createDefault()

// 高级配置
import { authServiceBuilder } from './services/auth'
const authService = authServiceBuilder()
  .withConfig({ apiBaseUrl: 'https://api.example.com' })
  .withDebugLogging(true)
  .build()

// 测试环境
import { QuickStart } from './services/auth'
const testAuthService = QuickStart.createTest({
  'POST /login': { data: { access_token: 'test-token', user: { id: 1 } } }
})

// 检查兼容性
import { Migration } from './services/auth'
const { isValid, errors } = Migration.checkCompatibility(config)
*/
