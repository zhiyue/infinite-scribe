# 认证状态管理最佳实践 V2

## 核心原则

### 1. 职责分离
- **全局状态（Zustand/useAuth）**：管理用户会话、认证状态、用户信息
- **本地状态（组件）**：管理表单状态、UI 状态、临时错误、操作加载状态

### 2. 错误处理策略
- **全局错误**：影响整个应用的错误（如 token 过期、未授权）
- **本地错误**：特定操作的错误（如表单验证、单次 API 调用失败）

### 3. Loading 状态管理
- **全局 isLoading**：仅用于影响整个应用的操作（如初始化认证、刷新 token）
- **本地 loading**：用于不影响页面结构的操作（如修改密码、更新资料）

## 推荐方案

### 方案 A：使用 useAuth Hook + 改进的错误处理（推荐）

#### 1. 改进 useAuth Hook
```typescript
// hooks/useAuth.ts
interface AuthStore extends AuthState {
    // 不抛出错误，返回结果对象
    changePassword: (data: ChangePasswordRequest) => Promise<{
        success: boolean;
        error?: string;
    }>;
}

// 实现 - 注意不设置全局 isLoading
changePassword: async (data) => {
    try {
        // 不设置全局 isLoading，避免影响 RequireAuth
        await authService.changePassword(data);
        return { success: true };
    } catch (error: any) {
        return { 
            success: false, 
            error: error?.detail || 'Failed to change password' 
        };
    }
}

// 仅在影响全局认证状态的操作中设置 isLoading
login: async (credentials) => {
    set({ isLoading: true, error: null }); // 登录时设置全局 loading
    try {
        const response = await authService.login(credentials);
        set({
            user: response.user,
            isAuthenticated: true,
            isLoading: false,
            error: null,
        });
        return { success: true, data: response };
    } catch (error) {
        const apiError = error as ApiError;
        set({
            user: null,
            isAuthenticated: false,
            isLoading: false,
            error: apiError.detail,
        });
        return { success: false, error: apiError.detail };
    }
}
```

#### 2. 组件使用方式
```typescript
const ChangePasswordPage = () => {
    const { changePassword } = useAuth();
    const [isLoading, setIsLoading] = useState(false); // 本地 loading 状态
    const [error, setError] = useState<string | null>(null);
    
    const onSubmit = async (data: ChangePasswordRequest) => {
        setError(null);
        setIsLoading(true); // 设置本地 loading
        
        const result = await changePassword(data);
        setIsLoading(false);
        
        if (result.success) {
            // 处理成功
            navigate('/dashboard');
        } else {
            // 处理错误
            setError(result.error);
        }
    };
};
```

**优点**：
- 清晰的错误处理流程
- 不会因为 loading 状态导致页面重新挂载
- 避免了 try-catch 嵌套
- 没有状态更新竞争

## Loading 状态使用指南

### 使用全局 isLoading 的场景
1. **用户登录** - 需要初始化整个应用状态
2. **用户登出** - 需要清理整个应用状态
3. **Token 刷新** - 可能影响所有 API 调用
4. **获取当前用户** - 初始化应用时需要

### 使用本地 loading 的场景
1. **修改密码** - 不影响认证状态
2. **更新个人资料** - 不影响认证状态
3. **重发验证邮件** - 不影响认证状态
4. **其他表单提交** - 局部操作

## RequireAuth 组件优化

如果需要在 RequireAuth 中显示加载状态，应该只在初始化时显示：

```typescript
const RequireAuth: React.FC<RequireAuthProps> = ({ children }) => {
    const { user, isAuthenticated, isLoading } = useAuth();
    const location = useLocation();
    const [isInitializing, setIsInitializing] = useState(true);

    useEffect(() => {
        // 只在组件首次挂载时考虑 isLoading
        if (!isLoading) {
            setIsInitializing(false);
        }
    }, [isLoading]);

    // 只在初始化时显示加载状态
    if (isInitializing && isLoading) {
        return <LoadingSpinner />;
    }

    if (!isAuthenticated || !user) {
        return <Navigate to="/login" state={{ from: location }} replace />;
    }

    return <>{children}</>;
};
```

## 总结

最佳实践是**使用改进的 useAuth Hook**，但要：
1. 返回结果对象而不是抛出异常 ✅
2. 让组件管理自己的错误状态 ✅
3. 保持全局状态只用于真正的全局数据（用户信息、认证状态）✅
4. **区分全局 loading 和本地 loading 状态** ⭐（新增）
5. 为复杂的业务逻辑创建专门的 hooks