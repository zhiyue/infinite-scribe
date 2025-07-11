/**
 * 认证相关的 TanStack Query hooks
 * 用于管理服务器端状态（Server State）
 */

import { useQuery } from '@tanstack/react-query'
import { queryKeys, queryOptions } from '../lib/queryClient'
import { authService } from '../services/auth'
import { unwrapApiResponse } from '../utils/api-response'
import { useAuthStore } from './useAuth'

/**
 * 获取当前用户数据
 * 单一数据源，避免数据双写问题
 */
export function useCurrentUser() {
  const { isAuthenticated } = useAuthStore()

  return useQuery({
    queryKey: queryKeys.currentUser(),
    queryFn: async () => {
      const response = await authService.getCurrentUser()
      return unwrapApiResponse(response)
    },
    enabled: isAuthenticated, // 仅在已认证时查询
    // 使用用户数据的特定配置
    ...queryOptions.user,
  })
}

/**
 * 获取用户权限
 * 依赖于 useCurrentUser 的数据
 */
export function usePermissions() {
  const { data: user } = useCurrentUser()

  return useQuery({
    queryKey: queryKeys.permissions(),
    queryFn: async () => {
      // TODO: 实现权限获取 API
      // const response = await authService.getPermissions()
      // return unwrapApiResponse(response)
      return []
    },
    enabled: !!user?.role, // 仅在有用户角色时查询
    // 使用权限数据的特定配置
    ...queryOptions.permissions,
  })
}

/**
 * 获取用户会话列表
 */
export function useSessions() {
  const { isAuthenticated } = useAuthStore()

  return useQuery({
    queryKey: queryKeys.sessions(),
    queryFn: async () => {
      // TODO: 实现会话获取 API
      // const response = await authService.getSessions()
      // return unwrapApiResponse(response)
      return []
    },
    enabled: isAuthenticated,
    // 使用会话数据的特定配置
    ...queryOptions.sessions,
  })
}