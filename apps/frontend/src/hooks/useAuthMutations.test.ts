/**
 * useAuthMutations hooks 的单元测试
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, waitFor, act } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import React from 'react'
import { useLogin, useLogout, useUpdateProfile, useRefreshToken } from './useAuthMutations'
import { useAuth } from './useAuth'
import { authService } from '../services/auth'
import { queryKeys } from '../lib/queryClient'
import type { User, LoginRequest, LoginResponse, UpdateProfileRequest, TokenResponse } from '../types/auth'

// Mock 认证服务
vi.mock('../services/auth', () => ({
  authService: {
    login: vi.fn(),
    logout: vi.fn(),
    updateProfile: vi.fn(),
    refreshTokens: vi.fn(),
    getPermissions: vi.fn(),
  },
}))

// Mock useAuth hook
vi.mock('./useAuth', () => ({
  useAuth: vi.fn(),
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

describe('useAuthMutations hooks', () => {
  let queryClient: QueryClient
  let mockSetAuthenticated: ReturnType<typeof vi.fn>
  let mockClearAuth: ReturnType<typeof vi.fn>

  beforeEach(() => {
    queryClient = createTestQueryClient()
    mockSetAuthenticated = vi.fn()
    mockClearAuth = vi.fn()
    vi.clearAllMocks()

    // 设置默认的 useAuth mock
    vi.mocked(useAuth).mockReturnValue({
      isAuthenticated: false,
      setAuthenticated: mockSetAuthenticated,
      clearAuth: mockClearAuth,
    } as any)

    // 清理 location.href 的赋值
    delete (window as any).location
    window.location = { href: '' } as any
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

  describe('useLogin', () => {
    it('应该成功处理登录', async () => {
      const mockUser: User = {
        id: 1,
        username: 'testuser',
        email: 'test@example.com',
        first_name: 'Test',
        last_name: 'User',
        is_active: true,
        is_verified: true,
        is_superuser: false,
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
      }

      const mockLoginResponse: LoginResponse = {
        success: true,
        user: mockUser,
        access_token: 'test-token',
        refresh_token: 'test-refresh-token',
      }

      vi.mocked(authService.login).mockResolvedValueOnce({
        success: true,
        data: mockLoginResponse,
        message: 'Login successful'
      })

      const { result } = renderHook(() => useLogin(), { wrapper })

      const loginData: LoginRequest = {
        email: 'test@example.com',
        password: 'password123',
      }

      // 执行登录
      await act(async () => {
        await result.current.mutateAsync(loginData)
      })

      // 验证调用
      expect(vi.mocked(authService.login)).toHaveBeenCalledWith(loginData)
      expect(mockSetAuthenticated).toHaveBeenCalledWith(true)

      // 验证缓存设置
      const cachedUser = queryClient.getQueryData(queryKeys.currentUser())
      expect(cachedUser).toEqual(mockUser)

      // 登录不会自动预取权限，权限由 usePermissions hook 独立管理
      expect(vi.mocked(authService.getPermissions)).not.toHaveBeenCalled()
    })

    it('应该处理登录失败', async () => {
      const loginError = new Error('Invalid credentials')
      vi.mocked(authService.login).mockRejectedValueOnce(loginError)

      const { result } = renderHook(() => useLogin(), { wrapper })

      const loginData: LoginRequest = {
        email: 'test@example.com',
        password: 'wrong-password',
      }

      // 执行登录
      await act(async () => {
        try {
          await result.current.mutateAsync(loginData)
        } catch (error) {
          expect(error).toEqual(loginError)
        }
      })

      // 验证错误处理
      expect(mockSetAuthenticated).toHaveBeenCalledWith(false)
      expect(queryClient.getQueryState(queryKeys.currentUser())).toBeUndefined()
    })

    it('应该在没有权限接口时跳过权限预取', async () => {
      const mockUser: User = {
        id: 1,
        username: 'testuser',
        email: 'test@example.com',
        first_name: 'Test',
        last_name: 'User',
        is_active: true,
        is_verified: true,
        is_superuser: false,
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
      }

      const mockLoginResponse: LoginResponse = {
        success: true,
        user: mockUser,
        access_token: 'test-token',
        refresh_token: 'test-refresh-token',
      }

      vi.mocked(authService.login).mockResolvedValueOnce({
        success: true,
        data: mockLoginResponse,
        message: 'Login successful'
      })

      const { result } = renderHook(() => useLogin(), { wrapper })

      const loginData: LoginRequest = {
        email: 'test@example.com',
        password: 'password123',
      }

      await act(async () => {
        await result.current.mutateAsync(loginData)
      })

      // 验证基本功能正常
      expect(mockSetAuthenticated).toHaveBeenCalledWith(true)
      expect(queryClient.getQueryData(queryKeys.currentUser())).toEqual(mockUser)
    })
  })

  describe('useLogout', () => {
    it('应该成功处理登出', async () => {
      vi.mocked(authService.logout).mockResolvedValueOnce(undefined)

      const { result } = renderHook(() => useLogout(), { wrapper })

      // 执行登出
      await act(async () => {
        await result.current.mutateAsync()
      })

      // 验证调用
      expect(vi.mocked(authService.logout)).toHaveBeenCalled()
      expect(mockClearAuth).toHaveBeenCalled()
      expect(mockNavigate).toHaveBeenCalledWith('/login', { replace: true })
    })

    it('应该在登出失败时也清理本地状态', async () => {
      const logoutError = new Error('Network error')
      vi.mocked(authService.logout).mockRejectedValueOnce(logoutError)

      const { result } = renderHook(() => useLogout(), { wrapper })

      // 执行登出
      await act(async () => {
        try {
          await result.current.mutateAsync()
        } catch (error) {
          expect(error).toEqual(logoutError)
        }
      })

      // 验证即使失败也清理状态
      expect(mockClearAuth).toHaveBeenCalled()
      expect(mockNavigate).toHaveBeenCalledWith('/login', { replace: true })
    })
  })

  describe('useUpdateProfile', () => {
    const mockUser: User = {
      id: 1,
      username: 'testuser',
      email: 'test@example.com',
      first_name: 'Test',
      last_name: 'User',
      is_active: true,
      is_verified: true,
      is_superuser: false,
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
    }

    beforeEach(() => {
      // 预设用户数据在缓存中
      queryClient.setQueryData(queryKeys.currentUser(), mockUser)
    })

    it('应该成功更新用户资料', async () => {
      const updateData: UpdateProfileRequest = {
        first_name: 'Updated',
        last_name: 'User',
      }

      const updatedUser = { ...mockUser, ...updateData }

      vi.mocked(authService.updateProfile).mockResolvedValueOnce({
        success: true,
        data: updatedUser,
        message: 'Profile updated successfully'
      })

      const { result } = renderHook(() => useUpdateProfile(), { wrapper })

      // 执行更新
      await act(async () => {
        await result.current.mutateAsync(updateData)
      })

      // 验证调用
      expect(vi.mocked(authService.updateProfile)).toHaveBeenCalledWith(updateData)

      // 验证缓存更新
      const cachedUser = queryClient.getQueryData(queryKeys.currentUser())
      expect(cachedUser).toEqual(updatedUser)
    })

    it('应该实现乐观更新', async () => {
      const updateData: UpdateProfileRequest = {
        first_name: 'Optimistic',
        last_name: 'Update',
      }

      let resolveUpdate: (value: any) => void
      const updatePromise = new Promise<any>((resolve) => {
        resolveUpdate = resolve
      })

      // 使用 Promise 控制 API 响应时机
      vi.mocked(authService.updateProfile).mockReturnValueOnce(updatePromise)

      const { result } = renderHook(() => useUpdateProfile(), { wrapper })

      // 执行更新
      await act(async () => {
        result.current.mutate(updateData)
      })

      // 立即检查乐观更新（在 Promise 解析之前）
      const optimisticUser = queryClient.getQueryData<User>(queryKeys.currentUser())
      expect(optimisticUser?.first_name).toBe('Optimistic')
      expect(optimisticUser?.last_name).toBe('Update')

      // 解析 Promise 完成更新
      await act(async () => {
        resolveUpdate!({
          success: true,
          data: { ...mockUser, ...updateData },
          message: 'Profile updated successfully'
        })
      })

      // 等待实际更新完成
      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true)
      })
    })

    it('应该在错误时回滚乐观更新', async () => {
      const updateData: UpdateProfileRequest = {
        first_name: 'Will',
        last_name: 'Fail',
      }

      const updateError = new Error('Update failed')
      vi.mocked(authService.updateProfile).mockRejectedValueOnce(updateError)

      const { result } = renderHook(() => useUpdateProfile(), { wrapper })

      // 执行更新
      await act(async () => {
        try {
          await result.current.mutateAsync(updateData)
        } catch (error) {
          expect(error).toEqual(updateError)
        }
      })

      // 验证回滚到原始数据
      const cachedUser = queryClient.getQueryData<User>(queryKeys.currentUser())
      expect(cachedUser).toEqual(mockUser)
    })

    it('应该在完成后使查询失效', async () => {
      const updateData: UpdateProfileRequest = {
        first_name: 'Updated',
        last_name: 'User',
      }

      vi.mocked(authService.updateProfile).mockResolvedValueOnce({
        success: true,
        data: { ...mockUser, ...updateData },
        message: 'Profile updated successfully'
      })

      const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')

      const { result } = renderHook(() => useUpdateProfile(), { wrapper })

      await act(async () => {
        await result.current.mutateAsync(updateData)
      })

      // 验证查询失效
      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: queryKeys.currentUser() })
    })
  })

  describe('useRefreshToken', () => {
    it('应该成功刷新 token', async () => {
      const mockTokenResponse: TokenResponse = {
        success: true,
        access_token: 'new-access-token',
        refresh_token: 'new-refresh-token',
      }

      vi.mocked(authService.refreshTokens).mockResolvedValueOnce(mockTokenResponse)

      const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')

      const { result } = renderHook(() => useRefreshToken(), { wrapper })

      await act(async () => {
        await result.current.mutateAsync()
      })

      // 验证调用
      expect(vi.mocked(authService.refreshTokens)).toHaveBeenCalled()

      // 验证所有查询失效
      expect(invalidateSpy).toHaveBeenCalledWith()
    })

    it('应该处理 token 刷新失败', async () => {
      const refreshError = new Error('Refresh token expired')
      vi.mocked(authService.refreshTokens).mockRejectedValueOnce(refreshError)

      const { result } = renderHook(() => useRefreshToken(), { wrapper })

      await act(async () => {
        try {
          await result.current.mutateAsync()
        } catch (error) {
          expect(error).toEqual(refreshError)
        }
      })

      // 验证错误处理
      expect(mockClearAuth).toHaveBeenCalled()
      expect(window.location.href).toBe('/login')
    })
  })

  describe('集成测试', () => {
    it('应该正确处理完整的登录-更新-登出流程', async () => {
      const mockUser: User = {
        id: 1,
        username: 'testuser',
        email: 'test@example.com',
        first_name: 'Test',
        last_name: 'User',
        is_active: true,
        is_verified: true,
        is_superuser: false,
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
      }

      const mockLoginResponse: LoginResponse = {
        success: true,
        user: mockUser,
        access_token: 'test-token',
        refresh_token: 'test-refresh-token',
      }

      vi.mocked(authService.login).mockResolvedValueOnce({
        success: true,
        data: mockLoginResponse,
        message: 'Login successful'
      })
      vi.mocked(authService.updateProfile).mockResolvedValueOnce({
        success: true,
        data: { ...mockUser, first_name: 'Updated', last_name: 'Name' },
        message: 'Profile updated successfully'
      })
      vi.mocked(authService.logout).mockResolvedValueOnce({
        success: true,
        data: undefined,
        message: 'Logged out successfully'
      })

      const { result } = renderHook(
        () => ({
          login: useLogin(),
          updateProfile: useUpdateProfile(),
          logout: useLogout(),
        }),
        { wrapper }
      )

      // 步骤 1: 登录
      await act(async () => {
        await result.current.login.mutateAsync({
          email: 'test@example.com',
          password: 'password123',
        })
      })

      expect(queryClient.getQueryData(queryKeys.currentUser())).toEqual(mockUser)

      // 步骤 2: 更新资料
      await act(async () => {
        await result.current.updateProfile.mutateAsync({ first_name: 'Updated', last_name: 'Name' })
      })

      const updatedUser = queryClient.getQueryData<User>(queryKeys.currentUser())
      expect(updatedUser?.first_name).toBe('Updated')
      expect(updatedUser?.last_name).toBe('Name')

      // 步骤 3: 登出
      await act(async () => {
        await result.current.logout.mutateAsync()
      })

      expect(queryClient.getQueryData(queryKeys.currentUser())).toBeUndefined()
      expect(mockClearAuth).toHaveBeenCalled()
    })
  })
})