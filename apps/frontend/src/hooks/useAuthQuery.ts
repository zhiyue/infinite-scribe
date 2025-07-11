/**
 * 认证相关的 TanStack Query hooks
 * 用于管理服务器端状态（Server State）
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useAuth } from './useAuth'
import { queryKeys } from '../lib/queryClient'
import { authService } from '../services/auth'
import type { User, UpdateProfileRequest } from '../types/auth'

/**
 * 获取当前用户数据
 * 单一数据源，避免数据双写问题
 */
export function useCurrentUser() {
  const { isAuthenticated } = useAuth()
  
  return useQuery({
    queryKey: queryKeys.currentUser(),
    queryFn: () => authService.getCurrentUser(),
    enabled: isAuthenticated, // 仅在已认证时查询
    staleTime: 5 * 60 * 1000, // 5分钟内认为数据是新鲜的
    gcTime: 10 * 60 * 1000,   // 10分钟垃圾回收（v5 中 cacheTime 改为 gcTime）
    retry: (failureCount, error: any) => {
      // 401 错误不重试，其他错误重试最多 3 次
      if (error?.status === 401 || error?.status_code === 401) {
        return false
      }
      return failureCount < 3
    },
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
    queryFn: () => authService.getPermissions?.() || Promise.resolve([]),
    enabled: !!user?.role, // 仅在有用户角色时查询
    staleTime: 10 * 60 * 1000, // 权限数据缓存更久（10分钟）
  })
}

/**
 * 获取用户会话列表
 */
export function useSessions() {
  const { isAuthenticated } = useAuth()
  
  return useQuery({
    queryKey: queryKeys.sessions(),
    queryFn: () => authService.getSessions?.() || Promise.resolve([]),
    enabled: isAuthenticated,
    staleTime: 2 * 60 * 1000, // 2分钟刷新一次会话列表
  })
}