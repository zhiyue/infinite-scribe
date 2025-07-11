/**
 * 额外的 useAuthMutations hooks 单元测试
 * 测试 useRegister, useResendVerification, useForgotPassword, useResetPassword, useChangePassword, useVerifyEmail
 */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, renderHook, waitFor } from '@testing-library/react'
import React from 'react'
import { BrowserRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { queryKeys } from '../lib/queryClient'
import { authService } from '../services/auth'
import type {
    ChangePasswordRequest,
    ForgotPasswordRequest,
    RegisterRequest,
    ResendVerificationRequest,
    ResetPasswordRequest
} from '../types/auth'
import { useAuthStore } from './useAuth'
import {
    useChangePassword,
    useForgotPassword,
    useRegister,
    useResendVerification,
    useResetPassword,
    useVerifyEmail
} from './useAuthMutations'

// Mock 认证服务
vi.mock('../services/auth', () => ({
  authService: {
    register: vi.fn(),
    resendVerification: vi.fn(),
    forgotPassword: vi.fn(),
    resetPassword: vi.fn(),
    changePassword: vi.fn(),
    verifyEmail: vi.fn(),
  },
}))

// Mock useAuthStore hook
vi.mock('./useAuth', () => ({
  useAuthStore: vi.fn(),
}))

// Mock useNavigate
const mockNavigate = vi.fn()
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  }
})

// 创建测试用的 QueryClient
const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        refetchOnWindowFocus: false,
      },
      mutations: {
        retry: false,
      },
    },
  })

describe('额外的 useAuthMutations hooks', () => {
  let queryClient: QueryClient
  let mockClearAuth: ReturnType<typeof vi.fn>

  beforeEach(() => {
    queryClient = createTestQueryClient()
    mockClearAuth = vi.fn()
    vi.clearAllMocks()

    // 设置默认的 useAuth mock - 创建完整的 store 对象
    const authStoreValue = {
      isAuthenticated: false,
      setAuthenticated: vi.fn(),
      clearAuth: mockClearAuth,
      handleTokenExpired: vi.fn(),
    } as any

    // 创建完整的 Zustand store mock
    const mockStore = Object.assign(() => authStoreValue, {
      getState: () => authStoreValue,
      subscribe: vi.fn(() => vi.fn()),
      setState: vi.fn(),
      destroy: vi.fn(),
    })

    vi.mocked(useAuthStore).mockReturnValue(authStoreValue)
    vi.mocked(useAuthStore).mockImplementation(() => authStoreValue)
  })

  afterEach(() => {
    queryClient.clear()
  })

  const wrapper = ({ children }: { children: React.ReactNode }) => {
    return React.createElement(
      BrowserRouter,
      {},
      React.createElement(QueryClientProvider, { client: queryClient }, children)
    )
  }

  describe('useRegister', () => {
    it('应该成功处理注册', async () => {
      const registerData: RegisterRequest = {
        email: 'newuser@example.com',
        password: 'password123',
        name: 'New User',
      }

      vi.mocked(authService.register).mockResolvedValueOnce({
        success: true,
        data: { id: '123', email: registerData.email },
        message: 'Registration successful',
      })

      const { result } = renderHook(() => useRegister(), { wrapper })

      await act(async () => {
        await result.current.mutateAsync(registerData)
      })

      // 验证调用
      expect(vi.mocked(authService.register)).toHaveBeenCalledWith(registerData)

      // 注册成功后不再自动导航，由组件处理
      expect(mockNavigate).not.toHaveBeenCalled()
    })

    it('应该处理注册失败', async () => {
      const registerData: RegisterRequest = {
        email: 'existing@example.com',
        password: 'password123',
        name: 'Existing User',
      }

      const registerError = new Error('Email already exists')
      vi.mocked(authService.register).mockRejectedValueOnce(registerError)

      const { result } = renderHook(() => useRegister(), { wrapper })

      await act(async () => {
        try {
          await result.current.mutateAsync(registerData)
        } catch (error) {
          expect(error).toEqual(registerError)
        }
      })

      // 验证没有导航
      expect(mockNavigate).not.toHaveBeenCalled()
    })

    it('应该处理注册时的验证错误', async () => {
      const registerData: RegisterRequest = {
        email: 'invalid-email',
        password: '123', // 太短
        name: '',
      }

      const validationError = new Error('Validation failed')
      ;(validationError as any).errors = {
        email: 'Invalid email format',
        password: 'Password too short',
        name: 'Name is required',
      }

      vi.mocked(authService.register).mockRejectedValueOnce(validationError)

      const { result } = renderHook(() => useRegister(), { wrapper })

      await act(async () => {
        try {
          await result.current.mutateAsync(registerData)
        } catch (error) {
          expect(error).toEqual(validationError)
          expect((error as any).errors).toBeDefined()
        }
      })

      expect(mockNavigate).not.toHaveBeenCalled()
    })
  })

  describe('useResendVerification', () => {
    it('应该成功重新发送验证邮件', async () => {
      const resendData: ResendVerificationRequest = {
        email: 'unverified@example.com',
      }

      vi.mocked(authService.resendVerification).mockResolvedValueOnce({
        success: true,
        data: undefined,
        message: 'Verification email sent',
      })

      const { result } = renderHook(() => useResendVerification(), { wrapper })

      await act(async () => {
        await result.current.mutateAsync(resendData)
      })

      expect(vi.mocked(authService.resendVerification)).toHaveBeenCalledWith(resendData)
      
      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true)
      })
    })

    it('应该处理重发验证邮件失败', async () => {
      const resendData: ResendVerificationRequest = {
        email: 'notfound@example.com',
      }

      const resendError = new Error('Email not found')
      vi.mocked(authService.resendVerification).mockRejectedValueOnce(resendError)

      const { result } = renderHook(() => useResendVerification(), { wrapper })

      await act(async () => {
        try {
          await result.current.mutateAsync(resendData)
        } catch (error) {
          expect(error).toEqual(resendError)
        }
      })

      await waitFor(() => {
        expect(result.current.isError).toBe(true)
      })
    })

    it('应该处理速率限制错误', async () => {
      const resendData: ResendVerificationRequest = {
        email: 'ratelimited@example.com',
      }

      const rateLimitError = new Error('Too many requests. Please try again later.')
      ;(rateLimitError as any).status = 429

      vi.mocked(authService.resendVerification).mockRejectedValueOnce(rateLimitError)

      const { result } = renderHook(() => useResendVerification(), { wrapper })

      await act(async () => {
        try {
          await result.current.mutateAsync(resendData)
        } catch (error) {
          expect(error).toEqual(rateLimitError)
          expect((error as any).status).toBe(429)
        }
      })
    })
  })

  describe('useForgotPassword', () => {
    it('应该成功发送密码重置邮件', async () => {
      const forgotData: ForgotPasswordRequest = {
        email: 'forgot@example.com',
      }

      vi.mocked(authService.forgotPassword).mockResolvedValueOnce({
        success: true,
        data: undefined,
        message: 'Password reset email sent',
      })

      const { result } = renderHook(() => useForgotPassword(), { wrapper })

      await act(async () => {
        await result.current.mutateAsync(forgotData)
      })

      expect(vi.mocked(authService.forgotPassword)).toHaveBeenCalledWith(forgotData)
      
      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true)
      })
    })

    it('应该处理未找到用户的情况', async () => {
      const forgotData: ForgotPasswordRequest = {
        email: 'nonexistent@example.com',
      }

      // 注意：出于安全考虑，即使用户不存在，API 也可能返回成功
      vi.mocked(authService.forgotPassword).mockResolvedValueOnce({
        success: true,
        message: 'If the email exists, a reset link has been sent',
      })

      const { result } = renderHook(() => useForgotPassword(), { wrapper })

      await act(async () => {
        await result.current.mutateAsync(forgotData)
      })

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true)
      })
    })
  })

  describe('useResetPassword', () => {
    it('应该成功重置密码', async () => {
      const resetData: ResetPasswordRequest = {
        token: 'valid-reset-token',
        password: 'newPassword123',
        confirmPassword: 'newPassword123',
      }

      vi.mocked(authService.resetPassword).mockResolvedValueOnce({
        success: true,
        message: 'Password reset successfully',
      })

      const { result } = renderHook(() => useResetPassword(), { wrapper })

      await act(async () => {
        await result.current.mutateAsync(resetData)
      })

      expect(vi.mocked(authService.resetPassword)).toHaveBeenCalledWith(resetData)
      // 重置密码成功后不再自动导航，由组件处理
      expect(mockNavigate).not.toHaveBeenCalled()
    })

    it('应该处理无效或过期的 token', async () => {
      const resetData: ResetPasswordRequest = {
        token: 'expired-token',
        password: 'newPassword123',
        confirmPassword: 'newPassword123',
      }

      const tokenError = new Error('Invalid or expired token')
      vi.mocked(authService.resetPassword).mockRejectedValueOnce(tokenError)

      const { result } = renderHook(() => useResetPassword(), { wrapper })

      await act(async () => {
        try {
          await result.current.mutateAsync(resetData)
        } catch (error) {
          expect(error).toEqual(tokenError)
        }
      })

      expect(mockNavigate).not.toHaveBeenCalled()
    })

    it('应该处理密码不匹配的情况', async () => {
      const resetData: ResetPasswordRequest = {
        token: 'valid-token',
        password: 'password123',
        confirmPassword: 'differentPassword',
      }

      const mismatchError = new Error('Passwords do not match')
      vi.mocked(authService.resetPassword).mockRejectedValueOnce(mismatchError)

      const { result } = renderHook(() => useResetPassword(), { wrapper })

      await act(async () => {
        try {
          await result.current.mutateAsync(resetData)
        } catch (error) {
          expect(error).toEqual(mismatchError)
        }
      })
    })
  })

  describe('useChangePassword', () => {
    it('应该成功修改密码', async () => {
      const changeData: ChangePasswordRequest = {
        currentPassword: 'oldPassword123',
        newPassword: 'newPassword456',
        confirmNewPassword: 'newPassword456',
      }

      vi.mocked(authService.changePassword).mockResolvedValueOnce({
        success: true,
        message: 'Password changed successfully',
      })

      const { result } = renderHook(() => useChangePassword(), { wrapper })

      await act(async () => {
        await result.current.mutateAsync(changeData)
      })

      expect(vi.mocked(authService.changePassword)).toHaveBeenCalledWith(changeData)
      expect(mockClearAuth).toHaveBeenCalled()
      expect(queryClient.getQueryData(queryKeys.currentUser())).toBeUndefined()
      // 修改密码成功后不再自动导航，由组件处理
      expect(mockNavigate).not.toHaveBeenCalled()
    })

    it('应该处理当前密码错误', async () => {
      const changeData: ChangePasswordRequest = {
        currentPassword: 'wrongPassword',
        newPassword: 'newPassword456',
        confirmNewPassword: 'newPassword456',
      }

      const wrongPasswordError = new Error('Current password is incorrect')
      vi.mocked(authService.changePassword).mockRejectedValueOnce(wrongPasswordError)

      const { result } = renderHook(() => useChangePassword(), { wrapper })

      await act(async () => {
        try {
          await result.current.mutateAsync(changeData)
        } catch (error) {
          expect(error).toEqual(wrongPasswordError)
        }
      })

      expect(mockClearAuth).not.toHaveBeenCalled()
      expect(mockNavigate).not.toHaveBeenCalled()
    })

    it('应该处理新密码与旧密码相同的情况', async () => {
      const changeData: ChangePasswordRequest = {
        currentPassword: 'samePassword123',
        newPassword: 'samePassword123',
        confirmNewPassword: 'samePassword123',
      }

      const samePasswordError = new Error('New password must be different from current password')
      vi.mocked(authService.changePassword).mockRejectedValueOnce(samePasswordError)

      const { result } = renderHook(() => useChangePassword(), { wrapper })

      await act(async () => {
        try {
          await result.current.mutateAsync(changeData)
        } catch (error) {
          expect(error).toEqual(samePasswordError)
        }
      })
    })
  })

  describe('useVerifyEmail', () => {
    it('应该成功验证邮箱', async () => {
      const verifyToken = 'valid-verify-token'

      vi.mocked(authService.verifyEmail).mockResolvedValueOnce({
        success: true,
        message: 'Email verified successfully',
      })

      const { result } = renderHook(() => useVerifyEmail(), { wrapper })

      await act(async () => {
        await result.current.mutateAsync(verifyToken)
      })

      expect(vi.mocked(authService.verifyEmail)).toHaveBeenCalledWith(verifyToken)
      expect(mockNavigate).toHaveBeenCalledWith('/login', {
        state: { message: 'Email verified successfully. You can now login.' }
      })
    })

    it('应该处理无效的验证 token', async () => {
      const invalidToken = 'invalid-token'

      const tokenError = new Error('Invalid verification token')
      vi.mocked(authService.verifyEmail).mockRejectedValueOnce(tokenError)

      const { result } = renderHook(() => useVerifyEmail(), { wrapper })

      await act(async () => {
        try {
          await result.current.mutateAsync(invalidToken)
        } catch (error) {
          expect(error).toEqual(tokenError)
        }
      })

      expect(mockNavigate).not.toHaveBeenCalled()
    })

    it('应该处理已经验证过的情况', async () => {
      const usedToken = 'already-used-token'

      const alreadyVerifiedError = new Error('Email already verified')
      vi.mocked(authService.verifyEmail).mockRejectedValueOnce(alreadyVerifiedError)

      const { result } = renderHook(() => useVerifyEmail(), { wrapper })

      await act(async () => {
        try {
          await result.current.mutateAsync(usedToken)
        } catch (error) {
          expect(error).toEqual(alreadyVerifiedError)
        }
      })
    })
  })

  describe('集成场景测试', () => {
    it('应该处理完整的注册-验证-登录流程', async () => {
      // 这是一个概念性测试，展示不同 hooks 之间的关系
      // 在实际应用中，这些步骤会在不同的页面/组件中进行

      // 步骤 1: 注册
      const registerData: RegisterRequest = {
        email: 'newuser@example.com',
        password: 'password123',
        name: 'New User',
      }

      vi.mocked(authService.register).mockResolvedValueOnce({
        success: true,
        data: { id: '123', email: registerData.email },
        message: 'Registration successful',
      })

      const { result: registerResult } = renderHook(() => useRegister(), { wrapper })

      await act(async () => {
        await registerResult.current.mutateAsync(registerData)
      })

      // 注册成功后不再自动导航，由组件处理
      expect(mockNavigate).not.toHaveBeenCalled()

      // 步骤 2: 验证邮箱
      vi.clearAllMocks()
      const verifyToken = 'verification-token-from-email'

      vi.mocked(authService.verifyEmail).mockResolvedValueOnce({
        success: true,
        message: 'Email verified successfully',
      })

      const { result: verifyResult } = renderHook(() => useVerifyEmail(), { wrapper })

      await act(async () => {
        await verifyResult.current.mutateAsync(verifyToken)
      })

      // useVerifyEmail 仍然会自动导航
      expect(mockNavigate).toHaveBeenCalledWith('/login', {
        state: { message: 'Email verified successfully. You can now login.' }
      })

      // 步骤 3: 之后用户可以使用 useLogin 登录
    })

    it('应该处理忘记密码-重置密码流程', async () => {
      // 步骤 1: 请求密码重置
      const forgotData: ForgotPasswordRequest = {
        email: 'user@example.com',
      }

      vi.mocked(authService.forgotPassword).mockResolvedValueOnce({
        success: true,
        data: undefined,
        message: 'Password reset email sent',
      })

      const { result: forgotResult } = renderHook(() => useForgotPassword(), { wrapper })

      await act(async () => {
        await forgotResult.current.mutateAsync(forgotData)
      })

      await waitFor(() => {
        expect(forgotResult.current.isSuccess).toBe(true)
      })

      // 步骤 2: 使用 token 重置密码
      vi.clearAllMocks()
      const resetData: ResetPasswordRequest = {
        token: 'reset-token-from-email',
        password: 'newPassword123',
        confirmPassword: 'newPassword123',
      }

      vi.mocked(authService.resetPassword).mockResolvedValueOnce({
        success: true,
        message: 'Password reset successfully',
      })

      const { result: resetResult } = renderHook(() => useResetPassword(), { wrapper })

      await act(async () => {
        await resetResult.current.mutateAsync(resetData)
      })

      // 重置密码成功后不再自动导航，由组件处理
      expect(mockNavigate).not.toHaveBeenCalled()
    })
  })
})