/**
 * errorHandler 工具的单元测试
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import {
  ErrorCode,
  AppError,
  parseApiError,
  handleNetworkError,
  handleError,
  logError,
  getUserFriendlyMessage,
} from './errorHandler'

describe('errorHandler', () => {
  describe('AppError', () => {
    it('应该创建带有默认消息的错误', () => {
      const error = new AppError(ErrorCode.BAD_REQUEST)

      expect(error).toBeInstanceOf(Error)
      expect(error).toBeInstanceOf(AppError)
      expect(error.name).toBe('AppError')
      expect(error.code).toBe(ErrorCode.BAD_REQUEST)
      expect(error.message).toBe('请求参数错误')
      expect(error.statusCode).toBeUndefined()
      expect(error.details).toBeUndefined()
    })

    it('应该创建带有自定义消息的错误', () => {
      const error = new AppError(ErrorCode.VALIDATION_ERROR, '邮箱格式不正确', 422, {
        field: 'email',
      })

      expect(error.code).toBe(ErrorCode.VALIDATION_ERROR)
      expect(error.message).toBe('邮箱格式不正确')
      expect(error.statusCode).toBe(422)
      expect(error.details).toEqual({ field: 'email' })
    })

    it('应该处理未知错误码', () => {
      const error = new AppError('UNKNOWN_CODE', '自定义消息')

      expect(error.message).toBe('自定义消息')
    })

    it('应该在没有消息时使用默认的未知错误消息', () => {
      const error = new AppError('UNKNOWN_CODE')

      expect(error.message).toBe('未知错误')
    })
  })

  describe('parseApiError', () => {
    it('应该解析标准 HTTP 错误状态码', () => {
      const response = new Response(null, { status: 401 })
      const error = parseApiError(response)

      expect(error.code).toBe(ErrorCode.UNAUTHORIZED)
      expect(error.statusCode).toBe(401)
      expect(error.message).toBe('未登录或登录已过期')
    })

    it('应该解析带有错误数据的响应', () => {
      const response = new Response(null, { status: 400 })
      const data = {
        error: {
          code: 'CUSTOM_ERROR',
          message: '自定义错误消息',
          details: { field: 'username' },
        },
      }

      const error = parseApiError(response, data)

      expect(error.code).toBe('CUSTOM_ERROR')
      expect(error.message).toBe('自定义错误消息')
      expect(error.statusCode).toBe(400)
      expect(error.details).toEqual({ field: 'username' })
    })

    it('应该处理没有错误字段的响应数据', () => {
      const response = new Response(null, { status: 500 })
      const data = { message: '这不是标准错误格式' }

      const error = parseApiError(response, data)

      expect(error.code).toBe(ErrorCode.INTERNAL_SERVER_ERROR)
      expect(error.statusCode).toBe(500)
    })

    it('应该处理未映射的 HTTP 状态码', () => {
      const response = new Response(null, { status: 418 }) // I'm a teapot
      const error = parseApiError(response)

      expect(error.code).toBe(ErrorCode.UNKNOWN_ERROR)
      expect(error.statusCode).toBe(418)
    })

    it('应该处理空数据', () => {
      const response = new Response(null, { status: 404 })
      const error = parseApiError(response, null)

      expect(error.code).toBe(ErrorCode.NOT_FOUND)
      expect(error.statusCode).toBe(404)
    })

    it('应该处理部分错误数据', () => {
      const response = new Response(null, { status: 403 })
      const data = {
        error: {
          message: '只有消息，没有代码',
        },
      }

      const error = parseApiError(response, data)

      expect(error.code).toBe(ErrorCode.FORBIDDEN)
      expect(error.message).toBe('只有消息，没有代码')
      expect(error.statusCode).toBe(403)
    })
  })

  describe('handleNetworkError', () => {
    it('应该处理中止错误', () => {
      const abortError = new Error('The operation was aborted')
      abortError.name = 'AbortError'

      const error = handleNetworkError(abortError)

      expect(error.code).toBe(ErrorCode.TIMEOUT_ERROR)
      expect(error.message).toBe('请求已取消')
    })

    it('应该处理 fetch 类型错误', () => {
      const fetchError = new TypeError('Failed to fetch')

      const error = handleNetworkError(fetchError)

      expect(error.code).toBe(ErrorCode.NETWORK_ERROR)
      expect(error.message).toBe('网络连接失败，请检查网络设置')
    })

    it('应该处理其他错误', () => {
      const genericError = new Error('Something went wrong')

      const error = handleNetworkError(genericError)

      expect(error.code).toBe(ErrorCode.UNKNOWN_ERROR)
      expect(error.message).toBe('Something went wrong')
    })

    it('应该处理非 Error 对象', () => {
      const error = handleNetworkError('字符串错误')

      expect(error.code).toBe(ErrorCode.UNKNOWN_ERROR)
      expect(error.message).toBe('字符串错误')
    })

    it('应该处理 null 和 undefined', () => {
      const nullError = handleNetworkError(null)
      expect(nullError.code).toBe(ErrorCode.UNKNOWN_ERROR)
      expect(nullError.message).toBe('null')

      const undefinedError = handleNetworkError(undefined)
      expect(undefinedError.code).toBe(ErrorCode.UNKNOWN_ERROR)
      expect(undefinedError.message).toBe('undefined')
    })
  })

  describe('handleError', () => {
    it('应该直接返回 AppError 实例', () => {
      const appError = new AppError(ErrorCode.BAD_REQUEST, '测试错误')
      const result = handleError(appError)

      expect(result).toBe(appError)
    })

    it('应该处理普通 Error 对象', () => {
      const error = new Error('普通错误')
      const result = handleError(error)

      expect(result).toBeInstanceOf(AppError)
      expect(result.code).toBe(ErrorCode.UNKNOWN_ERROR)
      expect(result.message).toBe('普通错误')
    })

    it('应该处理网络错误', () => {
      const fetchError = new TypeError('Failed to fetch')
      const result = handleError(fetchError)

      expect(result.code).toBe(ErrorCode.NETWORK_ERROR)
      expect(result.message).toBe('网络连接失败，请检查网络设置')
    })

    it('应该处理非 Error 对象', () => {
      const result = handleError({ error: '对象错误' })

      expect(result.code).toBe(ErrorCode.UNKNOWN_ERROR)
      expect(result.message).toBe('[object Object]')
    })

    it('应该处理原始类型', () => {
      expect(handleError('字符串').message).toBe('字符串')
      expect(handleError(123).message).toBe('123')
      expect(handleError(true).message).toBe('true')
      expect(handleError(null).message).toBe('null')
      expect(handleError(undefined).message).toBe('undefined')
    })
  })

  describe('logError', () => {
    let consoleErrorSpy: ReturnType<typeof vi.spyOn>
    let dateSpy: ReturnType<typeof vi.spyOn>

    beforeEach(() => {
      consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {
        // 故意为空 - 抑制测试中的错误日志输出
      })
      dateSpy = vi.spyOn(Date.prototype, 'toISOString').mockReturnValue('2024-01-01T00:00:00.000Z')
    })

    afterEach(() => {
      consoleErrorSpy.mockRestore()
      dateSpy.mockRestore()
    })

    it('应该记录错误信息', () => {
      const error = new AppError(ErrorCode.VALIDATION_ERROR, '验证失败', 422, {
        field: 'email',
      })

      logError(error)

      expect(consoleErrorSpy).toHaveBeenCalledWith('应用错误:', {
        code: ErrorCode.VALIDATION_ERROR,
        message: '验证失败',
        statusCode: 422,
        details: { field: 'email' },
        context: undefined,
        timestamp: '2024-01-01T00:00:00.000Z',
      })
    })

    it('应该记录带上下文的错误', () => {
      const error = new AppError(ErrorCode.NETWORK_ERROR)
      const context = { userId: '123', action: 'fetchProfile' }

      logError(error, context)

      expect(consoleErrorSpy).toHaveBeenCalledWith('应用错误:', {
        code: ErrorCode.NETWORK_ERROR,
        message: '网络连接失败',
        statusCode: undefined,
        details: undefined,
        context,
        timestamp: '2024-01-01T00:00:00.000Z',
      })
    })
  })

  describe('getUserFriendlyMessage', () => {
    it('应该返回网络错误的友好消息', () => {
      const error = new AppError(ErrorCode.NETWORK_ERROR)
      const message = getUserFriendlyMessage(error)

      expect(message).toBe('网络连接失败，请检查您的网络设置')
    })

    it('应该返回超时错误的友好消息', () => {
      const error = new AppError(ErrorCode.TIMEOUT_ERROR)
      const message = getUserFriendlyMessage(error)

      expect(message).toBe('请求超时，请稍后重试')
    })

    it('应该返回未授权错误的友好消息', () => {
      const error = new AppError(ErrorCode.UNAUTHORIZED)
      const message = getUserFriendlyMessage(error)

      expect(message).toBe('您需要登录才能访问此功能')
    })

    it('应该返回服务不可用的友好消息', () => {
      const error = new AppError(ErrorCode.SERVICE_UNAVAILABLE)
      const message = getUserFriendlyMessage(error)

      expect(message).toBe('服务暂时不可用，请稍后再试')
    })

    it('应该返回默认消息（使用错误消息）', () => {
      const error = new AppError(ErrorCode.VALIDATION_ERROR, '邮箱格式不正确')
      const message = getUserFriendlyMessage(error)

      expect(message).toBe('邮箱格式不正确')
    })

    it('应该返回默认消息（没有错误消息时）', () => {
      const error = new AppError('UNKNOWN_CODE')
      error.message = '' // 清空消息
      const message = getUserFriendlyMessage(error)

      expect(message).toBe('操作失败，请稍后重试')
    })

    it('应该处理所有已定义的错误码', () => {
      // 测试一些其他错误码
      expect(getUserFriendlyMessage(new AppError(ErrorCode.BAD_REQUEST))).toBe('请求参数错误')
      expect(getUserFriendlyMessage(new AppError(ErrorCode.FORBIDDEN))).toBe('没有权限访问该资源')
      expect(getUserFriendlyMessage(new AppError(ErrorCode.NOT_FOUND))).toBe('请求的资源不存在')
    })
  })

  describe('ErrorCode 枚举完整性', () => {
    it('应该包含所有预期的错误码', () => {
      const expectedCodes = [
        'BAD_REQUEST',
        'UNAUTHORIZED',
        'FORBIDDEN',
        'NOT_FOUND',
        'VALIDATION_ERROR',
        'INTERNAL_SERVER_ERROR',
        'SERVICE_UNAVAILABLE',
        'GATEWAY_TIMEOUT',
        'NETWORK_ERROR',
        'TIMEOUT_ERROR',
        'BUSINESS_ERROR',
        'UNKNOWN_ERROR',
      ]

      expectedCodes.forEach((code) => {
        expect(ErrorCode).toHaveProperty(code)
      })
    })
  })

  describe('集成场景测试', () => {
    it('应该正确处理 API 错误响应流程', () => {
      // 模拟 API 响应
      const response = new Response(null, { status: 422 })
      const responseData = {
        error: {
          code: 'VALIDATION_ERROR',
          message: '用户名已存在',
          details: { field: 'username', value: 'testuser' },
        },
      }

      // 解析错误
      const error = parseApiError(response, responseData)

      // 记录错误
      const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {
        // 故意为空 - 抑制测试中的错误日志输出
      })
      logError(error, { endpoint: '/api/register' })

      // 获取用户友好消息
      const userMessage = getUserFriendlyMessage(error)

      // 验证
      expect(error.code).toBe('VALIDATION_ERROR')
      expect(error.statusCode).toBe(422)
      expect(userMessage).toBe('用户名已存在')
      expect(consoleErrorSpy).toHaveBeenCalled()

      consoleErrorSpy.mockRestore()
    })

    it('应该正确处理网络错误流程', () => {
      // 模拟网络错误
      const networkError = new TypeError('Failed to fetch')

      // 处理错误
      const error = handleError(networkError)

      // 获取用户友好消息
      const userMessage = getUserFriendlyMessage(error)

      // 验证
      expect(error.code).toBe(ErrorCode.NETWORK_ERROR)
      expect(userMessage).toBe('网络连接失败，请检查您的网络设置')
    })
  })
})
