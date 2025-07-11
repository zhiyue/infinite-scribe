# TanStack Query 使用规范

## 概述

本文档提供了在 Infinite Scribe 项目中使用 TanStack Query 的最佳实践和规范。我们使用 TanStack Query v5 来管理所有服务器状态（Server State），而客户端状态（Client State）由 Zustand 管理。

## 核心原则

### 1. 单一数据源（Single Source of Truth）
- **服务器数据**：完全由 TanStack Query 管理
- **客户端状态**：由 Zustand 管理（如 isAuthenticated）
- **避免双写**：同一数据永远不要同时存储在两个地方

### 2. 职责分离
```typescript
// ❌ 错误：在 Zustand 中存储用户数据
const useAuthStore = create((set) => ({
  user: null, // 不要这样做
  isAuthenticated: false,
}))

// ✅ 正确：Zustand 只管理认证状态
const useAuthStore = create((set) => ({
  isAuthenticated: false, // 只存储认证标志
}))

// ✅ 正确：用户数据由 TanStack Query 管理
const { data: user } = useCurrentUser()
```

## 查询键（Query Keys）管理

### 1. 使用工厂函数模式
```typescript
// lib/queryClient.ts
export const queryKeys = {
  // 认证相关
  all: ['auth'] as const,
  user: () => [...queryKeys.all, 'user'] as const,
  currentUser: () => [...queryKeys.user(), 'current'] as const,
  permissions: () => [...queryKeys.all, 'permissions'] as const,
  
  // 项目相关
  projects: {
    all: ['projects'] as const,
    list: (filters?: Record<string, any>) => 
      [...queryKeys.projects.all, 'list', filters] as const,
    detail: (id: string) => 
      [...queryKeys.projects.all, 'detail', id] as const,
  },
}
```

### 2. 使用查询键的场景
```typescript
// 获取数据
const { data } = useQuery({
  queryKey: queryKeys.currentUser(),
  queryFn: fetchCurrentUser,
})

// 使缓存失效
queryClient.invalidateQueries({ 
  queryKey: queryKeys.user() // 使所有用户相关查询失效
})

// 设置缓存数据
queryClient.setQueryData(
  queryKeys.currentUser(), 
  updatedUser
)
```

## 统一的响应格式处理

### 1. API 响应包装器
```typescript
// utils/api-response.ts
import { wrapApiResponse, unwrapApiResponse } from '../utils/api-response'

// 在 service 层包装响应
async getCurrentUser(): Promise<ApiSuccessResponse<User>> {
  const response = await api.get('/me')
  return wrapApiResponse<User>(response.data, '获取用户成功')
}

// 在 hooks 中解包数据
const { data: user } = useQuery({
  queryKey: queryKeys.currentUser(),
  queryFn: async () => {
    const response = await authService.getCurrentUser()
    return unwrapApiResponse(response)
  },
})
```

## 资源特定配置

### 1. 配置不同资源的缓存策略
```typescript
// lib/queryClient.ts
export const queryOptions = {
  // 用户数据 - 较长缓存时间
  user: {
    staleTime: 1000 * 60 * 10,  // 10分钟
    gcTime: 1000 * 60 * 30,     // 30分钟
    retry: 3,
  },
  
  // 实时数据 - 较短缓存时间
  sessions: {
    staleTime: 1000 * 60 * 5,   // 5分钟
    gcTime: 1000 * 60 * 15,     // 15分钟
    retry: 1,
  },
}

// 使用配置
const { data } = useQuery({
  queryKey: queryKeys.currentUser(),
  queryFn: fetchUser,
  ...queryOptions.user, // 应用用户数据配置
})
```

## 查询 Hooks 最佳实践

### 1. 创建领域特定的 hooks
```typescript
// hooks/useAuthQuery.ts
export function useCurrentUser() {
  const { isAuthenticated } = useAuthStore()
  
  return useQuery({
    queryKey: queryKeys.currentUser(),
    queryFn: async () => {
      const response = await authService.getCurrentUser()
      return unwrapApiResponse(response)
    },
    enabled: isAuthenticated, // 条件查询
    ...queryOptions.user,
  })
}
```

### 2. 依赖查询
```typescript
export function usePermissions() {
  const { data: user } = useCurrentUser()
  
  return useQuery({
    queryKey: queryKeys.permissions(),
    queryFn: fetchPermissions,
    enabled: !!user?.role, // 只有用户有角色时才查询
    ...queryOptions.permissions,
  })
}
```

## Mutation Hooks 最佳实践

### 1. 基本 Mutation
```typescript
export function useLogin() {
  const queryClient = useQueryClient()
  const { setAuthenticated } = useAuthStore()
  
  return useMutation({
    mutationFn: async (credentials: LoginRequest) => {
      const response = await authService.login(credentials)
      return unwrapApiResponse(response)
    },
    onSuccess: (data) => {
      // 更新认证状态
      setAuthenticated(true)
      // 设置用户缓存
      queryClient.setQueryData(queryKeys.currentUser(), data.user)
    },
    onError: () => {
      setAuthenticated(false)
      queryClient.clear()
    },
  })
}
```

### 2. 乐观更新
```typescript
export function useUpdateProfile() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: updateProfile,
    
    // 乐观更新
    onMutate: async (newData) => {
      await queryClient.cancelQueries({ queryKey: queryKeys.currentUser() })
      const previousUser = queryClient.getQueryData(queryKeys.currentUser())
      
      // 立即更新 UI
      queryClient.setQueryData(queryKeys.currentUser(), {
        ...previousUser,
        ...newData,
      })
      
      return { previousUser }
    },
    
    // 错误回滚
    onError: (err, newData, context) => {
      queryClient.setQueryData(queryKeys.currentUser(), context?.previousUser)
    },
    
    // 成功后同步
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.currentUser() })
    },
  })
}
```

## 错误处理

### 1. 全局错误处理
```typescript
// lib/queryClient.ts
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: (failureCount, error) => {
        // 401 错误不重试
        if (error?.status === 401) return false
        // 网络错误重试
        if (!error?.status) return failureCount < 3
        // 5xx 错误重试
        if (error?.status >= 500) return failureCount < 2
        return false
      },
    },
    mutations: {
      onError: (error: any) => {
        if (error?.status === 401) {
          queryClient.clear()
          window.location.href = '/login'
        }
      },
    },
  },
})
```

### 2. 组件级错误处理
```typescript
function Profile() {
  const { data, error, isLoading } = useCurrentUser()
  
  if (error) {
    return <ErrorMessage error={error} />
  }
  
  if (isLoading) {
    return <LoadingSpinner />
  }
  
  return <ProfileView user={data} />
}
```

## 预取数据

### 1. 路由预取
```typescript
// 在用户即将访问某个页面前预取数据
export function usePrefetchDashboard() {
  const queryClient = useQueryClient()
  
  return useCallback(() => {
    queryClient.prefetchQuery({
      queryKey: queryKeys.dashboardStats(),
      queryFn: fetchDashboardStats,
      staleTime: 10 * 60 * 1000,
    })
  }, [queryClient])
}
```

### 2. 登录后预取
```typescript
const login = useLogin()

const handleLogin = async (credentials) => {
  await login.mutateAsync(credentials)
  
  // 预取用户常用数据
  await Promise.all([
    queryClient.prefetchQuery({
      queryKey: queryKeys.permissions(),
      queryFn: fetchPermissions,
    }),
    queryClient.prefetchQuery({
      queryKey: queryKeys.projects.list(),
      queryFn: fetchProjects,
    }),
  ])
  
  navigate('/dashboard')
}
```

## 缓存管理

### 1. 手动更新缓存
```typescript
// 直接设置缓存数据
queryClient.setQueryData(queryKeys.currentUser(), newUser)

// 使缓存失效（触发重新获取）
queryClient.invalidateQueries({ queryKey: queryKeys.user() })

// 移除缓存
queryClient.removeQueries({ queryKey: queryKeys.sessions() })

// 清空所有缓存
queryClient.clear()
```

### 2. 缓存同步
```typescript
// 登出时清理所有缓存
const logout = useLogout()

logout.mutate(undefined, {
  onSuccess: () => {
    queryClient.clear() // 清空所有缓存
    navigate('/login')
  },
})
```

## 性能优化

### 1. 避免过度查询
```typescript
// ❌ 错误：每个组件都查询
function Header() {
  const { data: user } = useCurrentUser() // 查询 1
}

function Sidebar() {
  const { data: user } = useCurrentUser() // 查询 2
}

// ✅ 正确：利用缓存
// 多个组件使用同一个 hook，TanStack Query 会自动去重
```

### 2. 批量操作
```typescript
// 批量使缓存失效
queryClient.invalidateQueries({
  predicate: (query) => 
    query.queryKey[0] === 'projects' || 
    query.queryKey[0] === 'tasks',
})
```

## 测试

### 1. 模拟 QueryClient
```typescript
// test-utils.ts
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

export function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false, // 测试时禁用重试
        cacheTime: 0, // 测试时禁用缓存
      },
    },
  })
}

export function TestWrapper({ children }) {
  const queryClient = createTestQueryClient()
  return (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  )
}
```

### 2. 测试查询 hooks
```typescript
import { renderHook, waitFor } from '@testing-library/react'

test('useCurrentUser returns user data', async () => {
  const { result } = renderHook(() => useCurrentUser(), {
    wrapper: TestWrapper,
  })
  
  await waitFor(() => {
    expect(result.current.isSuccess).toBe(true)
  })
  
  expect(result.current.data).toEqual(mockUser)
})
```

## 常见问题

### 1. 何时使用 TanStack Query vs Zustand？
- **TanStack Query**：所有来自服务器的数据
- **Zustand**：纯客户端状态（UI 状态、表单草稿等）

### 2. 如何处理 Token 刷新？
```typescript
// 在 axios 拦截器中处理
axios.interceptors.response.use(
  response => response,
  async error => {
    if (error.response?.status === 401 && !error.config._retry) {
      error.config._retry = true
      await authService.refreshTokens()
      queryClient.invalidateQueries() // 刷新所有查询
      return axios(error.config)
    }
    return Promise.reject(error)
  }
)
```

### 3. 如何调试缓存？
```typescript
// 开发环境使用 React Query DevTools
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      {/* 你的应用 */}
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  )
}
```

## 迁移检查清单

从旧模式迁移到 TanStack Query 时，请确保：

- [ ] 移除 Zustand 中的所有服务器数据
- [ ] 创建对应的查询 hooks
- [ ] 更新所有组件使用新 hooks
- [ ] 配置合适的缓存策略
- [ ] 实现错误处理
- [ ] 添加乐观更新（如需要）
- [ ] 更新测试用例
- [ ] 验证数据同步正确性