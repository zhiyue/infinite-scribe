import { apiService } from './api'
import { API_ENDPOINTS } from '@/config/api'
import type { HealthCheckResponse } from '@/types'

// 健康检查服务
export const healthService = {
  // 获取健康状态
  async check(): Promise<HealthCheckResponse> {
    return apiService.get<HealthCheckResponse>(API_ENDPOINTS.health)
  },
}