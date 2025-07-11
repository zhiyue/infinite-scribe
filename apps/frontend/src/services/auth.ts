/**
 * Authentication service with JWT token management
 */

import axios, { type AxiosInstance, type AxiosResponse } from 'axios';
import type {
    ApiError,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    RegisterResponse,
    ResendVerificationRequest,
    ResetPasswordRequest,
    TokenResponse,
    UpdateProfileRequest,
    User,
} from '../types/auth';
import { wrapApiResponse, type ApiSuccessResponse } from '../utils/api-response';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

class AuthService {
    private api: AxiosInstance;
    private accessToken: string | null = null;
    private refreshToken: string | null = null;
    private refreshPromise: Promise<void> | null = null;
    private readonly ACCESS_TOKEN_KEY = 'access_token';

    constructor() {
        this.api = axios.create({
            baseURL: `${API_BASE_URL}/api/v1/auth`,
            headers: {
                'Content-Type': 'application/json',
            },
            withCredentials: true, // For httpOnly cookies
        });

        // Initialize tokens from storage
        this.initializeTokens();
        this.setupInterceptors();
    }

    private initializeTokens() {
        // Load access token from localStorage on initialization
        this.accessToken = localStorage.getItem(this.ACCESS_TOKEN_KEY);
        // Refresh token is handled via httpOnly cookies
    }

    private setupInterceptors() {
        // Request interceptor - add authorization header
        this.api.interceptors.request.use(
            (config) => {
                if (this.accessToken) {
                    config.headers.Authorization = `Bearer ${this.accessToken}`;
                }
                return config;
            },
            (error) => Promise.reject(error)
        );

        // Response interceptor - handle 401 errors and token refresh
        this.api.interceptors.response.use(
            (response) => response,
            async (error) => {
                const originalRequest = error.config;

                // Don't try to refresh token for login/register/refresh endpoints
                const isAuthEndpoint = originalRequest.url?.includes('/login') || 
                                     originalRequest.url?.includes('/register') ||
                                     originalRequest.url?.includes('/refresh');
                
                if (error.response?.status === 401 && !originalRequest._retry && !isAuthEndpoint) {
                    originalRequest._retry = true;

                    try {
                        await this.refreshAccessToken();
                        // Retry the original request with new token
                        originalRequest.headers.Authorization = `Bearer ${this.accessToken}`;
                        return this.api(originalRequest);
                    } catch (refreshError) {
                        // Refresh failed, redirect to login
                        this.clearTokens();
                        window.location.href = '/login';
                        return Promise.reject(refreshError);
                    }
                }

                return Promise.reject(error);
            }
        );
    }

    private async refreshAccessToken(): Promise<void> {
        // Prevent concurrent refresh requests
        if (this.refreshPromise) {
            return this.refreshPromise;
        }

        this.refreshPromise = this.performTokenRefresh();
        try {
            await this.refreshPromise;
        } finally {
            this.refreshPromise = null;
        }
    }

    private async performTokenRefresh(): Promise<void> {
        try {
            // Try to refresh using httpOnly cookies first, then fallback to stored refresh token
            const response = await axios.post<TokenResponse>(
                `${API_BASE_URL}/api/v1/auth/refresh`,
                this.refreshToken ? { refresh_token: this.refreshToken } : {},
                {
                    withCredentials: true,
                    headers: {
                        'Content-Type': 'application/json',
                    },
                }
            );

            const { access_token, refresh_token } = response.data;
            this.setTokens(access_token, refresh_token);
        } catch (error) {
            this.clearTokens();
            throw error;
        }
    }

    private setTokens(accessToken: string, refreshToken: string) {
        this.accessToken = accessToken;
        this.refreshToken = refreshToken;

        // Store access token in localStorage for persistence across page refreshes
        localStorage.setItem(this.ACCESS_TOKEN_KEY, accessToken);
        // Refresh token is handled via httpOnly cookies
    }

    private clearTokens() {
        this.accessToken = null;
        this.refreshToken = null;

        // Clear access token from localStorage
        localStorage.removeItem(this.ACCESS_TOKEN_KEY);
    }

    // Authentication methods
    async login(credentials: LoginRequest): Promise<ApiSuccessResponse<LoginResponse>> {
        try {
            const response: AxiosResponse<LoginResponse> = await this.api.post('/login', credentials);
            const { access_token, refresh_token } = response.data;
            this.setTokens(access_token, refresh_token);
            return wrapApiResponse<LoginResponse>(response.data);
        } catch (error: any) {
            throw this.handleApiError(error);
        }
    }

    async register(data: RegisterRequest): Promise<ApiSuccessResponse<RegisterResponse>> {
        try {
            const response: AxiosResponse<RegisterResponse> = await this.api.post('/register', data);
            return wrapApiResponse<RegisterResponse>(response.data);
        } catch (error: any) {
            throw this.handleApiError(error);
        }
    }

    async logout(): Promise<ApiSuccessResponse<void>> {
        try {
            const response = await this.api.post('/logout');
            return wrapApiResponse<void>(response.data, 'Logged out successfully');
        } catch (error) {
            // Continue with logout even if API call fails
            console.warn('Logout API call failed:', error);
            return wrapApiResponse<void>(undefined, 'Logged out successfully');
        } finally {
            this.clearTokens();
        }
    }

    async getCurrentUser(): Promise<ApiSuccessResponse<User>> {
        try {
            const response: AxiosResponse<User> = await this.api.get('/me');
            return wrapApiResponse<User>(response.data, 'User profile retrieved successfully');
        } catch (error: any) {
            throw this.handleApiError(error);
        }
    }

    async updateProfile(data: UpdateProfileRequest): Promise<ApiSuccessResponse<User>> {
        try {
            const response: AxiosResponse<User> = await this.api.put('/me', data);
            return wrapApiResponse<User>(response.data, 'Profile updated successfully');
        } catch (error: any) {
            throw this.handleApiError(error);
        }
    }

    async changePassword(data: ChangePasswordRequest): Promise<ApiSuccessResponse<void>> {
        try {
            const response = await this.api.post('/change-password', data);
            return wrapApiResponse<void>(response.data, 'Password changed successfully');
        } catch (error: any) {
            throw this.handleApiError(error);
        }
    }

    async forgotPassword(data: ForgotPasswordRequest): Promise<ApiSuccessResponse<void>> {
        try {
            const response = await this.api.post('/forgot-password', data);
            return wrapApiResponse<void>(response.data, 'Password reset email sent');
        } catch (error: any) {
            throw this.handleApiError(error);
        }
    }

    async resetPassword(data: ResetPasswordRequest): Promise<ApiSuccessResponse<void>> {
        try {
            const response = await this.api.post('/reset-password', data);
            return wrapApiResponse<void>(response.data, 'Password reset successfully');
        } catch (error: any) {
            throw this.handleApiError(error);
        }
    }

    async verifyEmail(token: string): Promise<ApiSuccessResponse<void>> {
        try {
            const response = await this.api.get(`/verify-email?token=${token}`);
            return wrapApiResponse<void>(response.data, 'Email verified successfully');
        } catch (error: any) {
            throw this.handleApiError(error);
        }
    }

    async resendVerification(data: ResendVerificationRequest): Promise<ApiSuccessResponse<void>> {
        try {
            const response = await this.api.post('/resend-verification', data);
            return wrapApiResponse<void>(response.data, 'Verification email resent');
        } catch (error: any) {
            throw this.handleApiError(error);
        }
    }


    // Token management
    getAccessToken(): string | null {
        return this.accessToken;
    }

    isAuthenticated(): boolean {
        return !!this.accessToken;
    }

    // Manual token refresh (for use in auth context)
    async refreshTokens(): Promise<void> {
        await this.refreshAccessToken();
    }

    private handleApiError(error: any): ApiError {
        // 保留原始错误以便组件可以检查状态码
        const apiError: ApiError = {
            detail: 'An unexpected error occurred',
            status_code: 0,
        };

        if (error.response?.data) {
            // 处理嵌套的 detail 对象
            if (typeof error.response.data.detail === 'object' && error.response.data.detail?.message) {
                apiError.detail = error.response.data.detail.message;
            } else if (typeof error.response.data.detail === 'string') {
                apiError.detail = error.response.data.detail;
            } else {
                apiError.detail = 'An error occurred';
            }
            apiError.status_code = error.response.status;
            apiError.retry_after = error.response.data.retry_after;
        } else if (error.request) {
            apiError.detail = 'Network error - please check your connection';
            apiError.status_code = 0;
        } else {
            apiError.detail = error.message || 'An unexpected error occurred';
            apiError.status_code = 0;
        }

        // 将原始错误附加到 ApiError 上，以便组件可以访问响应状态
        (apiError as any).response = error.response;
        
        return apiError;
    }
}

// Export singleton instance
export const authService = new AuthService();
export default authService;