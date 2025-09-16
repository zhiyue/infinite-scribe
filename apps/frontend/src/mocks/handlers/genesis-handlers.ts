/**
 * Genesis Mock Handlers for MSW
 *
 * 使用 MSW 拦截创世相关的 API 请求并返回 mock 数据
 */

import type { ApiResponse } from '@/types/api'
import { http, HttpResponse } from 'msw'
import { genesisMockService } from '../services/genesis-mock-service'

// 支持绝对URL和相对URL
// 注意: 必须与前端请求的URL完全匹配
const API_BASE_URL = 'http://127.0.0.1:8000' // 直接使用127.0.0.1，与.env保持一致
const API_BASE = `${API_BASE_URL}/api/v1/conversations`

console.log('🔧 MSW Handlers - API_BASE:', API_BASE)

export const genesisHandlers = [
  // 测试 handler - 验证 MSW 是否工作
  http.get('http://127.0.0.1:8000/test', () => {
    console.log('✅ MSW Test handler triggered!')
    return HttpResponse.json({ message: 'MSW is working!' })
  }),

  // POST /api/v1/conversations/sessions - 创建会话
  http.post(`${API_BASE}/sessions`, async ({ request }) => {
    console.log('🔧 MSW - POST sessions handler triggered!')
    try {
      const requestData = (await request.json()) as any
      console.log('🔧 MSW - Creating session:', requestData)
      
      const sessionId = `session-${Date.now()}`
      const sessionData = {
        id: sessionId,
        scope: requestData.scope || 'GENESIS',
        scope_id: requestData.scope_id,
        scope_type: requestData.scope_type || 'novel',
        active: true,
        version: 1,
        stage: 'INITIAL_PROMPT',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      }

      const response: ApiResponse<typeof sessionData> = {
        code: 0,
        msg: '会话创建成功',
        data: sessionData,
      }

      return HttpResponse.json(response, {
        status: 201,
        headers: {
          'Content-Type': 'application/json',
          'X-Mock-Response': 'true',
        },
      })
    } catch (error) {
      const response: ApiResponse<null> = {
        code: -1,
        msg: `创建会话失败: ${(error as Error).message}`,
        data: null,
      }
      return HttpResponse.json(response, { status: 500 })
    }
  }),

  // GET /api/v1/conversations/sessions/{sessionId} - 获取会话详情
  http.get(`${API_BASE}/sessions/:sessionId`, ({ params }) => {
    console.log('🔧 MSW - GET session handler triggered!')
    try {
      const sessionId = params.sessionId as string
      
      const sessionData = {
        id: sessionId,
        scope: 'GENESIS',
        scope_id: 'd760e160-b803-4b06-a472-13f06bb9181a',
        scope_type: 'novel',
        active: true,
        version: 1,
        stage: 'INITIAL_PROMPT',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      }

      const response: ApiResponse<typeof sessionData> = {
        code: 0,
        msg: '获取会话成功',
        data: sessionData,
      }

      return HttpResponse.json(response, {
        status: 200,
        headers: {
          'Content-Type': 'application/json',
          'X-Mock-Response': 'true',
        },
      })
    } catch (error) {
      const response: ApiResponse<null> = {
        code: -1,
        msg: `获取会话失败: ${(error as Error).message}`,
        data: null,
      }
      return HttpResponse.json(response, { status: 500 })
    }
  }),

  // GET /api/v1/conversations/sessions/{sessionId}/stage
  http.get(`${API_BASE}/sessions/:sessionId/stage`, ({ params }) => {
    console.log('🔧 MSW - GET stage handler triggered!')
    try {
      const sessionId = params.sessionId as string
      const stageData = genesisMockService.getStage(sessionId)

      const response: ApiResponse<typeof stageData> = {
        code: 0,
        msg: '获取阶段成功',
        data: stageData,
      }

      return HttpResponse.json(response, {
        status: 200,
        headers: {
          'Content-Type': 'application/json',
          'X-Mock-Response': 'true',
        },
      })
    } catch (error) {
      const response: ApiResponse<null> = {
        code: -1,
        msg: `获取阶段失败: ${(error as Error).message}`,
        data: null,
      }
      return HttpResponse.json(response, { status: 500 })
    }
  }),

  // PUT /api/v1/conversations/sessions/{sessionId}/stage
  http.put(`${API_BASE}/sessions/:sessionId/stage`, async ({ params, request }) => {
    try {
      const sessionId = params.sessionId as string
      const requestData = (await request.json()) as any
      const stageData = genesisMockService.setStage(sessionId, requestData)

      const response: ApiResponse<typeof stageData> = {
        code: 0,
        msg: '切换阶段成功',
        data: stageData,
      }

      return HttpResponse.json(response, {
        status: 200,
        headers: {
          'Content-Type': 'application/json',
          'X-Mock-Response': 'true',
        },
      })
    } catch (error) {
      const response: ApiResponse<null> = {
        code: -1,
        msg: `切换阶段失败: ${(error as Error).message}`,
        data: null,
      }
      return HttpResponse.json(response, { status: 400 })
    }
  }),

  // GET /api/v1/conversations/sessions/{sessionId}/rounds
  http.get(`${API_BASE}/sessions/:sessionId/rounds`, ({ params, request }) => {
    console.log('🔧 MSW - GET rounds handler triggered!')
    try {
      const sessionId = params.sessionId as string
      const url = new URL(request.url)
      const limit = parseInt(url.searchParams.get('limit') || '50')

      const rounds = genesisMockService.getRounds(sessionId)

      // 直接返回数组，不要包装在 items 里
      const response: ApiResponse<typeof rounds> = {
        code: 0,
        msg: '获取轮次成功',
        data: rounds.slice(0, limit), // 直接返回数组
      }

      return HttpResponse.json(response, {
        status: 200,
        headers: {
          'Content-Type': 'application/json',
          'X-Mock-Response': 'true',
        },
      })
    } catch (error) {
      const response: ApiResponse<null> = {
        code: -1,
        msg: `获取轮次失败: ${(error as Error).message}`,
        data: null,
      }
      return HttpResponse.json(response, { status: 500 })
    }
  }),

  // POST /api/v1/conversations/sessions/{sessionId}/messages
  http.post(`${API_BASE}/sessions/:sessionId/messages`, async ({ params, request }) => {
    console.log('🔧 MSW - POST messages handler triggered!')
    try {
      const sessionId = params.sessionId as string
      const requestData = (await request.json()) as any
      console.log('🔧 MSW - Creating message:', requestData)

      // 模拟 AI 思考时间
      await new Promise((resolve) => setTimeout(resolve, 1500))

      const roundData = genesisMockService.createRound(sessionId, requestData.input || requestData)

      const response: ApiResponse<typeof roundData> = {
        code: 0,
        msg: '发送消息成功',
        data: roundData,
      }

      return HttpResponse.json(response, {
        status: 201,
        headers: {
          'Content-Type': 'application/json',
          'X-Mock-Response': 'true',
        },
      })
    } catch (error) {
      const response: ApiResponse<null> = {
        code: -1,
        msg: `发送消息失败: ${(error as Error).message}`,
        data: null,
      }
      return HttpResponse.json(response, { status: 500 })
    }
  }),

  // POST /api/v1/conversations/sessions/{sessionId}/rounds
  http.post(`${API_BASE}/sessions/:sessionId/rounds`, async ({ params, request }) => {
    console.log('🔧 MSW - POST rounds handler triggered!')
    try {
      const sessionId = params.sessionId as string
      const requestData = (await request.json()) as any
      console.log('🔧 MSW - Creating round:', requestData)

      // 模拟 AI 思考时间
      await new Promise((resolve) => setTimeout(resolve, 1500))

      const roundData = genesisMockService.createRound(sessionId, requestData.input || requestData)

      const response: ApiResponse<typeof roundData> = {
        code: 0,
        msg: '创建轮次成功',
        data: roundData,
      }

      return HttpResponse.json(response, {
        status: 201,
        headers: {
          'Content-Type': 'application/json',
          'X-Mock-Response': 'true',
        },
      })
    } catch (error) {
      const response: ApiResponse<null> = {
        code: -1,
        msg: `创建轮次失败: ${(error as Error).message}`,
        data: null,
      }
      return HttpResponse.json(response, { status: 500 })
    }
  }),
]

// 移除调试 handler，因为它会干扰正常的请求处理
