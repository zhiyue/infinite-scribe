import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import React from 'react'
import { useHealthCheck } from './useHealthCheck'
import { healthService } from '@/services/healthService'

// Mock健康检查服务
vi.mock('@/services/healthService', () => ({
  healthService: {
    check: vi.fn(),
  },
}))

// 创建测试用的QueryClient
const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        refetchOnWindowFocus: false,
      },
    },
  })

describe('useHealthCheck', () => {
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

  it('应该成功获取健康状态', async () => {
    const mockHealthData = {
      status: 'healthy' as const,
      timestamp: '2024-01-01T00:00:00Z',
      services: {
        database: 'healthy',
        redis: 'healthy',
        kafka: 'healthy',
      },
    }

    // 使用类型断言确保 mock 调用的类型安全
    ;(healthService.check as any).mockResolvedValueOnce?.(mockHealthData)

    const { result } = renderHook(() => useHealthCheck(), { wrapper })

    // 初始状态应该是loading
    expect(result.current.isLoading).toBe(true)
    expect(result.current.data).toBeUndefined()

    // 等待数据加载完成
    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
    })

    expect(result.current.data).toEqual(mockHealthData)
    expect(result.current.error).toBeNull()
  })

  it('应该处理健康检查失败的情况', async () => {
    const mockError = new Error('API Error: 500 Internal Server Error')
    // 使用类型断言确保 mock 调用的类型安全
    ;(healthService.check as any).mockRejectedValueOnce?.(mockError)

    const { result } = renderHook(() => useHealthCheck(), { wrapper })

    await waitFor(() => {
      expect(result.current.isError).toBe(true)
    })

    expect(result.current.error).toEqual(mockError)
    expect(result.current.data).toBeUndefined()
  })
})
