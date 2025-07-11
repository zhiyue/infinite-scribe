import { QueryClient } from '@tanstack/react-query'

// 创建全局 QueryClient 实例
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Token 过期时的默认行为
      retry: (failureCount, error: any) => {
        if (error?.status === 401) {
          // 401 错误不重试
          return false
        }
        return failureCount < 3
      },
      // 窗口聚焦时不自动重新获取（认证敏感）
      refetchOnWindowFocus: false,
      // 数据被认为是新鲜的时间（在此期间不会重新获取）
      staleTime: 5 * 60 * 1000, // 5分钟
      // 数据在缓存中保留的时间（v5中 cacheTime 改为 gcTime）
      gcTime: 10 * 60 * 1000,    // 10分钟垃圾回收
    },
    mutations: {
      // mutations 不重试
      retry: 0,
      // 突变错误时的默认行为
      onError: (error: any) => {
        if (error?.status === 401) {
          // Token 过期，清理所有缓存
          queryClient.clear()
          // 跳转登录
          window.location.href = '/login'
        }
      }
    },
  },
})

// 资源特定的查询配置
export const queryOptions = {
  // 用户数据配置
  user: {
    staleTime: 1000 * 60 * 10, // 用户数据10分钟内认为是新鲜的
    cacheTime: 1000 * 60 * 30, // 缓存保留30分钟
  },
  // 项目列表配置
  projects: {
    staleTime: 1000 * 60 * 2, // 项目列表2分钟内认为是新鲜的
    cacheTime: 1000 * 60 * 10, // 缓存保留10分钟
  },
  // 健康检查配置
  health: {
    staleTime: 1000 * 30, // 健康检查30秒内认为是新鲜的
    cacheTime: 1000 * 60, // 缓存保留1分钟
  },
  // 文档内容配置
  documents: {
    staleTime: 1000 * 60 * 15, // 文档内容15分钟内认为是新鲜的
    cacheTime: 1000 * 60 * 60, // 缓存保留1小时
  },
}

// 查询键管理
export const queryKeys = {
  all: ['auth'] as const,
  user: () => [...queryKeys.all, 'user'] as const,
  currentUser: () => [...queryKeys.user(), 'current'] as const,
  permissions: () => [...queryKeys.all, 'permissions'] as const,
  sessions: () => [...queryKeys.all, 'sessions'] as const,
  // 项目相关
  projects: {
    all: ['projects'] as const,
    list: (filters?: Record<string, any>) => [...queryKeys.projects.all, 'list', filters] as const,
    detail: (id: string) => [...queryKeys.projects.all, 'detail', id] as const,
  },
  // 健康检查
  health: {
    all: ['health'] as const,
    check: () => [...queryKeys.health.all, 'check'] as const,
  },
} as const