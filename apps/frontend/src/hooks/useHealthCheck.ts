import { useQuery } from '@tanstack/react-query'
import { healthService } from '@/services/healthService'
import type { HealthCheckResponse } from '@/types'

// 健康检查Hook
export function useHealthCheck() {
  return useQuery<HealthCheckResponse, Error>({
    queryKey: ['health'],
    queryFn: () => healthService.check(),
    // 每30秒刷新一次
    refetchInterval: 30000,
    // 保持数据新鲜
    staleTime: 20000,
    // 后台重新获取
    refetchOnWindowFocus: true,
  })
}
