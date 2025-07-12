/**
 * TokenManager 单元测试
 * 测试 JWT 令牌管理器的所有功能
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { TokenManager } from '../token-manager'
import { MemoryStorageService } from '../storage'
import type { IStorageService } from '../types'

describe('TokenManager', () => {
  let tokenManager: TokenManager
  let storageService: IStorageService
  
  // 测试用的有效 JWT Token（模拟）
  const createMockJwt = (payload: any, expiresInMinutes: number = 60): string => {
    const header = { alg: 'HS256', typ: 'JWT' }
    const exp = Math.floor(Date.now() / 1000) + (expiresInMinutes * 60)
    const tokenPayload = { ...payload, exp, iat: Math.floor(Date.now() / 1000) }
    
    const base64UrlEncode = (obj: any) => {
      return btoa(JSON.stringify(obj))
        .replace(/\+/g, '-')
        .replace(/\//g, '_')
        .replace(/=/g, '')
    }
    
    return `${base64UrlEncode(header)}.${base64UrlEncode(tokenPayload)}.mock-signature`
  }
  
  const validToken = createMockJwt({ sub: 'user123', role: 'user' }, 60)
  const expiredToken = createMockJwt({ sub: 'user123', role: 'user' }, -5) // 已过期
  const expiringSoonToken = createMockJwt({ sub: 'user123', role: 'user' }, 3) // 3分钟后过期

  beforeEach(() => {
    // 每个测试前重置存储和创建新的 TokenManager
    storageService = new MemoryStorageService('test_auth_')
    tokenManager = new TokenManager(storageService, 'access_token', 'refresh_token', 5)
    
    // 清理定时器
    vi.clearAllTimers()
    vi.useFakeTimers()
  })

  afterEach(() => {
    tokenManager.destroy()
    vi.useRealTimers()
  })

  describe('Token Storage', () => {
    it('应该能设置和获取访问令牌', () => {
      tokenManager.setTokens(validToken)
      
      expect(tokenManager.getAccessToken()).toBe(validToken)
    })

    it('应该能设置和获取刷新令牌', () => {
      const refreshToken = 'refresh_token_123'
      tokenManager.setTokens(validToken, refreshToken)
      
      expect(tokenManager.getAccessToken()).toBe(validToken)
      expect(tokenManager.getRefreshToken()).toBe(refreshToken)
    })

    it('应该能清空所有令牌', () => {
      tokenManager.setTokens(validToken, 'refresh_token_123')
      tokenManager.clearTokens()
      
      expect(tokenManager.getAccessToken()).toBeNull()
      expect(tokenManager.getRefreshToken()).toBeNull()
    })

    it('应该正确处理存储键前缀', () => {
      tokenManager.setTokens(validToken, 'refresh_token_123')
      
      // 检查底层存储是否使用了正确的键
      expect(storageService.getItem('access_token')).toBe(validToken)
      expect(storageService.getItem('refresh_token')).toBe('refresh_token_123')
    })
  })

  describe('Token Validation', () => {
    it('应该正确识别有效令牌', () => {
      expect(tokenManager.isTokenExpired(validToken)).toBe(false)
    })

    it('应该正确识别过期令牌', () => {
      expect(tokenManager.isTokenExpired(expiredToken)).toBe(true)
    })

    it('应该正确处理无效令牌格式', () => {
      // 模拟 console.warn 以避免测试中的警告日志
      const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})
      
      expect(tokenManager.isTokenExpired('invalid-token')).toBe(true)
      expect(tokenManager.isTokenExpired('')).toBe(true)
      expect(tokenManager.isTokenExpired(null as any)).toBe(true)
      
      consoleSpy.mockRestore()
    })

    it('应该正确检查是否有有效的访问令牌', () => {
      expect(tokenManager.hasValidAccessToken()).toBe(false)
      
      tokenManager.setTokens(validToken)
      expect(tokenManager.hasValidAccessToken()).toBe(true)
      
      tokenManager.setTokens(expiredToken)
      expect(tokenManager.hasValidAccessToken()).toBe(false)
    })
  })

  describe('Token Parsing', () => {
    it('应该正确解析令牌过期时间', () => {
      const expiration = tokenManager.getTokenExpiration(validToken)
      
      expect(expiration).toBeInstanceOf(Date)
      expect(expiration!.getTime()).toBeGreaterThan(Date.now())
    })

    it('应该正确计算令牌剩余时间', () => {
      const timeToExpiry = tokenManager.getTokenTimeToExpiry(validToken)
      
      expect(timeToExpiry).toBeGreaterThan(0)
      expect(timeToExpiry).toBeLessThanOrEqual(60 * 60) // 不超过1小时
    })

    it('应该正确识别即将过期的令牌', () => {
      expect(tokenManager.isTokenExpiringSoon(expiringSoonToken, 5)).toBe(true)
      expect(tokenManager.isTokenExpiringSoon(validToken, 5)).toBe(false)
    })

    it('应该处理格式错误的令牌', () => {
      // 模拟 console.warn 以避免测试中的警告日志
      const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})
      
      expect(tokenManager.getTokenExpiration('invalid')).toBeNull()
      expect(tokenManager.getTokenTimeToExpiry('invalid')).toBeNull()
      
      consoleSpy.mockRestore()
    })
  })

  describe('Automatic Token Refresh', () => {
    it('应该正确调度令牌刷新', async () => {
      // 创建新的有效令牌用于刷新后设置
      const newToken = createMockJwt({ sub: 'user123', role: 'user' }, 120) // 2小时后过期
      
      const refreshCallback = vi.fn().mockImplementation(async () => {
        // 模拟刷新成功，设置新令牌
        tokenManager.setTokens(newToken)
      })
      
      tokenManager.setTokens(validToken)
      tokenManager.scheduleRefresh(refreshCallback)
      
      // 快进到刷新时间
      const expiration = tokenManager.getTokenExpiration(validToken)!
      const refreshTime = expiration.getTime() - (5 * 60 * 1000) // 提前5分钟
      const delay = refreshTime - Date.now()
      
      vi.advanceTimersByTime(delay)
      
      // 等待异步操作完成
      await vi.runAllTimersAsync()
      
      expect(refreshCallback).toHaveBeenCalled()
      expect(tokenManager.getAccessToken()).toBe(newToken)
    })

    it('应该能取消令牌刷新计划', () => {
      const refreshCallback = vi.fn()
      
      tokenManager.setTokens(validToken)
      tokenManager.scheduleRefresh(refreshCallback)
      tokenManager.cancelRefresh()
      
      // 快进很长时间
      vi.advanceTimersByTime(60 * 60 * 1000) // 1小时
      
      expect(refreshCallback).not.toHaveBeenCalled()
    })

    it('应该立即刷新已过期的令牌', async () => {
      // 创建新的有效令牌用于刷新后设置
      const newToken = createMockJwt({ sub: 'user123', role: 'user' }, 120) // 2小时后过期
      
      const refreshCallback = vi.fn().mockImplementation(async () => {
        // 模拟刷新成功，设置新令牌
        tokenManager.setTokens(newToken)
      })
      
      tokenManager.setTokens(expiredToken)
      tokenManager.scheduleRefresh(refreshCallback)
      
      // 等待立即执行的刷新
      await vi.runAllTimersAsync()
      
      expect(refreshCallback).toHaveBeenCalled()
      expect(tokenManager.getAccessToken()).toBe(newToken)
    })

    it('应该处理刷新回调失败的情况', async () => {
      const refreshCallback = vi.fn().mockRejectedValue(new Error('Refresh failed'))
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
      
      tokenManager.setTokens(expiredToken)
      tokenManager.scheduleRefresh(refreshCallback)
      
      // 等待刷新执行并失败
      await vi.runAllTimersAsync()
      
      expect(refreshCallback).toHaveBeenCalledTimes(1) // 只调用一次，不会无限循环
      expect(consoleSpy).toHaveBeenCalledWith('Token refresh failed:', expect.any(Error))
      expect(tokenManager.getAccessToken()).toBeNull() // 令牌应该被清除
      
      consoleSpy.mockRestore()
    })
  })

  describe('Token Summary', () => {
    it('应该提供完整的令牌状态摘要', () => {
      tokenManager.setTokens(validToken, 'refresh_123')
      
      const summary = tokenManager.getTokenSummary()
      
      expect(summary).toEqual({
        hasAccessToken: true,
        hasRefreshToken: true,
        accessTokenExpiry: expect.any(Date),
        isAccessTokenValid: true,
        isAccessTokenExpiringSoon: false,
        timeToRefresh: expect.any(Number),
      })
    })

    it('应该正确反映空令牌状态', () => {
      const summary = tokenManager.getTokenSummary()
      
      expect(summary).toEqual({
        hasAccessToken: false,
        hasRefreshToken: false,
        accessTokenExpiry: null,
        isAccessTokenValid: false,
        isAccessTokenExpiringSoon: true,
        timeToRefresh: null,
      })
    })
  })

  describe('Edge Cases', () => {
    it('应该处理同时设置多个令牌的情况', () => {
      tokenManager.setTokens(validToken, 'refresh_1')
      tokenManager.setTokens(validToken, 'refresh_2')
      
      expect(tokenManager.getRefreshToken()).toBe('refresh_2')
    })

    it('应该处理存储服务错误', () => {
      const errorStorageService = {
        getItem: vi.fn().mockImplementation(() => {
          throw new Error('Storage error')
        }),
        setItem: vi.fn(),
        removeItem: vi.fn(),
        clear: vi.fn(),
      }
      
      const errorTokenManager = new TokenManager(errorStorageService, 'access_token')
      
      // 应该优雅地处理存储错误，返回null而不是抛出异常
      expect(() => {
        const result = errorTokenManager.getAccessToken()
        expect(result).toBeNull()
      }).not.toThrow()
    })

    it('应该正确处理 httpOnly cookies 模式', () => {
      // 不提供 refreshTokenKey，模拟 httpOnly cookies 模式
      const httpOnlyTokenManager = new TokenManager(storageService, 'access_token')
      
      httpOnlyTokenManager.setTokens(validToken, 'refresh_token')
      
      expect(httpOnlyTokenManager.getAccessToken()).toBe(validToken)
      expect(httpOnlyTokenManager.getRefreshToken()).toBeNull() // 应该为 null
    })
  })

  describe('JWT Parsing Edge Cases', () => {
    it('应该处理缺少过期时间的令牌', () => {
      const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})
      
      const tokenWithoutExp = createJwtWithoutExp({ sub: 'user123' })
      
      expect(tokenManager.isTokenExpired(tokenWithoutExp)).toBe(true)
      expect(tokenManager.getTokenExpiration(tokenWithoutExp)).toBeNull()
      
      consoleSpy.mockRestore()
    })

    it('应该处理格式错误的 Base64 编码', () => {
      const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})
      
      const invalidBase64Token = 'header.invalid-base64!@#.signature'
      
      expect(tokenManager.isTokenExpired(invalidBase64Token)).toBe(true)
      expect(tokenManager.getTokenExpiration(invalidBase64Token)).toBeNull()
      
      consoleSpy.mockRestore()
    })

    it('应该处理只有两个部分的令牌', () => {
      const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})
      
      const incompletToken = 'header.payload'
      
      expect(tokenManager.isTokenExpired(incompletToken)).toBe(true)
      
      consoleSpy.mockRestore()
    })
  })

  describe('Memory Management', () => {
    it('应该正确清理资源', () => {
      const refreshCallback = vi.fn()
      
      tokenManager.setTokens(validToken)
      tokenManager.scheduleRefresh(refreshCallback)
      
      tokenManager.destroy()
      
      // 快进时间，确保定时器已被清理
      vi.advanceTimersByTime(60 * 60 * 1000)
      expect(refreshCallback).not.toHaveBeenCalled()
    })
  })

  // 辅助函数：创建没有过期时间的JWT
  function createJwtWithoutExp(payload: any): string {
    const header = { alg: 'HS256', typ: 'JWT' }
    const tokenPayload = { ...payload, iat: Math.floor(Date.now() / 1000) }
    
    const base64UrlEncode = (obj: any) => {
      return btoa(JSON.stringify(obj))
        .replace(/\+/g, '-')
        .replace(/\//g, '_')
        .replace(/=/g, '')
    }
    
    return `${base64UrlEncode(header)}.${base64UrlEncode(tokenPayload)}.mock-signature`
  }
})