/**
 * 测试认证 mock 是否正确工作
 */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderHook, waitFor } from '@testing-library/react'
import React from 'react'
import { BrowserRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { authService } from '../services/auth'
import type { User } from '../types/auth'
import { useAuthStore } from './useAuth'
import { useCurrentUser } from './useAuthQuery'

// Mock 认证服务
vi.mock('../services/auth', () => ({
  authService: {
    getCurrentUser: vi.fn(),
  },
}))

// Mock useAuth hook
vi.mock('./useAuth', () => ({
  useAuthStore: vi.fn(),
}))

const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        refetchOnWindowFocus: false,
      },
    },
  })

describe('认证 Mock 测试', () => {
  let queryClient: QueryClient

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
    role: 'user',
  }

  beforeEach(() => {
    queryClient = createTestQueryClient()
    vi.clearAllMocks()
  })

  const createWrapper = () => {
    return ({ children }: { children: React.ReactNode }) => {
      return React.createElement(
        BrowserRouter,
        {},
        React.createElement(QueryClientProvider, { client: queryClient }, children)
      )
    }
  }

  it('useAuthStore mock 应该正确工作', () => {
    // 设置 mock
    const mockAuthStore = {
      isAuthenticated: true,
      setAuthenticated: vi.fn(),
      clearAuth: vi.fn(),
    }
    
    vi.mocked(useAuthStore).mockReturnValue(mockAuthStore)

    // 测试 mock 是否工作
    const store = useAuthStore()
    expect(store.isAuthenticated).toBe(true)
    expect(store).toEqual(mockAuthStore)
  })

  it('useCurrentUser 应该在认证状态下正确渲染', async () => {
    // 设置认证状态
    const mockAuthStore = {
      isAuthenticated: true,
      setAuthenticated: vi.fn(),
      clearAuth: vi.fn(),
    }
    
    vi.mocked(useAuthStore).mockImplementation(() => mockAuthStore)

    // 设置 API mock
    vi.mocked(authService.getCurrentUser).mockResolvedValue({
      success: true,
      data: mockUser,
      message: 'Success',
    })

    const { result } = renderHook(() => useCurrentUser(), { wrapper: createWrapper() })

    // 验证 hook 正确渲染
    expect(result.current).not.toBeNull()
    expect(result.current).toBeTruthy()

    // 等待数据加载
    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true)
      expect(result.current.data).toEqual(mockUser)
    })
  })

  it('useCurrentUser 在未认证状态下不应该发起请求', () => {
    // 设置未认证状态
    const mockAuthStore = {
      isAuthenticated: false,
      setAuthenticated: vi.fn(),
      clearAuth: vi.fn(),
    }
    
    vi.mocked(useAuthStore).mockImplementation(() => mockAuthStore)

    const { result } = renderHook(() => useCurrentUser(), { wrapper: createWrapper() })

    // 验证 hook 正确渲染但查询被禁用
    expect(result.current).not.toBeNull()
    expect(result.current).toBeTruthy()
    expect(result.current.data).toBeUndefined()
    expect(result.current.isLoading).toBe(false)
    expect(result.current.isSuccess).toBe(false)

    // 验证没有调用 API
    expect(vi.mocked(authService.getCurrentUser)).not.toHaveBeenCalled()
  })
})