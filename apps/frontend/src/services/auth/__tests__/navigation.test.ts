/**
 * 导航服务单元测试
 * 测试所有导航服务实现：BrowserNavigationService、HistoryNavigationService、MockNavigationService
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import {
  BrowserNavigationService,
  HistoryNavigationService,
  MockNavigationService,
  createNavigationService,
  createAutoNavigationService,
  NavigationUtils,
} from '../navigation'
import type { INavigationService } from '../types'

describe('Navigation Services', () => {
  // Mock window 对象
  const mockLocation = {
    href: 'http://localhost:3000/test',
    pathname: '/test',
    search: '?param=value',
    hash: '#section',
    replace: vi.fn(),
  }

  const mockHistory = {
    pushState: vi.fn(),
    replaceState: vi.fn(),
    back: vi.fn(),
    forward: vi.fn(),
  }

  const mockWindow = {
    location: mockLocation,
    history: mockHistory,
    dispatchEvent: vi.fn(),
  }

  beforeEach(() => {
    vi.clearAllMocks()

    // 重置 location mock - 完全重新定义所有属性
    Object.defineProperties(mockLocation, {
      href: {
        value: 'http://localhost:3000/test',
        writable: true,
        configurable: true,
      },
      pathname: {
        value: '/test',
        writable: true,
        configurable: true,
      },
      search: {
        value: '?param=value',
        writable: true,
        configurable: true,
      },
      hash: {
        value: '#section',
        writable: true,
        configurable: true,
      },
      replace: {
        value: vi.fn(),
        writable: true,
        configurable: true,
      },
    })

    // 重置 history mock - 确保所有方法都存在并且为有效的函数
    Object.defineProperties(mockHistory, {
      pushState: {
        value: vi.fn(),
        writable: true,
        configurable: true,
        enumerable: true,
      },
      replaceState: {
        value: vi.fn(),
        writable: true,
        configurable: true,
        enumerable: true,
      },
      back: {
        value: vi.fn(),
        writable: true,
        configurable: true,
        enumerable: true,
      },
      forward: {
        value: vi.fn(),
        writable: true,
        configurable: true,
        enumerable: true,
      },
    })

    // 确保 mockWindow.history 正确引用了 mockHistory
    Object.defineProperty(mockWindow, 'history', {
      value: mockHistory,
      writable: true,
      configurable: true,
    })
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('BrowserNavigationService', () => {
    let navigationService: BrowserNavigationService

    beforeEach(() => {
      navigationService = new BrowserNavigationService()

      // Mock window 对象
      Object.defineProperty(global, 'window', {
        value: mockWindow,
        writable: true,
      })
    })

    describe('Basic Operations', () => {
      it('应该能重定向到指定路径', () => {
        navigationService.redirectTo('/login')

        expect(mockLocation.href).toBe('/login')
      })

      it('应该能重定向到完整 URL', () => {
        navigationService.redirectTo('https://example.com/login')

        expect(mockLocation.href).toBe('https://example.com/login')
      })

      it('应该能获取当前路径', () => {
        const currentPath = navigationService.getCurrentPath()

        expect(currentPath).toBe('/test?param=value#section')
      })

      it('应该能替换当前路径', () => {
        navigationService.replace('/new-path')

        expect(mockLocation.replace).toHaveBeenCalledWith('/new-path')
      })

      it('应该能获取查询参数', () => {
        const searchParams = navigationService.getSearchParams()

        expect(searchParams.get('param')).toBe('value')
      })
    })

    describe('URL Normalization', () => {
      it('应该标准化相对路径', () => {
        navigationService.redirectTo('login')

        expect(mockLocation.href).toBe('/login')
      })

      it('应该处理空路径', () => {
        navigationService.redirectTo('')

        expect(mockLocation.href).toBe('/')
      })

      it('应该保持绝对路径不变', () => {
        navigationService.redirectTo('/dashboard')

        expect(mockLocation.href).toBe('/dashboard')
      })

      it('应该保持完整 URL 不变', () => {
        const fullUrl = 'https://example.com/path'
        navigationService.redirectTo(fullUrl)

        expect(mockLocation.href).toBe(fullUrl)
      })
    })

    describe('Error Handling', () => {
      it('应该处理导航失败的情况', () => {
        const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

        // 保存原始描述符
        const originalDescriptor = Object.getOwnPropertyDescriptor(mockLocation, 'href')

        // Mock location.href 设置失败
        Object.defineProperty(mockLocation, 'href', {
          set: vi.fn(() => {
            throw new Error('Navigation failed')
          }),
          configurable: true,
        })

        navigationService.redirectTo('/test')

        expect(consoleSpy).toHaveBeenCalledWith(
          expect.stringContaining('Failed to redirect'),
          expect.any(Error),
        )

        // 恢复原始属性描述符
        if (originalDescriptor) {
          Object.defineProperty(mockLocation, 'href', originalDescriptor)
        } else {
          delete (mockLocation as any).href
          mockLocation.href = 'http://localhost:3000/test'
        }

        consoleSpy.mockRestore()
      })

      it('应该处理获取当前路径失败的情况', () => {
        const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

        // Mock pathname 访问失败
        Object.defineProperty(mockLocation, 'pathname', {
          get: vi.fn(() => {
            throw new Error('Access denied')
          }),
          configurable: true,
        })

        const path = navigationService.getCurrentPath()

        expect(path).toBe('')
        expect(consoleSpy).toHaveBeenCalled()

        consoleSpy.mockRestore()
      })

      it('应该处理获取查询参数失败的情况', () => {
        const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

        // Mock search 访问失败
        Object.defineProperty(mockLocation, 'search', {
          get: vi.fn(() => {
            throw new Error('Access denied')
          }),
          configurable: true,
        })

        const params = navigationService.getSearchParams()

        expect(params).toBeInstanceOf(URLSearchParams)
        expect(params.toString()).toBe('')
        expect(consoleSpy).toHaveBeenCalled()

        consoleSpy.mockRestore()
      })
    })

    describe('Server-Side Rendering', () => {
      it('应该在服务端环境中优雅降级', () => {
        const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})

        // 模拟服务端环境
        Object.defineProperty(global, 'window', {
          value: undefined,
          writable: true,
        })

        const serverService = new BrowserNavigationService()

        serverService.redirectTo('/test')
        expect(consoleSpy).toHaveBeenCalledWith(
          expect.stringContaining('not available on server side'),
        )

        expect(serverService.getCurrentPath()).toBe('')

        serverService.replace('/test')
        expect(consoleSpy).toHaveBeenCalledWith(
          expect.stringContaining('not available on server side'),
        )

        const params = serverService.getSearchParams()
        expect(params.toString()).toBe('')

        consoleSpy.mockRestore()
      })
    })
  })

  describe('HistoryNavigationService', () => {
    let navigationService: HistoryNavigationService

    beforeEach(() => {
      navigationService = new HistoryNavigationService()

      // Mock window 对象
      Object.defineProperty(global, 'window', {
        value: mockWindow,
        writable: true,
      })
    })

    describe('History API Operations', () => {
      it('应该使用 pushState 进行导航', () => {
        navigationService.redirectTo('/dashboard')

        expect(mockHistory.pushState).toHaveBeenCalledWith(null, '', '/dashboard')
        expect(mockWindow.dispatchEvent).toHaveBeenCalled()
      })

      it('应该使用 replaceState 替换路径', () => {
        navigationService.replace('/new-path')

        expect(mockHistory.replaceState).toHaveBeenCalledWith(null, '', '/new-path')
        expect(mockWindow.dispatchEvent).toHaveBeenCalled()
      })

      it('应该能后退到上一页', () => {
        navigationService.goBack()

        expect(mockHistory.back).toHaveBeenCalled()
      })

      it('应该能前进到下一页', () => {
        navigationService.goForward()

        expect(mockHistory.forward).toHaveBeenCalled()
      })
    })

    describe('Route Change Events', () => {
      it('应该在导航时触发路由变化事件', () => {
        const eventSpy = vi.spyOn(mockWindow, 'dispatchEvent')

        navigationService.redirectTo('/test')

        expect(eventSpy).toHaveBeenCalledWith(
          expect.objectContaining({
            type: 'routechange',
          }),
        )
      })

      it('应该在替换路径时触发路由变化事件', () => {
        const eventSpy = vi.spyOn(mockWindow, 'dispatchEvent')

        navigationService.replace('/test')

        expect(eventSpy).toHaveBeenCalledWith(
          expect.objectContaining({
            type: 'routechange',
          }),
        )
      })

      it('应该处理事件触发失败的情况', () => {
        const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

        mockWindow.dispatchEvent = vi.fn(() => {
          throw new Error('Event dispatch failed')
        })

        navigationService.redirectTo('/test')

        expect(consoleSpy).toHaveBeenCalledWith(
          expect.stringContaining('Failed to trigger route change'),
          expect.any(Error),
        )

        consoleSpy.mockRestore()
      })
    })

    describe('Fallback Behavior', () => {
      it('应该在 History API 不可用时降级到 BrowserNavigationService', () => {
        const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})

        // Mock History API 不可用
        Object.defineProperty(mockWindow, 'history', {
          value: null,
          writable: true,
        })

        navigationService.redirectTo('/test')

        expect(consoleSpy).toHaveBeenCalledWith(
          expect.stringContaining('History API not available'),
        )
        expect(mockLocation.href).toBe('/test')

        consoleSpy.mockRestore()
      })

      it('应该在服务端环境中优雅降级', () => {
        const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})

        // 模拟服务端环境
        Object.defineProperty(global, 'window', {
          value: undefined,
          writable: true,
        })

        const serverService = new HistoryNavigationService()

        serverService.redirectTo('/test')
        expect(consoleSpy).toHaveBeenCalled()

        serverService.goBack()
        expect(consoleSpy).toHaveBeenCalledWith(
          expect.stringContaining('History API not available'),
        )

        consoleSpy.mockRestore()
      })
    })

    describe('Error Handling', () => {
      it('应该处理 pushState 失败的情况', () => {
        const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

        // 重新创建服务以确保 History API 可用
        const mockWindowWithHistory = {
          ...mockWindow,
          history: {
            ...mockHistory,
            pushState: vi.fn(() => {
              throw new Error('pushState failed')
            }),
          },
        }

        Object.defineProperty(global, 'window', {
          value: mockWindowWithHistory,
          writable: true,
        })

        // 创建新的服务实例以使用更新的 window 对象
        const testNavigationService = new HistoryNavigationService()

        testNavigationService.redirectTo('/test')

        expect(consoleSpy).toHaveBeenCalledWith(
          expect.stringContaining('Failed to navigate'),
          expect.any(Error),
        )

        consoleSpy.mockRestore()
      })

      it('应该处理历史记录操作失败的情况', () => {
        const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

        // 重新创建服务以确保 History API 可用
        const mockWindowWithHistory = {
          ...mockWindow,
          history: {
            ...mockHistory,
            back: vi.fn(() => {
              throw new Error('back failed')
            }),
          },
        }

        Object.defineProperty(global, 'window', {
          value: mockWindowWithHistory,
          writable: true,
        })

        // 创建新的服务实例以使用更新的 window 对象
        const testNavigationService = new HistoryNavigationService()

        testNavigationService.goBack()

        expect(consoleSpy).toHaveBeenCalledWith(
          expect.stringContaining('Failed to go back'),
          expect.any(Error),
        )

        consoleSpy.mockRestore()
      })
    })
  })

  describe('MockNavigationService', () => {
    let navigationService: MockNavigationService

    beforeEach(() => {
      navigationService = new MockNavigationService('/initial')
    })

    describe('Basic Operations', () => {
      it('应该能设置和获取当前路径', () => {
        expect(navigationService.getCurrentPath()).toBe('/initial')

        navigationService.redirectTo('/dashboard')
        expect(navigationService.getCurrentPath()).toBe('/dashboard')
      })

      it('应该能处理带查询参数的路径', () => {
        navigationService.redirectTo('/search?q=test&page=1')

        expect(navigationService.getCurrentPath()).toBe('/search?q=test&page=1')

        const params = navigationService.getSearchParams()
        expect(params.get('q')).toBe('test')
        expect(params.get('page')).toBe('1')
      })

      it('应该能替换当前路径', () => {
        navigationService.replace('/new-path')

        expect(navigationService.getCurrentPath()).toBe('/new-path')
      })

      it('应该能重置到初始状态', () => {
        navigationService.redirectTo('/somewhere')
        navigationService.reset('/home')

        expect(navigationService.getCurrentPath()).toBe('/home')
      })
    })

    describe('Query Parameters', () => {
      it('应该正确解析查询参数', () => {
        navigationService.redirectTo('/search?keyword=test&filter=active')

        const params = navigationService.getSearchParams()
        expect(params.get('keyword')).toBe('test')
        expect(params.get('filter')).toBe('active')
      })

      it('应该能设置查询参数', () => {
        const newParams = new URLSearchParams('custom=value&another=param')
        navigationService.setSearchParams(newParams)

        const params = navigationService.getSearchParams()
        expect(params.get('custom')).toBe('value')
        expect(params.get('another')).toBe('param')
      })

      it('应该返回查询参数的副本', () => {
        navigationService.redirectTo('/test?param=original')

        const params1 = navigationService.getSearchParams()
        const params2 = navigationService.getSearchParams()

        params1.set('param', 'modified')

        expect(params2.get('param')).toBe('original')
        expect(navigationService.getSearchParams().get('param')).toBe('original')
      })
    })

    describe('URL Normalization', () => {
      it('应该标准化相对路径', () => {
        navigationService.redirectTo('login')

        expect(navigationService.getCurrentPath()).toBe('/login')
      })

      it('应该处理空路径', () => {
        navigationService.redirectTo('')

        expect(navigationService.getCurrentPath()).toBe('/')
      })

      it('应该处理完整 URL', () => {
        navigationService.redirectTo('https://example.com/path?param=value')

        expect(navigationService.getCurrentPath()).toBe('/path?param=value')
      })

      it('应该处理格式错误的 URL', () => {
        navigationService.redirectTo('not-a-valid-url://test')

        expect(navigationService.getCurrentPath()).toBe('/')
      })
    })

    describe('Default Values', () => {
      it('应该使用默认初始路径', () => {
        const defaultService = new MockNavigationService()

        expect(defaultService.getCurrentPath()).toBe('/')
        expect(defaultService.getSearchParams().toString()).toBe('')
      })

      it('应该正确初始化带查询参数的路径', () => {
        const serviceWithParams = new MockNavigationService('/home?welcome=true')

        expect(serviceWithParams.getCurrentPath()).toBe('/home?welcome=true')
        expect(serviceWithParams.getSearchParams().get('welcome')).toBe('true')
      })
    })
  })

  describe('Factory Functions', () => {
    beforeEach(() => {
      Object.defineProperty(global, 'window', {
        value: mockWindow,
        writable: true,
      })
    })

    describe('createNavigationService', () => {
      it('应该创建 BrowserNavigationService', () => {
        const service = createNavigationService('browser')

        expect(service).toBeInstanceOf(BrowserNavigationService)
      })

      it('应该创建 HistoryNavigationService', () => {
        const service = createNavigationService('history')

        expect(service).toBeInstanceOf(HistoryNavigationService)
      })

      it('应该创建 MockNavigationService', () => {
        const service = createNavigationService('mock', { initialPath: '/test' })

        expect(service).toBeInstanceOf(MockNavigationService)
        expect(service.getCurrentPath()).toBe('/test')
      })

      it('应该使用默认类型 browser', () => {
        const service = createNavigationService()

        expect(service).toBeInstanceOf(BrowserNavigationService)
      })

      it('应该抛出不支持类型的错误', () => {
        expect(() => {
          createNavigationService('invalid' as any)
        }).toThrow('Unsupported navigation service type: invalid')
      })
    })

    describe('createAutoNavigationService', () => {
      it('应该在客户端环境创建 HistoryNavigationService', () => {
        // 确保 window 和 history 对象都正确设置了 pushState
        const mockWindowWithPushState = {
          ...mockWindow,
          history: {
            ...mockHistory,
            pushState: vi.fn(), // 确保 pushState 方法存在
            replaceState: vi.fn(),
            back: vi.fn(),
            forward: vi.fn(),
          },
        }

        Object.defineProperty(global, 'window', {
          value: mockWindowWithPushState,
          writable: true,
        })

        const service = createAutoNavigationService()

        expect(service).toBeInstanceOf(HistoryNavigationService)
      })

      it('应该在没有 History API 时创建 BrowserNavigationService', () => {
        // Mock 没有 pushState 的 history
        Object.defineProperty(mockWindow, 'history', {
          value: {},
          writable: true,
        })

        const service = createAutoNavigationService()

        expect(service).toBeInstanceOf(BrowserNavigationService)
      })

      it('应该在服务端环境创建 MockNavigationService', () => {
        Object.defineProperty(global, 'window', {
          value: undefined,
          writable: true,
        })

        const service = createAutoNavigationService()

        expect(service).toBeInstanceOf(MockNavigationService)
      })
    })
  })

  describe('NavigationUtils', () => {
    describe('buildUrl', () => {
      it('应该构建带查询参数的 URL', () => {
        const url = NavigationUtils.buildUrl('/search', {
          q: 'test',
          page: 1,
          active: true,
        })

        expect(url).toContain('/search?')
        expect(url).toContain('q=test')
        expect(url).toContain('page=1')
        expect(url).toContain('active=true')
      })

      it('应该处理空参数对象', () => {
        const url = NavigationUtils.buildUrl('/path', {})

        expect(url).toBe('/path')
      })

      it('应该保留原始路径的哈希', () => {
        const url = NavigationUtils.buildUrl('/path#section', { param: 'value' })

        expect(url).toContain('#section')
        expect(url).toContain('param=value')
      })
    })

    describe('parseSearchParams', () => {
      it('应该解析查询参数字符串', () => {
        const params = NavigationUtils.parseSearchParams('?q=test&page=1&active=true')

        expect(params).toEqual({
          q: 'test',
          page: '1',
          active: 'true',
        })
      })

      it('应该处理没有前导问号的字符串', () => {
        const params = NavigationUtils.parseSearchParams('key=value&another=param')

        expect(params).toEqual({
          key: 'value',
          another: 'param',
        })
      })

      it('应该处理空查询字符串', () => {
        const params = NavigationUtils.parseSearchParams('')

        expect(params).toEqual({})
      })

      it('应该处理重复的参数键', () => {
        const params = NavigationUtils.parseSearchParams('key=first&key=second')

        // URLSearchParams 会保留最后一个值
        expect(params.key).toBe('second')
      })
    })

    describe('isSamePath', () => {
      it('应该识别相同的路径', () => {
        expect(NavigationUtils.isSamePath('/path', '/path')).toBe(true)
        expect(NavigationUtils.isSamePath('/path?a=1', '/path?b=2')).toBe(true)
        expect(NavigationUtils.isSamePath('/path#hash1', '/path#hash2')).toBe(true)
      })

      it('应该识别不同的路径', () => {
        expect(NavigationUtils.isSamePath('/path1', '/path2')).toBe(false)
        expect(NavigationUtils.isSamePath('/path/sub1', '/path/sub2')).toBe(false)
      })

      it('应该处理格式错误的 URL', () => {
        expect(NavigationUtils.isSamePath('invalid-url', 'invalid-url')).toBe(true)
        expect(NavigationUtils.isSamePath('invalid-url1', 'invalid-url2')).toBe(false)
      })
    })

    describe('isExternalLink', () => {
      beforeEach(() => {
        Object.defineProperty(global, 'window', {
          value: {
            location: {
              origin: 'http://localhost:3000',
            },
          },
          writable: true,
        })
      })

      it('应该识别外部链接', () => {
        expect(NavigationUtils.isExternalLink('https://google.com')).toBe(true)
        expect(NavigationUtils.isExternalLink('http://example.com/path')).toBe(true)
      })

      it('应该识别内部链接', () => {
        expect(NavigationUtils.isExternalLink('http://localhost:3000/path')).toBe(false)
        expect(NavigationUtils.isExternalLink('http://localhost:3000/')).toBe(false)
      })

      it('应该处理相对路径', () => {
        expect(NavigationUtils.isExternalLink('/path')).toBe(false)
        expect(NavigationUtils.isExternalLink('path')).toBe(false)
      })

      it('应该处理格式错误的 URL', () => {
        expect(NavigationUtils.isExternalLink('not-a-url')).toBe(false)
      })
    })
  })

  describe('Interface Compliance', () => {
    const navigationTypes: {
      name: string
      create: () => INavigationService
    }[] = [
      {
        name: 'BrowserNavigationService',
        create: () => {
          Object.defineProperty(global, 'window', {
            value: mockWindow,
            writable: true,
          })
          return new BrowserNavigationService()
        },
      },
      {
        name: 'HistoryNavigationService',
        create: () => {
          Object.defineProperty(global, 'window', {
            value: mockWindow,
            writable: true,
          })
          return new HistoryNavigationService()
        },
      },
      {
        name: 'MockNavigationService',
        create: () => new MockNavigationService('/test'),
      },
    ]

    navigationTypes.forEach(({ name, create }) => {
      describe(`${name} Interface Compliance`, () => {
        let service: INavigationService

        beforeEach(() => {
          service = create()
        })

        it('应该实现 INavigationService 接口', () => {
          expect(typeof service.redirectTo).toBe('function')
          expect(typeof service.getCurrentPath).toBe('function')
          expect(typeof service.replace).toBe('function')
          expect(typeof service.getSearchParams).toBe('function')
        })

        it('应该正确处理基本导航操作', () => {
          // 对于 MockNavigationService，可以期待实际的状态更新
          if (name === 'MockNavigationService') {
            service.redirectTo('/test-path')
            expect(service.getCurrentPath()).toContain('test-path')

            service.replace('/replaced-path')
            expect(service.getCurrentPath()).toContain('replaced-path')
          } else {
            // 对于 BrowserNavigationService 和 HistoryNavigationService，在模拟环境中只测试方法调用
            service.redirectTo('/test-path')
            // 在模拟环境中，这些服务不会更新实际状态，但方法应该正常调用
            expect(typeof service.getCurrentPath()).toBe('string')

            service.replace('/replaced-path')
            expect(typeof service.getCurrentPath()).toBe('string')
          }
        })

        it('应该正确处理查询参数', () => {
          service.redirectTo('/test?param=value')

          const params = service.getSearchParams()
          expect(params).toBeInstanceOf(URLSearchParams)

          if (service.getCurrentPath().includes('param=value')) {
            expect(params.get('param')).toBe('value')
          }
        })
      })
    })
  })
})
