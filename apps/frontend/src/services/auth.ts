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
    PasswordValidationResponse,
    RegisterRequest,
    RegisterResponse,
    ResendVerificationRequest,
    ResetPasswordRequest,
    TokenResponse,
    UpdateProfileRequest,
    User,
    ValidatePasswordRequest,
} from '../types/auth';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

class AuthService {
    private api: AxiosInstance;
    private accessToken: string | null = null;
    private refreshToken: string | null = null;
    private refreshPromise: Promise<void> | null = null;

    constructor() {
        this.api = axios.create({
            baseURL: `${API_BASE_URL}/api/v1/auth`,
            headers: {
                'Content-Type': 'application/json',
            },
            withCredentials: true, // For httpOnly cookies
        });

        this.setupInterceptors();
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

                if (error.response?.status === 401 && !originalRequest._retry) {
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
            const response = await axios.post<TokenResponse>(
                `${API_BASE_URL}/api/v1/auth/refresh`,
                {},
                {
                    withCredentials: true,
                    headers: {
                        Authorization: this.refreshToken ? `Bearer ${this.refreshToken}` : undefined,
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

        // Store in memory only for security
        // Refresh token is handled via httpOnly cookies
    }

    private clearTokens() {
        this.accessToken = null;
        this.refreshToken = null;
    }

    // Authentication methods
    async login(credentials: LoginRequest): Promise<LoginResponse> {
        try {
            const response: AxiosResponse<LoginResponse> = await this.api.post('/login', credentials);
            const { access_token, refresh_token } = response.data;
            this.setTokens(access_token, refresh_token);
            return response.data;
        } catch (error: any) {
            throw this.handleApiError(error);
        }
    }

    async register(data: RegisterRequest): Promise<RegisterResponse> {
        try {
            const response: AxiosResponse<RegisterResponse> = await this.api.post('/register', data);
            return response.data;
        } catch (error: any) {
            throw this.handleApiError(error);
        }
    }

    async logout(): Promise<void> {
        try {
            await this.api.post('/logout');
        } catch (error) {
            // Continue with logout even if API call fails
            console.warn('Logout API call failed:', error);
        } finally {
            this.clearTokens();
        }
    }

    async getCurrentUser(): Promise<User> {
        try {
            const response: AxiosResponse<User> = await this.api.get('/me');
            return response.data;
        } catch (error: any) {
            throw this.handleApiError(error);
        }
    }

    async updateProfile(data: UpdateProfileRequest): Promise<User> {
        try {
            const response: AxiosResponse<User> = await this.api.put('/me', data);
            return response.data;
        } catch (error: any) {
            throw this.handleApiError(error);
        }
    }

    async changePassword(data: ChangePasswordRequest): Promise<void> {
        try {
            await this.api.post('/change-password', data);
        } catch (error: any) {
            throw this.handleApiError(error);
        }
    }

    async forgotPassword(data: ForgotPasswordRequest): Promise<void> {
        try {
            await this.api.post('/forgot-password', data);
        } catch (error: any) {
            throw this.handleApiError(error);
        }
    }

    async resetPassword(data: ResetPasswordRequest): Promise<void> {
        try {
            await this.api.post('/reset-password', data);
        } catch (error: any) {
            throw this.handleApiError(error);
        }
    }

    async verifyEmail(token: string): Promise<void> {
        try {
            await this.api.get(`/verify-email?token=${token}`);
        } catch (error: any) {
            throw this.handleApiError(error);
        }
    }

    async resendVerification(data: ResendVerificationRequest): Promise<void> {
        try {
            await this.api.post('/resend-verification', data);
        } catch (error: any) {
            throw this.handleApiError(error);
        }
    }

    async validatePassword(data: ValidatePasswordRequest): Promise<PasswordValidationResponse> {
        try {
            const response: AxiosResponse<PasswordValidationResponse> = await this.api.post('/validate-password', data);
            return response.data;
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
        if (error.response?.data) {
            return {
                detail: error.response.data.detail || 'An error occurred',
                status_code: error.response.status,
                retry_after: error.response.data.retry_after,
            };
        }

        if (error.request) {
            return {
                detail: 'Network error - please check your connection',
                status_code: 0,
            };
        }

        return {
            detail: error.message || 'An unexpected error occurred',
            status_code: 0,
        };
    }
}

// Export singleton instance
export const authService = new AuthService();
export default authService;