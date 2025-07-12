/**
 * 导航服务实现
 * 提供抽象的导航接口，支持多种导航方式（window.location、history API、Next.js router 等）
 */

import type { INavigationService } from './types'

/**
 * 浏览器原生导航服务实现
 * 基于 window.location 和 history API
 */
export class BrowserNavigationService implements INavigationService {
  /**
   * 重定向到指定路径
   */
  redirectTo(path: string): void {
    if (!this.isClientSide()) {
      console.warn('Navigation not available on server side')
      return
    }

    try {
      // 使用 window.location.href 进行页面跳转
      window.location.href = this.normalizeUrl(path)
    } catch (error) {
      console.error(`Failed to redirect to ${path}:`, error)
    }
  }

  /**
   * 获取当前路径
   */
  getCurrentPath(): string {
    if (!this.isClientSide()) {
      return ''
    }

    try {
      return window.location.pathname + window.location.search + window.location.hash
    } catch (error) {
      console.error('Failed to get current path:', error)
      return ''
    }
  }

  /**
   * 替换当前路径（不产生历史记录）
   */
  replace(path: string): void {
    if (!this.isClientSide()) {
      console.warn('Navigation not available on server side')
      return
    }

    try {
      window.location.replace(this.normalizeUrl(path))
    } catch (error) {
      console.error(`Failed to replace current path with ${path}:`, error)
    }
  }

  /**
   * 获取当前 URL 查询参数
   */
  getSearchParams(): URLSearchParams {
    if (!this.isClientSide()) {
      return new URLSearchParams()
    }

    try {
      return new URLSearchParams(window.location.search)
    } catch (error) {
      console.error('Failed to get search params:', error)
      return new URLSearchParams()
    }
  }

  /**
   * 检查是否在客户端环境
   * @private
   */
  private isClientSide(): boolean {
    return typeof window !== 'undefined' && typeof window.location !== 'undefined'
  }

  /**
   * 标准化 URL
   * @private
   */
  private normalizeUrl(path: string): string {
    if (!path) {
      return '/'
    }

    // 如果是完整的 URL，直接返回
    if (path.startsWith('http://') || path.startsWith('https://')) {
      return path
    }

    // 确保路径以 / 开头
    if (!path.startsWith('/')) {
      return `/${path}`
    }

    return path
  }
}

/**
 * History API 导航服务实现
 * 基于 HTML5 History API，支持 SPA 路由
 */
export class HistoryNavigationService implements INavigationService {
  /**
   * 重定向到指定路径（使用 pushState）
   */
  redirectTo(path: string): void {
    if (!this.isClientSide() || !this.isHistorySupported()) {
      console.warn('History API not available, falling back to location')
      new BrowserNavigationService().redirectTo(path)
      return
    }

    try {
      const normalizedPath = this.normalizeUrl(path)
      window.history.pushState(null, '', normalizedPath)
      
      // 触发 popstate 事件，通知应用路由变化
      this.triggerRouteChange()
    } catch (error) {
      console.error(`Failed to navigate to ${path}:`, error)
    }
  }

  /**
   * 获取当前路径
   */
  getCurrentPath(): string {
    if (!this.isClientSide()) {
      return ''
    }

    try {
      return window.location.pathname + window.location.search + window.location.hash
    } catch (error) {
      console.error('Failed to get current path:', error)
      return ''
    }
  }

  /**
   * 替换当前路径（不产生历史记录）
   */
  replace(path: string): void {
    if (!this.isClientSide() || !this.isHistorySupported()) {
      console.warn('History API not available, falling back to location')
      new BrowserNavigationService().replace(path)
      return
    }

    try {
      const normalizedPath = this.normalizeUrl(path)
      window.history.replaceState(null, '', normalizedPath)
      
      // 触发 popstate 事件，通知应用路由变化
      this.triggerRouteChange()
    } catch (error) {
      console.error(`Failed to replace current path with ${path}:`, error)
    }
  }

  /**
   * 获取当前 URL 查询参数
   */
  getSearchParams(): URLSearchParams {
    if (!this.isClientSide()) {
      return new URLSearchParams()
    }

    try {
      return new URLSearchParams(window.location.search)
    } catch (error) {
      console.error('Failed to get search params:', error)
      return new URLSearchParams()
    }
  }

  /**
   * 后退到上一页
   */
  goBack(): void {
    if (!this.isClientSide() || !this.isHistorySupported()) {
      console.warn('History API not available')
      return
    }

    try {
      window.history.back()
    } catch (error) {
      console.error('Failed to go back:', error)
    }
  }

  /**
   * 前进到下一页
   */
  goForward(): void {
    if (!this.isClientSide() || !this.isHistorySupported()) {
      console.warn('History API not available')
      return
    }

    try {
      window.history.forward()
    } catch (error) {
      console.error('Failed to go forward:', error)
    }
  }

  /**
   * 检查是否在客户端环境
   * @private
   */
  private isClientSide(): boolean {
    return typeof window !== 'undefined'
  }

  /**
   * 检查是否支持 History API
   * @private
   */
  private isHistorySupported(): boolean {
    return !!(window.history && window.history.pushState)
  }

  /**
   * 标准化 URL
   * @private
   */
  private normalizeUrl(path: string): string {
    if (!path) {
      return '/'
    }

    // 如果是完整的 URL，直接返回
    if (path.startsWith('http://') || path.startsWith('https://')) {
      return path
    }

    // 确保路径以 / 开头
    if (!path.startsWith('/')) {
      return `/${path}`
    }

    return path
  }

  /**
   * 触发路由变化事件
   * @private
   */
  private triggerRouteChange(): void {
    try {
      // 创建并派发自定义事件
      const event = new Event('routechange')
      window.dispatchEvent(event)
    } catch (error) {
      console.error('Failed to trigger route change event:', error)
    }
  }
}

/**
 * 模拟导航服务实现
 * 用于测试环境或服务端渲染环境
 */
export class MockNavigationService implements INavigationService {
  private currentPath: string = '/'
  private searchParams: URLSearchParams = new URLSearchParams()

  constructor(initialPath: string = '/') {
    this.currentPath = initialPath
    const url = new URL(initialPath, 'http://localhost')
    this.searchParams = new URLSearchParams(url.search)
  }

  redirectTo(path: string): void {
    this.currentPath = this.normalizeUrl(path)
    const url = new URL(this.currentPath, 'http://localhost')
    this.searchParams = new URLSearchParams(url.search)
  }

  getCurrentPath(): string {
    return this.currentPath
  }

  replace(path: string): void {
    // 在模拟环境中，replace 和 redirectTo 行为相同
    this.redirectTo(path)
  }

  getSearchParams(): URLSearchParams {
    return new URLSearchParams(this.searchParams)
  }

  /**
   * 设置查询参数（测试专用）
   */
  setSearchParams(params: URLSearchParams): void {
    this.searchParams = new URLSearchParams(params)
  }

  /**
   * 重置到初始状态（测试专用）
   */
  reset(initialPath: string = '/'): void {
    this.currentPath = initialPath
    const url = new URL(initialPath, 'http://localhost')
    this.searchParams = new URLSearchParams(url.search)
  }

  /**
   * 标准化 URL
   * @private
   */
  private normalizeUrl(path: string): string {
    if (!path) {
      return '/'
    }

    // 检查是否包含协议（包括无效协议）
    if (path.includes('://')) {
      // 如果是完整的 URL，提取路径部分
      if (path.startsWith('http://') || path.startsWith('https://')) {
        try {
          const url = new URL(path)
          return url.pathname + url.search + url.hash
        } catch {
          return '/'
        }
      } else {
        // 如果是无效的协议，返回默认路径
        return '/'
      }
    }

    // 确保路径以 / 开头
    if (!path.startsWith('/')) {
      return `/${path}`
    }

    return path
  }
}

/**
 * 导航服务工厂函数
 */
export function createNavigationService(
  type: 'browser' | 'history' | 'mock' = 'browser',
  options?: { initialPath?: string },
): INavigationService {
  switch (type) {
    case 'browser':
      return new BrowserNavigationService()
    case 'history':
      return new HistoryNavigationService()
    case 'mock':
      return new MockNavigationService(options?.initialPath)
    default:
      throw new Error(`Unsupported navigation service type: ${type}`)
  }
}

/**
 * 自动检测并创建最佳的导航服务
 */
export function createAutoNavigationService(): INavigationService {
  // 服务端渲染环境
  if (typeof window === 'undefined') {
    return new MockNavigationService()
  }

  // 检查是否支持 History API
  if (window.history && window.history.pushState) {
    return new HistoryNavigationService()
  }

  // 降级到基础的浏览器导航
  return new BrowserNavigationService()
}

/**
 * 导航服务工具函数
 */
export const NavigationUtils = {
  /**
   * 构建带查询参数的 URL
   */
  buildUrl(path: string, params: Record<string, string | number | boolean>): string {
    const url = new URL(path, 'http://localhost')
    
    Object.entries(params).forEach(([key, value]) => {
      url.searchParams.set(key, String(value))
    })
    
    return url.pathname + url.search + url.hash
  },

  /**
   * 解析 URL 查询参数
   */
  parseSearchParams(search: string): Record<string, string> {
    const params = new URLSearchParams(search)
    const result: Record<string, string> = {}
    
    params.forEach((value, key) => {
      result[key] = value
    })
    
    return result
  },

  /**
   * 检查两个路径是否相同（忽略查询参数）
   */
  isSamePath(path1: string, path2: string): boolean {
    try {
      const url1 = new URL(path1, 'http://localhost')
      const url2 = new URL(path2, 'http://localhost')
      return url1.pathname === url2.pathname
    } catch {
      return path1 === path2
    }
  },

  /**
   * 检查路径是否为外部链接
   */
  isExternalLink(path: string): boolean {
    try {
      const url = new URL(path)
      return url.origin !== window.location.origin
    } catch {
      return false
    }
  },
}