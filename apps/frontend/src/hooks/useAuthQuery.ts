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

  // 提取用户角色，只有角色变化时才会触发重新查询
  const userRole = user?.role

  return useQuery({
    queryKey: [...queryKeys.permissions(), userRole], // 将角色作为查询键的一部分
    queryFn: async () => {
      // 如果 authService.getPermissions 已实现，使用它
      if (authService.getPermissions) {
        try {
          const response = await authService.getPermissions()
          return unwrapApiResponse(response)
        } catch {
          // 如果接口未实现，返回空数组
          return []
        }
      }
      return []
    },
    enabled: !!userRole, // 仅在有用户角色时查询
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
      // 如果后端还没有会话管理接口，返回空数组
      if (!authService.getSessions) {
        return []
      }
      // 使用类型断言确保函数调用的类型安全
      const response = await (authService.getSessions as any)?.()
      return unwrapApiResponse(response)
    },
    enabled: isAuthenticated,
    placeholderData: [], // 使用 placeholderData 而不是 initialData，避免 undefined 闪烁
    // 使用会话数据的特定配置
    ...queryOptions.sessions,
  })
}
