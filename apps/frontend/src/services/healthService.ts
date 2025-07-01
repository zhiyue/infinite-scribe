import { apiService } from './api'
import { API_ENDPOINTS } from '@/config/api'

// 健康检查响应类型
export interface HealthCheckResponse {
  status: 'healthy' | 'unhealthy'
  timestamp: string
  services?: {
    database?: string
    redis?: string
    kafka?: string
  }
}

// 健康检查服务
export const healthService = {
  // 获取健康状态
  async check(): Promise<HealthCheckResponse> {
    return apiService.get<HealthCheckResponse>(API_ENDPOINTS.health)
  },
}