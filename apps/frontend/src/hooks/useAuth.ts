/**
 * useAuth hook for authentication state management
 */

import React from 'react';
import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { authService } from '../services/auth';
import type {
    ApiError,
    AuthState,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    LoginResult,
    OperationResult,
    RegisterRequest,
    RegisterResult,
    ResendVerificationRequest,
    ResetPasswordRequest,
    UpdateProfileRequest,
    UpdateProfileResult,
    User,
} from '../types/auth';

interface AuthStore extends AuthState {
    // Actions - 返回结果对象而不是抛出异常
    login: (credentials: LoginRequest) => Promise<LoginResult>;
    register: (data: RegisterRequest) => Promise<RegisterResult>;
    logout: () => Promise<OperationResult>;
    refreshToken: () => Promise<OperationResult>;
    updateProfile: (data: UpdateProfileRequest) => Promise<UpdateProfileResult>;
    changePassword: (data: ChangePasswordRequest) => Promise<OperationResult>;
    forgotPassword: (data: ForgotPasswordRequest) => Promise<OperationResult>;
    resetPassword: (data: ResetPasswordRequest) => Promise<OperationResult>;
    resendVerification: (data: ResendVerificationRequest) => Promise<OperationResult>;
    verifyEmail: (token: string) => Promise<OperationResult>;
    getCurrentUser: () => Promise<OperationResult>;
    clearError: () => void;
    setLoading: (loading: boolean) => void;
    setError: (error: string | null) => void;
    setUser: (user: User | null) => void;
}

export const useAuthStore = create<AuthStore>()(
    persist(
        (set, get) => ({
            // Initial state
            user: null,
            isAuthenticated: false,
            isLoading: false,
            error: null,

            // Actions
            login: async (credentials: LoginRequest) => {
                set({ isLoading: true, error: null });
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
            },

            register: async (data: RegisterRequest) => {
                set({ isLoading: true, error: null });
                try {
                    const response = await authService.register(data);
                    set({ isLoading: false, error: null });
                    return { success: true, data: response };
                } catch (error) {
                    const apiError = error as ApiError;
                    set({
                        isLoading: false,
                        error: apiError.detail,
                    });
                    return { success: false, error: apiError.detail };
                }
            },

            logout: async () => {
                set({ isLoading: true });
                try {
                    await authService.logout();
                } catch (error) {
                    console.warn('Logout error:', error);
                } finally {
                    set({
                        user: null,
                        isAuthenticated: false,
                        isLoading: false,
                        error: null,
                    });
                }
                return { success: true };
            },

            refreshToken: async () => {
                try {
                    await authService.refreshTokens();
                    // Token refresh doesn't return user data, so we might need to fetch current user
                    const currentUser = await authService.getCurrentUser();
                    set({
                        user: currentUser,
                        isAuthenticated: true,
                        error: null,
                    });
                    return { success: true };
                } catch (error) {
                    set({
                        user: null,
                        isAuthenticated: false,
                        error: 'Session expired. Please login again.',
                    });
                    return { success: false, error: 'Session expired. Please login again.' };
                }
            },

            updateProfile: async (data: UpdateProfileRequest) => {
                set({ isLoading: true, error: null });
                try {
                    const updatedUser = await authService.updateProfile(data);
                    set({
                        user: updatedUser,
                        isLoading: false,
                        error: null,
                    });
                    return { success: true, data: updatedUser };
                } catch (error) {
                    const apiError = error as ApiError;
                    set({
                        isLoading: false,
                        error: apiError.detail,
                    });
                    return { success: false, error: apiError.detail };
                }
            },

            changePassword: async (data: ChangePasswordRequest) => {
                // 不设置全局的 isLoading，避免影响 RequireAuth
                try {
                    await authService.changePassword(data);
                    return { success: true };
                } catch (error) {
                    const apiError = error as ApiError;
                    return { success: false, error: apiError.detail };
                }
            },

            forgotPassword: async (data: ForgotPasswordRequest) => {
                set({ isLoading: true, error: null });
                try {
                    await authService.forgotPassword(data);
                    set({ isLoading: false, error: null });
                    return { success: true };
                } catch (error) {
                    const apiError = error as ApiError;
                    set({
                        isLoading: false,
                        error: apiError.detail,
                    });
                    return { success: false, error: apiError.detail };
                }
            },

            resetPassword: async (data: ResetPasswordRequest) => {
                set({ isLoading: true, error: null });
                try {
                    await authService.resetPassword(data);
                    set({ isLoading: false, error: null });
                    return { success: true };
                } catch (error) {
                    const apiError = error as ApiError;
                    set({
                        isLoading: false,
                        error: apiError.detail,
                    });
                    return { success: false, error: apiError.detail };
                }
            },

            resendVerification: async (data: ResendVerificationRequest) => {
                set({ isLoading: true, error: null });
                try {
                    await authService.resendVerification(data);
                    set({ isLoading: false, error: null });
                    return { success: true };
                } catch (error) {
                    const apiError = error as ApiError;
                    set({
                        isLoading: false,
                        error: apiError.detail,
                    });
                    return { success: false, error: apiError.detail };
                }
            },

            verifyEmail: async (token: string) => {
                set({ isLoading: true, error: null });
                try {
                    await authService.verifyEmail(token);
                    set({ isLoading: false, error: null });
                    // Refresh user data after verification
                    const userResult = await get().getCurrentUser();
                    if (!userResult.success) {
                        // If getting user fails, we still consider verification successful
                        console.warn('Failed to refresh user data after verification');
                    }
                    return { success: true };
                } catch (error) {
                    const apiError = error as ApiError;
                    set({
                        isLoading: false,
                        error: apiError.detail,
                    });
                    return { success: false, error: apiError.detail };
                }
            },

            getCurrentUser: async () => {
                set({ isLoading: true, error: null });
                try {
                    const user = await authService.getCurrentUser();
                    set({
                        user,
                        isAuthenticated: true,
                        isLoading: false,
                        error: null,
                    });
                    return { success: true };
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
            },

            clearError: () => {
                console.log('clearError called - clearing error state');
                set({ error: null });
            },

            setLoading: (loading: boolean) => {
                set({ isLoading: loading });
            },

            setError: (error: string | null) => {
                console.log('setError called with:', error);
                set({ error });
            },

            setUser: (user: User | null) => {
                set({
                    user,
                    isAuthenticated: !!user
                });
            },
        }),
        {
            name: 'auth-storage',
            // Only persist user data, not tokens (for security)
            partialize: (state) => ({
                user: state.user,
                isAuthenticated: state.isAuthenticated,
            }),
        }
    )
);

// Custom hook for easier usage
export const useAuth = () => {
    const store = useAuthStore();

    // Initialize user on app start if token exists
    React.useEffect(() => {
        const initAuth = async () => {
            const hasToken = authService.isAuthenticated();

            if (hasToken && !store.user) {
                // Access token exists but user not in store -> fetch user
                const result = await store.getCurrentUser();
                if (!result.success) {
                    // Token invalid; clear state
                    store.setUser(null);
                }
            } else if (!hasToken && store.user) {
                // No access token but we have a persisted user – try silent refresh first
                const result = await store.refreshToken();
                if (!result.success) {
                    // Refresh failed – clear auth state to force login
                    store.setUser(null);
                }
            }
        };

        initAuth();
    }, [store]);

    return store;
};

export default useAuth;