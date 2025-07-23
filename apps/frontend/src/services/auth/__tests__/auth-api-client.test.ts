/**
 * AuthApiClient 单元测试
 * 测试所有认证 API 客户端的功能
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { AuthApiClient } from '../auth-api-client'
import type { IHttpClient, AuthServiceConfig } from '../types'
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
} from '../../../types/auth'

describe('AuthApiClient', () => {
  let authApiClient: AuthApiClient
  let mockHttpClient: IHttpClient
  let mockConfig: AuthServiceConfig

  beforeEach(() => {
    // 创建 HttpClient 的 mock
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
      setBaseURL: vi.fn(),
      setTimeout: vi.fn(),
    } as any

    // 创建配置 mock
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
    }

    authApiClient = new AuthApiClient(mockHttpClient, mockConfig)
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  describe('Initialization', () => {
    it('应该正确设置 HTTP 客户端', () => {
      expect(mockHttpClient.setBaseURL).toHaveBeenCalledWith('https://api.example.com/auth')
      expect(mockHttpClient.setTimeout).toHaveBeenCalledWith(10000)
      expect(mockHttpClient.setDefaultHeader).toHaveBeenCalledWith(
        'Content-Type',
        'application/json',
      )
    })

    it('应该处理没有 setBaseURL 方法的 HTTP 客户端', () => {
      const httpClientWithoutSetBaseURL = {
        ...mockHttpClient,
        setBaseURL: undefined,
      } as any

      expect(() => {
        new AuthApiClient(httpClientWithoutSetBaseURL, mockConfig)
      }).not.toThrow()
    })
  })

  describe('Authentication Operations', () => {
    describe('login', () => {
      it('应该能成功登录', async () => {
        const loginRequest: LoginRequest = {
          email: 'test@example.com',
          password: 'password123',
        }

        const loginResponse: LoginResponse = {
          access_token: 'access_token_123',
          refresh_token: 'refresh_token_123',
          token_type: 'bearer',
          expires_in: 3600,
          user: {
            id: '1',
            email: 'test@example.com',
            name: 'Test User',
            is_verified: true,
            created_at: '2023-01-01T00:00:00Z',
            updated_at: '2023-01-01T00:00:00Z',
          },
        }

        mockHttpClient.post.mockResolvedValue({
          data: loginResponse,
          status: 200,
          statusText: 'OK',
          headers: {},
          config: {},
          request: {},
        })

        const result = await authApiClient.login(loginRequest)

        expect(mockHttpClient.post).toHaveBeenCalledWith('/login', loginRequest, {
          withCredentials: false,
        })
        expect(result).toEqual(loginResponse)
      })

      it('应该在使用 httpOnly cookies 时设置 withCredentials', async () => {
        const configWithHttpOnly = { ...mockConfig, useHttpOnlyCookies: true }
        const apiClientWithHttpOnly = new AuthApiClient(mockHttpClient, configWithHttpOnly)

        mockHttpClient.post.mockResolvedValue({
          data: { access_token: 'token' },
          status: 200,
          statusText: 'OK',
          headers: {},
          config: {},
          request: {},
        })

        await apiClientWithHttpOnly.login({
          email: 'test@example.com',
          password: 'password123',
        })

        expect(mockHttpClient.post).toHaveBeenCalledWith('/login', expect.any(Object), {
          withCredentials: true,
        })
      })

      it('应该处理无效的登录响应', async () => {
        mockHttpClient.post.mockResolvedValue({
          data: null,
          status: 200,
          statusText: 'OK',
          headers: {},
          config: {},
          request: {},
        })

        await expect(
          authApiClient.login({
            email: 'test@example.com',
            password: 'password123',
          }),
        ).rejects.toThrow('Invalid login response')
      })

      it('应该处理登录错误', async () => {
        const mockError = {
          response: {
            status: 401,
            data: { detail: 'Invalid credentials' },
          },
        }

        mockHttpClient.post.mockRejectedValue(mockError)

        try {
          await authApiClient.login({
            email: 'test@example.com',
            password: 'wrong_password',
          })
        } catch (error: any) {
          expect(error.detail).toBe('Invalid credentials')
          expect(error.status_code).toBe(401)
        }
      })
    })

    describe('register', () => {
      it('应该能成功注册', async () => {
        const registerRequest: RegisterRequest = {
          email: 'new@example.com',
          password: 'password123',
          name: 'New User',
        }

        const registerResponse: RegisterResponse = {
          user: {
            id: '2',
            email: 'new@example.com',
            name: 'New User',
            is_verified: false,
            created_at: '2023-01-01T00:00:00Z',
            updated_at: '2023-01-01T00:00:00Z',
          },
          message: 'Registration successful',
        }

        mockHttpClient.post.mockResolvedValue({
          data: registerResponse,
          status: 201,
          statusText: 'Created',
          headers: {},
          config: {},
          request: {},
        })

        const result = await authApiClient.register(registerRequest)

        expect(mockHttpClient.post).toHaveBeenCalledWith('/register', registerRequest)
        expect(result).toEqual(registerResponse)
      })

      it('应该处理注册错误', async () => {
        const mockError = {
          response: {
            status: 400,
            data: { detail: 'Email already exists' },
          },
        }

        mockHttpClient.post.mockRejectedValue(mockError)

        try {
          await authApiClient.register({
            email: 'existing@example.com',
            password: 'password123',
            name: 'User',
          })
        } catch (error: any) {
          expect(error.detail).toBe('Email already exists')
          expect(error.status_code).toBe(400)
        }
      })
    })

    describe('logout', () => {
      it('应该能成功登出', async () => {
        mockHttpClient.post.mockResolvedValue({
          data: {},
          status: 200,
          statusText: 'OK',
          headers: {},
          config: {},
          request: {},
        })

        await authApiClient.logout()

        expect(mockHttpClient.post).toHaveBeenCalledWith(
          '/logout',
          {},
          {
            withCredentials: false,
          },
        )
      })

      it('应该处理登出错误但不阻断流程', async () => {
        const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})

        const mockError = {
          response: {
            status: 500,
            data: { detail: 'Server error' },
          },
        }

        mockHttpClient.post.mockRejectedValue(mockError)

        try {
          await authApiClient.logout()
        } catch (error: any) {
          expect(error.detail).toBe('Server error')
          expect(consoleSpy).toHaveBeenCalledWith('Logout API call failed:', mockError)
        }

        consoleSpy.mockRestore()
      })
    })

    describe('refreshToken', () => {
      it('应该能成功刷新令牌（非 httpOnly cookies）', async () => {
        const refreshToken = 'refresh_token_123'
        const tokenResponse: TokenResponse = {
          access_token: 'new_access_token',
          refresh_token: 'new_refresh_token',
          token_type: 'bearer',
          expires_in: 3600,
        }

        mockHttpClient.post.mockResolvedValue({
          data: tokenResponse,
          status: 200,
          statusText: 'OK',
          headers: {},
          config: {},
          request: {},
        })

        const result = await authApiClient.refreshToken(refreshToken)

        expect(mockHttpClient.post).toHaveBeenCalledWith(
          '/refresh',
          {
            refresh_token: refreshToken,
          },
          {
            withCredentials: false,
          },
        )
        expect(result).toEqual(tokenResponse)
      })

      it('应该在 httpOnly cookies 模式下不发送 refresh token', async () => {
        const configWithHttpOnly = { ...mockConfig, useHttpOnlyCookies: true }
        const apiClientWithHttpOnly = new AuthApiClient(mockHttpClient, configWithHttpOnly)

        mockHttpClient.post.mockResolvedValue({
          data: { access_token: 'new_token' },
          status: 200,
          statusText: 'OK',
          headers: {},
          config: {},
          request: {},
        })

        await apiClientWithHttpOnly.refreshToken()

        expect(mockHttpClient.post).toHaveBeenCalledWith(
          '/refresh',
          {},
          {
            withCredentials: true,
          },
        )
      })

      it('应该处理刷新令牌错误', async () => {
        const mockError = {
          response: {
            status: 401,
            data: { detail: 'Invalid refresh token' },
          },
        }

        mockHttpClient.post.mockRejectedValue(mockError)

        try {
          await authApiClient.refreshToken('invalid_token')
        } catch (error: any) {
          expect(error.detail).toBe('Invalid refresh token')
          expect(error.status_code).toBe(401)
        }
      })
    })
  })

  describe('User Management', () => {
    describe('getCurrentUser', () => {
      it('应该能获取当前用户信息', async () => {
        const user: User = {
          id: '1',
          email: 'test@example.com',
          name: 'Test User',
          is_verified: true,
          created_at: '2023-01-01T00:00:00Z',
          updated_at: '2023-01-01T00:00:00Z',
        }

        mockHttpClient.get.mockResolvedValue({
          data: user,
          status: 200,
          statusText: 'OK',
          headers: {},
          config: {},
          request: {},
        })

        const result = await authApiClient.getCurrentUser()

        expect(mockHttpClient.get).toHaveBeenCalledWith('/me')
        expect(result).toEqual(user)
      })

      it('应该处理无效的用户响应', async () => {
        mockHttpClient.get.mockResolvedValue({
          data: null,
          status: 200,
          statusText: 'OK',
          headers: {},
          config: {},
          request: {},
        })

        await expect(authApiClient.getCurrentUser()).rejects.toThrow('Invalid user response')
      })
    })

    describe('updateProfile', () => {
      it('应该能更新用户资料', async () => {
        const updateRequest: UpdateProfileRequest = {
          name: 'Updated Name',
          avatar_url: 'https://example.com/avatar.jpg',
        }

        const updatedUser: User = {
          id: '1',
          email: 'test@example.com',
          name: 'Updated Name',
          is_verified: true,
          created_at: '2023-01-01T00:00:00Z',
          updated_at: '2023-01-02T00:00:00Z',
          avatar_url: 'https://example.com/avatar.jpg',
        }

        mockHttpClient.put.mockResolvedValue({
          data: updatedUser,
          status: 200,
          statusText: 'OK',
          headers: {},
          config: {},
          request: {},
        })

        const result = await authApiClient.updateProfile(updateRequest)

        expect(mockHttpClient.put).toHaveBeenCalledWith('/me', updateRequest)
        expect(result).toEqual(updatedUser)
      })
    })

    describe('changePassword', () => {
      it('应该能修改密码', async () => {
        const changePasswordRequest: ChangePasswordRequest = {
          current_password: 'old_password',
          new_password: 'new_password',
        }

        mockHttpClient.post.mockResolvedValue({
          data: {},
          status: 200,
          statusText: 'OK',
          headers: {},
          config: {},
          request: {},
        })

        await authApiClient.changePassword(changePasswordRequest)

        expect(mockHttpClient.post).toHaveBeenCalledWith('/change-password', changePasswordRequest)
      })

      it('应该处理密码修改错误', async () => {
        const mockError = {
          response: {
            status: 400,
            data: { detail: 'Current password is incorrect' },
          },
        }

        mockHttpClient.post.mockRejectedValue(mockError)

        try {
          await authApiClient.changePassword({
            current_password: 'wrong_password',
            new_password: 'new_password',
          })
        } catch (error: any) {
          expect(error.detail).toBe('Current password is incorrect')
        }
      })
    })
  })

  describe('Password Reset', () => {
    describe('forgotPassword', () => {
      it('应该能发送忘记密码请求', async () => {
        const forgotPasswordRequest: ForgotPasswordRequest = {
          email: 'test@example.com',
        }

        mockHttpClient.post.mockResolvedValue({
          data: {},
          status: 200,
          statusText: 'OK',
          headers: {},
          config: {},
          request: {},
        })

        await authApiClient.forgotPassword(forgotPasswordRequest)

        expect(mockHttpClient.post).toHaveBeenCalledWith('/forgot-password', forgotPasswordRequest)
      })
    })

    describe('resetPassword', () => {
      it('应该能重置密码', async () => {
        const resetPasswordRequest: ResetPasswordRequest = {
          token: 'reset_token_123',
          new_password: 'new_password',
        }

        mockHttpClient.post.mockResolvedValue({
          data: {},
          status: 200,
          statusText: 'OK',
          headers: {},
          config: {},
          request: {},
        })

        await authApiClient.resetPassword(resetPasswordRequest)

        expect(mockHttpClient.post).toHaveBeenCalledWith('/reset-password', resetPasswordRequest)
      })
    })
  })

  describe('Email Verification', () => {
    describe('verifyEmail', () => {
      it('应该能验证邮箱', async () => {
        const token = 'verification_token_123'

        mockHttpClient.get.mockResolvedValue({
          data: {},
          status: 200,
          statusText: 'OK',
          headers: {},
          config: {},
          request: {},
        })

        await authApiClient.verifyEmail(token)

        expect(mockHttpClient.get).toHaveBeenCalledWith(
          `/verify-email?token=${encodeURIComponent(token)}`,
        )
      })

      it('应该正确编码验证令牌', async () => {
        const token = 'token with spaces & special chars!'

        mockHttpClient.get.mockResolvedValue({
          data: {},
          status: 200,
          statusText: 'OK',
          headers: {},
          config: {},
          request: {},
        })

        await authApiClient.verifyEmail(token)

        expect(mockHttpClient.get).toHaveBeenCalledWith(
          `/verify-email?token=${encodeURIComponent(token)}`,
        )
      })
    })

    describe('resendVerification', () => {
      it('应该能重发验证邮件', async () => {
        const resendRequest: ResendVerificationRequest = {
          email: 'test@example.com',
        }

        mockHttpClient.post.mockResolvedValue({
          data: {},
          status: 200,
          statusText: 'OK',
          headers: {},
          config: {},
          request: {},
        })

        await authApiClient.resendVerification(resendRequest)

        expect(mockHttpClient.post).toHaveBeenCalledWith('/resend-verification', resendRequest)
      })
    })

    describe('validateEmails', () => {
      it('应该能批量验证邮箱', async () => {
        const emails = ['valid@example.com', 'invalid-email', 'another@example.com']
        const expectedResponse = {
          valid: ['valid@example.com', 'another@example.com'],
          invalid: ['invalid-email'],
        }

        mockHttpClient.post.mockResolvedValue({
          data: expectedResponse,
          status: 200,
          statusText: 'OK',
          headers: {},
          config: {},
          request: {},
        })

        const result = await authApiClient.validateEmails(emails)

        expect(mockHttpClient.post).toHaveBeenCalledWith('/validate-emails', { emails })
        expect(result).toEqual(expectedResponse)
      })
    })
  })

  describe('Session Management', () => {
    describe('getUserSessions', () => {
      it('应该能获取用户会话列表', async () => {
        const sessions = [
          {
            id: 'session_1',
            ip_address: '192.168.1.1',
            user_agent: 'Mozilla/5.0...',
            created_at: '2023-01-01T00:00:00Z',
            last_activity: '2023-01-01T12:00:00Z',
            is_current: true,
          },
          {
            id: 'session_2',
            ip_address: '192.168.1.2',
            user_agent: 'Chrome/...',
            created_at: '2023-01-01T00:00:00Z',
            last_activity: '2023-01-01T10:00:00Z',
            is_current: false,
          },
        ]

        mockHttpClient.get.mockResolvedValue({
          data: sessions,
          status: 200,
          statusText: 'OK',
          headers: {},
          config: {},
          request: {},
        })

        const result = await authApiClient.getUserSessions()

        expect(mockHttpClient.get).toHaveBeenCalledWith('/sessions')
        expect(result).toEqual(sessions)
      })
    })

    describe('revokeSession', () => {
      it('应该能撤销指定会话', async () => {
        const sessionId = 'session_123'

        mockHttpClient.delete.mockResolvedValue({
          data: {},
          status: 200,
          statusText: 'OK',
          headers: {},
          config: {},
          request: {},
        })

        await authApiClient.revokeSession(sessionId)

        expect(mockHttpClient.delete).toHaveBeenCalledWith(`/sessions/${sessionId}`)
      })
    })

    describe('revokeAllOtherSessions', () => {
      it('应该能撤销所有其他会话', async () => {
        mockHttpClient.post.mockResolvedValue({
          data: {},
          status: 200,
          statusText: 'OK',
          headers: {},
          config: {},
          request: {},
        })

        await authApiClient.revokeAllOtherSessions()

        expect(mockHttpClient.post).toHaveBeenCalledWith('/sessions/revoke-others')
      })
    })
  })

  describe('Two-Factor Authentication', () => {
    describe('enableTwoFactor', () => {
      it('应该能启用两因素认证', async () => {
        const twoFactorResponse = {
          secret: 'JBSWY3DPEHPK3PXP',
          qr_code: 'data:image/png;base64,iVBORw0...',
        }

        mockHttpClient.post.mockResolvedValue({
          data: twoFactorResponse,
          status: 200,
          statusText: 'OK',
          headers: {},
          config: {},
          request: {},
        })

        const result = await authApiClient.enableTwoFactor()

        expect(mockHttpClient.post).toHaveBeenCalledWith('/2fa/enable')
        expect(result).toEqual(twoFactorResponse)
      })
    })

    describe('confirmTwoFactor', () => {
      it('应该能确认两因素认证', async () => {
        const code = '123456'
        const confirmResponse = {
          backup_codes: ['code1', 'code2', 'code3'],
        }

        mockHttpClient.post.mockResolvedValue({
          data: confirmResponse,
          status: 200,
          statusText: 'OK',
          headers: {},
          config: {},
          request: {},
        })

        const result = await authApiClient.confirmTwoFactor(code)

        expect(mockHttpClient.post).toHaveBeenCalledWith('/2fa/confirm', { code })
        expect(result).toEqual(confirmResponse)
      })
    })

    describe('disableTwoFactor', () => {
      it('应该能禁用两因素认证', async () => {
        const code = '123456'

        mockHttpClient.post.mockResolvedValue({
          data: {},
          status: 200,
          statusText: 'OK',
          headers: {},
          config: {},
          request: {},
        })

        await authApiClient.disableTwoFactor(code)

        expect(mockHttpClient.post).toHaveBeenCalledWith('/2fa/disable', { code })
      })
    })

    describe('generateBackupCodes', () => {
      it('应该能生成新的备份代码', async () => {
        const backupResponse = {
          backup_codes: ['new_code1', 'new_code2', 'new_code3'],
        }

        mockHttpClient.post.mockResolvedValue({
          data: backupResponse,
          status: 200,
          statusText: 'OK',
          headers: {},
          config: {},
          request: {},
        })

        const result = await authApiClient.generateBackupCodes()

        expect(mockHttpClient.post).toHaveBeenCalledWith('/2fa/backup-codes')
        expect(result).toEqual(backupResponse)
      })
    })
  })

  describe('System Operations', () => {
    describe('getHealthStatus', () => {
      it('应该能获取 API 健康状态', async () => {
        const healthResponse = {
          status: 'healthy',
          timestamp: '2023-01-01T12:00:00Z',
        }

        mockHttpClient.get.mockResolvedValue({
          data: healthResponse,
          status: 200,
          statusText: 'OK',
          headers: {},
          config: {},
          request: {},
        })

        const result = await authApiClient.getHealthStatus()

        expect(mockHttpClient.get).toHaveBeenCalledWith('/health')
        expect(result).toEqual(healthResponse)
      })
    })

    describe('getApiVersion', () => {
      it('应该能获取 API 版本信息', async () => {
        const versionResponse = {
          version: '1.0.0',
          build: 'abc123',
        }

        mockHttpClient.get.mockResolvedValue({
          data: versionResponse,
          status: 200,
          statusText: 'OK',
          headers: {},
          config: {},
          request: {},
        })

        const result = await authApiClient.getApiVersion()

        expect(mockHttpClient.get).toHaveBeenCalledWith('/version')
        expect(result).toEqual(versionResponse)
      })
    })
  })

  describe('Error Handling', () => {
    it('应该处理带有嵌套 detail 对象的错误', async () => {
      const mockError = {
        response: {
          status: 400,
          data: {
            detail: {
              message: 'Nested error message',
            },
          },
        },
      }

      mockHttpClient.post.mockRejectedValue(mockError)

      try {
        await authApiClient.login({
          email: 'test@example.com',
          password: 'password',
        })
      } catch (error: any) {
        expect(error.detail).toBe('Nested error message')
        expect(error.status_code).toBe(400)
      }
    })

    it('应该处理字符串类型的 detail', async () => {
      const mockError = {
        response: {
          status: 401,
          data: {
            detail: 'Direct error message',
          },
        },
      }

      mockHttpClient.post.mockRejectedValue(mockError)

      try {
        await authApiClient.login({
          email: 'test@example.com',
          password: 'password',
        })
      } catch (error: any) {
        expect(error.detail).toBe('Direct error message')
        expect(error.status_code).toBe(401)
      }
    })

    it('应该处理只有 message 字段的错误', async () => {
      const mockError = {
        response: {
          status: 500,
          data: {
            message: 'Server error message',
          },
        },
      }

      mockHttpClient.post.mockRejectedValue(mockError)

      try {
        await authApiClient.login({
          email: 'test@example.com',
          password: 'password',
        })
      } catch (error: any) {
        expect(error.detail).toBe('Server error message')
        expect(error.status_code).toBe(500)
      }
    })

    it('应该处理网络错误', async () => {
      const mockError = {
        request: {},
        message: 'Network Error',
      }

      mockHttpClient.post.mockRejectedValue(mockError)

      try {
        await authApiClient.login({
          email: 'test@example.com',
          password: 'password',
        })
      } catch (error: any) {
        expect(error.detail).toBe('Network error - please check your connection')
        expect(error.status_code).toBe(0)
      }
    })

    it('应该处理请求配置错误', async () => {
      const mockError = {
        message: 'Request configuration error',
      }

      mockHttpClient.post.mockRejectedValue(mockError)

      try {
        await authApiClient.login({
          email: 'test@example.com',
          password: 'password',
        })
      } catch (error: any) {
        expect(error.detail).toBe('Request configuration error')
        expect(error.status_code).toBe(0)
      }
    })

    it('应该保留 retry_after 信息', async () => {
      const mockError = {
        response: {
          status: 429,
          data: {
            detail: 'Rate limit exceeded',
            retry_after: 60,
          },
        },
      }

      mockHttpClient.post.mockRejectedValue(mockError)

      try {
        await authApiClient.login({
          email: 'test@example.com',
          password: 'password',
        })
      } catch (error: any) {
        expect(error.detail).toBe('Rate limit exceeded')
        expect(error.status_code).toBe(429)
        expect(error.retry_after).toBe(60)
        expect(error.response).toBe(mockError.response)
      }
    })

    it('应该使用默认错误消息', async () => {
      const mockError = {
        response: {
          status: 400,
          data: {},
        },
      }

      mockHttpClient.post.mockRejectedValue(mockError)

      try {
        await authApiClient.login({
          email: 'test@example.com',
          password: 'password',
        })
      } catch (error: any) {
        expect(error.detail).toBe('Login failed')
        expect(error.status_code).toBe(400)
      }
    })
  })

  describe('Configuration Edge Cases', () => {
    it('应该处理没有可选方法的 HTTP 客户端', () => {
      const minimalHttpClient = {
        get: vi.fn(),
        post: vi.fn(),
        put: vi.fn(),
        delete: vi.fn(),
        setDefaultHeader: vi.fn(),
        removeDefaultHeader: vi.fn(),
        addRequestInterceptor: vi.fn(),
        addResponseInterceptor: vi.fn(),
        removeInterceptor: vi.fn(),
        // 缺少 setBaseURL 和 setTimeout
      } as any

      expect(() => {
        new AuthApiClient(minimalHttpClient, mockConfig)
      }).not.toThrow()

      expect(minimalHttpClient.setDefaultHeader).toHaveBeenCalledWith(
        'Content-Type',
        'application/json',
      )
    })

    it('应该处理不同的配置组合', () => {
      const differentConfig = {
        ...mockConfig,
        apiBaseUrl: 'http://localhost:8000',
        authApiPrefix: '/api/auth',
        timeout: 5000,
        useHttpOnlyCookies: true,
      }

      const apiClient = new AuthApiClient(mockHttpClient, differentConfig)

      expect(mockHttpClient.setBaseURL).toHaveBeenCalledWith('http://localhost:8000/api/auth')
      expect(mockHttpClient.setTimeout).toHaveBeenCalledWith(5000)
    })
  })
})
