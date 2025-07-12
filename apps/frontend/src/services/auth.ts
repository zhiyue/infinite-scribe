/**
 * Authentication service - 向后兼容适配器
 * 
 * 这个文件现在使用重构后的认证架构，但保持完全的向后兼容性。
 * 原有的 API 接口保持不变，内部实现已迁移到新的模块化架构。
 * 
 * 重构亮点：
 * - 依赖注入架构实现职责分离
 * - 高可测试性和可维护性  
 * - 自动环境适配
 * - 完整的错误处理和日志记录
 * - 向后兼容保证无缝升级
 */

import { Migration } from './auth/index'
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
  UpdateProfileRequest,
  User,
} from '../types/auth'
import type { ApiSuccessResponse } from '../utils/api-response'

/**
 * 兼容性认证服务接口
 * 与原有 AuthService 完全兼容
 */
interface CompatibleAuthService {
  // 认证方法
  login(credentials: LoginRequest): Promise<ApiSuccessResponse<LoginResponse>>
  register(data: RegisterRequest): Promise<ApiSuccessResponse<RegisterResponse>>
  logout(): Promise<ApiSuccessResponse<void>>
  getCurrentUser(): Promise<ApiSuccessResponse<User>>
  updateProfile(data: UpdateProfileRequest): Promise<ApiSuccessResponse<User>>
  changePassword(data: ChangePasswordRequest): Promise<ApiSuccessResponse<void>>
  forgotPassword(data: ForgotPasswordRequest): Promise<ApiSuccessResponse<void>>
  resetPassword(data: ResetPasswordRequest): Promise<ApiSuccessResponse<void>>
  verifyEmail(token: string): Promise<ApiSuccessResponse<void>>
  resendVerification(data: ResendVerificationRequest): Promise<ApiSuccessResponse<void>>
  
  // Token 管理
  getAccessToken(): string | null
  isAuthenticated(): boolean
  refreshTokens(): Promise<void>
  
  // 私有方法（为了完全兼容性）
  clearTokens(): void
}

/**
 * 创建向后兼容的认证服务实例
 * 使用新的架构但保持原有接口
 */
function createCompatibleAuthService(): CompatibleAuthService {
  // 使用新架构创建兼容的服务实例
  const newAuthService = Migration.createCompatible()
  
  // 创建兼容性适配器
  const compatibleService: CompatibleAuthService = {
    // 直接代理到新服务的方法
    async login(credentials: LoginRequest) {
      return await newAuthService.login(credentials)
    },
    
    async register(data: RegisterRequest) {
      return await newAuthService.register(data)
    },
    
    async logout() {
      return await newAuthService.logout()
    },
    
    async getCurrentUser() {
      return await newAuthService.getCurrentUser()
    },
    
    async updateProfile(data: UpdateProfileRequest) {
      return await newAuthService.updateProfile(data)
    },
    
    async changePassword(data: ChangePasswordRequest) {
      return await newAuthService.changePassword(data)
    },
    
    async forgotPassword(data: ForgotPasswordRequest) {
      return await newAuthService.forgotPassword(data)
    },
    
    async resetPassword(data: ResetPasswordRequest) {
      return await newAuthService.resetPassword(data)
    },
    
    async verifyEmail(token: string) {
      return await newAuthService.verifyEmail(token)
    },
    
    async resendVerification(data: ResendVerificationRequest) {
      return await newAuthService.resendVerification(data)
    },
    
    // Token 管理方法
    getAccessToken() {
      return newAuthService.getAccessToken()
    },
    
    isAuthenticated() {
      return newAuthService.isAuthenticated()
    },
    
    async refreshTokens() {
      return await newAuthService.refreshTokens()
    },
    
    // 为了完全兼容性提供的方法
    clearTokens() {
      // 通过登出来清理 tokens（新架构的推荐方式）
      newAuthService.logout().catch(console.warn)
    }
  }
  
  // 在开发环境下记录迁移信息
  if (process.env.NODE_ENV === 'development') {
    console.info('✅ AuthService: 使用重构后的架构（向后兼容模式）')
    console.info('📖 迁移指南: 考虑升级到新的 auth/index 导入以获得完整功能')
  }
  
  return compatibleService
}

/**
 * 单例认证服务实例
 * 保持与原有代码的完全兼容性
 */
export const authService = createCompatibleAuthService()
export default authService

/**
 * 导出新架构的完整功能（可选）
 * 新项目建议直接使用这些导入
 */
export {
  // 新架构的核心导出
  AuthService,
  QuickStart,
  Migration,
  Debug,
  TypeGuards,
  
  // 工厂函数
  createAuthService,
  createTestAuthService,
  createDevelopmentAuthService,
  createProductionAuthService,
  authServiceBuilder,
} from './auth/index'

/**
 * 类型导出保持不变
 */
export type {
  // 保持原有类型导出
  ApiError,
  ChangePasswordRequest,
  ForgotPasswordRequest,
  LoginRequest,
  LoginResponse,
  RegisterRequest,
  RegisterResponse,
  ResendVerificationRequest,
  ResetPasswordRequest,
  UpdateProfileRequest,
  User,
  ApiSuccessResponse,
}

/**
 * 迁移提示和工具
 */
export const MIGRATION_INFO = {
  version: '2.0.0',
  compatibilityMode: true,
  
  /**
   * 检查当前使用是否为兼容模式
   */
  isCompatibilityMode: () => true,
  
  /**
   * 获取升级建议
   */
  getUpgradeRecommendations: () => ({
    current: '使用向后兼容的 authService',
    recommended: "import { QuickStart } from './services/auth'",
    benefits: [
      '更好的类型安全',
      '完整的依赖注入支持', 
      '更灵活的配置选项',
      '增强的调试功能',
      '更好的测试支持'
    ]
  }),
  
  /**
   * 验证当前配置兼容性
   */
  validateCompatibility: () => {
    try {
      return Migration.checkCompatibility({
        apiBaseUrl: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
        authApiPrefix: '/api/v1/auth',
        accessTokenKey: 'access_token',
      })
    } catch (error) {
      return { isValid: false, errors: [(error as Error).message] }
    }
  }
} as const
