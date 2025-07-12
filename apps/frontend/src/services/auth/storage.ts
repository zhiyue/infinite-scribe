/**
 * 存储服务实现
 * 提供抽象的存储接口，支持多种存储后端（localStorage、sessionStorage、内存存储等）
 */

import type { IStorageService } from './types'

/**
 * 本地存储服务实现
 * 封装 localStorage 操作，提供错误处理和类型安全
 */
export class LocalStorageService implements IStorageService {
  private readonly prefix: string

  constructor(prefix: string = 'auth_') {
    this.prefix = prefix
  }

  /**
   * 获取存储的值
   */
  getItem(key: string): string | null {
    try {
      if (!this.isStorageAvailable()) {
        console.error('localStorage is not available')
        return null
      }

      const fullKey = this.getFullKey(key)
      return localStorage.getItem(fullKey)
    } catch (error) {
      console.error(`Failed to get item from localStorage: ${key}`, error)
      return null
    }
  }

  /**
   * 设置存储的值
   */
  setItem(key: string, value: string): void {
    try {
      if (!this.isStorageAvailable()) {
        console.error('localStorage is not available, skipping setItem')
        return
      }

      const fullKey = this.getFullKey(key)
      localStorage.setItem(fullKey, value)
    } catch (error) {
      console.error(`Failed to set item in localStorage: ${key}`, error)
      
      // 如果是存储空间不足错误，尝试清理旧数据
      if (this.isQuotaExceededError(error)) {
        this.handleQuotaExceeded(key, value)
      }
    }
  }

  /**
   * 移除存储的值
   */
  removeItem(key: string): void {
    try {
      if (!this.isStorageAvailable()) {
        console.error('localStorage is not available, skipping removeItem')
        return
      }

      const fullKey = this.getFullKey(key)
      localStorage.removeItem(fullKey)
    } catch (error) {
      console.error(`Failed to remove item from localStorage: ${key}`, error)
    }
  }

  /**
   * 清空所有存储（仅清空当前前缀的数据）
   */
  clear(): void {
    try {
      if (!this.isStorageAvailable()) {
        console.error('localStorage is not available, skipping clear')
        return
      }

      // 只清理带有当前前缀的键
      const keysToRemove: string[] = []
      
      for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i)
        if (key && key.startsWith(this.prefix)) {
          keysToRemove.push(key)
        }
      }

      keysToRemove.forEach(key => localStorage.removeItem(key))
    } catch (error) {
      console.error('Failed to clear localStorage', error)
    }
  }

  /**
   * 获取完整的存储键名
   * @private
   */
  private getFullKey(key: string): string {
    return `${this.prefix}${key}`
  }

  /**
   * 检查 localStorage 是否可用
   * @private
   */
  private isStorageAvailable(): boolean {
    try {
      const test = '__storage_test__'
      localStorage.setItem(test, test)
      localStorage.removeItem(test)
      return true
    } catch {
      return false
    }
  }

  /**
   * 检查是否是存储空间不足错误
   * @private
   */
  private isQuotaExceededError(error: any): boolean {
    // 在测试环境中，更宽松地检查错误类型
    const isDOMException = error instanceof DOMException || 
                          error?.constructor?.name === 'DOMException' ||
                          (error && typeof error === 'object' && error.name === 'QuotaExceededError')
    
    return isDOMException && (
      error.code === 22 ||
      error.code === 1014 ||
      error.name === 'QuotaExceededError' ||
      error.name === 'NS_ERROR_DOM_QUOTA_REACHED'
    )
  }

  /**
   * 处理存储空间不足的情况
   * @private
   */
  private handleQuotaExceeded(key: string, value: string): void {
    try {
      console.warn('localStorage quota exceeded, attempting to free space')
      
      // 尝试清理一些非关键数据（这里可以根据实际需求定制）
      const nonCriticalKeys = this.getNonCriticalKeys()
      
      for (const keyToRemove of nonCriticalKeys) {
        localStorage.removeItem(keyToRemove)
        
        // 尝试重新设置原始值
        try {
          const fullKey = this.getFullKey(key)
          localStorage.setItem(fullKey, value)
          console.log('Successfully stored item after freeing space')
          return
        } catch {
          // 继续清理更多数据
          continue
        }
      }
      
      console.error('Failed to free enough space for localStorage')
    } catch (error) {
      console.error('Failed to handle quota exceeded error', error)
    }
  }

  /**
   * 获取非关键的存储键列表（用于空间不足时清理）
   */
  getNonCriticalKeys(): string[] {
    const nonCriticalKeys: string[] = []
    
    try {
      for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i)
        if (key && this.isNonCriticalKey(key)) {
          nonCriticalKeys.push(key)
        }
      }
    } catch (error) {
      console.error('Failed to get non-critical keys', error)
    }
    
    return nonCriticalKeys
  }

  /**
   * 判断是否是非关键键（可以在空间不足时删除）
   * @private
   */
  private isNonCriticalKey(key: string): boolean {
    // 定义非关键的键模式
    const nonCriticalPatterns = [
      'cache_',
      'temp_',
      'analytics_',
      'debug_',
      '_session_',
    ]
    
    // 不删除认证相关的关键数据
    const criticalPatterns = [
      this.prefix, // 当前认证前缀
      'access_token',
      'refresh_token',
      'user_',
    ]
    
    // 检查是否是关键键
    for (const pattern of criticalPatterns) {
      if (key.includes(pattern)) {
        return false
      }
    }
    
    // 检查是否是非关键键
    for (const pattern of nonCriticalPatterns) {
      if (key.includes(pattern)) {
        return true
      }
    }
    
    return false
  }

  /**
   * 获取存储使用情况统计
   */
  getStorageStats(): {
    totalKeys: number
    authKeys: number
    totalSize: number
    authSize: number
    available: boolean
  } {
    const stats = {
      totalKeys: 0,
      authKeys: 0,
      totalSize: 0,
      authSize: 0,
      available: this.isStorageAvailable(),
    }

    if (!stats.available) {
      return stats
    }

    try {
      for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i)
        if (key) {
          stats.totalKeys++
          const value = localStorage.getItem(key) || ''
          stats.totalSize += key.length + value.length

          if (key.startsWith(this.prefix)) {
            stats.authKeys++
            stats.authSize += key.length + value.length
          }
        }
      }
    } catch (error) {
      console.error('Failed to get storage stats', error)
    }

    return stats
  }
}

/**
 * 会话存储服务实现
 * 与 LocalStorageService 类似，但使用 sessionStorage
 */
export class SessionStorageService implements IStorageService {
  private readonly prefix: string

  constructor(prefix: string = 'auth_') {
    this.prefix = prefix
  }

  getItem(key: string): string | null {
    try {
      if (!this.isStorageAvailable()) {
        console.error('sessionStorage is not available')
        return null
      }
      const fullKey = this.getFullKey(key)
      return sessionStorage.getItem(fullKey)
    } catch (error) {
      console.error(`Failed to get item from sessionStorage: ${key}`, error)
      return null
    }
  }

  setItem(key: string, value: string): void {
    try {
      if (!this.isStorageAvailable()) {
        console.error('sessionStorage is not available, skipping setItem')
        return
      }
      const fullKey = this.getFullKey(key)
      sessionStorage.setItem(fullKey, value)
    } catch (error) {
      console.error(`Failed to set item in sessionStorage: ${key}`, error)
    }
  }

  removeItem(key: string): void {
    try {
      if (!this.isStorageAvailable()) {
        console.error('sessionStorage is not available, skipping removeItem')
        return
      }
      const fullKey = this.getFullKey(key)
      sessionStorage.removeItem(fullKey)
    } catch (error) {
      console.error(`Failed to remove item from sessionStorage: ${key}`, error)
    }
  }

  clear(): void {
    try {
      if (!this.isStorageAvailable()) {
        console.error('sessionStorage is not available, skipping clear')
        return
      }

      const keysToRemove: string[] = []
      for (let i = 0; i < sessionStorage.length; i++) {
        const key = sessionStorage.key(i)
        if (key && key.startsWith(this.prefix)) {
          keysToRemove.push(key)
        }
      }

      keysToRemove.forEach(key => sessionStorage.removeItem(key))
    } catch (error) {
      console.error('Failed to clear sessionStorage', error)
    }
  }

  private getFullKey(key: string): string {
    return `${this.prefix}${key}`
  }

  private isStorageAvailable(): boolean {
    try {
      const test = '__storage_test__'
      sessionStorage.setItem(test, test)
      sessionStorage.removeItem(test)
      return true
    } catch {
      return false
    }
  }
}

/**
 * 内存存储服务实现
 * 用于测试环境或不支持 Web Storage 的环境
 */
export class MemoryStorageService implements IStorageService {
  private storage = new Map<string, string>()
  private readonly prefix: string

  constructor(prefix: string = 'auth_') {
    this.prefix = prefix
  }

  getItem(key: string): string | null {
    const fullKey = this.getFullKey(key)
    const value = this.storage.get(fullKey)
    return value !== undefined ? value : null
  }

  setItem(key: string, value: string): void {
    const fullKey = this.getFullKey(key)
    this.storage.set(fullKey, value)
  }

  removeItem(key: string): void {
    const fullKey = this.getFullKey(key)
    this.storage.delete(fullKey)
  }

  clear(): void {
    const keysToRemove: string[] = []
    for (const key of this.storage.keys()) {
      if (key.startsWith(this.prefix)) {
        keysToRemove.push(key)
      }
    }
    keysToRemove.forEach(key => this.storage.delete(key))
  }

  private getFullKey(key: string): string {
    return `${this.prefix}${key}`
  }

  /**
   * 获取存储状态（仅用于调试）
   */
  getStorage(): Map<string, string> {
    return new Map(this.storage)
  }
}

/**
 * 存储服务工厂函数
 */
export function createStorageService(
  type: 'localStorage' | 'sessionStorage' | 'memory' = 'localStorage',
  prefix?: string,
): IStorageService {
  switch (type) {
    case 'localStorage':
      return new LocalStorageService(prefix)
    case 'sessionStorage':
      return new SessionStorageService(prefix)
    case 'memory':
      return new MemoryStorageService(prefix)
    default:
      throw new Error(`Unsupported storage type: ${type}`)
  }
}