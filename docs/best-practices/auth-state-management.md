# 认证状态管理最佳实践

## 核心原则

### 1. 职责分离
- **全局状态（Zustand/useAuth）**：管理用户会话、认证状态、用户信息
- **本地状态（组件）**：管理表单状态、UI 状态、临时错误

### 2. 错误处理策略
- **全局错误**：影响整个应用的错误（如 token 过期、未授权）
- **本地错误**：特定操作的错误（如表单验证、单次 API 调用失败）

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

// 实现
changePassword: async (data) => {
    try {
        set({ isLoading: true });
        await authService.changePassword(data);
        set({ isLoading: false });
        return { success: true };
    } catch (error: any) {
        set({ isLoading: false });
        // 不设置全局 error，让组件自行处理
        return { 
            success: false, 
            error: error?.detail || 'Failed to change password' 
        };
    }
}
```

#### 2. 组件使用方式
```typescript
const ChangePasswordPage = () => {
    const { changePassword, isLoading } = useAuth();
    const [error, setError] = useState<string | null>(null);
    
    const onSubmit = async (data: ChangePasswordRequest) => {
        setError(null);
        
        const result = await changePassword(data);
        
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
- 利用 useAuth 提供的 loading 状态
- 避免了 try-catch 嵌套
- 没有状态更新竞争

### 方案 B：区分操作类型

#### 1. 会话相关操作使用 useAuth
```typescript
// 登录、登出、刷新 token 等影响全局认证状态的操作
const { login, logout, user } = useAuth();
```

#### 2. 用户操作直接使用 Service
```typescript
// 修改密码、更新资料等不影响认证状态的操作
import { authService } from '@/services/auth';

const handleChangePassword = async (data) => {
    try {
        await authService.changePassword(data);
        // 成功处理
    } catch (error) {
        // 错误处理
    }
};
```

### 方案 C：自定义 Hook 封装

```typescript
// hooks/useChangePassword.ts
export const useChangePassword = () => {
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    
    const changePassword = async (data: ChangePasswordRequest) => {
        try {
            setIsLoading(true);
            setError(null);
            await authService.changePassword(data);
            return { success: true };
        } catch (err: any) {
            const errorMsg = err?.detail || 'Failed to change password';
            setError(errorMsg);
            return { success: false, error: errorMsg };
        } finally {
            setIsLoading(false);
        }
    };
    
    return { changePassword, isLoading, error };
};

// 使用
const ChangePasswordPage = () => {
    const { changePassword, isLoading, error } = useChangePassword();
    // ...
};
```

## 最终推荐

### 🏆 最佳实践：方案 A（改进的 useAuth Hook）

**理由**：
1. **一致性**：所有认证相关操作通过同一个 hook
2. **可维护性**：集中管理认证逻辑
3. **类型安全**：TypeScript 友好的返回值
4. **避免副作用**：不抛出异常，返回结果对象
5. **灵活性**：组件可以自行决定如何处理错误

### 实施步骤

1. **第一步**：修改 useAuth hook 的方法签名
   - 从抛出错误改为返回结果对象
   - 移除不必要的全局错误状态设置

2. **第二步**：更新所有使用这些方法的组件
   - 从 try-catch 改为检查返回值
   - 使用本地状态管理错误

3. **第三步**：为复杂操作创建专门的 hooks
   - 如 usePasswordReset、useEmailVerification 等
   - 封装特定的业务逻辑和状态管理

## 代码示例

### 改进后的 useAuth Hook
```typescript
export const useAuthStore = create<AuthStore>()(
    persist(
        (set, get) => ({
            // ... 其他状态
            
            changePassword: async (data) => {
                set({ isLoading: true });
                try {
                    await authService.changePassword(data);
                    set({ isLoading: false });
                    return { success: true };
                } catch (error: any) {
                    set({ isLoading: false });
                    return { 
                        success: false, 
                        error: error?.detail || error?.message || 'Failed to change password'
                    };
                }
            },
            
            // 类似地改进其他方法...
        }),
        // ... persist 配置
    )
);
```

### 使用示例
```typescript
const ChangePasswordPage = () => {
    const { changePassword, isLoading } = useAuth();
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState(false);
    
    const onSubmit = async (data: ChangePasswordRequest) => {
        setError(null);
        setSuccess(false);
        
        const result = await changePassword(data);
        
        if (result.success) {
            setSuccess(true);
            setTimeout(() => navigate('/dashboard'), 2000);
        } else {
            setError(result.error || 'An error occurred');
        }
    };
    
    return (
        <form onSubmit={handleSubmit(onSubmit)}>
            {error && <ErrorAlert message={error} />}
            {success && <SuccessAlert message="Password changed successfully!" />}
            {/* 表单字段 */}
            <Button type="submit" disabled={isLoading}>
                {isLoading ? 'Changing...' : 'Change Password'}
            </Button>
        </form>
    );
};
```

## 总结

最佳实践是**使用改进的 useAuth Hook**，但要：
1. 返回结果对象而不是抛出异常
2. 让组件管理自己的错误状态
3. 保持全局状态只用于真正的全局数据（用户信息、认证状态）
4. 为复杂的业务逻辑创建专门的 hooks