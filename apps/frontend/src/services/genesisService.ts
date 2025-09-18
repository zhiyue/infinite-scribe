/**
 * Genesis API客户端服务
 * 实现创世阶段相关的API调用
 */

import type { ApiResponse, ConversationHeaders } from '@/types/api'
import { GenesisStage, GenesisStatus, StageSessionStatus } from '@/types/enums'
import { authenticatedApiService } from './authenticatedApiService'

/**
 * Genesis流程响应
 */
export interface GenesisFlowResponse {
  id: string
  novel_id: string
  status: GenesisStatus
  current_stage: GenesisStage | null
  current_stage_id: string | null
  version: number
  state: Record<string, any> | null
  created_at: string
  updated_at: string
}

/**
 * 阶段切换请求
 */
export interface SwitchStageRequest {
  target_stage: GenesisStage
}

/**
 * 阶段会话响应
 */
export interface StageSessionResponse {
  id: string
  stage_id: string
  session_id: string
  status: StageSessionStatus
  is_primary: boolean
  session_kind: string | null
  created_at: string
  updated_at: string
}

/**
 * 创建阶段会话请求
 */
export interface CreateStageSessionRequest {
  novel_id: string
  session_id?: string // 可选，如果提供则绑定现有会话
  is_primary?: boolean
  session_kind?: string
}

/**
 * 阶段记录响应
 */
export interface StageRecordResponse {
  id: string
  flow_id: string
  stage: GenesisStage
  config: Record<string, any> | null
  iteration_count: number
  created_at: string
  updated_at: string
}

/**
 * 活跃会话响应
 */
export interface ActiveSessionResponse {
  stage: StageRecordResponse
  session?: {
    id: string
    status: string
    created_at: string
  }
}

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

export class GenesisService {
  private basePath = '/api/v1/genesis'

  // ===== Genesis Flow Management =====

  /**
   * 创建或获取Genesis流程（幂等）
   * POST /api/v1/genesis/flows/{novel_id}
   */
  async createOrGetFlow(
    novelId: string,
    headers?: ConversationHeaders,
  ): Promise<GenesisFlowResponse> {
    const response = await authenticatedApiService.post<ApiResponse<GenesisFlowResponse>>(
      `${this.basePath}/flows/${novelId}`,
      {},
      { headers: buildHeaders(headers) },
    )
    return handleApiResponse(response)
  }

  /**
   * 获取Genesis流程
   * GET /api/v1/genesis/flows/{novel_id}
   */
  async getFlow(novelId: string, headers?: ConversationHeaders): Promise<GenesisFlowResponse> {
    const response = await authenticatedApiService.get<ApiResponse<GenesisFlowResponse>>(
      `${this.basePath}/flows/${novelId}`,
      { headers: buildHeaders(headers) },
    )
    return handleApiResponse(response)
  }

  /**
   * 切换流程阶段
   * POST /api/v1/genesis/flows/{novel_id}/switch-stage
   */
  async switchStage(
    novelId: string,
    request: SwitchStageRequest,
    headers?: ConversationHeaders,
  ): Promise<GenesisFlowResponse> {
    const response = await authenticatedApiService.post<ApiResponse<GenesisFlowResponse>>(
      `${this.basePath}/flows/${novelId}/switch-stage`,
      request,
      { headers: buildHeaders(headers) },
    )
    return handleApiResponse(response)
  }

  /**
   * 完成Genesis流程
   * POST /api/v1/genesis/flows/{novel_id}/complete
   */
  async completeFlow(novelId: string, headers?: ConversationHeaders): Promise<GenesisFlowResponse> {
    const response = await authenticatedApiService.post<ApiResponse<GenesisFlowResponse>>(
      `${this.basePath}/flows/${novelId}/complete`,
      {},
      { headers: buildHeaders(headers) },
    )
    return handleApiResponse(response)
  }

  // ===== Genesis Stage Session Management =====

  /**
   * 创建阶段会话
   * POST /api/v1/genesis/stages/{stage_id}/sessions
   */
  async createStageSession(
    stageId: string,
    request: CreateStageSessionRequest,
    headers?: ConversationHeaders,
  ): Promise<[string, StageSessionResponse]> {
    const response = await authenticatedApiService.post<
      ApiResponse<[string, StageSessionResponse]>
    >(`${this.basePath}/stages/${stageId}/sessions`, request, { headers: buildHeaders(headers) })
    return handleApiResponse(response)
  }

  /**
   * 列出阶段会话
   * GET /api/v1/genesis/stages/{stage_id}/sessions
   */
  async listStageSessions(
    stageId: string,
    params?: {
      status?: StageSessionStatus
      limit?: number
      offset?: number
    },
    headers?: ConversationHeaders,
  ): Promise<StageSessionResponse[]> {
    const searchParams = new URLSearchParams()

    if (params?.status) searchParams.append('status', params.status)
    if (params?.limit) searchParams.append('limit', params.limit.toString())
    if (params?.offset) searchParams.append('offset', params.offset.toString())

    const query = searchParams.toString()
    const url = query
      ? `${this.basePath}/stages/${stageId}/sessions?${query}`
      : `${this.basePath}/stages/${stageId}/sessions`

    const response = await authenticatedApiService.get<ApiResponse<StageSessionResponse[]>>(url, {
      headers: buildHeaders(headers),
    })
    return handleApiResponse(response)
  }

  /**
   * 获取活跃会话
   * GET /api/v1/genesis/stages/{stage_id}/active-session
   */
  async getActiveSession(
    stageId: string,
    headers?: ConversationHeaders,
  ): Promise<ActiveSessionResponse> {
    const response = await authenticatedApiService.get<ApiResponse<ActiveSessionResponse>>(
      `${this.basePath}/stages/${stageId}/active-session`,
      { headers: buildHeaders(headers) },
    )
    return handleApiResponse(response)
  }

  // ===== Stage Config Management =====

  /**
   * 获取阶段配置 JSON Schema
   * GET /api/v1/genesis/stages/{stage}/config/schema
   */
  async getStageConfigSchema(
    stage: GenesisStage,
    headers?: ConversationHeaders,
  ): Promise<Record<string, any>> {
    return authenticatedApiService.get<Record<string, any>>(
      `${this.basePath}/stages/${stage}/config/schema`,
      { headers: buildHeaders(headers) },
    )
  }

  /**
   * 获取阶段配置默认模板
   * GET /api/v1/genesis/stages/{stage}/config/template
   */
  async getStageConfigTemplate(
    stage: GenesisStage,
    headers?: ConversationHeaders,
  ): Promise<Record<string, any>> {
    return authenticatedApiService.get<Record<string, any>>(
      `${this.basePath}/stages/${stage}/config/template`,
      { headers: buildHeaders(headers) },
    )
  }

  /**
   * 更新阶段配置
   * PATCH /api/v1/genesis/stages/{stage_id}/config
   */
  async updateStageConfig(
    stageId: string,
    config: Record<string, any>,
    headers?: ConversationHeaders,
  ): Promise<StageRecordResponse> {
    const response = await authenticatedApiService.patch<ApiResponse<StageRecordResponse>>(
      `${this.basePath}/stages/${stageId}/config`,
      config,
      { headers: buildHeaders(headers) },
    )
    return handleApiResponse(response)
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
export const genesisService = new GenesisService()
