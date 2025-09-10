/**
 * 对话管理API客户端服务
 * 实现所有对话相关的API调用
 */

import type {
  ApiResponse,
  CommandAcceptedResponse,
  CommandRequest,
  CommandStatusResponse,
  ContentResponse,
  ContentSearchItem,
  ContentSearchRequest,
  ConversationHeaders,
  CreateSessionRequest,
  MessageRequest,
  PaginatedApiResponse,
  PaginatedResponse,
  QualityScoreResponse,
  RoundCreateRequest,
  RoundQueryParams,
  RoundResponse,
  SessionResponse,
  SetStageRequest,
  StageResponse,
  UpdateSessionRequest,
  VersionCreateRequest,
  VersionInfo,
  VersionMergeRequest,
} from '@/types/api'
import { authenticatedApiService } from './authenticatedApiService'

/**
 * 处理API响应的辅助函数
 */
function handleApiResponse<T>(response: ApiResponse<T>): T {
  if (response.code === 0) {
    return response.data as T
  } else {
    throw new Error(response.msg || 'API请求失败')
  }
}

/**
 * 构建请求头
 */
function buildHeaders(headers?: ConversationHeaders): Record<string, string> {
  const result: Record<string, string> = {}

  if (headers?.['X-Correlation-Id']) {
    result['X-Correlation-Id'] = headers['X-Correlation-Id']
  }
  if (headers?.['Idempotency-Key']) {
    result['Idempotency-Key'] = headers['Idempotency-Key']
  }
  if (headers?.['If-Match']) {
    result['If-Match'] = headers['If-Match']
  }

  return result
}

export class ConversationsService {
  private basePath = '/api/v1/conversations'

  // ===== Session Management =====

  /**
   * 创建新会话
   * POST /api/v1/conversations/sessions
   */
  async createSession(
    request: CreateSessionRequest,
    headers?: ConversationHeaders,
  ): Promise<SessionResponse> {
    const response = await authenticatedApiService.post<ApiResponse<SessionResponse>>(
      `${this.basePath}/sessions`,
      request,
      { headers: buildHeaders(headers) },
    )
    return handleApiResponse(response)
  }

  /**
   * 获取会话详情
   * GET /api/v1/conversations/sessions/{session_id}
   */
  async getSession(sessionId: string): Promise<SessionResponse> {
    const response = await authenticatedApiService.get<ApiResponse<SessionResponse>>(
      `${this.basePath}/sessions/${sessionId}`,
    )
    return handleApiResponse(response)
  }

  /**
   * 更新会话
   * PATCH /api/v1/conversations/sessions/{session_id}
   */
  async updateSession(
    sessionId: string,
    request: UpdateSessionRequest,
    headers?: ConversationHeaders,
  ): Promise<SessionResponse> {
    const response = await authenticatedApiService.patch<ApiResponse<SessionResponse>>(
      `${this.basePath}/sessions/${sessionId}`,
      request,
      { headers: buildHeaders(headers) },
    )
    return handleApiResponse(response)
  }

  /**
   * 删除会话
   * DELETE /api/v1/conversations/sessions/{session_id}
   */
  async deleteSession(sessionId: string): Promise<void> {
    const response = await authenticatedApiService.delete<ApiResponse<null>>(
      `${this.basePath}/sessions/${sessionId}`,
    )
    handleApiResponse(response)
  }

  // ===== Rounds Management =====

  /**
   * 获取轮次列表
   * GET /api/v1/conversations/sessions/{session_id}/rounds
   */
  async getRounds(sessionId: string, params?: RoundQueryParams): Promise<RoundResponse[]> {
    const searchParams = new URLSearchParams()

    if (params) {
      if (params.after) searchParams.append('after', params.after)
      if (params.limit) searchParams.append('limit', params.limit.toString())
      if (params.order) searchParams.append('order', params.order)
      if (params.role) searchParams.append('role', params.role)
    }

    const query = searchParams.toString()
    const url = query
      ? `${this.basePath}/sessions/${sessionId}/rounds?${query}`
      : `${this.basePath}/sessions/${sessionId}/rounds`

    const response = await authenticatedApiService.get<ApiResponse<RoundResponse[]>>(url)
    return handleApiResponse(response)
  }

  /**
   * 创建新轮次
   * POST /api/v1/conversations/sessions/{session_id}/rounds
   */
  async createRound(
    sessionId: string,
    request: RoundCreateRequest,
    headers?: ConversationHeaders,
  ): Promise<RoundResponse> {
    const response = await authenticatedApiService.post<ApiResponse<RoundResponse>>(
      `${this.basePath}/sessions/${sessionId}/rounds`,
      request,
      { headers: buildHeaders(headers) },
    )
    return handleApiResponse(response)
  }

  /**
   * 获取特定轮次
   * GET /api/v1/conversations/sessions/{session_id}/rounds/{round_id}
   */
  async getRound(sessionId: string, roundId: string): Promise<RoundResponse> {
    const response = await authenticatedApiService.get<ApiResponse<RoundResponse>>(
      `${this.basePath}/sessions/${sessionId}/rounds/${roundId}`,
    )
    return handleApiResponse(response)
  }

  // ===== Messages (Alias for Rounds) =====

  /**
   * 发送消息（创建轮次的别名，默认角色为 'user'）
   * POST /api/v1/conversations/sessions/{session_id}/messages
   */
  async sendMessage(
    sessionId: string,
    request: MessageRequest,
    headers?: ConversationHeaders,
  ): Promise<RoundResponse> {
    const roundRequest: RoundCreateRequest = {
      role: request.role || 'user',
      input: request.input,
      model: request.model,
      correlation_id: request.correlation_id,
    }

    const response = await authenticatedApiService.post<ApiResponse<RoundResponse>>(
      `${this.basePath}/sessions/${sessionId}/messages`,
      roundRequest,
      { headers: buildHeaders(headers) },
    )
    return handleApiResponse(response)
  }

  // ===== Commands =====

  /**
   * 提交异步命令
   * POST /api/v1/conversations/sessions/{session_id}/commands
   */
  async submitCommand(
    sessionId: string,
    request: CommandRequest,
    headers?: ConversationHeaders,
  ): Promise<CommandAcceptedResponse> {
    const response = await authenticatedApiService.post<ApiResponse<CommandAcceptedResponse>>(
      `${this.basePath}/sessions/${sessionId}/commands`,
      request,
      { headers: buildHeaders(headers) },
    )
    return handleApiResponse(response)
  }

  /**
   * 获取命令状态
   * GET /api/v1/conversations/sessions/{session_id}/commands/{cmd_id}
   */
  async getCommandStatus(sessionId: string, commandId: string): Promise<CommandStatusResponse> {
    const response = await authenticatedApiService.get<ApiResponse<CommandStatusResponse>>(
      `${this.basePath}/sessions/${sessionId}/commands/${commandId}`,
    )
    return handleApiResponse(response)
  }

  /**
   * 轮询命令状态直到完成
   */
  async pollCommandStatus(
    sessionId: string,
    commandId: string,
    options?: {
      interval?: number
      timeout?: number
      onProgress?: (status: CommandStatusResponse) => void
    },
  ): Promise<CommandStatusResponse> {
    const interval = options?.interval || 1000
    const timeout = options?.timeout || 30000
    const startTime = Date.now()

    while (Date.now() - startTime < timeout) {
      const status = await this.getCommandStatus(sessionId, commandId)

      if (options?.onProgress) {
        options.onProgress(status)
      }

      // 检查是否完成
      if (['completed', 'failed', 'cancelled'].includes(status.status.toLowerCase())) {
        return status
      }

      // 等待下一次轮询
      await new Promise((resolve) => setTimeout(resolve, interval))
    }

    throw new Error(`Command ${commandId} timed out after ${timeout}ms`)
  }

  // ===== Stage Management =====

  /**
   * 获取当前阶段
   * GET /api/v1/conversations/sessions/{session_id}/stage
   */
  async getStage(sessionId: string): Promise<StageResponse> {
    const response = await authenticatedApiService.get<ApiResponse<StageResponse>>(
      `${this.basePath}/sessions/${sessionId}/stage`,
    )
    return handleApiResponse(response)
  }

  /**
   * 设置阶段
   * PUT /api/v1/conversations/sessions/{session_id}/stage
   */
  async setStage(
    sessionId: string,
    request: SetStageRequest,
    headers?: ConversationHeaders,
  ): Promise<StageResponse> {
    const response = await authenticatedApiService.put<ApiResponse<StageResponse>>(
      `${this.basePath}/sessions/${sessionId}/stage`,
      request,
      { headers: buildHeaders(headers) },
    )
    return handleApiResponse(response)
  }

  /**
   * 验证阶段
   * POST /api/v1/conversations/sessions/{session_id}/stage/validate
   */
  async validateStage(sessionId: string): Promise<CommandAcceptedResponse> {
    const response = await authenticatedApiService.post<ApiResponse<CommandAcceptedResponse>>(
      `${this.basePath}/sessions/${sessionId}/stage/validate`,
    )
    return handleApiResponse(response)
  }

  /**
   * 锁定阶段
   * POST /api/v1/conversations/sessions/{session_id}/stage/lock
   */
  async lockStage(sessionId: string): Promise<CommandAcceptedResponse> {
    const response = await authenticatedApiService.post<ApiResponse<CommandAcceptedResponse>>(
      `${this.basePath}/sessions/${sessionId}/stage/lock`,
    )
    return handleApiResponse(response)
  }

  // ===== Content Management =====

  /**
   * 获取聚合内容
   * GET /api/v1/conversations/sessions/{session_id}/content
   */
  async getContent(sessionId: string): Promise<ContentResponse> {
    const response = await authenticatedApiService.get<ApiResponse<ContentResponse>>(
      `${this.basePath}/sessions/${sessionId}/content`,
    )
    return handleApiResponse(response)
  }

  /**
   * 导出内容
   * POST /api/v1/conversations/sessions/{session_id}/content/export
   */
  async exportContent(sessionId: string): Promise<CommandAcceptedResponse> {
    const response = await authenticatedApiService.post<ApiResponse<CommandAcceptedResponse>>(
      `${this.basePath}/sessions/${sessionId}/content/export`,
    )
    return handleApiResponse(response)
  }

  /**
   * 搜索内容
   * POST /api/v1/conversations/sessions/{session_id}/content/search
   */
  async searchContent(
    sessionId: string,
    request: ContentSearchRequest,
  ): Promise<PaginatedResponse<ContentSearchItem>> {
    const response = await authenticatedApiService.post<PaginatedApiResponse<ContentSearchItem>>(
      `${this.basePath}/sessions/${sessionId}/content/search`,
      request,
    )
    return handleApiResponse(response)
  }

  // ===== Quality & Consistency =====

  /**
   * 获取质量评分
   * GET /api/v1/conversations/sessions/{session_id}/quality
   */
  async getQualityScore(sessionId: string): Promise<QualityScoreResponse> {
    const response = await authenticatedApiService.get<ApiResponse<QualityScoreResponse>>(
      `${this.basePath}/sessions/${sessionId}/quality`,
    )
    return handleApiResponse(response)
  }

  /**
   * 触发一致性检查
   * POST /api/v1/conversations/sessions/{session_id}/consistency
   */
  async checkConsistency(sessionId: string): Promise<CommandAcceptedResponse> {
    const response = await authenticatedApiService.post<ApiResponse<CommandAcceptedResponse>>(
      `${this.basePath}/sessions/${sessionId}/consistency`,
    )
    return handleApiResponse(response)
  }

  // ===== Version Control =====

  /**
   * 获取版本列表
   * GET /api/v1/conversations/sessions/{session_id}/versions
   */
  async getVersions(sessionId: string): Promise<VersionInfo[]> {
    const response = await authenticatedApiService.get<ApiResponse<VersionInfo[]>>(
      `${this.basePath}/sessions/${sessionId}/versions`,
    )
    return handleApiResponse(response)
  }

  /**
   * 创建版本分支
   * POST /api/v1/conversations/sessions/{session_id}/versions
   */
  async createVersion(sessionId: string, request: VersionCreateRequest): Promise<VersionInfo> {
    const response = await authenticatedApiService.post<ApiResponse<VersionInfo>>(
      `${this.basePath}/sessions/${sessionId}/versions`,
      request,
    )
    return handleApiResponse(response)
  }

  /**
   * 合并版本
   * PUT /api/v1/conversations/sessions/{session_id}/versions/merge
   */
  async mergeVersions(sessionId: string, request: VersionMergeRequest): Promise<void> {
    const response = await authenticatedApiService.put<ApiResponse<null>>(
      `${this.basePath}/sessions/${sessionId}/versions/merge`,
      request,
    )
    handleApiResponse(response)
  }

  // ===== Helper Methods =====

  /**
   * 生成幂等键
   */
  generateIdempotencyKey(): string {
    return `${Date.now()}-${Math.random().toString(36).substring(2, 15)}`
  }

  /**
   * 生成关联ID
   */
  generateCorrelationId(): string {
    return `corr-${Date.now()}-${Math.random().toString(36).substring(2, 15)}`
  }
}

// 导出单例实例
export const conversationsService = new ConversationsService()
