/**
 * useAuthQuery hooks 的单元测试
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, waitFor, act } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import React from 'react'
import { useCurrentUser, usePermissions, useSessions } from './useAuthQuery'
import { useAuth, useAuthStore } from './useAuth'
import { authService } from '../services/auth'
import type { User } from '../types/auth'

// Mock 认证服务
vi.mock('../services/auth', () => ({
  authService: {
    getCurrentUser: vi.fn(),
    getPermissions: vi.fn(),
    getSessions: vi.fn(),
  },
}))

// Mock useAuth hook
vi.mock('./useAuth', () => ({
  useAuth: vi.fn(),
  useAuthStore: vi.fn(),
}))

// Mock queryOptions to control retry behavior in tests - 使用模块级别的mock
vi.mock('../lib/queryClient', async () => {
  const actual = await vi.importActual('../lib/queryClient')
  return {
    ...actual,
    queryOptions: {
      user: {
        staleTime: 1000 * 60 * 10,
        gcTime: 1000 * 60 * 30,
        // 在测试中使用智能重试而不是固定数字
        retry: (failureCount: number, error: any) => {
          if (error?.status === 401) return false
          return failureCount < 2
        },
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
      },
    },
  })

describe('useAuthQuery hooks', () => {
  let queryClient: QueryClient

  beforeEach(() => {
    queryClient = createTestQueryClient()
    vi.clearAllMocks()
    
    // 设置默认的 useAuth mock - 创建完整的 store 对象
    const defaultAuthStoreValue = {
      isAuthenticated: false,
      setAuthenticated: vi.fn(),
      clearAuth: vi.fn(),
      handleTokenExpired: vi.fn(),
    } as any

    // 创建完整的 Zustand store mock
    const mockStore = Object.assign(() => defaultAuthStoreValue, {
      getState: () => defaultAuthStoreValue,
      subscribe: vi.fn(() => vi.fn()),
      setState: vi.fn(),
      destroy: vi.fn(),
    })

    vi.mocked(useAuth).mockReturnValue(defaultAuthStoreValue)
    vi.mocked(useAuthStore).mockReturnValue(defaultAuthStoreValue)
  })

  afterEach(() => {
    queryClient.clear()
  })

  const wrapper = ({ children }: { children: React.ReactNode }) => {
    return React.createElement(QueryClientProvider, { client: queryClient }, children)
  }

  describe('useCurrentUser', () => {
    it('应该在未认证时不执行查询', () => {
      const mockAuthStore = {
        isAuthenticated: false,
        setAuthenticated: vi.fn(),
        clearAuth: vi.fn(),
      } as any

      vi.mocked(useAuth).mockReturnValue(mockAuthStore)
      vi.mocked(useAuthStore).mockReturnValue(mockAuthStore)

      const { result } = renderHook(() => useCurrentUser(), { wrapper })

      expect(result.current.isLoading).toBe(false)
      expect(result.current.data).toBeUndefined()
      expect(vi.mocked(authService.getCurrentUser)).not.toHaveBeenCalled()
    })

    it('应该在认证后获取用户数据', async () => {
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

      const mockAuthStore = {
        isAuthenticated: true,
        setAuthenticated: vi.fn(),
        clearAuth: vi.fn(),
      } as any

      vi.mocked(useAuth).mockReturnValue(mockAuthStore)
      vi.mocked(useAuthStore).mockReturnValue(mockAuthStore)

      vi.mocked(authService.getCurrentUser).mockResolvedValueOnce({
        success: true,
        data: mockUser,
        message: 'User profile retrieved successfully'
      })

      const { result } = renderHook(() => useCurrentUser(), { wrapper })

      // 初始状态应该是 loading
      expect(result.current.isLoading).toBe(true)
      expect(result.current.data).toBeUndefined()

      // 等待数据加载完成
      await waitFor(() => {
        expect(result.current.isLoading).toBe(false)
      }, { timeout: 2000 })

      expect(result.current.data).toEqual(mockUser)
      expect(result.current.error).toBeNull()
      expect(vi.mocked(authService.getCurrentUser)).toHaveBeenCalledTimes(1)
    })

    it('应该处理 401 错误不重试', async () => {
      const mockAuthStore = {
        isAuthenticated: true,
        setAuthenticated: vi.fn(),
        clearAuth: vi.fn(),
      } as any

      vi.mocked(useAuth).mockReturnValue(mockAuthStore)
      vi.mocked(useAuthStore).mockReturnValue(mockAuthStore)

      // 创建符合 authService.handleApiError 处理后的错误结构
      const error401 = new Error('Unauthorized')
      ;(error401 as any).status = 401
      ;(error401 as any).response = { status: 401 }

      vi.mocked(authService.getCurrentUser).mockRejectedValueOnce(error401)

      const { result } = renderHook(() => useCurrentUser(), { wrapper })

      await waitFor(() => {
        expect(result.current.isError).toBe(true)
      }, { timeout: 3000 })

      expect(result.current.error).toEqual(error401)
      // 确保只调用一次，没有重试
      expect(vi.mocked(authService.getCurrentUser)).toHaveBeenCalledTimes(1)
    })

    it('应该处理其他错误并重试', async () => {
      const mockAuthStore = {
        isAuthenticated: true,
        setAuthenticated: vi.fn(),
        clearAuth: vi.fn(),
        handleTokenExpired: vi.fn(),
      } as any

      vi.mocked(useAuth).mockReturnValue(mockAuthStore)
      vi.mocked(useAuthStore).mockReturnValue(mockAuthStore)

      const networkError = new Error('Network Error')
      
      // 让所有调用都失败，这样我们可以观察重试次数
      vi.mocked(authService.getCurrentUser).mockRejectedValue(networkError)

      // 修改 QueryClient 配置以允许重试
      const testQueryClient = new QueryClient({
        defaultOptions: {
          queries: {
            retry: 2, // 减少重试次数以加快测试
            retryDelay: 0, // 立即重试以加快测试
            refetchOnWindowFocus: false,
          },
        },
      })

      const testWrapper = ({ children }: { children: React.ReactNode }) => {
        return React.createElement(QueryClientProvider, { client: testQueryClient }, children)
      }

      const { result } = renderHook(() => useCurrentUser(), { wrapper: testWrapper })

      await waitFor(() => {
        expect(result.current.isError).toBe(true)
        expect(result.current.error).toEqual(networkError)
      })

      // 验证发生了重试 (初始请求 + 2 次重试 = 3 次总调用)
      expect(vi.mocked(authService.getCurrentUser)).toHaveBeenCalledTimes(3)
    })

    it('应该正确处理数据缓存', async () => {
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

      const mockAuthStore = {
        isAuthenticated: true,
        setAuthenticated: vi.fn(),
        clearAuth: vi.fn(),
      } as any

      vi.mocked(useAuth).mockReturnValue(mockAuthStore)
      vi.mocked(useAuthStore).mockReturnValue(mockAuthStore)

      vi.mocked(authService.getCurrentUser).mockResolvedValue({
        success: true,
        data: mockUser,
        message: 'User profile retrieved successfully'
      })

      // 第一次渲染
      const { result: result1 } = renderHook(() => useCurrentUser(), { wrapper })

      await waitFor(() => {
        expect(result1.current.isLoading).toBe(false)
      })

      expect(result1.current.data).toEqual(mockUser)
      expect(vi.mocked(authService.getCurrentUser)).toHaveBeenCalledTimes(1)

      // 第二次渲染应该使用缓存
      const { result: result2 } = renderHook(() => useCurrentUser(), { wrapper })

      // 由于数据已经在缓存中，第二次应该立即获得数据
      expect(result2.current.isLoading).toBe(false)
      expect(result2.current.data).toEqual(mockUser)
      // 由于在 staleTime 内，不应该再次调用 API
      expect(vi.mocked(authService.getCurrentUser)).toHaveBeenCalledTimes(1)
    })
  })

  describe('usePermissions', () => {
    it('应该在没有用户角色时不执行查询', () => {
      const mockAuthStore = {
        isAuthenticated: true,
        setAuthenticated: vi.fn(),
        clearAuth: vi.fn(),
      } as any

      vi.mocked(useAuth).mockReturnValue(mockAuthStore)
      vi.mocked(useAuthStore).mockReturnValue(mockAuthStore)

      // 模拟 useCurrentUser 返回没有角色的用户
      const { result } = renderHook(
        () => {
          return {
            user: useCurrentUser(),
            permissions: usePermissions(),
          }
        },
        { wrapper }
      )

      expect(result.current.permissions.isLoading).toBe(false)
      expect(result.current.permissions.data).toBeUndefined()
      expect(vi.mocked(authService.getPermissions)).not.toHaveBeenCalled()
    })

    it('应该在有用户角色时尝试获取权限并处理错误', async () => {
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
        role: 'user', // 添加角色属性
      }

      const mockAuthStore = {
        isAuthenticated: true,
        setAuthenticated: vi.fn(),
        clearAuth: vi.fn(),
      } as any

      vi.mocked(useAuth).mockReturnValue(mockAuthStore)
      vi.mocked(useAuthStore).mockReturnValue(mockAuthStore)

      vi.mocked(authService.getCurrentUser).mockResolvedValueOnce({
        success: true,
        data: mockUser,
        message: 'User profile retrieved successfully'
      })

      const { result } = renderHook(
        () => {
          const user = useCurrentUser()
          const permissions = usePermissions()
          return { user, permissions }
        },
        { wrapper }
      )

      // 等待用户数据加载
      await waitFor(() => {
        expect(result.current.user.isLoading).toBe(false)
      })

      // 等待权限数据加载
      await waitFor(() => {
        expect(result.current.permissions.isLoading).toBe(false)
      })

      // 由于权限API可能未实现，应该返回空数组
      expect(result.current.permissions.data).toEqual([])
      // 应该尝试调用authService.getPermissions
      expect(vi.mocked(authService.getPermissions)).toHaveBeenCalled()
    }, 10000)

    it('应该处理权限接口不存在的情况', async () => {
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
        role: 'user', // 添加角色属性
      }

      const mockAuthStore = {
        isAuthenticated: true,
        setAuthenticated: vi.fn(),
        clearAuth: vi.fn(),
      } as any

      vi.mocked(useAuth).mockReturnValue(mockAuthStore)
      vi.mocked(useAuthStore).mockReturnValue(mockAuthStore)

      vi.mocked(authService.getCurrentUser).mockResolvedValueOnce({
        success: true,
        data: mockUser,
        message: 'User profile retrieved successfully'
      })
      // 模拟 getPermissions 不存在
      vi.mocked(authService.getPermissions).mockImplementation(undefined as any)

      const { result } = renderHook(
        () => {
          const user = useCurrentUser()
          const permissions = usePermissions()
          return { user, permissions }
        },
        { wrapper }
      )

      // 等待用户数据加载
      await waitFor(() => {
        expect(result.current.user.isLoading).toBe(false)
      })

      // 等待权限查询执行
      await waitFor(() => {
        expect(result.current.permissions.isLoading).toBe(false)
      })

      // 应该返回空数组
      expect(result.current.permissions.data).toEqual([])
    })
  })

  describe('useSessions', () => {
    it('应该在未认证时不执行查询', () => {
      const mockAuthStore = {
        isAuthenticated: false,
        setAuthenticated: vi.fn(),
        clearAuth: vi.fn(),
      } as any

      vi.mocked(useAuth).mockReturnValue(mockAuthStore)
      vi.mocked(useAuthStore).mockReturnValue(mockAuthStore)

      const { result } = renderHook(() => useSessions(), { wrapper })

      expect(result.current.isLoading).toBe(false)
      expect(result.current.data).toEqual([]) // 现在有 initialData
      expect(vi.mocked(authService.getSessions)).not.toHaveBeenCalled()
    })

    it('应该在认证后返回空会话列表（API未实现）', async () => {
      const mockAuthStore = {
        isAuthenticated: true,
        setAuthenticated: vi.fn(),
        clearAuth: vi.fn(),
      } as any

      vi.mocked(useAuth).mockReturnValue(mockAuthStore)
      vi.mocked(useAuthStore).mockReturnValue(mockAuthStore)

      // 模拟 getSessions 方法存在但返回空数组
      vi.mocked(authService.getSessions).mockResolvedValueOnce({
        success: true,
        data: [],
        message: 'No sessions found'
      })

      const { result } = renderHook(() => useSessions(), { wrapper })

      // 由于有 initialData，isLoading 应该是 false
      expect(result.current.isLoading).toBe(false)
      
      // 等待查询完成
      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true)
      })

      // 由于mock返回空数组，应该得到空数组
      expect(result.current.data).toEqual([])
      // 应该调用authService.getSessions（因为方法存在）
      expect(vi.mocked(authService.getSessions)).toHaveBeenCalledTimes(1)
    })

    it('应该处理会话接口不存在的情况', async () => {
      const mockAuthStore = {
        isAuthenticated: true,
        setAuthenticated: vi.fn(),
        clearAuth: vi.fn(),
      } as any

      vi.mocked(useAuth).mockReturnValue(mockAuthStore)
      vi.mocked(useAuthStore).mockReturnValue(mockAuthStore)

      // 临时移除 getSessions 方法来模拟API不存在
      const originalGetSessions = vi.mocked(authService.getSessions)
      vi.mocked(authService).getSessions = undefined as any

      const { result } = renderHook(() => useSessions(), { wrapper })

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false)
      })

      // 应该返回空数组（因为API不存在时的默认行为）
      expect(result.current.data).toEqual([])
      
      // 恢复原始mock以免影响后续测试
      vi.mocked(authService).getSessions = originalGetSessions
    })

    it('应该实现会话查询的缓存和刷新机制', async () => {
      const mockAuthStore = {
        isAuthenticated: true,
        setAuthenticated: vi.fn(),
        clearAuth: vi.fn(),
      } as any

      vi.mocked(useAuth).mockReturnValue(mockAuthStore)
      vi.mocked(useAuthStore).mockReturnValue(mockAuthStore)

      // 模拟 getSessions 方法存在但返回空数组
      vi.mocked(authService.getSessions).mockResolvedValue({
        success: true,
        data: [],
        message: 'No sessions found'
      })

      const { result } = renderHook(() => useSessions(), { wrapper })

      // 由于有 initialData，isLoading 应该是 false
      expect(result.current.isLoading).toBe(false)

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true)
      })

      // 由于mock返回空数组，应该得到空数组
      expect(result.current.data).toEqual([])

      // 验证查询键管理正常工作
      const sessionQueryState = queryClient.getQueryState(['auth', 'sessions'])
      expect(sessionQueryState).toBeDefined()
    }, 10000)
  })
})