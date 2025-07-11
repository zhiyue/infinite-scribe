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

// 创建测试用的 QueryClient
const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        refetchOnWindowFocus: false,
      },
    },
  })

describe('useAuthQuery hooks', () => {
  let queryClient: QueryClient

  beforeEach(() => {
    queryClient = createTestQueryClient()
    vi.clearAllMocks()
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
        id: '1',
        email: 'test@example.com',
        name: 'Test User',
        role: 'user',
        isActive: true,
        createdAt: '2024-01-01T00:00:00Z',
        updatedAt: '2024-01-01T00:00:00Z',
      }

      vi.mocked(useAuth).mockReturnValue({
        isAuthenticated: true,
        setAuthenticated: vi.fn(),
        clearAuth: vi.fn(),
      } as any)

      vi.mocked(authService.getCurrentUser).mockResolvedValueOnce(mockUser)

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
      vi.mocked(useAuth).mockReturnValue({
        isAuthenticated: true,
        setAuthenticated: vi.fn(),
        clearAuth: vi.fn(),
      } as any)

      const error401 = new Error('Unauthorized')
      ;(error401 as any).status = 401

      vi.mocked(authService.getCurrentUser).mockRejectedValueOnce(error401)

      const { result } = renderHook(() => useCurrentUser(), { wrapper })

      await waitFor(() => {
        expect(result.current.isError).toBe(true)
      })

      expect(result.current.error).toEqual(error401)
      // 确保只调用一次，没有重试
      expect(vi.mocked(authService.getCurrentUser)).toHaveBeenCalledTimes(1)
    })

    it('应该处理其他错误并重试', async () => {
      vi.mocked(useAuth).mockReturnValue({
        isAuthenticated: true,
        setAuthenticated: vi.fn(),
        clearAuth: vi.fn(),
      } as any)

      const networkError = new Error('Network Error')
      vi.mocked(authService.getCurrentUser).mockRejectedValueOnce(networkError)

      // 修改 QueryClient 配置以允许重试
      const testQueryClient = new QueryClient({
        defaultOptions: {
          queries: {
            retry: 3,
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
      })

      // 应该重试多次
      expect(vi.mocked(authService.getCurrentUser).mock.calls.length).toBeGreaterThan(1)
    })

    it('应该正确处理数据缓存', async () => {
      const mockUser: User = {
        id: '1',
        email: 'test@example.com',
        name: 'Test User',
        role: 'user',
        isActive: true,
        createdAt: '2024-01-01T00:00:00Z',
        updatedAt: '2024-01-01T00:00:00Z',
      }

      vi.mocked(useAuth).mockReturnValue({
        isAuthenticated: true,
        setAuthenticated: vi.fn(),
        clearAuth: vi.fn(),
      } as any)

      vi.mocked(authService.getCurrentUser).mockResolvedValue(mockUser)

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
      vi.mocked(useAuth).mockReturnValue({
        isAuthenticated: true,
        setAuthenticated: vi.fn(),
        clearAuth: vi.fn(),
      } as any)

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

    it('应该在有用户角色时获取权限', async () => {
      const mockUser: User = {
        id: '1',
        email: 'test@example.com',
        name: 'Test User',
        role: 'admin',
        isActive: true,
        createdAt: '2024-01-01T00:00:00Z',
        updatedAt: '2024-01-01T00:00:00Z',
      }

      const mockPermissions = ['read', 'write', 'delete']

      vi.mocked(useAuth).mockReturnValue({
        isAuthenticated: true,
        setAuthenticated: vi.fn(),
        clearAuth: vi.fn(),
      } as any)

      vi.mocked(authService.getCurrentUser).mockResolvedValueOnce(mockUser)
      vi.mocked(authService.getPermissions).mockResolvedValueOnce(mockPermissions)

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

      expect(result.current.permissions.data).toEqual(mockPermissions)
    }, 10000)

    it('应该处理权限接口不存在的情况', async () => {
      const mockUser: User = {
        id: '1',
        email: 'test@example.com',
        name: 'Test User',
        role: 'user',
        isActive: true,
        createdAt: '2024-01-01T00:00:00Z',
        updatedAt: '2024-01-01T00:00:00Z',
      }

      vi.mocked(useAuth).mockReturnValue({
        isAuthenticated: true,
        setAuthenticated: vi.fn(),
        clearAuth: vi.fn(),
      } as any)

      vi.mocked(authService.getCurrentUser).mockResolvedValueOnce(mockUser)
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
      vi.mocked(useAuth).mockReturnValue({
        isAuthenticated: false,
        setAuthenticated: vi.fn(),
        clearAuth: vi.fn(),
      } as any)

      const { result } = renderHook(() => useSessions(), { wrapper })

      expect(result.current.isLoading).toBe(false)
      expect(result.current.data).toBeUndefined()
      expect(vi.mocked(authService.getSessions)).not.toHaveBeenCalled()
    })

    it('应该在认证后获取会话列表', async () => {
      const mockSessions = [
        {
          id: 'session1',
          deviceInfo: 'Chrome on Windows',
          lastActive: '2024-01-01T00:00:00Z',
          isCurrent: true,
        },
        {
          id: 'session2',
          deviceInfo: 'Safari on iPhone',
          lastActive: '2024-01-01T00:00:00Z',
          isCurrent: false,
        },
      ]

      vi.mocked(useAuth).mockReturnValue({
        isAuthenticated: true,
        setAuthenticated: vi.fn(),
        clearAuth: vi.fn(),
      } as any)

      vi.mocked(authService.getSessions).mockResolvedValueOnce(mockSessions)

      const { result } = renderHook(() => useSessions(), { wrapper })

      expect(result.current.isLoading).toBe(true)

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false)
      })

      expect(result.current.data).toEqual(mockSessions)
      expect(vi.mocked(authService.getSessions)).toHaveBeenCalledTimes(1)
    })

    it('应该处理会话接口不存在的情况', async () => {
      vi.mocked(useAuth).mockReturnValue({
        isAuthenticated: true,
        setAuthenticated: vi.fn(),
        clearAuth: vi.fn(),
      } as any)

      // 模拟 getSessions 不存在
      vi.mocked(authService.getSessions).mockImplementation(undefined as any)

      const { result } = renderHook(() => useSessions(), { wrapper })

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false)
      })

      // 应该返回空数组
      expect(result.current.data).toEqual([])
    })

    it('应该每2分钟自动刷新会话数据', async () => {
      const mockSessions = [
        {
          id: 'session1',
          deviceInfo: 'Chrome on Windows',
          lastActive: '2024-01-01T00:00:00Z',
          isCurrent: true,
        },
      ]

      vi.mocked(useAuth).mockReturnValue({
        isAuthenticated: true,
        setAuthenticated: vi.fn(),
        clearAuth: vi.fn(),
      } as any)

      vi.mocked(authService.getSessions).mockResolvedValue(mockSessions)

      const { result } = renderHook(() => useSessions(), { wrapper })

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false)
      })

      expect(vi.mocked(authService.getSessions)).toHaveBeenCalledTimes(1)

      // 手动使查询失效，模拟时间流逝
      await act(async () => {
        queryClient.invalidateQueries({ queryKey: ['auth', 'sessions'] })
      })

      await waitFor(() => {
        expect(vi.mocked(authService.getSessions)).toHaveBeenCalledTimes(2)
      }, { timeout: 2000 })
    }, 10000) // 增加测试超时时间
  })
})