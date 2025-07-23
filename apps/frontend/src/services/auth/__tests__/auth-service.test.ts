/**
 * AuthService 主类单元测试
 * 测试重构后的认证服务主类的所有功能
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { AuthService } from '../auth-service'
import type {
  ITokenManager,
  IStorageService,
  INavigationService,
  IHttpClient,
  IAuthApiClient,
  AuthServiceConfig,
  AuthDependencies,
} from '../types'
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
} from '../../../types/auth'

describe('AuthService', () => {
  let authService: AuthService
  let mockTokenManager: ITokenManager
  let mockStorageService: IStorageService
  let mockNavigationService: INavigationService
  let mockHttpClient: IHttpClient
  let mockAuthApiClient: IAuthApiClient
  let mockConfig: AuthServiceConfig
  let mockDependencies: AuthDependencies

  // 测试数据
  const mockUser: User = {
    id: '1',
    email: 'test@example.com',
    name: 'Test User',
    is_verified: true,
    created_at: '2023-01-01T00:00:00Z',
    updated_at: '2023-01-01T00:00:00Z',
  }

  const mockLoginResponse: LoginResponse = {
    access_token: 'access_token_123',
    refresh_token: 'refresh_token_123',
    token_type: 'bearer',
    expires_in: 3600,
    user: mockUser,
  }

  beforeEach(() => {
    vi.clearAllMocks()

    // 创建所有依赖的 mock
    mockTokenManager = {
      getAccessToken: vi.fn(),
      getRefreshToken: vi.fn(),
      setTokens: vi.fn(),
      clearTokens: vi.fn(),
      hasValidAccessToken: vi.fn(),
      isTokenExpired: vi.fn(),
      scheduleRefresh: vi.fn(),
      cancelRefresh: vi.fn(),
      getTokenSummary: vi.fn(),
      destroy: vi.fn(),
      getTokenExpiration: vi.fn(),
      getTokenTimeToExpiry: vi.fn(),
      isTokenExpiringSoon: vi.fn(),
    }

    mockStorageService = {
      getItem: vi.fn(),
      setItem: vi.fn(),
      removeItem: vi.fn(),
      clear: vi.fn(),
    }

    mockNavigationService = {
      redirectTo: vi.fn(),
      getCurrentPath: vi.fn(),
      replace: vi.fn(),
      getSearchParams: vi.fn(),
    }

    mockHttpClient = {
      get: vi.fn(),
      post: vi.fn(),
      put: vi.fn(),
      delete: vi.fn(),
      setDefaultHeader: vi.fn(),
      removeDefaultHeader: vi.fn(),
      addRequestInterceptor: vi.fn(),
      addResponseInterceptor: vi.fn(),
      removeInterceptor: vi.fn(),
      clearAllInterceptors: vi.fn(),
      setBaseURL: vi.fn(),
      setTimeout: vi.fn(),
    }

    mockAuthApiClient = {
      login: vi.fn(),
      register: vi.fn(),
      logout: vi.fn(),
      refreshToken: vi.fn(),
      getCurrentUser: vi.fn(),
      updateProfile: vi.fn(),
      changePassword: vi.fn(),
      forgotPassword: vi.fn(),
      resetPassword: vi.fn(),
      verifyEmail: vi.fn(),
      resendVerification: vi.fn(),
      getHealthStatus: vi.fn(),
      getApiVersion: vi.fn(),
      validateEmails: vi.fn(),
      getUserSessions: vi.fn(),
      revokeSession: vi.fn(),
      revokeAllOtherSessions: vi.fn(),
      enableTwoFactor: vi.fn(),
      confirmTwoFactor: vi.fn(),
      disableTwoFactor: vi.fn(),
      generateBackupCodes: vi.fn(),
    }

    mockConfig = {
      apiBaseUrl: 'https://api.example.com',
      authApiPrefix: '/auth',
      timeout: 10000,
      useHttpOnlyCookies: false,
      tokenStorageKey: 'access_token',
      refreshTokenStorageKey: 'refresh_token',
      storageType: 'localStorage',
      navigationType: 'browser',
      httpClientType: 'axios',
      refreshThresholdMinutes: 5,
      enableAutoRefresh: true,
      loginPath: '/login',
    }

    mockDependencies = {
      tokenManager: mockTokenManager,
      storageService: mockStorageService,
      navigationService: mockNavigationService,
      httpClient: mockHttpClient,
      authApiClient: mockAuthApiClient,
      config: mockConfig,
    }
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('Initialization', () => {
    it('应该正确初始化所有依赖', () => {
      authService = new AuthService(mockDependencies)

      expect(mockHttpClient.addRequestInterceptor).toHaveBeenCalled()
      expect(mockHttpClient.addResponseInterceptor).toHaveBeenCalled()
    })

    it('应该在有有效令牌时开始自动刷新', () => {
      mockTokenManager.hasValidAccessToken.mockReturnValue(true)

      authService = new AuthService(mockDependencies)

      expect(mockTokenManager.scheduleRefresh).toHaveBeenCalled()
    })

    it('应该在没有有效令牌时不开始自动刷新', () => {
      mockTokenManager.hasValidAccessToken.mockReturnValue(false)

      authService = new AuthService(mockDependencies)

      expect(mockTokenManager.scheduleRefresh).not.toHaveBeenCalled()
    })

    it('应该在禁用自动刷新时不调度刷新', () => {
      const configWithoutAutoRefresh = { ...mockConfig, enableAutoRefresh: false }
      const dependenciesWithoutAutoRefresh = {
        ...mockDependencies,
        config: configWithoutAutoRefresh,
      }

      mockTokenManager.hasValidAccessToken.mockReturnValue(true)

      authService = new AuthService(dependenciesWithoutAutoRefresh)

      expect(mockTokenManager.scheduleRefresh).not.toHaveBeenCalled()
    })

    it('应该处理初始化错误', () => {
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

      mockHttpClient.addRequestInterceptor.mockImplementation(() => {
        throw new Error('Interceptor setup failed')
      })

      expect(() => {
        new AuthService(mockDependencies)
      }).not.toThrow()

      expect(consoleSpy).toHaveBeenCalledWith(
        expect.stringContaining('Failed to initialize AuthService'),
        expect.any(Error),
      )

      consoleSpy.mockRestore()
    })
  })

  describe('Authentication Operations', () => {
    beforeEach(() => {
      authService = new AuthService(mockDependencies)
    })

    describe('login', () => {
      it('应该能成功登录', async () => {
        mockAuthApiClient.login.mockResolvedValue(mockLoginResponse)

        const loginRequest: LoginRequest = {
          email: 'test@example.com',
          password: 'password123',
        }

        const result = await authService.login(loginRequest)

        expect(mockAuthApiClient.login).toHaveBeenCalledWith(loginRequest)
        expect(mockTokenManager.setTokens).toHaveBeenCalledWith(
          mockLoginResponse.access_token,
          mockLoginResponse.refresh_token,
        )
        expect(mockTokenManager.scheduleRefresh).toHaveBeenCalled()
        expect(result.success).toBe(true)
        expect(result.data).toEqual(mockLoginResponse)
        expect(result.message).toBe('Login successful')
      })

      it('应该在禁用自动刷新时不调度刷新', async () => {
        const configWithoutAutoRefresh = { ...mockConfig, enableAutoRefresh: false }
        const dependenciesWithoutAutoRefresh = {
          ...mockDependencies,
          config: configWithoutAutoRefresh,
        }
        const serviceWithoutAutoRefresh = new AuthService(dependenciesWithoutAutoRefresh)

        mockAuthApiClient.login.mockResolvedValue(mockLoginResponse)

        await serviceWithoutAutoRefresh.login({
          email: 'test@example.com',
          password: 'password123',
        })

        expect(mockTokenManager.setTokens).toHaveBeenCalled()
        expect(mockTokenManager.scheduleRefresh).not.toHaveBeenCalled()
      })

      it('应该处理登录错误', async () => {
        const loginError = new Error('Invalid credentials')
        mockAuthApiClient.login.mockRejectedValue(loginError)

        await expect(
          authService.login({
            email: 'test@example.com',
            password: 'wrong_password',
          }),
        ).rejects.toThrow('Invalid credentials')
      })
    })

    describe('register', () => {
      it('应该能成功注册', async () => {
        const registerRequest: RegisterRequest = {
          email: 'new@example.com',
          password: 'password123',
          name: 'New User',
        }

        const registerResponse = {
          user: mockUser,
          message: 'Registration successful',
        }

        mockAuthApiClient.register.mockResolvedValue(registerResponse)

        const result = await authService.register(registerRequest)

        expect(mockAuthApiClient.register).toHaveBeenCalledWith(registerRequest)
        expect(result.success).toBe(true)
        expect(result.data).toEqual(registerResponse)
        expect(result.message).toBe('Registration successful')
      })

      it('应该处理注册错误', async () => {
        const registerError = new Error('Email already exists')
        mockAuthApiClient.register.mockRejectedValue(registerError)

        await expect(
          authService.register({
            email: 'existing@example.com',
            password: 'password123',
            name: 'User',
          }),
        ).rejects.toThrow('Email already exists')
      })
    })

    describe('logout', () => {
      it('应该能成功登出', async () => {
        mockAuthApiClient.logout.mockResolvedValue()

        const result = await authService.logout()

        expect(mockTokenManager.cancelRefresh).toHaveBeenCalled()
        expect(mockAuthApiClient.logout).toHaveBeenCalled()
        expect(mockTokenManager.clearTokens).toHaveBeenCalled()
        expect(result.success).toBe(true)
        expect(result.message).toBe('Logged out successfully')
      })

      it('应该在 API 调用失败时仍然清理本地状态', async () => {
        const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})

        const logoutError = new Error('Logout API failed')
        mockAuthApiClient.logout.mockRejectedValue(logoutError)

        const result = await authService.logout()

        expect(mockTokenManager.cancelRefresh).toHaveBeenCalled()
        expect(mockTokenManager.clearTokens).toHaveBeenCalled()
        expect(consoleSpy).toHaveBeenCalledWith('Logout API call failed:', logoutError)
        expect(result.success).toBe(true)
        expect(result.message).toBe('Logged out successfully')

        consoleSpy.mockRestore()
      })
    })
  })

  describe('User Management', () => {
    beforeEach(() => {
      authService = new AuthService(mockDependencies)
    })

    describe('getCurrentUser', () => {
      it('应该能获取当前用户信息', async () => {
        mockAuthApiClient.getCurrentUser.mockResolvedValue(mockUser)

        const result = await authService.getCurrentUser()

        expect(mockAuthApiClient.getCurrentUser).toHaveBeenCalled()
        expect(result.success).toBe(true)
        expect(result.data).toEqual(mockUser)
        expect(result.message).toBe('User profile retrieved successfully')
      })

      it('应该处理获取用户信息错误', async () => {
        const userError = new Error('User not found')
        mockAuthApiClient.getCurrentUser.mockRejectedValue(userError)

        await expect(authService.getCurrentUser()).rejects.toThrow('User not found')
      })
    })

    describe('updateProfile', () => {
      it('应该能更新用户资料', async () => {
        const updateRequest: UpdateProfileRequest = {
          name: 'Updated Name',
        }

        const updatedUser = { ...mockUser, name: 'Updated Name' }
        mockAuthApiClient.updateProfile.mockResolvedValue(updatedUser)

        const result = await authService.updateProfile(updateRequest)

        expect(mockAuthApiClient.updateProfile).toHaveBeenCalledWith(updateRequest)
        expect(result.success).toBe(true)
        expect(result.data).toEqual(updatedUser)
        expect(result.message).toBe('Profile updated successfully')
      })
    })

    describe('changePassword', () => {
      it('应该能修改密码', async () => {
        const changePasswordRequest: ChangePasswordRequest = {
          current_password: 'old_password',
          new_password: 'new_password',
        }

        mockAuthApiClient.changePassword.mockResolvedValue()

        const result = await authService.changePassword(changePasswordRequest)

        expect(mockAuthApiClient.changePassword).toHaveBeenCalledWith(changePasswordRequest)
        expect(result.success).toBe(true)
        expect(result.message).toBe('Password changed successfully')
      })
    })
  })

  describe('Password Reset', () => {
    beforeEach(() => {
      authService = new AuthService(mockDependencies)
    })

    describe('forgotPassword', () => {
      it('应该能发送忘记密码请求', async () => {
        const forgotPasswordRequest: ForgotPasswordRequest = {
          email: 'test@example.com',
        }

        mockAuthApiClient.forgotPassword.mockResolvedValue()

        const result = await authService.forgotPassword(forgotPasswordRequest)

        expect(mockAuthApiClient.forgotPassword).toHaveBeenCalledWith(forgotPasswordRequest)
        expect(result.success).toBe(true)
        expect(result.message).toBe('Password reset email sent')
      })
    })

    describe('resetPassword', () => {
      it('应该能重置密码', async () => {
        const resetPasswordRequest: ResetPasswordRequest = {
          token: 'reset_token',
          new_password: 'new_password',
        }

        mockAuthApiClient.resetPassword.mockResolvedValue()

        const result = await authService.resetPassword(resetPasswordRequest)

        expect(mockAuthApiClient.resetPassword).toHaveBeenCalledWith(resetPasswordRequest)
        expect(result.success).toBe(true)
        expect(result.message).toBe('Password reset successfully')
      })
    })
  })

  describe('Email Verification', () => {
    beforeEach(() => {
      authService = new AuthService(mockDependencies)
    })

    describe('verifyEmail', () => {
      it('应该能验证邮箱', async () => {
        const token = 'verification_token'

        mockAuthApiClient.verifyEmail.mockResolvedValue()

        const result = await authService.verifyEmail(token)

        expect(mockAuthApiClient.verifyEmail).toHaveBeenCalledWith(token)
        expect(result.success).toBe(true)
        expect(result.message).toBe('Email verified successfully')
      })
    })

    describe('resendVerification', () => {
      it('应该能重发验证邮件', async () => {
        const resendRequest: ResendVerificationRequest = {
          email: 'test@example.com',
        }

        mockAuthApiClient.resendVerification.mockResolvedValue()

        const result = await authService.resendVerification(resendRequest)

        expect(mockAuthApiClient.resendVerification).toHaveBeenCalledWith(resendRequest)
        expect(result.success).toBe(true)
        expect(result.message).toBe('Verification email resent')
      })
    })
  })

  describe('Token Management', () => {
    beforeEach(() => {
      authService = new AuthService(mockDependencies)
    })

    describe('getAccessToken', () => {
      it('应该返回访问令牌', () => {
        const token = 'access_token_123'
        mockTokenManager.getAccessToken.mockReturnValue(token)

        const result = authService.getAccessToken()

        expect(mockTokenManager.getAccessToken).toHaveBeenCalled()
        expect(result).toBe(token)
      })

      it('应该在没有令牌时返回 null', () => {
        mockTokenManager.getAccessToken.mockReturnValue(null)

        const result = authService.getAccessToken()

        expect(result).toBeNull()
      })
    })

    describe('isAuthenticated', () => {
      it('应该在有有效令牌时返回 true', () => {
        mockTokenManager.hasValidAccessToken.mockReturnValue(true)

        const result = authService.isAuthenticated()

        expect(mockTokenManager.hasValidAccessToken).toHaveBeenCalled()
        expect(result).toBe(true)
      })

      it('应该在没有有效令牌时返回 false', () => {
        mockTokenManager.hasValidAccessToken.mockReturnValue(false)

        const result = authService.isAuthenticated()

        expect(result).toBe(false)
      })
    })

    describe('refreshTokens', () => {
      it('应该能手动刷新令牌', async () => {
        const refreshResponse = {
          access_token: 'new_access_token',
          refresh_token: 'new_refresh_token',
          token_type: 'bearer',
          expires_in: 3600,
        }

        mockTokenManager.getRefreshToken.mockReturnValue('refresh_token')
        mockAuthApiClient.refreshToken.mockResolvedValue(refreshResponse)

        await authService.refreshTokens()

        expect(mockAuthApiClient.refreshToken).toHaveBeenCalledWith('refresh_token')
        expect(mockTokenManager.setTokens).toHaveBeenCalledWith(
          refreshResponse.access_token,
          refreshResponse.refresh_token,
        )
      })

      it('应该处理刷新令牌失败', async () => {
        const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

        const refreshError = new Error('Refresh token expired')
        mockTokenManager.getRefreshToken.mockReturnValue('refresh_token')
        mockAuthApiClient.refreshToken.mockRejectedValue(refreshError)

        await expect(authService.refreshTokens()).rejects.toThrow('Refresh token expired')

        expect(mockTokenManager.clearTokens).toHaveBeenCalled()
        expect(mockNavigationService.redirectTo).toHaveBeenCalledWith('/login')

        consoleSpy.mockRestore()
      })

      it('应该防止并发刷新请求', async () => {
        const refreshResponse = {
          access_token: 'new_access_token',
          refresh_token: 'new_refresh_token',
          token_type: 'bearer',
          expires_in: 3600,
        }

        mockTokenManager.getRefreshToken.mockReturnValue('refresh_token')
        mockAuthApiClient.refreshToken.mockResolvedValue(refreshResponse)

        // 发起多个并发刷新请求
        const promises = [
          authService.refreshTokens(),
          authService.refreshTokens(),
          authService.refreshTokens(),
        ]

        await Promise.all(promises)

        // API 应该只被调用一次
        expect(mockAuthApiClient.refreshToken).toHaveBeenCalledTimes(1)
      })
    })
  })

  describe('HTTP Interceptors', () => {
    let requestInterceptor: any
    let responseInterceptor: any

    beforeEach(() => {
      mockHttpClient.addRequestInterceptor.mockImplementation((fulfilled) => {
        requestInterceptor = fulfilled
        return 1
      })

      mockHttpClient.addResponseInterceptor.mockImplementation((fulfilled, rejected) => {
        responseInterceptor = { fulfilled, rejected }
        return 2
      })

      authService = new AuthService(mockDependencies)
    })

    describe('Request Interceptor', () => {
      it('应该在有令牌时添加授权头', () => {
        mockTokenManager.getAccessToken.mockReturnValue('access_token_123')

        const config = { headers: {} }
        const result = requestInterceptor(config)

        expect(result.headers.Authorization).toBe('Bearer access_token_123')
      })

      it('应该在没有令牌时不添加授权头', () => {
        mockTokenManager.getAccessToken.mockReturnValue(null)

        const config = { headers: {} }
        const result = requestInterceptor(config)

        expect(result.headers.Authorization).toBeUndefined()
      })

      it('应该处理空的 headers 对象', () => {
        mockTokenManager.getAccessToken.mockReturnValue('access_token_123')

        const config = {}
        const result = requestInterceptor(config)

        expect(result.headers).toBeDefined()
        expect(result.headers.Authorization).toBe('Bearer access_token_123')
      })
    })

    describe('Response Interceptor', () => {
      it('应该直接返回成功响应', () => {
        const response = { status: 200, data: { success: true } }

        const result = responseInterceptor.fulfilled(response)

        expect(result).toBe(response)
      })

      it('应该在 401 错误时尝试刷新令牌', async () => {
        const originalRequest = {
          url: '/api/users',
          headers: {},
          _retry: undefined,
        }

        const error = {
          response: { status: 401 },
          config: originalRequest,
        }

        const refreshResponse = {
          access_token: 'new_access_token',
          refresh_token: 'new_refresh_token',
          token_type: 'bearer',
          expires_in: 3600,
        }

        mockTokenManager.hasValidAccessToken.mockReturnValue(true)
        mockTokenManager.getRefreshToken.mockReturnValue('refresh_token')
        mockAuthApiClient.refreshToken.mockResolvedValue(refreshResponse)
        mockTokenManager.getAccessToken.mockReturnValue('new_access_token')
        mockHttpClient.get.mockResolvedValue({ status: 200, data: {} })

        await responseInterceptor.rejected(error)

        expect(originalRequest._retry).toBe(true)
        expect(mockAuthApiClient.refreshToken).toHaveBeenCalled()
        expect(mockTokenManager.setTokens).toHaveBeenCalledWith(
          refreshResponse.access_token,
          refreshResponse.refresh_token,
        )
        expect(mockHttpClient.get).toHaveBeenCalledWith('/api/users', originalRequest)
      })

      it('应该跳过认证端点的令牌刷新', async () => {
        const originalRequest = {
          url: '/auth/login',
          headers: {},
        }

        const error = {
          response: { status: 401 },
          config: originalRequest,
        }

        await expect(responseInterceptor.rejected(error)).rejects.toEqual(error)

        expect(mockAuthApiClient.refreshToken).not.toHaveBeenCalled()
      })

      it('应该跳过已重试的请求', async () => {
        const originalRequest = {
          url: '/api/users',
          headers: {},
          _retry: true,
        }

        const error = {
          response: { status: 401 },
          config: originalRequest,
        }

        await expect(responseInterceptor.rejected(error)).rejects.toEqual(error)

        expect(mockAuthApiClient.refreshToken).not.toHaveBeenCalled()
      })

      it('应该跳过未认证用户的令牌刷新', async () => {
        const originalRequest = {
          url: '/api/users',
          headers: {},
        }

        const error = {
          response: { status: 401 },
          config: originalRequest,
        }

        mockTokenManager.hasValidAccessToken.mockReturnValue(false)

        await expect(responseInterceptor.rejected(error)).rejects.toEqual(error)

        expect(mockAuthApiClient.refreshToken).not.toHaveBeenCalled()
      })

      it('应该在刷新失败时清理状态并重定向', async () => {
        const originalRequest = {
          url: '/api/users',
          headers: {},
        }

        const error = {
          response: { status: 401 },
          config: originalRequest,
        }

        const refreshError = new Error('Refresh failed')

        mockTokenManager.hasValidAccessToken.mockReturnValue(true)
        mockTokenManager.getRefreshToken.mockReturnValue('refresh_token')
        mockAuthApiClient.refreshToken.mockRejectedValue(refreshError)

        await expect(responseInterceptor.rejected(error)).rejects.toEqual(refreshError)

        expect(mockTokenManager.clearTokens).toHaveBeenCalled()
        expect(mockNavigationService.redirectTo).toHaveBeenCalledWith('/login')
      })

      it('应该处理非 401 错误', async () => {
        const error = {
          response: { status: 500 },
          config: { url: '/api/users' },
        }

        await expect(responseInterceptor.rejected(error)).rejects.toEqual(error)

        expect(mockAuthApiClient.refreshToken).not.toHaveBeenCalled()
      })
    })
  })

  describe('Service Management', () => {
    beforeEach(() => {
      authService = new AuthService(mockDependencies)
    })

    describe('getServiceStatus', () => {
      it('应该返回服务状态摘要', () => {
        const tokenSummary = {
          hasAccessToken: true,
          hasRefreshToken: true,
          accessTokenExpiry: new Date(),
          isAccessTokenValid: true,
          isAccessTokenExpiringSoon: false,
          timeToRefresh: 3600,
        }

        mockTokenManager.hasValidAccessToken.mockReturnValue(true)
        mockTokenManager.getTokenSummary.mockReturnValue(tokenSummary)

        const status = authService.getServiceStatus()

        expect(status).toEqual({
          isInitialized: true,
          isAuthenticated: true,
          tokenInfo: tokenSummary,
          config: mockConfig,
        })
      })
    })

    describe('destroy', () => {
      it('应该清理所有资源', () => {
        authService.destroy()

        expect(mockTokenManager.cancelRefresh).toHaveBeenCalled()
        expect(mockHttpClient.clearAllInterceptors).toHaveBeenCalled()
        expect(mockTokenManager.destroy).toHaveBeenCalled()
      })

      it('应该处理没有可选方法的依赖', () => {
        // 创建没有可选方法的 mock
        const limitedHttpClient = {
          ...mockHttpClient,
          clearAllInterceptors: undefined,
        }

        const limitedTokenManager = {
          ...mockTokenManager,
          destroy: undefined,
        }

        const limitedDependencies = {
          ...mockDependencies,
          httpClient: limitedHttpClient,
          tokenManager: limitedTokenManager,
        }

        const limitedService = new AuthService(limitedDependencies)

        expect(() => {
          limitedService.destroy()
        }).not.toThrow()
      })
    })

    describe('forceTokenExpiry', () => {
      it('应该在开发/测试环境中清除令牌', () => {
        process.env.NODE_ENV = 'test'

        authService.forceTokenExpiry()

        expect(mockTokenManager.clearTokens).toHaveBeenCalled()
      })

      it('应该在生产环境中不清除令牌', () => {
        process.env.NODE_ENV = 'production'

        authService.forceTokenExpiry()

        expect(mockTokenManager.clearTokens).not.toHaveBeenCalled()
      })
    })

    describe('getExtendedApi', () => {
      it('应该返回扩展的 API 客户端', () => {
        const result = authService.getExtendedApi()

        expect(result).toBe(mockAuthApiClient)
      })
    })
  })

  describe('Edge Cases', () => {
    beforeEach(() => {
      authService = new AuthService(mockDependencies)
    })

    it('应该防止重复初始化', () => {
      // 第一次创建已经调用了初始化
      expect(mockHttpClient.addRequestInterceptor).toHaveBeenCalledTimes(1)
      expect(mockHttpClient.addResponseInterceptor).toHaveBeenCalledTimes(1)

      // 手动调用初始化应该不会重复执行
      const initializeMethod = (authService as any).initialize
      initializeMethod.call(authService)

      expect(mockHttpClient.addRequestInterceptor).toHaveBeenCalledTimes(1)
      expect(mockHttpClient.addResponseInterceptor).toHaveBeenCalledTimes(1)
    })

    it('应该正确判断认证端点', () => {
      const isAuthEndpoint = (authService as any).isAuthEndpoint

      expect(isAuthEndpoint('/auth/login')).toBe(true)
      expect(isAuthEndpoint('/auth/register')).toBe(true)
      expect(isAuthEndpoint('/auth/refresh')).toBe(true)
      expect(isAuthEndpoint('/auth/logout')).toBe(true)
      expect(isAuthEndpoint('/api/users')).toBe(false)
      expect(isAuthEndpoint('/api/profile')).toBe(false)
      expect(isAuthEndpoint('')).toBe(false)
      expect(isAuthEndpoint(undefined)).toBe(false)
    })

    it('应该处理没有 config 的请求拦截器', () => {
      mockHttpClient.addRequestInterceptor.mockImplementation((fulfilled) => {
        const error = new Error('Request interceptor error')
        const rejectedError = fulfilled(undefined)
        return Promise.reject(rejectedError)
      })

      expect(() => {
        new AuthService(mockDependencies)
      }).not.toThrow()
    })

    it('应该处理响应拦截器中的空 config', async () => {
      let rejectedHandler: any

      mockHttpClient.addResponseInterceptor.mockImplementation((fulfilled, rejected) => {
        rejectedHandler = rejected
        return 1
      })

      new AuthService(mockDependencies)

      const error = {
        response: { status: 401 },
        config: null,
      }

      await expect(rejectedHandler(error)).rejects.toEqual(error)
    })
  })
})
