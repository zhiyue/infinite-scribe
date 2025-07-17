/**
 * 测试工具函数
 * 提供统一的测试配置和 mock 工具，避免重复代码
 */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import React from 'react'
import { BrowserRouter } from 'react-router-dom'
import { vi } from 'vitest'
import type { AuthStore } from './useAuth'

interface QueryClientOverrides {
  queries?: Partial<{
    retry: boolean | number | ((failureCount: number, error: unknown) => boolean)
    refetchOnWindowFocus: boolean
    staleTime: number
    gcTime: number
  }>
  mutations?: Partial<{
    retry: boolean | number
  }>
}

/**
 * 创建测试用的 QueryClient
 * 默认配置：关闭重试、关闭窗口聚焦刷新
 */
export const createTestQueryClient = (overrides?: QueryClientOverrides) =>
  new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        refetchOnWindowFocus: false,
        ...overrides?.queries,
      },
      mutations: {
        retry: false,
        ...overrides?.mutations,
      },
    },
  })

/**
 * 创建智能重试的 QueryClient
 * 401 错误不重试，其他错误最多重试 2 次
 */
export const createTestQueryClientWithSmartRetry = (maxRetries = 2) =>
  new QueryClient({
    defaultOptions: {
      queries: {
        retry: (failureCount: number, error: unknown) => {
          if ((error as { status?: number })?.status === 401) return false
          return failureCount < maxRetries
        },
        refetchOnWindowFocus: false,
      },
      mutations: {
        retry: false,
      },
    },
  })

/**
 * 创建测试 wrapper
 * 包含 QueryClientProvider 和 BrowserRouter
 */
export const createWrapper = (queryClient: QueryClient) => {
  return ({ children }: { children: ReactNode }) => {
    return React.createElement(
      BrowserRouter,
      {},
      React.createElement(QueryClientProvider, { client: queryClient }, children),
    )
  }
}

/**
 * 创建 mock AuthStore
 * 提供完整的 Zustand store 接口
 */
export const createMockAuthStore = (overrides?: Partial<AuthStore>) => {
  const setAuthenticated = vi.fn<[boolean], void>()
  const clearAuth = vi.fn<[], void>()
  const handleTokenExpired = vi.fn<[], Promise<void>>()

  const defaultAuthStoreValue: AuthStore = {
    isAuthenticated: false,
    setAuthenticated,
    clearAuth,
    handleTokenExpired,
    ...(overrides || {}),
  }

  // 创建完整的 Zustand store mock
  type MockStoreType = (() => AuthStore) & {
    getState: () => AuthStore
    subscribe: ReturnType<typeof vi.fn>
    setState: ReturnType<typeof vi.fn>
    destroy: ReturnType<typeof vi.fn>
  }

  const mockStore: MockStoreType = Object.assign(() => defaultAuthStoreValue, {
    getState: () => defaultAuthStoreValue,
    subscribe: vi.fn(() => vi.fn()),
    setState: vi.fn(),
    destroy: vi.fn(),
  }) as MockStoreType

  return {
    storeValue: defaultAuthStoreValue,
    store: mockStore,
  }
}

/**
 * 设置常用的测试 mock
 * 包括 react-router-dom 的 useNavigate
 */
export const setupCommonMocks = () => {
  const mockNavigate = vi.fn()

  vi.mock('react-router-dom', async () => {
    const actual = await vi.importActual('react-router-dom')
    return {
      ...actual,
      useNavigate: () => mockNavigate,
    }
  })

  return {
    mockNavigate,
  }
}

/**
 * 清理 window.location
 * 用于测试需要修改 location 的场景
 */
export const cleanupWindowLocation = () => {
  delete (window as Window & { location?: Location }).location
  window.location = { href: '' } as Location
}

/**
 * 等待所有挂起的 timer
 * 用于测试 refetchInterval 等场景
 */
export const flushPromisesAndTimers = async () => {
  const { act } = await import('@testing-library/react')
  await act(async () => {
    await new Promise((resolve) => setTimeout(resolve, 0))
  })
}

// 重新导出 act 以便统一使用
export { act } from '@testing-library/react'
