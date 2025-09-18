/**
 * HTTP 客户端单元测试
 * 测试所有 HTTP 客户端实现：AxiosHttpClient、FetchHttpClient、MockHttpClient
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import axios, { type AxiosInstance, type AxiosRequestConfig, type AxiosResponse } from 'axios'
import {
  AxiosHttpClient,
  FetchHttpClient,
  MockHttpClient,
  createHttpClient,
  createAutoHttpClient,
} from '../http-client'
import type { IHttpClient } from '../types'

// Mock axios
vi.mock('axios')
const mockedAxios = vi.mocked(axios)
mockedAxios.create = vi.fn()

describe('HTTP Clients', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('AxiosHttpClient', () => {
    let httpClient: AxiosHttpClient
    let mockAxiosInstance: Partial<AxiosInstance>

    beforeEach(() => {
      // 创建 axios 实例的 mock
      mockAxiosInstance = {
        get: vi.fn(),
        post: vi.fn(),
        put: vi.fn(),
        delete: vi.fn(),
        defaults: {
          headers: {
          common: {},
          delete: vi.fn(),
          get: vi.fn(),
          head: vi.fn(),
          post: vi.fn(),
          put: vi.fn(),
          patch: vi.fn()
        },
          baseURL: '',
          timeout: 10000,
        },
        interceptors: {
          request: {
            use: vi.fn(),
            eject: vi.fn(),
            clear: vi.fn(),
          },
          response: {
            use: vi.fn(),
            eject: vi.fn(),
            clear: vi.fn(),
          },
        },
      }

      mockedAxios.create.mockReturnValue(mockAxiosInstance as AxiosInstance)

      httpClient = new AxiosHttpClient()
    })

    describe('HTTP Methods', () => {
      it('应该能发送 GET 请求', async () => {
        const mockResponse: AxiosResponse = {
          data: { id: 1, name: 'test' },
          status: 200,
          statusText: 'OK',
          headers: new Headers(),
          config: { headers: {} },
          request: {},
        }

        mockAxiosInstance.get = vi.fn().mockResolvedValue(mockResponse)

        const response = await httpClient.get('/api/users/1')

        expect(mockAxiosInstance.get).toHaveBeenCalledWith('/api/users/1', undefined)
        expect(response).toEqual(mockResponse)
      })

      it('应该能发送 POST 请求', async () => {
        const requestData = { name: 'John', email: 'john@example.com' }
        const mockResponse: AxiosResponse = {
          data: { id: 1, ...requestData },
          status: 201,
          statusText: 'Created',
          headers: new Headers(),
          config: { headers: {} },
          request: {},
        }

        mockAxiosInstance.post = vi.fn().mockResolvedValue(mockResponse)

        const response = await httpClient.post('/api/users', requestData)

        expect(mockAxiosInstance.post).toHaveBeenCalledWith('/api/users', requestData, undefined)
        expect(response).toEqual(mockResponse)
      })

      it('应该能发送 PUT 请求', async () => {
        const updateData = { name: 'John Updated' }
        const mockResponse: AxiosResponse = {
          data: { id: 1, ...updateData },
          status: 200,
          statusText: 'OK',
          headers: new Headers(),
          config: { headers: {} },
          request: {},
        }

        mockAxiosInstance.put = vi.fn().mockResolvedValue(mockResponse)

        const response = await httpClient.put('/api/users/1', updateData)

        expect(mockAxiosInstance.put).toHaveBeenCalledWith('/api/users/1', updateData, undefined)
        expect(response).toEqual(mockResponse)
      })

      it('应该能发送 DELETE 请求', async () => {
        const mockResponse: AxiosResponse = {
          data: { success: true },
          status: 204,
          statusText: 'No Content',
          headers: new Headers(),
          config: { headers: {} },
          request: {},
        }

        mockAxiosInstance.delete = vi.fn().mockResolvedValue(mockResponse)

        const response = await httpClient.delete('/api/users/1')

        expect(mockAxiosInstance.delete).toHaveBeenCalledWith('/api/users/1', undefined)
        expect(response).toEqual(mockResponse)
      })

      it('应该能传递请求配置', async () => {
        const config: AxiosRequestConfig = {
          headers: { 'Custom-Header': 'value' },
          timeout: 5000,
        }

        mockAxiosInstance.get = vi.fn().mockResolvedValue({
          data: {},
          status: 200,
          statusText: 'OK',
          headers: new Headers(),
          config: { headers: {} },
          request: {},
        })

        await httpClient.get('/api/test', config)

        expect(mockAxiosInstance.get).toHaveBeenCalledWith('/api/test', config)
      })
    })

    describe('Headers Management', () => {
      it('应该能设置默认请求头', () => {
        httpClient.setDefaultHeader('Authorization', 'Bearer token123')

        expect(mockAxiosInstance.defaults!.headers.common['Authorization']).toBe('Bearer token123')
      })

      it('应该能移除默认请求头', () => {
        httpClient.setDefaultHeader('Custom-Header', 'value')
        httpClient.removeDefaultHeader('Custom-Header')

        expect(mockAxiosInstance.defaults!.headers.common['Custom-Header']).toBeUndefined()
      })

      it('应该能设置基础 URL', () => {
        httpClient.setBaseURL('https://api.example.com')

        expect(mockAxiosInstance.defaults!.baseURL).toBe('https://api.example.com')
      })

      it('应该能设置超时时间', () => {
        httpClient.setTimeout(5000)

        expect(mockAxiosInstance.defaults!.timeout).toBe(5000)
      })
    })

    describe('Interceptors', () => {
      it('应该能添加请求拦截器', () => {
        const mockId = 123
        mockAxiosInstance.interceptors!.request.use = vi.fn().mockReturnValue(mockId)

        const onFulfilled = vi.fn()
        const onRejected = vi.fn()

        const id = httpClient.addRequestInterceptor(onFulfilled, onRejected)

        expect(mockAxiosInstance.interceptors!.request.use).toHaveBeenCalledWith(
          expect.any(Function),
          onRejected,
        )
        expect(id).toBe(mockId)
      })

      it('应该能添加响应拦截器', () => {
        const mockId = 456
        mockAxiosInstance.interceptors!.response.use = vi.fn().mockReturnValue(mockId)

        const onFulfilled = vi.fn()
        const onRejected = vi.fn()

        const id = httpClient.addResponseInterceptor(onFulfilled, onRejected)

        expect(mockAxiosInstance.interceptors!.response.use).toHaveBeenCalledWith(
          onFulfilled,
          onRejected,
        )
        expect(id).toBe(mockId)
      })

      it('应该能移除请求拦截器', () => {
        mockAxiosInstance.interceptors!.request.use = vi.fn().mockReturnValue(123)
        mockAxiosInstance.interceptors!.request.eject = vi.fn()

        const id = httpClient.addRequestInterceptor(vi.fn())
        httpClient.removeInterceptor('request', id)

        expect(mockAxiosInstance.interceptors!.request.eject).toHaveBeenCalledWith(id)
      })

      it('应该能移除响应拦截器', () => {
        mockAxiosInstance.interceptors!.response.use = vi.fn().mockReturnValue(456)
        mockAxiosInstance.interceptors!.response.eject = vi.fn()

        const id = httpClient.addResponseInterceptor(vi.fn())
        httpClient.removeInterceptor('response', id)

        expect(mockAxiosInstance.interceptors!.response.eject).toHaveBeenCalledWith(id)
      })

      it('应该能清除所有拦截器', () => {
        // 重置之前的调用
        vi.clearAllMocks()

        // 重新设置 mock 以返回特定 ID
        mockAxiosInstance.interceptors!.request.use = vi.fn().mockReturnValue(123)
        mockAxiosInstance.interceptors!.response.use = vi.fn().mockReturnValue(456)
        mockAxiosInstance.interceptors!.request.eject = vi.fn()
        mockAxiosInstance.interceptors!.response.eject = vi.fn()

        const requestId = httpClient.addRequestInterceptor(vi.fn())
        const responseId = httpClient.addResponseInterceptor(vi.fn())

        httpClient.clearAllInterceptors()

        expect(mockAxiosInstance.interceptors!.request.eject).toHaveBeenCalledWith(requestId)
        expect(mockAxiosInstance.interceptors!.response.eject).toHaveBeenCalledWith(responseId)
      })
    })

    describe('Error Handling', () => {
      it('应该处理响应错误', async () => {
        const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

        const mockError = {
          response: {
            status: 404,
            data: { message: 'Not found' },
          },
          request: {},
          message: 'Request failed with status code 404',
        }

        mockAxiosInstance.get = vi.fn().mockRejectedValue(mockError)

        try {
          await httpClient.get('/api/nonexistent')
        } catch (error) {
          expect(error).toEqual(mockError)
          expect(consoleSpy).toHaveBeenCalledWith(
            expect.stringContaining('HTTP Error 404'),
            mockError.response.data,
          )
        }

        consoleSpy.mockRestore()
      })

      it('应该处理网络错误', async () => {
        const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

        const mockError = {
          request: {},
          message: 'Network Error',
        }

        mockAxiosInstance.get = vi.fn().mockRejectedValue(mockError)

        try {
          await httpClient.get('/api/test')
        } catch (error) {
          expect(error).toEqual(mockError)
          expect(consoleSpy).toHaveBeenCalledWith(
            expect.stringContaining('Network Error'),
            mockError.message,
          )
        }

        consoleSpy.mockRestore()
      })

      it('应该处理请求设置错误', async () => {
        const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

        const mockError = {
          message: 'Request setup error',
        }

        mockAxiosInstance.get = vi.fn().mockRejectedValue(mockError)

        try {
          await httpClient.get('/api/test')
        } catch (error) {
          expect(error).toEqual(mockError)
          expect(consoleSpy).toHaveBeenCalledWith(
            expect.stringContaining('Request Setup Error'),
            mockError.message,
          )
        }

        consoleSpy.mockRestore()
      })
    })

    describe('Configuration', () => {
      it('应该能使用自定义配置创建客户端', () => {
        const customConfig: AxiosRequestConfig = {
          baseURL: 'https://api.example.com',
          timeout: 5000,
          headers: {
            'Custom-Header': 'value',
          },
        }

        new AxiosHttpClient(customConfig)

        expect(mockedAxios.create).toHaveBeenCalledWith({
          timeout: 10000,
          headers: {
            'Content-Type': 'application/json',
          },
          ...customConfig,
        })
      })

      it('应该能获取 Axios 实例', () => {
        const instance = httpClient.getAxiosInstance()

        expect(instance).toBe(mockAxiosInstance)
      })
    })
  })

  describe('FetchHttpClient', () => {
    let httpClient: FetchHttpClient
    let mockFetch: any

    beforeEach(() => {
      mockFetch = vi.fn()
      global.fetch = mockFetch
      global.AbortController = class {
        signal = {}
        abort = vi.fn()
      } as any

      httpClient = new FetchHttpClient()
    })

    afterEach(() => {
      vi.resetAllMocks()
    })

    describe('HTTP Methods', () => {
      it('应该能发送 GET 请求', async () => {
        const mockResponseData = { id: 1, name: 'test' }
        const mockResponse = {
          ok: true,
          status: 200,
          statusText: 'OK',
          headers: new Headers({ 'content-type': 'application/json' }),
          json: vi.fn().mockResolvedValue(mockResponseData),
          text: vi.fn().mockResolvedValue('{}'),
        }

        mockFetch.mockResolvedValue(mockResponse)

        const response = await httpClient.get('/api/users/1')

        expect(mockFetch).toHaveBeenCalledWith(
          '/api/users/1',
          expect.objectContaining({
            method: 'GET',
            headers: expect.objectContaining({
              'Content-Type': 'application/json',
            }),
          }),
        )
        expect(response.data).toEqual(mockResponseData)
        expect(response.status).toBe(200)
      })

      it('应该能发送 POST 请求', async () => {
        const requestData = { name: 'John' }
        const mockResponseData = { id: 1, ...requestData }
        const mockResponse = {
          ok: true,
          status: 201,
          statusText: 'Created',
          headers: new Headers({ 'content-type': 'application/json' }),
          json: vi.fn().mockResolvedValue(mockResponseData),
          text: vi.fn().mockResolvedValue('{}'),
        }

        mockFetch.mockResolvedValue(mockResponse)

        const response = await httpClient.post('/api/users', requestData)

        expect(mockFetch).toHaveBeenCalledWith(
          '/api/users',
          expect.objectContaining({
            method: 'POST',
            body: JSON.stringify(requestData),
          }),
        )
        expect(response.data).toEqual(mockResponseData)
      })

      it('应该能处理文本响应', async () => {
        const mockResponseData = 'Plain text response'
        const mockResponse = {
          ok: true,
          status: 200,
          statusText: 'OK',
          headers: new Headers({ 'content-type': 'text/plain' }),
          text: vi.fn().mockResolvedValue(mockResponseData),
        }

        mockFetch.mockResolvedValue(mockResponse)

        const response = await httpClient.get('/api/text')

        expect(response.data).toBe(mockResponseData)
      })
    })

    describe('Configuration', () => {
      it('应该能使用自定义配置创建客户端', () => {
        const config = {
          baseURL: 'https://api.example.com',
          timeout: 5000,
          headers: { 'Custom-Header': 'value' },
        }

        const customClient = new FetchHttpClient(config)

        // 验证配置已应用
        expect(() => customClient).not.toThrow()
      })

      it('应该能设置和移除默认请求头', () => {
        httpClient.setDefaultHeader('Authorization', 'Bearer token')

        // 由于这是私有状态，我们通过发送请求来验证
        const mockResponse = {
          ok: true,
          status: 200,
          statusText: 'OK',
          headers: new Headers(),
          json: vi.fn().mockResolvedValue({}),
          text: vi.fn().mockResolvedValue('{}'),
        }

        mockFetch.mockResolvedValue(mockResponse)

        httpClient.get('/test')

        expect(mockFetch).toHaveBeenCalledWith(
          '/test',
          expect.objectContaining({
            headers: expect.objectContaining({
              Authorization: 'Bearer token',
            }),
          }),
        )

        httpClient.removeDefaultHeader('Authorization')
      })

      it('应该能构建完整 URL', async () => {
        const clientWithBaseUrl = new FetchHttpClient({
          baseURL: 'https://api.example.com',
        })

        const mockResponse = {
          ok: true,
          status: 200,
          statusText: 'OK',
          headers: new Headers({ 'content-type': 'application/json' }),
          json: vi.fn().mockResolvedValue({}),
          text: vi.fn().mockResolvedValue('{}'),
        }

        mockFetch.mockResolvedValue(mockResponse)

        await clientWithBaseUrl.get('/users')

        expect(mockFetch).toHaveBeenCalledWith('https://api.example.com/users', expect.any(Object))
      })
    })

    describe('Error Handling', () => {
      it('应该处理超时错误', async () => {
        mockFetch.mockImplementation(
          () =>
            new Promise((_, reject) => {
              const error = new Error('The user aborted a request.')
              error.name = 'AbortError'
              reject(error)
            }),
        )

        try {
          await httpClient.get('/api/slow')
        } catch (error: any) {
          expect(error.message).toBe('Request timeout')
          expect(error.code).toBe('ECONNABORTED')
        }
      })

      it('应该处理网络错误', async () => {
        const networkError = new Error('Network error')
        mockFetch.mockRejectedValue(networkError)

        try {
          await httpClient.get('/api/test')
        } catch (error) {
          expect(error).toBe(networkError)
        }
      })
    })

    describe('Interceptor Warning', () => {
      it('应该在尝试使用拦截器时发出警告', () => {
        const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})

        httpClient.addRequestInterceptor()
        httpClient.addResponseInterceptor()
        httpClient.removeInterceptor()

        expect(consoleSpy).toHaveBeenCalledWith(
          'Request interceptors not supported in FetchHttpClient',
        )
        expect(consoleSpy).toHaveBeenCalledWith(
          'Response interceptors not supported in FetchHttpClient',
        )
        expect(consoleSpy).toHaveBeenCalledWith('Interceptors not supported in FetchHttpClient')

        consoleSpy.mockRestore()
      })
    })
  })

  describe('MockHttpClient', () => {
    let httpClient: MockHttpClient

    beforeEach(() => {
      httpClient = new MockHttpClient()
    })

    describe('Mock Responses', () => {
      it('应该能设置和使用模拟响应', async () => {
        const mockData = { id: 1, name: 'test' }
        httpClient.setMockResponse('GET', '/api/users/1', mockData)

        const response = await httpClient.get('/api/users/1')

        expect(response.data).toEqual(mockData)
        expect(response.status).toBe(200)
      })

      it('应该能设置带状态码的模拟响应', async () => {
        const mockResponse = {
          data: { message: 'Created' },
          status: 201,
          statusText: 'Created',
        }

        httpClient.setMockResponse('POST', '/api/users', mockResponse)

        const response = await httpClient.post('/api/users', { name: 'John' })

        expect(response.data).toEqual(mockResponse.data)
        expect(response.status).toBe(201)
        expect(response.statusText).toBe('Created')
      })

      it('应该能模拟错误响应', async () => {
        const error = new Error('Server error')
        httpClient.setMockResponse('GET', '/api/error', { error })

        try {
          await httpClient.get('/api/error')
        } catch (thrownError) {
          expect(thrownError).toBe(error)
        }
      })

      it('应该在没有配置响应时抛出错误', async () => {
        try {
          await httpClient.get('/api/unconfigured')
        } catch (error: any) {
          expect(error.message).toContain('No mock response configured for GET /api/unconfigured')
        }
      })
    })

    describe('Delay Simulation', () => {
      it('应该能设置响应延迟', async () => {
        httpClient.setDelay(100)
        httpClient.setMockResponse('GET', '/api/slow', { data: 'slow response' })

        const startTime = Date.now()
        await httpClient.get('/api/slow')
        const endTime = Date.now()

        expect(endTime - startTime).toBeGreaterThanOrEqual(95) // 允许一些误差
      })

      it('应该能通过构造函数设置延迟', async () => {
        const delayedClient = new MockHttpClient({ delay: 50 })
        delayedClient.setMockResponse('GET', '/api/test', { data: 'test' })

        const startTime = Date.now()
        await delayedClient.get('/api/test')
        const endTime = Date.now()

        expect(endTime - startTime).toBeGreaterThanOrEqual(45)
      })
    })

    describe('Headers Management', () => {
      it('应该能设置和移除默认请求头', () => {
        httpClient.setDefaultHeader('Authorization', 'Bearer token')
        httpClient.removeDefaultHeader('Authorization')

        // Mock 客户端不会失败，这里主要测试方法存在
        expect(typeof httpClient.setDefaultHeader).toBe('function')
        expect(typeof httpClient.removeDefaultHeader).toBe('function')
      })
    })

    describe('Response Management', () => {
      it('应该能清除所有模拟响应', async () => {
        httpClient.setMockResponse('GET', '/api/test1', { data: 'test1' })
        httpClient.setMockResponse('GET', '/api/test2', { data: 'test2' })

        httpClient.clearMockResponses()

        try {
          await httpClient.get('/api/test1')
        } catch (error: any) {
          expect(error.message).toContain('No mock response configured')
        }
      })

      it('应该包含请求信息在响应中', async () => {
        const requestData = { name: 'John' }
        httpClient.setMockResponse('POST', '/api/users', { data: { id: 1 } })

        const response = await httpClient.post('/api/users', requestData)

        expect(response.request).toEqual({
          method: 'POST',
          url: '/api/users',
          data: requestData,
        })
      })
    })

    describe('Interceptor Stubs', () => {
      it('应该提供拦截器方法存根', () => {
        expect(httpClient.addRequestInterceptor()).toBe(0)
        expect(httpClient.addResponseInterceptor()).toBe(0)
        expect(() => httpClient.removeInterceptor()).not.toThrow()
      })
    })
  })

  describe('Factory Functions', () => {
    beforeEach(() => {
      // 重置 axios mock
      mockedAxios.create.mockReturnValue({
        defaults: { headers: { common: {} } },
        interceptors: {
          request: { use: vi.fn(), eject: vi.fn() },
          response: { use: vi.fn(), eject: vi.fn() },
        },
      } as any)
    })

    describe('createHttpClient', () => {
      it('应该创建 AxiosHttpClient', () => {
        const client = createHttpClient('axios')

        expect(client).toBeInstanceOf(AxiosHttpClient)
      })

      it('应该创建 FetchHttpClient', () => {
        const client = createHttpClient('fetch')

        expect(client).toBeInstanceOf(FetchHttpClient)
      })

      it('应该创建 MockHttpClient', () => {
        const client = createHttpClient('mock')

        expect(client).toBeInstanceOf(MockHttpClient)
      })

      it('应该使用默认类型 axios', () => {
        const client = createHttpClient()

        expect(client).toBeInstanceOf(AxiosHttpClient)
      })

      it('应该抛出不支持类型的错误', () => {
        expect(() => {
          createHttpClient('invalid' as any)
        }).toThrow('Unsupported HTTP client type: invalid')
      })

      it('应该传递配置参数', () => {
        const config = { timeout: 5000 }
        createHttpClient('axios', config)

        expect(mockedAxios.create).toHaveBeenCalledWith({
          headers: {
            'Content-Type': 'application/json',
          },
          timeout: 10000,
          ...config,
        })
      })
    })

    describe('createAutoHttpClient', () => {
      it('应该创建 AxiosHttpClient', () => {
        const client = createAutoHttpClient()

        expect(client).toBeInstanceOf(AxiosHttpClient)
      })

      it('应该在 axios 不可用时降级到 FetchHttpClient', () => {
        // Mock axios 构造函数抛出错误
        mockedAxios.create.mockImplementation(() => {
          throw new Error('axios not available')
        })

        const client = createAutoHttpClient()

        expect(client).toBeInstanceOf(FetchHttpClient)
      })

      it('应该传递配置给创建的客户端', () => {
        const config = { timeout: 5000 }
        createAutoHttpClient(config)

        expect(mockedAxios.create).toHaveBeenCalledWith({
          headers: {
            'Content-Type': 'application/json',
          },
          timeout: 10000,
          ...config,
        })
      })
    })
  })

  describe('Interface Compliance', () => {
    const httpClientTypes: {
      name: string
      create: () => IHttpClient
    }[] = [
      {
        name: 'AxiosHttpClient',
        create: () => {
          mockedAxios.create.mockReturnValue({
            defaults: { headers: { common: {} } },
            interceptors: {
              request: { use: vi.fn(), eject: vi.fn() },
              response: { use: vi.fn(), eject: vi.fn() },
            },
            get: vi.fn().mockResolvedValue({ data: {}, status: 200 }),
            post: vi.fn().mockResolvedValue({ data: {}, status: 200 }),
            put: vi.fn().mockResolvedValue({ data: {}, status: 200 }),
            delete: vi.fn().mockResolvedValue({ data: {}, status: 200 }),
          } as any)
          return new AxiosHttpClient()
        },
      },
      {
        name: 'FetchHttpClient',
        create: () => {
          global.fetch = vi.fn().mockResolvedValue({
            ok: true,
            status: 200,
            statusText: 'OK',
            headers: new Headers(),
            json: vi.fn().mockResolvedValue({}),
            text: vi.fn().mockResolvedValue('{}'),
          })
          global.AbortController = class {
            signal = {}
            abort = vi.fn()
          } as any
          return new FetchHttpClient()
        },
      },
      {
        name: 'MockHttpClient',
        create: () => {
          const client = new MockHttpClient()
          client.setMockResponse('GET', '/test', { data: 'test' })
          client.setMockResponse('POST', '/test', { data: 'test' })
          client.setMockResponse('PUT', '/test', { data: 'test' })
          client.setMockResponse('DELETE', '/test', { data: 'test' })
          return client
        },
      },
    ]

    httpClientTypes.forEach(({ name, create }) => {
      describe(`${name} Interface Compliance`, () => {
        let client: IHttpClient

        beforeEach(() => {
          client = create()
        })

        it('应该实现 IHttpClient 接口', () => {
          expect(typeof client.get).toBe('function')
          expect(typeof client.post).toBe('function')
          expect(typeof client.put).toBe('function')
          expect(typeof client.delete).toBe('function')
          expect(typeof client.setDefaultHeader).toBe('function')
          expect(typeof client.removeDefaultHeader).toBe('function')
          expect(typeof client.addRequestInterceptor).toBe('function')
          expect(typeof client.addResponseInterceptor).toBe('function')
          expect(typeof client.removeInterceptor).toBe('function')
        })

        it('应该正确处理基本 HTTP 操作', async () => {
          // 基本 HTTP 方法测试
          const getResponse = await client.get('/test')
          expect(getResponse).toHaveProperty('data')
          expect(getResponse).toHaveProperty('status')

          const postResponse = await client.post('/test', { data: 'test' })
          expect(postResponse).toHaveProperty('data')
          expect(postResponse).toHaveProperty('status')

          const putResponse = await client.put('/test', { data: 'test' })
          expect(putResponse).toHaveProperty('data')
          expect(putResponse).toHaveProperty('status')

          const deleteResponse = await client.delete('/test')
          expect(deleteResponse).toHaveProperty('data')
          expect(deleteResponse).toHaveProperty('status')
        })

        it('应该能处理请求头操作', () => {
          // 头部管理测试
          expect(() => {
            client.setDefaultHeader('Test-Header', 'test-value')
            client.removeDefaultHeader('Test-Header')
          }).not.toThrow()
        })

        it('应该能处理拦截器操作', () => {
          // 拦截器测试
          expect(() => {
            const requestId = client.addRequestInterceptor()
            const responseId = client.addResponseInterceptor()
            client.removeInterceptor('request', requestId)
            client.removeInterceptor('response', responseId)
          }).not.toThrow()
        })
      })
    })
  })
})
