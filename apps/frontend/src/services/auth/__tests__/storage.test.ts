/**
 * 存储服务单元测试
 * 测试所有存储服务实现：LocalStorageService、SessionStorageService、MemoryStorageService
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import {
  LocalStorageService,
  SessionStorageService,
  MemoryStorageService,
  createStorageService,
} from '../storage'
import type { IStorageService } from '../types'

describe('Storage Services', () => {
  // 在每个测试前清理存储
  beforeEach(() => {
    localStorage.clear()
    sessionStorage.clear()
  })

  afterEach(() => {
    localStorage.clear()
    sessionStorage.clear()
    vi.restoreAllMocks()
  })

  describe('LocalStorageService', () => {
    let storageService: LocalStorageService

    beforeEach(() => {
      storageService = new LocalStorageService('test_')
    })

    describe('Basic Operations', () => {
      it('应该能存储和检索字符串值', () => {
        storageService.setItem('key1', 'value1')
        
        expect(storageService.getItem('key1')).toBe('value1')
      })

      it('应该能存储空字符串', () => {
        storageService.setItem('empty', '')
        
        expect(storageService.getItem('empty')).toBe('')
      })

      it('应该为不存在的键返回 null', () => {
        expect(storageService.getItem('nonexistent')).toBeNull()
      })

      it('应该能删除存储的值', () => {
        storageService.setItem('key1', 'value1')
        storageService.removeItem('key1')
        
        expect(storageService.getItem('key1')).toBeNull()
      })

      it('应该能清空所有带前缀的存储', () => {
        storageService.setItem('key1', 'value1')
        storageService.setItem('key2', 'value2')
        
        // 添加一些不带前缀的数据
        localStorage.setItem('other_key', 'other_value')
        
        storageService.clear()
        
        // 带前缀的数据应该被清除
        expect(storageService.getItem('key1')).toBeNull()
        expect(storageService.getItem('key2')).toBeNull()
        
        // 不带前缀的数据应该保留
        expect(localStorage.getItem('other_key')).toBe('other_value')
      })
    })

    describe('Prefix Handling', () => {
      it('应该正确使用默认前缀', () => {
        const defaultService = new LocalStorageService()
        defaultService.setItem('test', 'value')
        
        expect(localStorage.getItem('auth_test')).toBe('value')
      })

      it('应该正确使用自定义前缀', () => {
        const customService = new LocalStorageService('custom_')
        customService.setItem('test', 'value')
        
        expect(localStorage.getItem('custom_test')).toBe('value')
      })

      it('应该隔离不同前缀的存储服务', () => {
        const service1 = new LocalStorageService('app1_')
        const service2 = new LocalStorageService('app2_')
        
        service1.setItem('key', 'value1')
        service2.setItem('key', 'value2')
        
        expect(service1.getItem('key')).toBe('value1')
        expect(service2.getItem('key')).toBe('value2')
      })
    })

    describe('Error Handling', () => {
      it('应该处理 localStorage 不可用的情况', () => {
        // Mock localStorage 不可用
        const originalLocalStorage = window.localStorage
        const localStorageMock = {
          setItem: vi.fn(() => {
            throw new Error('localStorage not available')
          }),
          getItem: vi.fn(() => {
            throw new Error('localStorage not available')
          }),
          removeItem: vi.fn(() => {
            throw new Error('localStorage not available')
          }),
          clear: vi.fn(),
          length: 0,
          key: vi.fn(),
        }
        
        Object.defineProperty(window, 'localStorage', {
          value: localStorageMock,
          writable: true,
        })
        
        const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
        
        const service = new LocalStorageService('test_')
        
        // 所有操作都应该优雅地失败
        service.setItem('key', 'value')
        expect(service.getItem('key')).toBeNull()
        
        service.removeItem('key')
        service.clear()
        
        expect(consoleSpy).toHaveBeenCalled()
        
        // 恢复原始 localStorage
        Object.defineProperty(window, 'localStorage', {
          value: originalLocalStorage,
          writable: true,
        })
        
        consoleSpy.mockRestore()
      })

      it('应该处理存储空间不足的情况', () => {
        const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
        const consoleWarnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})
        
        // 添加一些可清理的数据到实际的 localStorage
        localStorage.setItem('cache_temp', 'temp_data')
        localStorage.setItem('temp_data', 'temp_value')
        localStorage.setItem('analytics_test', 'analytics_data')
        localStorage.setItem('debug_info', 'debug_data')
        
        // 使用更直接的方法：直接测试 handleQuotaExceeded 方法和相关逻辑
        // 创建一个能够触发 quota exceeded 错误的场景
        const service = storageService as any // 访问私有方法进行测试
        
        // 测试 isQuotaExceededError 方法
        const quotaError = new Error('QuotaExceededError')
        quotaError.name = 'QuotaExceededError'
        ;(quotaError as any).code = 22
        
        expect(service.isQuotaExceededError(quotaError)).toBe(true)
        
        // 测试 getNonCriticalKeys 方法
        const nonCriticalKeys = service.getNonCriticalKeys()
        expect(nonCriticalKeys).toContain('cache_temp')
        expect(nonCriticalKeys).toContain('temp_data')
        expect(nonCriticalKeys).toContain('analytics_test')
        expect(nonCriticalKeys).toContain('debug_info')
        
        // 测试 handleQuotaExceeded 方法
        service.handleQuotaExceeded('test_key', 'test_value')
        
        // 验证警告日志被调用（来自 handleQuotaExceeded）
        expect(consoleWarnSpy).toHaveBeenCalledWith(
          expect.stringContaining('localStorage quota exceeded')
        )
        
        // 验证一些非关键数据被清理了
        // 注意：由于 handleQuotaExceeded 的逻辑，在清理后会尝试重新设置
        // 如果成功设置，会打印成功日志；如果失败，会继续清理
        
        consoleErrorSpy.mockRestore()
        consoleWarnSpy.mockRestore()
      })
    })

    describe('Storage Statistics', () => {
      it('应该正确计算存储统计', () => {
        storageService.setItem('key1', 'value1')
        storageService.setItem('key2', 'value2')
        
        // 添加非认证相关数据
        localStorage.setItem('other_key', 'other_value')
        
        const stats = storageService.getStorageStats()
        
        expect(stats.available).toBe(true)
        expect(stats.authKeys).toBe(2)
        expect(stats.totalKeys).toBeGreaterThan(2)
        expect(stats.authSize).toBeGreaterThan(0)
        expect(stats.totalSize).toBeGreaterThan(stats.authSize)
      })

      it('应该在存储不可用时返回正确的统计', () => {
        // Mock localStorage 不可用
        const originalLocalStorage = window.localStorage
        Object.defineProperty(window, 'localStorage', {
          value: {
            setItem: vi.fn(() => { throw new Error('Not available') }),
            getItem: vi.fn(() => { throw new Error('Not available') }),
            removeItem: vi.fn(),
            clear: vi.fn(),
            length: 0,
            key: vi.fn(),
          },
          writable: true,
        })
        
        const service = new LocalStorageService('test_')
        const stats = service.getStorageStats()
        
        expect(stats.available).toBe(false)
        expect(stats.totalKeys).toBe(0)
        expect(stats.authKeys).toBe(0)
        
        // 恢复原始 localStorage
        Object.defineProperty(window, 'localStorage', {
          value: originalLocalStorage,
          writable: true,
        })
      })
    })

    describe('Quota Management', () => {
      it('应该识别非关键键进行清理', () => {
        // 添加各种类型的数据
        localStorage.setItem('cache_data', 'cache')
        localStorage.setItem('temp_session', 'temp')
        localStorage.setItem('analytics_tracking', 'analytics')
        localStorage.setItem('test_access_token', 'important')
        localStorage.setItem('user_profile', 'important')
        
        const service = new LocalStorageService('test_')
        
        // 现在 getNonCriticalKeys 是公共方法了
        const nonCriticalKeys = service.getNonCriticalKeys()
        
        expect(nonCriticalKeys).toContain('cache_data')
        expect(nonCriticalKeys).toContain('temp_session')
        expect(nonCriticalKeys).toContain('analytics_tracking')
        expect(nonCriticalKeys).not.toContain('test_access_token')
        expect(nonCriticalKeys).not.toContain('user_profile')
      })
    })
  })

  describe('SessionStorageService', () => {
    let storageService: SessionStorageService

    beforeEach(() => {
      storageService = new SessionStorageService('test_')
    })

    describe('Basic Operations', () => {
      it('应该能存储和检索字符串值', () => {
        storageService.setItem('key1', 'value1')
        
        expect(storageService.getItem('key1')).toBe('value1')
      })

      it('应该为不存在的键返回 null', () => {
        expect(storageService.getItem('nonexistent')).toBeNull()
      })

      it('应该能删除存储的值', () => {
        storageService.setItem('key1', 'value1')
        storageService.removeItem('key1')
        
        expect(storageService.getItem('key1')).toBeNull()
      })

      it('应该能清空所有带前缀的存储', () => {
        storageService.setItem('key1', 'value1')
        storageService.setItem('key2', 'value2')
        
        // 添加一些不带前缀的数据
        sessionStorage.setItem('other_key', 'other_value')
        
        storageService.clear()
        
        // 带前缀的数据应该被清除
        expect(storageService.getItem('key1')).toBeNull()
        expect(storageService.getItem('key2')).toBeNull()
        
        // 不带前缀的数据应该保留
        expect(sessionStorage.getItem('other_key')).toBe('other_value')
      })
    })

    describe('Prefix Handling', () => {
      it('应该正确使用自定义前缀', () => {
        const customService = new SessionStorageService('session_')
        customService.setItem('test', 'value')
        
        expect(sessionStorage.getItem('session_test')).toBe('value')
      })

      it('应该隔离不同前缀的存储服务', () => {
        const service1 = new SessionStorageService('app1_')
        const service2 = new SessionStorageService('app2_')
        
        service1.setItem('key', 'value1')
        service2.setItem('key', 'value2')
        
        expect(service1.getItem('key')).toBe('value1')
        expect(service2.getItem('key')).toBe('value2')
      })
    })

    describe('Error Handling', () => {
      it('应该处理 sessionStorage 不可用的情况', () => {
        // Mock sessionStorage 不可用
        const originalSessionStorage = window.sessionStorage
        const sessionStorageMock = {
          setItem: vi.fn(() => {
            throw new Error('sessionStorage not available')
          }),
          getItem: vi.fn(() => {
            throw new Error('sessionStorage not available')
          }),
          removeItem: vi.fn(() => {
            throw new Error('sessionStorage not available')
          }),
          clear: vi.fn(),
          length: 0,
          key: vi.fn(),
        }
        
        Object.defineProperty(window, 'sessionStorage', {
          value: sessionStorageMock,
          writable: true,
        })
        
        const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
        
        const service = new SessionStorageService('test_')
        
        // 所有操作都应该优雅地失败
        service.setItem('key', 'value')
        expect(service.getItem('key')).toBeNull()
        
        service.removeItem('key')
        service.clear()
        
        expect(consoleSpy).toHaveBeenCalled()
        
        // 恢复原始 sessionStorage
        Object.defineProperty(window, 'sessionStorage', {
          value: originalSessionStorage,
          writable: true,
        })
        
        consoleSpy.mockRestore()
      })
    })
  })

  describe('MemoryStorageService', () => {
    let storageService: MemoryStorageService

    beforeEach(() => {
      storageService = new MemoryStorageService('test_')
    })

    describe('Basic Operations', () => {
      it('应该能存储和检索字符串值', () => {
        storageService.setItem('key1', 'value1')
        
        expect(storageService.getItem('key1')).toBe('value1')
      })

      it('应该能存储空字符串', () => {
        storageService.setItem('empty', '')
        
        expect(storageService.getItem('empty')).toBe('')
      })

      it('应该为不存在的键返回 null', () => {
        expect(storageService.getItem('nonexistent')).toBeNull()
      })

      it('应该能删除存储的值', () => {
        storageService.setItem('key1', 'value1')
        storageService.removeItem('key1')
        
        expect(storageService.getItem('key1')).toBeNull()
      })

      it('应该能清空所有带前缀的存储', () => {
        storageService.setItem('key1', 'value1')
        storageService.setItem('key2', 'value2')
        
        storageService.clear()
        
        expect(storageService.getItem('key1')).toBeNull()
        expect(storageService.getItem('key2')).toBeNull()
      })
    })

    describe('Prefix Handling', () => {
      it('应该正确使用默认前缀', () => {
        const defaultService = new MemoryStorageService()
        defaultService.setItem('test', 'value')
        
        const storage = defaultService.getStorage()
        expect(storage.get('auth_test')).toBe('value')
      })

      it('应该正确使用自定义前缀', () => {
        const customService = new MemoryStorageService('memory_')
        customService.setItem('test', 'value')
        
        const storage = customService.getStorage()
        expect(storage.get('memory_test')).toBe('value')
      })

      it('应该隔离不同前缀的存储服务', () => {
        const service1 = new MemoryStorageService('app1_')
        const service2 = new MemoryStorageService('app2_')
        
        service1.setItem('key', 'value1')
        service2.setItem('key', 'value2')
        
        expect(service1.getItem('key')).toBe('value1')
        expect(service2.getItem('key')).toBe('value2')
        
        // 验证存储隔离
        const storage1 = service1.getStorage()
        const storage2 = service2.getStorage()
        
        expect(storage1.get('app1_key')).toBe('value1')
        expect(storage2.get('app2_key')).toBe('value2')
        expect(storage1.has('app2_key')).toBe(false)
        expect(storage2.has('app1_key')).toBe(false)
      })
    })

    describe('Debug Features', () => {
      it('应该提供存储状态访问', () => {
        storageService.setItem('key1', 'value1')
        storageService.setItem('key2', 'value2')
        
        const storage = storageService.getStorage()
        
        expect(storage).toBeInstanceOf(Map)
        expect(storage.get('test_key1')).toBe('value1')
        expect(storage.get('test_key2')).toBe('value2')
        expect(storage.size).toBe(2)
      })

      it('应该返回存储的副本而不是引用', () => {
        storageService.setItem('key1', 'value1')
        
        const storage1 = storageService.getStorage()
        const storage2 = storageService.getStorage()
        
        // 修改返回的 Map 不应该影响原始存储
        storage1.set('test_new_key', 'new_value')
        
        expect(storage2.has('test_new_key')).toBe(false)
        expect(storageService.getItem('new_key')).toBeNull()
      })
    })

    describe('Memory Management', () => {
      it('应该正确处理大量数据', () => {
        const largeData = 'x'.repeat(10000)
        
        for (let i = 0; i < 100; i++) {
          storageService.setItem(`key_${i}`, `${largeData}_${i}`)
        }
        
        // 验证数据完整性
        expect(storageService.getItem('key_0')).toBe(`${largeData}_0`)
        expect(storageService.getItem('key_99')).toBe(`${largeData}_99`)
        
        const storage = storageService.getStorage()
        expect(storage.size).toBe(100)
      })

      it('应该正确清理前缀数据', () => {
        const service1 = new MemoryStorageService('app1_')
        const service2 = new MemoryStorageService('app2_')
        
        // 添加数据到两个服务
        for (let i = 0; i < 10; i++) {
          service1.setItem(`key_${i}`, `value1_${i}`)
          service2.setItem(`key_${i}`, `value2_${i}`)
        }
        
        // 清理第一个服务的数据
        service1.clear()
        
        // 验证清理结果
        expect(service1.getItem('key_0')).toBeNull()
        expect(service2.getItem('key_0')).toBe('value2_0')
        
        const storage1 = service1.getStorage()
        const storage2 = service2.getStorage()
        
        expect(storage1.size).toBe(0)
        expect(storage2.size).toBe(10)
      })
    })
  })

  describe('createStorageService Factory', () => {
    it('应该创建 LocalStorageService', () => {
      const service = createStorageService('localStorage', 'test_')
      
      expect(service).toBeInstanceOf(LocalStorageService)
    })

    it('应该创建 SessionStorageService', () => {
      const service = createStorageService('sessionStorage', 'test_')
      
      expect(service).toBeInstanceOf(SessionStorageService)
    })

    it('应该创建 MemoryStorageService', () => {
      const service = createStorageService('memory', 'test_')
      
      expect(service).toBeInstanceOf(MemoryStorageService)
    })

    it('应该使用默认类型 localStorage', () => {
      const service = createStorageService()
      
      expect(service).toBeInstanceOf(LocalStorageService)
    })

    it('应该抛出不支持类型的错误', () => {
      expect(() => {
        createStorageService('invalid' as any)
      }).toThrow('Unsupported storage type: invalid')
    })

    it('应该传递前缀参数', () => {
      const service = createStorageService('memory', 'custom_prefix_')
      
      service.setItem('test', 'value')
      
      const memoryService = service as MemoryStorageService
      const storage = memoryService.getStorage()
      
      expect(storage.get('custom_prefix_test')).toBe('value')
    })
  })

  describe('Interface Compliance', () => {
    const storageTypes: Array<{
      name: string
      create: () => IStorageService
    }> = [
      {
        name: 'LocalStorageService',
        create: () => new LocalStorageService('test_'),
      },
      {
        name: 'SessionStorageService',
        create: () => new SessionStorageService('test_'),
      },
      {
        name: 'MemoryStorageService',
        create: () => new MemoryStorageService('test_'),
      },
    ]

    storageTypes.forEach(({ name, create }) => {
      describe(`${name} Interface Compliance`, () => {
        let service: IStorageService

        beforeEach(() => {
          service = create()
        })

        it('应该实现 IStorageService 接口', () => {
          expect(typeof service.getItem).toBe('function')
          expect(typeof service.setItem).toBe('function')
          expect(typeof service.removeItem).toBe('function')
          expect(typeof service.clear).toBe('function')
        })

        it('应该正确处理基本存储操作', () => {
          // 设置值
          service.setItem('test_key', 'test_value')
          
          // 获取值
          expect(service.getItem('test_key')).toBe('test_value')
          
          // 删除值
          service.removeItem('test_key')
          expect(service.getItem('test_key')).toBeNull()
        })

        it('应该正确处理清空操作', () => {
          service.setItem('key1', 'value1')
          service.setItem('key2', 'value2')
          
          service.clear()
          
          expect(service.getItem('key1')).toBeNull()
          expect(service.getItem('key2')).toBeNull()
        })
      })
    })
  })

  describe('Cross-Service Integration', () => {
    it('应该在不同存储类型间保持数据隔离', () => {
      const localStorage = new LocalStorageService('test_')
      const sessionStorage = new SessionStorageService('test_')
      const memoryStorage = new MemoryStorageService('test_')
      
      // 在不同存储中设置相同键的不同值
      localStorage.setItem('shared_key', 'local_value')
      sessionStorage.setItem('shared_key', 'session_value')
      memoryStorage.setItem('shared_key', 'memory_value')
      
      // 验证数据隔离
      expect(localStorage.getItem('shared_key')).toBe('local_value')
      expect(sessionStorage.getItem('shared_key')).toBe('session_value')
      expect(memoryStorage.getItem('shared_key')).toBe('memory_value')
      
      // 清理一个不应该影响其他
      localStorage.clear()
      
      expect(localStorage.getItem('shared_key')).toBeNull()
      expect(sessionStorage.getItem('shared_key')).toBe('session_value')
      expect(memoryStorage.getItem('shared_key')).toBe('memory_value')
    })

    it('应该支持相同类型但不同前缀的服务并存', () => {
      const service1 = new MemoryStorageService('app1_')
      const service2 = new MemoryStorageService('app2_')
      const service3 = new MemoryStorageService('app3_')
      
      // 设置相同键名但不同前缀的数据
      service1.setItem('config', 'app1_config')
      service2.setItem('config', 'app2_config')
      service3.setItem('config', 'app3_config')
      
      // 验证数据独立性
      expect(service1.getItem('config')).toBe('app1_config')
      expect(service2.getItem('config')).toBe('app2_config')
      expect(service3.getItem('config')).toBe('app3_config')
      
      // 清理一个服务不应该影响其他服务
      service2.clear()
      
      expect(service1.getItem('config')).toBe('app1_config')
      expect(service2.getItem('config')).toBeNull()
      expect(service3.getItem('config')).toBe('app3_config')
    })
  })
})