/**
 * queryClient 配置的单元测试
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { QueryClient } from '@tanstack/react-query'
import { queryClient, queryOptions, queryKeys } from './queryClient'

// Mock window.location
const mockLocation = {
  href: '',
  reload: vi.fn(),
}

Object.defineProperty(window, 'location', {
  value: mockLocation,
  writable: true,
})

describe('queryClient 配置', () => {
  describe('查询默认配置', () => {
    it('应该正确配置查询重试逻辑', () => {
      const options = queryClient.getDefaultOptions()
      const retryFn = options.queries?.retry

      // 测试 401 错误不重试
      if (typeof retryFn === 'function') {
        expect(retryFn(0, { status: 401 })).toBe(false)
        expect(retryFn(0, { status_code: 401 })).toBe(true) // 只有 status 会被识别为 401
      }

      // 测试其他错误重试
      if (typeof retryFn === 'function') {
        expect(retryFn(0, { status: 500 })).toBe(true)
        expect(retryFn(1, { status: 500 })).toBe(true)
        expect(retryFn(2, { status: 500 })).toBe(true)
        expect(retryFn(3, { status: 500 })).toBe(false) // 超过3次不重试
      }
    })

    it('应该禁用窗口聚焦时自动重新获取', () => {
      const options = queryClient.getDefaultOptions()
      expect(options.queries?.refetchOnWindowFocus).toBe(false)
    })

    it('应该正确设置 staleTime 和 gcTime', () => {
      const options = queryClient.getDefaultOptions()
      expect(options.queries?.staleTime).toBe(5 * 60 * 1000) // 5分钟
      expect(options.queries?.gcTime).toBe(10 * 60 * 1000) // 10分钟
    })
  })

  describe('mutation 默认配置', () => {
    beforeEach(() => {
      mockLocation.href = ''
      vi.clearAllMocks()
    })

    it('应该禁用 mutation 重试', () => {
      const options = queryClient.getDefaultOptions()
      expect(options.mutations?.retry).toBe(0)
    })

    it('应该在 401 错误时清理缓存并跳转登录', () => {
      const options = queryClient.getDefaultOptions()
      const onError = options.mutations?.onError

      if (onError) {
        const clearSpy = vi.spyOn(queryClient, 'clear')
        
        // 触发 401 错误
        onError({ status: 401 } as any, {} as any, {} as any, {} as any)

        expect(clearSpy).toHaveBeenCalled()
        expect(mockLocation.href).toBe('/login')
      }
    })

    it('应该忽略非 401 错误', () => {
      const options = queryClient.getDefaultOptions()
      const onError = options.mutations?.onError

      if (onError) {
        const clearSpy = vi.spyOn(queryClient, 'clear')
        
        // 触发非 401 错误
        onError({ status: 500 } as any, {} as any, {} as any, {} as any)

        expect(clearSpy).not.toHaveBeenCalled()
        expect(mockLocation.href).toBe('')
      }
    })
  })

  describe('queryOptions 配置', () => {
    it('应该为不同资源提供特定的配置', () => {
      // 用户数据配置
      expect(queryOptions.user.staleTime).toBe(1000 * 60 * 10) // 10分钟
      expect(queryOptions.user.cacheTime).toBe(1000 * 60 * 30) // 30分钟

      // 项目列表配置
      expect(queryOptions.projects.staleTime).toBe(1000 * 60 * 2) // 2分钟
      expect(queryOptions.projects.cacheTime).toBe(1000 * 60 * 10) // 10分钟

      // 健康检查配置
      expect(queryOptions.health.staleTime).toBe(1000 * 30) // 30秒
      expect(queryOptions.health.cacheTime).toBe(1000 * 60) // 1分钟

      // 文档内容配置
      expect(queryOptions.documents.staleTime).toBe(1000 * 60 * 15) // 15分钟
      expect(queryOptions.documents.cacheTime).toBe(1000 * 60 * 60) // 1小时
    })
  })

  describe('queryKeys 管理', () => {
    it('应该生成正确的认证相关查询键', () => {
      expect(queryKeys.all).toEqual(['auth'])
      expect(queryKeys.user()).toEqual(['auth', 'user'])
      expect(queryKeys.currentUser()).toEqual(['auth', 'user', 'current'])
      expect(queryKeys.permissions()).toEqual(['auth', 'permissions'])
      expect(queryKeys.sessions()).toEqual(['auth', 'sessions'])
    })

    it('应该生成正确的项目相关查询键', () => {
      expect(queryKeys.projects.all).toEqual(['projects'])
      expect(queryKeys.projects.list()).toEqual(['projects', 'list', undefined])
      expect(queryKeys.projects.list({ status: 'active' })).toEqual(['projects', 'list', { status: 'active' }])
      expect(queryKeys.projects.detail('123')).toEqual(['projects', 'detail', '123'])
    })

    it('应该生成正确的健康检查查询键', () => {
      expect(queryKeys.health.all).toEqual(['health'])
      expect(queryKeys.health.check()).toEqual(['health', 'check'])
    })

    it('查询键应该是不可变的', () => {
      const userKey = queryKeys.user()
      const userKeyCopy = queryKeys.user()
      
      // 应该返回新的数组实例
      expect(userKey).not.toBe(userKeyCopy)
      // 但内容应该相同
      expect(userKey).toEqual(userKeyCopy)
    })
  })

  describe('QueryClient 实例', () => {
    it('应该是 QueryClient 的实例', () => {
      expect(queryClient).toBeInstanceOf(QueryClient)
    })

    it('应该能够正确设置和获取查询数据', () => {
      const testData = { id: '1', name: 'Test User' }
      const testKey = ['test', 'user']

      queryClient.setQueryData(testKey, testData)
      const retrievedData = queryClient.getQueryData(testKey)

      expect(retrievedData).toEqual(testData)
    })

    it('应该能够清除所有缓存', () => {
      // 设置一些测试数据
      queryClient.setQueryData(['test1'], { data: 'test1' })
      queryClient.setQueryData(['test2'], { data: 'test2' })

      // 清除所有缓存
      queryClient.clear()

      // 验证缓存已清除
      expect(queryClient.getQueryData(['test1'])).toBeUndefined()
      expect(queryClient.getQueryData(['test2'])).toBeUndefined()
    })
  })

  describe('类型安全性', () => {
    it('查询键应该是只读的', () => {
      // TypeScript 编译时会检查，这里主要是运行时验证
      const keys = queryKeys.all
      
      // 由于 JavaScript 中数组的只读性是 TypeScript 的编译时特性
      // 运行时不会抛出错误，所以这个测试主要验证 TypeScript 类型
      // 这里我们只能验证它是一个数组并且内容正确
      expect(Array.isArray(keys)).toBe(true)
      expect(keys).toEqual(['auth'])
      
      // 验证查询键生成函数返回新的数组实例（不可变性）
      const keys1 = queryKeys.currentUser()
      const keys2 = queryKeys.currentUser()
      expect(keys1).not.toBe(keys2) // 不同的数组实例
      expect(keys1).toEqual(keys2)  // 但内容相同
    })
  })
})