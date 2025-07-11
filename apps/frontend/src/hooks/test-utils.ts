/**
 * 测试工具函数
 * 提供统一的测试配置和 mock 工具，避免重复代码
 */

import React from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import { vi } from 'vitest'
import type { ReactNode } from 'react'
import type { AuthStore } from './useAuth'

/**
 * 创建测试用的 QueryClient
 * 默认配置：关闭重试、关闭窗口聚焦刷新
 */
export const createTestQueryClient = (overrides?: any) =>
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
        retry: (failureCount, error: any) => {
          if (error?.status === 401) return false
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
      React.createElement(QueryClientProvider, { client: queryClient }, children)
    )
  }
}

/**
 * 创建 mock AuthStore
 * 提供完整的 Zustand store 接口
 */
export const createMockAuthStore = (overrides?: Partial<AuthStore>) => {
  const defaultAuthStoreValue: AuthStore = {
    isAuthenticated: false,
    setAuthenticated: vi.fn(),
    clearAuth: vi.fn(),
    handleTokenExpired: vi.fn(),
    ...overrides,
  } as any

  // 创建完整的 Zustand store mock
  const mockStore = Object.assign(() => defaultAuthStoreValue, {
    getState: () => defaultAuthStoreValue,
    subscribe: vi.fn(() => vi.fn()),
    setState: vi.fn(),
    destroy: vi.fn(),
  })

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
  delete (window as any).location
  window.location = { href: '' } as any
}

/**
 * 等待所有挂起的 timer
 * 用于测试 refetchInterval 等场景
 */
export const flushPromisesAndTimers = async () => {
  await act(async () => {
    await new Promise(resolve => setTimeout(resolve, 0))
  })
}

// 重新导出 act 以便统一使用
export { act } from '@testing-library/react'