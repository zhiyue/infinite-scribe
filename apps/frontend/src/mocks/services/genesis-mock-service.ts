/**
 * Genesis Mock Service
 *
 * 前端 mock 服务，用于模拟创世阶段的 API 调用
 * 可以通过环境变量控制启用/禁用
 */

import type { RoundResponse, SetStageRequest, StageResponse } from '@/types/api'
import { GenesisStage } from '@/types/enums'

// 环境变量控制是否启用 mock
const USE_MOCK_GENESIS = import.meta.env.VITE_USE_MOCK_GENESIS !== 'false'

// Mock 数据存储
interface MockSessionData {
  stage: string
  updated_at: string
}

interface MockRoundData {
  sessionId: string
  round_path: string
  role: 'user' | 'assistant'
  input?: any
  output?: any
  model?: string
  correlation_id?: string
  created_at: string
}

class GenesisMockService {
  private sessionStages = new Map<string, MockSessionData>()
  private sessionRounds = new Map<string, MockRoundData[]>()

  // 创世阶段的 AI 回复模板
  private readonly STAGE_RESPONSES = {
    [GenesisStage.INITIAL_PROMPT]: [
      '你好！我是你的创世助手。让我们一起构建你的小说世界吧！请告诉我你的创作灵感，比如故事的类型、主题，或者任何激发你创作欲望的内容。',
      '我可以帮你将模糊的想法转化为具体的小说设定。你想创作什么样的故事呢？',
    ],
    [GenesisStage.WORLDVIEW]: [
      '太棒了！基于你的灵感，让我们来构建这个世界的详细设定。这个世界有什么独特的规则或特点吗？',
      '让我们继续深入这个世界的背景设定。告诉我更多关于这个世界的社会结构、地理环境或者独特的力量体系。',
    ],
    [GenesisStage.CHARACTERS]: [
      '现在让我们来创造这个世界中的角色。主角是什么样的人？有什么特别的经历或动机吗？',
      '角色设定很有趣！让我们继续完善主角和其他重要角色的关系网络。',
    ],
    [GenesisStage.PLOT_OUTLINE]: [
      '故事的大纲正在成形！让我们规划一下主要的情节线。故事从哪里开始？有什么重要的转折点？',
      '剧情设定很精彩！让我们继续完善故事的结构和关键事件。',
    ],
    [GenesisStage.FINISHED]: ['恭喜！你的创世设定已经完成了。现在可以开始正式的小说写作了！'],
  }

  /**
   * 检查是否启用 mock
   */
  isEnabled(): boolean {
    return USE_MOCK_GENESIS
  }

  /**
   * 获取创世阶段
   */
  getStage(sessionId: string): StageResponse {
    const data = this.sessionStages.get(sessionId) || {
      stage: GenesisStage.INITIAL_PROMPT,
      updated_at: new Date().toISOString(),
    }

    this.sessionStages.set(sessionId, data)
    return data
  }

  /**
   * 设置创世阶段
   */
  setStage(sessionId: string, request: SetStageRequest): StageResponse {
    const validStages = Object.values(GenesisStage)

    if (!validStages.includes(request.stage as GenesisStage)) {
      throw new Error(`Invalid stage. Must be one of: ${validStages.join(', ')}`)
    }

    const data: MockSessionData = {
      stage: request.stage,
      updated_at: new Date().toISOString(),
    }

    this.sessionStages.set(sessionId, data)
    return data
  }

  /**
   * 获取会话轮次
   */
  getRounds(sessionId: string): RoundResponse[] {
    return this.sessionRounds.get(sessionId) || []
  }

  /**
   * 创建新轮次（发送消息）
   */
  createRound(sessionId: string, userInput: any): RoundResponse {
    const rounds = this.sessionRounds.get(sessionId) || []
    const roundPath = (rounds.length + 1).toString()

    // 获取当前阶段
    const currentStage = this.sessionStages.get(sessionId)?.stage || GenesisStage.INITIAL_PROMPT

    // 创建用户轮次
    const userRound: MockRoundData = {
      sessionId,
      round_path: roundPath,
      role: 'user',
      input: userInput,
      created_at: new Date().toISOString(),
    }

    // 生成 AI 回复
    const aiResponse = this.generateAIResponse(currentStage, userInput?.user_input || '')
    const aiRound: MockRoundData = {
      sessionId,
      round_path: (rounds.length + 2).toString(),
      role: 'assistant',
      output: {
        content: aiResponse,
        type: 'ai_response',
      },
      created_at: new Date().toISOString(),
    }

    // 保存轮次
    rounds.push(userRound, aiRound)
    this.sessionRounds.set(sessionId, rounds)

    // 返回 AI 轮次（模拟 AI 回复）
    return {
      session_id: sessionId,
      round_path: aiRound.round_path,
      role: aiRound.role,
      input: aiRound.input,
      output: aiRound.output,
      model: aiRound.model,
      correlation_id: aiRound.correlation_id,
      created_at: aiRound.created_at,
    }
  }

  /**
   * 生成 AI 回复
   */
  private generateAIResponse(stage: string, userInput: string): string {
    const responses = this.STAGE_RESPONSES[stage as GenesisStage] || [
      '很有意思的想法！让我们继续深入探讨这个部分。',
      '这个设定很棒！我们可以进一步完善它。',
    ]

    // 根据输入长度选择回复
    if (userInput.length > 100) {
      return responses[0] || '感谢你详细的分享！'
    } else {
      return responses[responses.length - 1] || '请告诉我更多详细信息。'
    }
  }
}

// 导出单例实例
export const genesisMockService = new GenesisMockService()
