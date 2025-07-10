/**
 * Authentication related type definitions
 */

// User interface - 匹配后端 UserResponse
export interface User {
    id: number;                    // 后端返回 number 类型
    username: string;
    email: string;
    first_name?: string;
    last_name?: string;
    bio?: string;
    is_active: boolean;
    is_verified: boolean;
    is_superuser: boolean;
    created_at: string;            // ISO datetime string
    updated_at: string;            // ISO datetime string
    email_verified_at?: string;    // ISO datetime string
    last_login_at?: string;        // ISO datetime string
}

// Login request/response
export interface LoginRequest {
    email: string;
    password: string;
}

// 登录响应 - 匹配后端 AuthResponse
export interface LoginResponse {
    success: boolean;              // 后端总是返回 success 字段
    access_token: string;
    refresh_token: string;
    user: User;
    message?: string;              // 可选消息字段
}

// Register request/response
export interface RegisterRequest {
    email: string;
    username: string;
    password: string;
    first_name?: string;
    last_name?: string;
}

// 注册响应 - 匹配后端 RegisterResponse
export interface RegisterResponse {
    success: boolean;              // 后端总是返回 success 字段
    user: User;
    message: string;
}

// 令牌刷新响应 - 匹配后端 TokenResponse
export interface TokenResponse {
    success: boolean;              // 后端总是返回 success 字段
    access_token: string;
    refresh_token: string;
}

// Password related
export interface ChangePasswordRequest {
    current_password: string;
    new_password: string;
}

export interface ForgotPasswordRequest {
    email: string;
}

export interface ResetPasswordRequest {
    token: string;
    new_password: string;
}

// Profile update
export interface UpdateProfileRequest {
    first_name?: string;
    last_name?: string;
    bio?: string;
}

// Email verification
export interface ResendVerificationRequest {
    email: string;
}

// Auth state
export interface AuthState {
    user: User | null;
    isAuthenticated: boolean;
    isLoading: boolean;
    error: string | null;
}

// API 错误响应 - 匹配后端错误格式
export interface ApiError {
    detail: string;                // FastAPI 标准错误格式
    status_code?: number;
    retry_after?: number;
}

// 认证错误响应 (带扩展信息)
export interface AuthError {
    message: string;
    error: string;                 // 向后兼容
    remaining_attempts?: number;   // 剩余尝试次数
    locked_until?: string;         // 锁定到期时间 (ISO datetime)
}

// 通用消息响应
export interface MessageResponse {
    success: boolean;
    message: string;
}

// 通用错误响应
export interface ErrorResponse {
    success: boolean;              // 默认 false
    error: string;
    details?: Record<string, any>; // 可选的详细信息
}

// Auth context
export interface AuthContextType {
    user: User | null;
    isAuthenticated: boolean;
    isLoading: boolean;
    error: string | null;
    login: (credentials: LoginRequest) => Promise<void>;
    register: (data: RegisterRequest) => Promise<void>;
    logout: () => Promise<void>;
    refreshToken: () => Promise<void>;
    updateProfile: (data: UpdateProfileRequest) => Promise<void>;
    changePassword: (data: ChangePasswordRequest) => Promise<void>;
    forgotPassword: (data: ForgotPasswordRequest) => Promise<void>;
    resetPassword: (data: ResetPasswordRequest) => Promise<void>;
    resendVerification: (data: ResendVerificationRequest) => Promise<void>;
    clearError: () => void;
}

// Form validation schemas (for use with react-hook-form + zod)
export interface LoginFormData {
    email: string;
    password: string;
}

export interface RegisterFormData {
    email: string;
    username: string;
    password: string;
    confirmPassword: string;
    first_name?: string;
    last_name?: string;
}

export interface ForgotPasswordFormData {
    email: string;
}

export interface ResetPasswordFormData {
    password: string;
    confirmPassword: string;
}

export interface ChangePasswordFormData {
    currentPassword: string;
    newPassword: string;
    confirmPassword: string;
}

export interface UpdateProfileFormData {
    first_name: string;
    last_name: string;
    bio: string;
}