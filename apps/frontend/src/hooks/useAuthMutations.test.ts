/**
 * useAuthMutations hooks 的单元测试
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, waitFor, act } from '@testing-library/react'
import { QueryClient } from '@tanstack/react-query'
import { useLogin, useLogout, useUpdateProfile, useRefreshToken } from './useAuthMutations'
import { useCurrentUser } from './useAuthQuery'
import { useAuthStore } from './useAuth'
import { authService } from '../services/auth'
import { queryKeys } from '../lib/queryClient'
import {
  createTestQueryClient,
  createWrapper,
  createMockAuthStore,
  cleanupWindowLocation,
} from './test-utils'
import type {
  User,
  LoginRequest,
  LoginResponse,
  UpdateProfileRequest,
  TokenResponse,
} from '../types/auth'

// Mock 认证服务
vi.mock('../services/auth', () => ({
  authService: {
    login: vi.fn(),
    logout: vi.fn(),
    updateProfile: vi.fn(),
    refreshTokens: vi.fn(),
    getPermissions: vi.fn(),
    getCurrentUser: vi.fn(),
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

describe('useAuthMutations hooks', () => {
  let queryClient: QueryClient
  let mockAuthStore: ReturnType<typeof createMockAuthStore>
  let wrapper: ({ children }: { children: React.ReactNode }) => React.ReactElement

  beforeEach(() => {
    queryClient = createTestQueryClient()
    mockAuthStore = createMockAuthStore()
    wrapper = createWrapper(queryClient)
    vi.clearAllMocks()

    // 设置默认的 useAuthStore mock
    vi.mocked(useAuthStore).mockReturnValue(mockAuthStore.storeValue)

    // 清理 location.href 的赋值
    cleanupWindowLocation()
  })

  afterEach(() => {
    queryClient.clear()
  })

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
        message: 'Login successful',
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
      expect(mockAuthStore.storeValue.setAuthenticated).toHaveBeenCalledWith(true)

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
      expect(mockAuthStore.storeValue.setAuthenticated).toHaveBeenCalledWith(false)
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
        message: 'Login successful',
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
      expect(mockAuthStore.storeValue.setAuthenticated).toHaveBeenCalledWith(true)
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
      expect(mockAuthStore.storeValue.clearAuth).toHaveBeenCalled()
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
      expect(mockAuthStore.storeValue.clearAuth).toHaveBeenCalled()
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
        message: 'Profile updated successfully',
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
          message: 'Profile updated successfully',
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

    it('应该在完成后刷新用户数据', async () => {
      const mockUser: User = {
        id: 1,
        username: 'testuser',
        email: 'test@example.com',
        first_name: 'Test',
        last_name: 'User',
        is_active: true,
      }

      const updateData: UpdateProfileRequest = {
        first_name: 'Updated',
        last_name: 'User',
      }

      const updatedUser = { ...mockUser, ...updateData }

      // 设置初始用户数据
      queryClient.setQueryData(queryKeys.currentUser(), mockUser)

      vi.mocked(authService.updateProfile).mockResolvedValueOnce({
        success: true,
        data: updatedUser,
        message: 'Profile updated successfully',
      })

      // Mock getCurrentUser 用于查询刷新
      vi.mocked(authService.getCurrentUser).mockResolvedValueOnce(updatedUser)

      const { result } = renderHook(() => useUpdateProfile(), { wrapper })

      await act(async () => {
        await result.current.mutateAsync(updateData)
      })

      // 使用 useCurrentUser hook 来验证数据是否被刷新
      const { result: userResult } = renderHook(() => useCurrentUser(), {
        wrapper,
      })

      await waitFor(() => {
        expect(userResult.current.data).toEqual(updatedUser)
      })
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

      const { result } = renderHook(() => useRefreshToken(), { wrapper })

      await act(async () => {
        await result.current.mutateAsync()
      })

      // 验证 mutation 成功完成
      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true)
      })

      // 验证返回的数据
      expect(result.current.data).toEqual(mockTokenResponse)

      // 验证 refreshTokens 被调用
      expect(vi.mocked(authService.refreshTokens)).toHaveBeenCalled()
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
      expect(mockAuthStore.storeValue.clearAuth).toHaveBeenCalled()
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
        message: 'Login successful',
      })
      vi.mocked(authService.updateProfile).mockResolvedValueOnce({
        success: true,
        data: { ...mockUser, first_name: 'Updated', last_name: 'Name' },
        message: 'Profile updated successfully',
      })
      vi.mocked(authService.logout).mockResolvedValueOnce({
        success: true,
        data: undefined,
        message: 'Logged out successfully',
      })

      const { result } = renderHook(
        () => ({
          login: useLogin(),
          updateProfile: useUpdateProfile(),
          logout: useLogout(),
        }),
        { wrapper },
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
        await result.current.updateProfile.mutateAsync({
          first_name: 'Updated',
          last_name: 'Name',
        })
      })

      const updatedUser = queryClient.getQueryData<User>(queryKeys.currentUser())
      expect(updatedUser?.first_name).toBe('Updated')
      expect(updatedUser?.last_name).toBe('Name')

      // 步骤 3: 登出
      await act(async () => {
        await result.current.logout.mutateAsync()
      })

      expect(queryClient.getQueryData(queryKeys.currentUser())).toBeUndefined()
      expect(mockAuthStore.storeValue.clearAuth).toHaveBeenCalled()
    })
  })
})
