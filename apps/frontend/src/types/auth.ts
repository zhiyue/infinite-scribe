/**
 * Authentication related type definitions
 */

// User interface
export interface User {
    id: string;
    email: string;
    username: string;
    full_name?: string;
    is_verified: boolean;
    is_active: boolean;
    created_at: string;
    updated_at: string;
}

// Login request/response
export interface LoginRequest {
    email: string;
    password: string;
}

export interface LoginResponse {
    access_token: string;
    refresh_token: string;
    token_type: string;
    expires_in: number;
    user: User;
}

// Register request/response
export interface RegisterRequest {
    email: string;
    username: string;
    password: string;
    full_name?: string;
}

export interface RegisterResponse {
    user: User;
    message: string;
}

// Token response
export interface TokenResponse {
    access_token: string;
    refresh_token: string;
    token_type: string;
    expires_in: number;
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

export interface ValidatePasswordRequest {
    password: string;
}

export interface PasswordValidationResponse {
    is_valid: boolean;
    score: number;
    feedback: string[];
}

// Profile update
export interface UpdateProfileRequest {
    username?: string;
    full_name?: string;
    email?: string;
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

// API Error response
export interface ApiError {
    detail: string;
    status_code?: number;
    retry_after?: number;
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
    full_name?: string;
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
    username: string;
    full_name: string;
    email: string;
}