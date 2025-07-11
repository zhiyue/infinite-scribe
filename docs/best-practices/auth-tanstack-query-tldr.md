# 认证状态管理与 TanStack Query 集成 - TLDR

## 核心理念

在使用 TanStack Query 的项目中，认证状态管理应该遵循**单一数据源**原则：
- **Zustand**: 仅管理认证状态标志（isAuthenticated、tokens）
- **TanStack Query**: 管理所有服务端数据（用户信息、权限等）

## 快速实现

### 1. 基础 Hook 设置

```typescript
// hooks/useAuthQuery.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuth } from './useAuth';

// 获取当前用户（单一数据源）
export function useCurrentUser() {
    const { isAuthenticated } = useAuth();
    
    return useQuery({
        queryKey: ['currentUser'],
        queryFn: () => authService.getCurrentUser(),
        enabled: isAuthenticated, // 仅在已认证时查询
        staleTime: 5 * 60 * 1000, // 5分钟内不重新请求
        gcTime: 10 * 60 * 1000,   // 10分钟垃圾回收
        retry: (failureCount, error) => {
            if (error.status === 401) return false; // 401 不重试
            return failureCount < 3;
        }
    });
}
```

### 2. 登录流程集成

```typescript
// hooks/useLogin.ts
export function useLogin() {
    const queryClient = useQueryClient();
    const { setAuthenticated } = useAuth();
    
    return useMutation({
        mutationFn: (credentials: LoginRequest) => authService.login(credentials),
        onSuccess: (data) => {
            // 1. 更新认证状态
            setAuthenticated(true);
            
            // 2. 设置用户数据到缓存
            queryClient.setQueryData(['currentUser'], data.user);
            
            // 3. 预取相关数据
            queryClient.prefetchQuery({
                queryKey: ['userPermissions'],
                queryFn: () => authService.getPermissions()
            });
        },
        onError: (error) => {
            // 清理状态
            setAuthenticated(false);
            queryClient.clear(); // 清除所有缓存
        }
    });
}
```

### 3. 更新用户资料（乐观更新）

```typescript
// hooks/useUpdateProfile.ts
export function useUpdateProfile() {
    const queryClient = useQueryClient();
    
    return useMutation({
        mutationFn: (data: UpdateProfileRequest) => authService.updateProfile(data),
        
        // 乐观更新
        onMutate: async (newData) => {
            // 取消进行中的请求
            await queryClient.cancelQueries({ queryKey: ['currentUser'] });
            
            // 保存当前数据
            const previousUser = queryClient.getQueryData(['currentUser']);
            
            // 乐观更新
            queryClient.setQueryData(['currentUser'], (old: User) => ({
                ...old,
                ...newData
            }));
            
            return { previousUser };
        },
        
        // 错误回滚
        onError: (err, newData, context) => {
            queryClient.setQueryData(['currentUser'], context.previousUser);
        },
        
        // 成功后重新验证
        onSettled: () => {
            queryClient.invalidateQueries({ queryKey: ['currentUser'] });
        }
    });
}
```

### 4. Token 刷新与 Query Client

```typescript
// api/client.ts
import { QueryClient } from '@tanstack/react-query';

// 创建 QueryClient 时配置默认行为
export const queryClient = new QueryClient({
    defaultOptions: {
        queries: {
            // Token 过期时的默认行为
            retry: (failureCount, error: any) => {
                if (error?.status === 401) {
                    // 401 错误不重试
                    return false;
                }
                return failureCount < 3;
            },
            // 窗口聚焦时不自动重新获取（认证敏感）
            refetchOnWindowFocus: false,
        },
        mutations: {
            // 突变错误时的默认行为
            onError: (error: any) => {
                if (error?.status === 401) {
                    // Token 过期，清理所有缓存
                    queryClient.clear();
                    // 跳转登录
                    window.location.href = '/login';
                }
            }
        }
    }
});

// API 拦截器中的 Token 刷新
axios.interceptors.response.use(
    response => response,
    async error => {
        if (error.response?.status === 401 && !error.config._retry) {
            error.config._retry = true;
            
            try {
                await authService.refreshToken();
                
                // 刷新成功，使所有查询失效以获取新数据
                queryClient.invalidateQueries();
                
                return axios(error.config);
            } catch (refreshError) {
                // 刷新失败，清理缓存
                queryClient.clear();
                throw refreshError;
            }
        }
        return Promise.reject(error);
    }
);
```

### 5. 登出处理

```typescript
// hooks/useLogout.ts
export function useLogout() {
    const queryClient = useQueryClient();
    const { clearAuth } = useAuth();
    
    return useMutation({
        mutationFn: () => authService.logout(),
        onSuccess: () => {
            // 1. 清理认证状态
            clearAuth();
            
            // 2. 清理所有缓存数据
            queryClient.clear();
            
            // 3. 取消所有进行中的请求
            queryClient.cancelQueries();
            
            // 4. 跳转到登录页
            window.location.href = '/login';
        }
    });
}
```

### 6. 同步 Zustand 和 TanStack Query

```typescript
// components/AuthSync.tsx
export function AuthSync() {
    const { user } = useAuth();
    const queryClient = useQueryClient();
    
    // 单向同步：Zustand → TanStack Query
    useEffect(() => {
        if (user) {
            // 设置用户数据到缓存
            queryClient.setQueryData(['currentUser'], user);
        } else {
            // 移除用户数据
            queryClient.removeQueries({ queryKey: ['currentUser'] });
        }
    }, [user, queryClient]);
    
    return null;
}
```

## 最佳实践

### 1. 查询键（Query Keys）管理

```typescript
// utils/queryKeys.ts
export const queryKeys = {
    all: ['auth'] as const,
    user: () => [...queryKeys.all, 'user'] as const,
    currentUser: () => [...queryKeys.user(), 'current'] as const,
    permissions: () => [...queryKeys.all, 'permissions'] as const,
    sessions: () => [...queryKeys.all, 'sessions'] as const,
};

// 使用
queryClient.invalidateQueries({ queryKey: queryKeys.user() }); // 使所有用户相关查询失效
```

### 2. 预取策略

```typescript
// 在路由加载前预取数据
export function usePrefetchDashboard() {
    const queryClient = useQueryClient();
    
    return useCallback(() => {
        // 批量预取
        Promise.all([
            queryClient.prefetchQuery({
                queryKey: ['dashboard-stats'],
                queryFn: fetchDashboardStats,
                staleTime: 10 * 60 * 1000, // 10分钟
            }),
            queryClient.prefetchQuery({
                queryKey: ['recent-activities'],
                queryFn: fetchRecentActivities,
            })
        ]);
    }, [queryClient]);
}
```

### 3. 依赖查询

```typescript
// 依赖于用户角色的权限查询
export function usePermissions() {
    const { data: user } = useCurrentUser();
    
    return useQuery({
        queryKey: ['permissions', user?.role],
        queryFn: () => authService.getPermissionsByRole(user.role),
        enabled: !!user?.role, // 仅在有角色时查询
    });
}
```

## 注意事项

1. **避免数据重复**
   - 不要在 Zustand 中存储可以从服务器获取的数据
   - 用户信息应该从 TanStack Query 获取，而不是 Zustand

2. **缓存策略**
   - 认证相关数据使用较短的 `staleTime`（如 5 分钟）
   - 权限数据可以使用较长的缓存时间

3. **错误处理**
   - 401 错误应该触发全局登出流程
   - 使用 `onError` 回调处理特定错误

4. **性能优化**
   - 使用 `select` 选择器避免不必要的重渲染
   - 合理使用 `enabled` 选项避免无效查询

## 示例：完整的认证流程

```typescript
// pages/Login.tsx
function LoginPage() {
    const navigate = useNavigate();
    const login = useLogin();
    const prefetchDashboard = usePrefetchDashboard();
    
    const handleLogin = async (credentials: LoginRequest) => {
        try {
            await login.mutateAsync(credentials);
            
            // 预取 Dashboard 数据
            await prefetchDashboard();
            
            // 导航到 Dashboard
            navigate('/dashboard');
        } catch (error) {
            // 错误已经在 mutation 中处理
        }
    };
    
    return (
        <form onSubmit={handleSubmit(handleLogin)}>
            {/* 表单内容 */}
        </form>
    );
}

// pages/Dashboard.tsx
function Dashboard() {
    // 从 TanStack Query 获取用户数据
    const { data: user, isLoading } = useCurrentUser();
    const { data: permissions } = usePermissions();
    
    if (isLoading) return <LoadingSpinner />;
    if (!user) return <Navigate to="/login" />;
    
    return (
        <div>
            <h1>Welcome, {user.name}!</h1>
            {/* Dashboard 内容 */}
        </div>
    );
}
```

## 总结

使用 TanStack Query 管理认证相关的服务端状态可以：
- ✅ 自动处理缓存和更新
- ✅ 提供乐观更新能力
- ✅ 统一的错误处理
- ✅ 避免状态重复
- ✅ 更好的性能和用户体验

关键是要保持 **Zustand 负责认证标志，TanStack Query 负责服务端数据** 的清晰分工。