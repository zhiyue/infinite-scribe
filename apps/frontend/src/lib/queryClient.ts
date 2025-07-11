import { QueryClient } from '@tanstack/react-query'

// 重试延迟策略
function getRetryDelay(retryAttempt: number): number {
  // 指数退避：1秒、2秒、4秒...
  return Math.min(1000 * 2 ** retryAttempt, 30000)
}

// 判断是否应该重试的错误
function shouldRetryError(error: any): boolean {
  // 不重试的情况
  if (
    error?.status === 401 || // 未授权
    error?.status === 403 || // 禁止访问
    error?.status === 404 || // 资源不存在
    error?.status === 422 // 验证错误
  ) {
    return false
  }

  // 重试的情况
  if (
    error?.status === 408 || // 请求超时
    error?.status === 429 || // 请求过多（限流）
    error?.status === 500 || // 服务器内部错误
    error?.status === 502 || // 网关错误
    error?.status === 503 || // 服务不可用
    error?.status === 504 || // 网关超时
    error?.code === 'ECONNABORTED' || // 连接中断
    error?.code === 'ENOTFOUND' || // DNS 解析失败
    error?.code === 'ETIMEDOUT' || // 超时
    !error?.status // 网络错误，没有状态码
  ) {
    return true
  }

  return false
}

// 创建全局 QueryClient 实例
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // 智能重试策略
      retry: (failureCount, error: any) => {
        // 检查是否应该重试
        if (!shouldRetryError(error)) {
          return false
        }

        // 对于限流错误，检查 Retry-After 头
        if (error?.status === 429 && error?.headers?.['retry-after']) {
          const retryAfter = parseInt(error.headers['retry-after'], 10)
          if (!isNaN(retryAfter)) {
            // 等待指定的时间后重试
            return new Promise((resolve) => {
              setTimeout(() => resolve(true), retryAfter * 1000)
            })
          }
        }

        // 普通错误：最多重试 3 次
        return failureCount < 3
      },
      // 重试延迟策略
      retryDelay: getRetryDelay,
      // 窗口聚焦时不自动重新获取（认证敏感）
      refetchOnWindowFocus: false,
      // 数据被认为是新鲜的时间（在此期间不会重新获取）
      staleTime: 5 * 60 * 1000, // 5分钟
      // 数据在缓存中保留的时间（v5中 cacheTime 改为 gcTime）
      gcTime: 10 * 60 * 1000, // 10分钟垃圾回收
    },
    mutations: {
      // mutations 有选择地重试
      retry: (failureCount, error: any) => {
        // 对于幂等操作（如 PUT、DELETE），可以重试网络错误
        if (!error?.status && failureCount < 2) {
          // 只有网络错误才重试，最多 2 次
          return true
        }
        // 其他错误不重试
        return false
      },
      retryDelay: getRetryDelay,
      // 突变错误时的默认行为
      onError: (error: any) => {
        if (error?.status === 401) {
          // Token 过期，清理所有缓存
          queryClient.clear()
          // 跳转登录
          window.location.href = '/login'
        }
      },
    },
  },
})

// 资源特定的查询配置
export const queryOptions = {
  // 用户数据配置
  user: {
    staleTime: 1000 * 60 * 10, // 用户数据10分钟内认为是新鲜的
    gcTime: 1000 * 60 * 30, // 缓存保留30分钟
    retry: 3, // 用户数据重要，多重试几次
  },
  // 项目列表配置
  projects: {
    staleTime: 1000 * 60 * 2, // 项目列表2分钟内认为是新鲜的
    gcTime: 1000 * 60 * 10, // 缓存保留10分钟
    retry: 2, // 列表数据可以少重试
  },
  // 健康检查配置
  health: {
    staleTime: 1000 * 30, // 健康检查30秒内认为是新鲜的
    gcTime: 1000 * 60, // 缓存保留1分钟
    retry: 1, // 健康检查快速失败
    retryDelay: 500, // 快速重试
  },
  // 文档内容配置
  documents: {
    staleTime: 1000 * 60 * 15, // 文档内容15分钟内认为是新鲜的
    gcTime: 1000 * 60 * 60, // 缓存保留1小时
    retry: 3, // 文档重要，多重试
  },
  // 权限配置
  permissions: {
    staleTime: 1000 * 60 * 30, // 权限30分钟内认为是新鲜的
    gcTime: 1000 * 60 * 120, // 缓存保留2小时
    retry: 2,
  },
  // 会话列表配置
  sessions: {
    staleTime: 1000 * 60 * 5, // 会话5分钟内认为是新鲜的
    gcTime: 1000 * 60 * 15, // 缓存保留15分钟
    retry: 1, // 会话列表不太重要
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
