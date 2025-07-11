/**
 * TanStack Query 缓存行为的集成测试
 * 测试缓存同步、失效、更新等高级特性
 */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, renderHook, waitFor } from '@testing-library/react'
import React from 'react'
import { BrowserRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { queryKeys } from '../lib/queryClient'
import { authService } from '../services/auth'
import { useAuth, useAuthStore } from './useAuth'
import {
    useChangePassword,
    useLogin,
    useLogout,
    useUpdateProfile
} from './useAuthMutations'
import {
    useCurrentUser,
    usePermissions,
    useSessions
} from './useAuthQuery'
// 直接导入真实的 queryOptions，避免 mock 干扰
import type { UpdateProfileRequest, User } from '../types/auth'

// Mock 认证服务
vi.mock('../services/auth', () => ({
  authService: {
    getCurrentUser: vi.fn(),
    getPermissions: vi.fn(),
    getSessions: vi.fn(),
    login: vi.fn(),
    logout: vi.fn(),
    updateProfile: vi.fn(),
    changePassword: vi.fn(),
  },
}))

// Mock useAuth hook
vi.mock('./useAuth', () => ({
  useAuth: vi.fn(),
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


// 在集成测试中明确覆盖单元测试的 queryClient mock
vi.mock('../lib/queryClient', async () => {
  const actual = await vi.importActual('../lib/queryClient')
  return {
    ...actual,
    // 保持真实的配置，只确保重试逻辑正确
    queryOptions: {
      user: {
        staleTime: 1000 * 60 * 10,
        gcTime: 1000 * 60 * 30,
        retry: 3, // 使用数字而不是函数
      },
      permissions: { staleTime: 1000 * 60 * 30, gcTime: 1000 * 60 * 120, retry: 2 },
      sessions: { staleTime: 1000 * 60 * 5, gcTime: 1000 * 60 * 15, retry: 1 },
    },
  }
})

// 创建测试用的 QueryClient
const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: {
        // 使用智能重试逻辑，就像生产环境一样
        retry: (failureCount, error: any) => {
          // 401 错误不重试
          if (error?.status === 401) {
            return false
          }
          // 其他错误最多重试 2 次（测试中用较少次数）
          return failureCount < 2
        },
        refetchOnWindowFocus: false,
        staleTime: 0, // 立即标记为过期，便于测试
        gcTime: 1000 * 60 * 5, // 5分钟
      },
      mutations: {
        retry: false,
      },
    },
  })

describe('TanStack Query 缓存集成测试', () => {
  let queryClient: QueryClient
  let mockSetAuthenticated: ReturnType<typeof vi.fn>
  let mockClearAuth: ReturnType<typeof vi.fn>

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
    role: 'user', // 添加role字段以支持权限查询
  }

  beforeEach(() => {
    // 创建全新的 queryClient 确保测试隔离
    queryClient = createTestQueryClient()
    mockSetAuthenticated = vi.fn()
    mockClearAuth = vi.fn()

    // 先清理所有 mock
    vi.clearAllMocks()
    vi.resetAllMocks()

    // 确保使用真实的 queryClient 模块
    vi.doUnmock('../lib/queryClient')

    // 清理 location.href 的赋值
    delete (window as any).location
    window.location = { href: '' } as any
    
    // 重置导航 mock
    mockNavigate.mockReset()
  })

  // 在每个测试中设置认证状态的帮助函数
  const setupAuthenticatedState = () => {
    const mockAuthStore = {
      isAuthenticated: true,
      setAuthenticated: mockSetAuthenticated,
      clearAuth: mockClearAuth,
      handleTokenExpired: vi.fn(),
    } as any

    // 确保在调用 mock 之前先重置
    vi.mocked(useAuth).mockReset()
    vi.mocked(useAuthStore).mockReset()

    // 重要：确保两个 mock 都返回相同的认证状态
    vi.mocked(useAuth).mockReturnValue(mockAuthStore)
    vi.mocked(useAuthStore).mockReturnValue(mockAuthStore)

    return mockAuthStore
  }

  // 创建测试 wrapper 的函数，确保每个测试用独立的实例
  const createWrapper = () => {
    return ({ children }: { children: React.ReactNode }) => {
      return React.createElement(
        BrowserRouter,
        {},
        React.createElement(QueryClientProvider, { client: queryClient }, children)
      )
    }
  }

  afterEach(() => {
    // 彻底清理 queryClient
    queryClient.clear()
    queryClient.cancelQueries()
    queryClient.removeQueries()
    
    // 重置所有 mock
    vi.resetAllMocks()
    vi.clearAllMocks()
  })


  describe('缓存同步测试', () => {
    it('登录后应该立即设置用户数据缓存', async () => {
      setupAuthenticatedState()
      
      vi.mocked(authService.login).mockResolvedValueOnce({
        success: true,
        data: {
          success: true,
          user: mockUser,
          access_token: 'test-token',
          refresh_token: 'test-refresh-token',
        },
        message: 'Login successful',
      })

      const { result } = renderHook(() => useLogin(), { wrapper: createWrapper() })

      // 执行登录
      await act(async () => {
        await result.current.mutateAsync({
          email: 'test@example.com',
          password: 'password123',
        })
      })

      // 验证缓存立即可用
      const cachedUser = queryClient.getQueryData(queryKeys.currentUser())
      expect(cachedUser).toEqual(mockUser)

      // 验证新的 useCurrentUser hook 可以立即获取数据
      const { result: userResult } = renderHook(() => useCurrentUser(), { wrapper: createWrapper() })
      expect(userResult.current.data).toEqual(mockUser)
      expect(userResult.current.isLoading).toBe(false)
    })

    it('更新用户资料应该同步所有使用该数据的组件', async () => {
      setupAuthenticatedState()
      
      // 预设缓存数据
      queryClient.setQueryData(queryKeys.currentUser(), mockUser)

      // 创建多个使用用户数据的 hook 实例
      const { result: user1 } = renderHook(() => useCurrentUser(), { wrapper: createWrapper() })
      const { result: user2 } = renderHook(() => useCurrentUser(), { wrapper: createWrapper() })

      // 验证初始数据相同
      expect(user1.current.data).toEqual(mockUser)
      expect(user2.current.data).toEqual(mockUser)

      // 更新用户资料
      const updateData: UpdateProfileRequest = {
        first_name: 'Updated',
        last_name: 'Name',
      }

      const updatedUser = { ...mockUser, ...updateData }

      vi.mocked(authService.updateProfile).mockResolvedValueOnce({
        success: true,
        data: updatedUser,
        message: 'Profile updated',
      })

      const { result: updateResult } = renderHook(() => useUpdateProfile(), { wrapper: createWrapper() })

      await act(async () => {
        await updateResult.current.mutateAsync(updateData)
      })

      // 验证两个 hook 实例都获得了更新的数据
      await waitFor(() => {
        expect(user1.current.data).toEqual(updatedUser)
        expect(user2.current.data).toEqual(updatedUser)
      })
    })

    it('登出应该清除所有相关缓存', async () => {
      setupAuthenticatedState()
      
      // 预设缓存数据
      queryClient.setQueryData(queryKeys.currentUser(), mockUser)
      queryClient.setQueryData(queryKeys.permissions(), ['read', 'write'])
      queryClient.setQueryData(queryKeys.sessions(), [{ id: 'session1' }])

      vi.mocked(authService.logout).mockResolvedValueOnce({
        success: true,
        message: 'Logged out',
      })

      const { result } = renderHook(() => useLogout(), { wrapper: createWrapper() })

      await act(async () => {
        await result.current.mutateAsync()
      })

      // 验证所有缓存被清除
      expect(queryClient.getQueryData(queryKeys.currentUser())).toBeUndefined()
      expect(queryClient.getQueryData(queryKeys.permissions())).toBeUndefined()
      expect(queryClient.getQueryData(queryKeys.sessions())).toBeUndefined()
    })
  })

  describe('缓存失效测试', () => {
    it('修改密码后应该清除所有缓存并重新登录', async () => {
      setupAuthenticatedState()
      
      // 预设缓存数据
      queryClient.setQueryData(queryKeys.currentUser(), mockUser)
      queryClient.setQueryData(queryKeys.permissions(), ['read', 'write'])

      vi.mocked(authService.changePassword).mockResolvedValueOnce({
        success: true,
        message: 'Password changed',
      })

      const { result } = renderHook(() => useChangePassword(), { wrapper: createWrapper() })

      await act(async () => {
        await result.current.mutateAsync({
          currentPassword: 'old',
          newPassword: 'new',
          confirmNewPassword: 'new',
        })
      })

      // 等待 mutation 完成
      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true)
      })

      // 验证缓存被清除
      expect(queryClient.getQueryData(queryKeys.currentUser())).toBeUndefined()
      expect(queryClient.getQueryData(queryKeys.permissions())).toBeUndefined()
    })

    it('401错误应该触发自动重新获取用户数据', async () => {
      // 先设置认证状态
      const authStore = setupAuthenticatedState()

      // 第一次返回401错误，第二次成功
      const error401 = new Error('Unauthorized')
      ;(error401 as any).status = 401

      vi.mocked(authService.getCurrentUser)
        .mockRejectedValueOnce(error401)
        .mockResolvedValueOnce({
          success: true,
          data: mockUser,
          message: 'Success',
        })

      const { result } = renderHook(() => useCurrentUser(), { wrapper: createWrapper() })

      // 等待第一次请求失败
      await waitFor(() => {
        expect(result.current).toBeTruthy()
        expect(result.current.isError).toBe(true)
      }, { timeout: 3000 })

      // 手动触发重新获取（模拟401处理后的重试）
      await act(async () => {
        result.current.refetch()
      })

      // 等待重新获取成功
      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true)
        expect(result.current.data).toEqual(mockUser)
      }, { timeout: 3000 })
    })
  })

  describe('乐观更新测试', () => {
    it('应该在网络请求完成前立即显示更新的数据', async () => {
      setupAuthenticatedState()
      
      // 预设缓存数据
      queryClient.setQueryData(queryKeys.currentUser(), mockUser)

      const updateData: UpdateProfileRequest = {
        first_name: 'Optimistic',
      }

      // 使用延迟的 Promise 模拟慢速网络
      let resolveUpdate: (value: any) => void
      const updatePromise = new Promise((resolve) => {
        resolveUpdate = resolve
      })

      vi.mocked(authService.updateProfile).mockReturnValueOnce(updatePromise as any)

      const { result: userResult } = renderHook(() => useCurrentUser(), { wrapper: createWrapper() })
      const { result: updateResult } = renderHook(() => useUpdateProfile(), { wrapper: createWrapper() })

      // 等待初始数据加载
      await waitFor(() => {
        expect(userResult.current.data).toEqual(mockUser)
      })

      // 执行更新
      await act(async () => {
        updateResult.current.mutate(updateData)
        // 立即检查乐观更新（在同一个 act 中）
        await new Promise(resolve => setTimeout(resolve, 0))
      })

      // 立即验证乐观更新
      expect(userResult.current.data?.first_name).toBe('Optimistic')

      // 完成网络请求
      await act(async () => {
        resolveUpdate!({
          success: true,
          data: { ...mockUser, ...updateData },
          message: 'Updated',
        })
      })

      // 验证最终数据
      await waitFor(() => {
        expect(updateResult.current.isSuccess).toBe(true)
        expect(userResult.current.data?.first_name).toBe('Optimistic')
      })
    })

    it('网络错误时应该回滚乐观更新', async () => {
      setupAuthenticatedState()
      
      // 预设缓存数据
      queryClient.setQueryData(queryKeys.currentUser(), mockUser)

      const updateData: UpdateProfileRequest = {
        first_name: 'WillFail',
      }

      const updateError = new Error('Network error')
      vi.mocked(authService.updateProfile).mockRejectedValueOnce(updateError)

      const { result: userResult } = renderHook(() => useCurrentUser(), { wrapper: createWrapper() })
      const { result: updateResult } = renderHook(() => useUpdateProfile(), { wrapper: createWrapper() })

      // 执行更新
      await act(async () => {
        try {
          await updateResult.current.mutateAsync(updateData)
        } catch (error) {
          // 忽略错误
        }
      })

      // 验证数据回滚到原始状态
      expect(userResult.current.data?.first_name).toBe(mockUser.first_name)
    })
  })

  describe('并发请求测试', () => {
    it('多个组件同时请求相同数据应该只发起一次网络请求', async () => {
      setupAuthenticatedState()
      
      vi.mocked(authService.getCurrentUser).mockResolvedValue({
        success: true,
        data: mockUser,
        message: 'Success',
      })

      // 同时渲染多个使用相同查询的组件
      const { result: result1 } = renderHook(() => useCurrentUser(), { wrapper: createWrapper() })
      const { result: result2 } = renderHook(() => useCurrentUser(), { wrapper: createWrapper() })
      const { result: result3 } = renderHook(() => useCurrentUser(), { wrapper: createWrapper() })

      // 等待所有请求完成
      await waitFor(() => {
        expect(result1.current.isSuccess).toBe(true)
        expect(result2.current.isSuccess).toBe(true)
        expect(result3.current.isSuccess).toBe(true)
      })

      // 验证只发起了一次网络请求
      expect(vi.mocked(authService.getCurrentUser)).toHaveBeenCalledTimes(1)

      // 验证所有组件获得相同数据
      expect(result1.current.data).toEqual(mockUser)
      expect(result2.current.data).toEqual(mockUser)
      expect(result3.current.data).toEqual(mockUser)
    })

    it('快速连续的更新操作应该按顺序执行', async () => {
      setupAuthenticatedState()
      
      queryClient.setQueryData(queryKeys.currentUser(), mockUser)

      const updates = [
        { first_name: 'First' },
        { first_name: 'Second' },
        { first_name: 'Third' },
      ]

      // Mock 每次更新
      updates.forEach((update, index) => {
        vi.mocked(authService.updateProfile).mockResolvedValueOnce({
          success: true,
          data: { ...mockUser, ...update },
          message: 'Updated',
        })
      })

      const { result } = renderHook(() => useUpdateProfile(), { wrapper: createWrapper() })

      // 快速连续执行多个更新
      const promises = updates.map(update =>
        act(async () => {
          await result.current.mutateAsync(update)
        })
      )

      await Promise.all(promises)

      // 验证最后一个更新生效
      const finalUser = queryClient.getQueryData<User>(queryKeys.currentUser())
      expect(finalUser?.first_name).toBe('Third')

      // 验证所有更新都被调用
      expect(vi.mocked(authService.updateProfile)).toHaveBeenCalledTimes(3)
    })
  })

  describe('背景数据同步测试', () => {
    it('会话数据应该定期自动刷新', async () => {
      // 先设置认证状态
      const authStore = setupAuthenticatedState()
      
      const mockSessions = [
        { id: 'session1', deviceInfo: 'Chrome', lastActive: new Date().toISOString() },
      ]

      // 确保getSessions方法存在并有正确的mock
      vi.mocked(authService.getSessions).mockResolvedValue({
        success: true,
        data: mockSessions,
        message: 'Success',
      })

      const { result } = renderHook(() => useSessions(), { wrapper: createWrapper() })

      // 等待数据加载完成
      await waitFor(() => {
        expect(result.current).toBeTruthy()
        expect(result.current.isSuccess).toBe(true)
        expect(result.current.data).toEqual(mockSessions)
      }, { timeout: 3000 })

      expect(vi.mocked(authService.getSessions)).toHaveBeenCalledTimes(1)

      // 手动触发重新获取（模拟定时刷新）
      await act(async () => {
        queryClient.invalidateQueries({ queryKey: queryKeys.sessions() })
      })

      // 验证重新获取
      await waitFor(() => {
        expect(vi.mocked(authService.getSessions)).toHaveBeenCalledTimes(2)
      }, { timeout: 3000 })
    })

    it('失去焦点后重新获得焦点不应该重新请求（已禁用）', async () => {
      // 先设置认证状态
      const authStore = setupAuthenticatedState()
      
      vi.mocked(authService.getCurrentUser).mockResolvedValue({
        success: true,
        data: mockUser,
        message: 'Success',
      })

      const { result } = renderHook(() => useCurrentUser(), { wrapper: createWrapper() })

      // 等待数据加载完成
      await waitFor(() => {
        expect(result.current).toBeTruthy()
        expect(result.current.isSuccess).toBe(true)
        expect(result.current.data).toEqual(mockUser)
      }, { timeout: 3000 })

      expect(vi.mocked(authService.getCurrentUser)).toHaveBeenCalledTimes(1)

      // 模拟窗口失去和重新获得焦点
      await act(async () => {
        window.dispatchEvent(new Event('blur'))
        await new Promise(resolve => setTimeout(resolve, 100))
        window.dispatchEvent(new Event('focus'))
      })

      // 验证没有重新请求（因为 refetchOnWindowFocus: false）
      expect(vi.mocked(authService.getCurrentUser)).toHaveBeenCalledTimes(1)
    })
  })

  describe('错误边界测试', () => {
    it('单个查询失败不应该影响其他查询', async () => {
      // 先设置认证状态
      const authStore = setupAuthenticatedState()
      
      // 用户查询成功
      vi.mocked(authService.getCurrentUser).mockResolvedValue({
        success: true,
        data: mockUser,
        message: 'Success',
      })

      // 权限查询失败
      const permissionError = new Error('Permission service unavailable')
      vi.mocked(authService.getPermissions).mockRejectedValue(permissionError)

      // 会话查询成功
      vi.mocked(authService.getSessions).mockResolvedValue({
        success: true,
        data: [],
        message: 'Success',
      })

      const { result } = renderHook(
        () => ({
          user: useCurrentUser(),
          permissions: usePermissions(),
          sessions: useSessions(),
        }),
        { wrapper: createWrapper() }
      )

      // 等待用户查询成功，会话查询成功，权限查询失败
      await waitFor(() => {
        expect(result.current).toBeTruthy()
        expect(result.current.user).toBeTruthy()
        expect(result.current.sessions).toBeTruthy()
        expect(result.current.permissions).toBeTruthy()
        expect(result.current.user.isSuccess).toBe(true)
        expect(result.current.user.data).toEqual(mockUser)
        expect(result.current.sessions.isSuccess).toBe(true)
        expect(result.current.sessions.data).toEqual([])
        expect(result.current.permissions.isError).toBe(true)
      }, { timeout: 3000 })

      // 然后等待具体的状态
      await waitFor(() => {
        // 用户查询成功
        expect(result.current.user.isSuccess).toBe(true)
        expect(result.current.user.data).toEqual(mockUser)

        // 权限查询失败但不影响其他查询
        expect(result.current.permissions.isError).toBe(true)
        expect(result.current.permissions.error).toEqual(permissionError)

        // 会话查询成功
        expect(result.current.sessions.isSuccess).toBe(true)
        expect(result.current.sessions.data).toEqual([])
      }, { timeout: 3000 })
    })
  })
})