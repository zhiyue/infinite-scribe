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
    RegisterRequest,
    ResendVerificationRequest,
    ResetPasswordRequest,
    UpdateProfileRequest,
    User,
} from '../types/auth';

interface AuthStore extends AuthState {
    // Actions
    login: (credentials: LoginRequest) => Promise<void>;
    register: (data: RegisterRequest) => Promise<void>;
    logout: () => Promise<void>;
    refreshToken: () => Promise<void>;
    updateProfile: (data: UpdateProfileRequest) => Promise<void>;
    changePassword: (data: ChangePasswordRequest) => Promise<void>;
    forgotPassword: (data: ForgotPasswordRequest) => Promise<void>;
    resetPassword: (data: ResetPasswordRequest) => Promise<void>;
    resendVerification: (data: ResendVerificationRequest) => Promise<void>;
    verifyEmail: (token: string) => Promise<void>;
    getCurrentUser: () => Promise<void>;
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
                try {
                    set({ isLoading: true, error: null });
                    const response = await authService.login(credentials);
                    set({
                        user: response.user,
                        isAuthenticated: true,
                        isLoading: false,
                        error: null,
                    });
                } catch (error) {
                    const apiError = error as ApiError;
                    set({
                        user: null,
                        isAuthenticated: false,
                        isLoading: false,
                        error: apiError.detail,
                    });
                    throw error;
                }
            },

            register: async (data: RegisterRequest) => {
                try {
                    set({ isLoading: true, error: null });
                    await authService.register(data);
                    set({ isLoading: false, error: null });
                } catch (error) {
                    const apiError = error as ApiError;
                    set({
                        isLoading: false,
                        error: apiError.detail,
                    });
                    throw error;
                }
            },

            logout: async () => {
                try {
                    set({ isLoading: true });
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
                } catch (error) {
                    set({
                        user: null,
                        isAuthenticated: false,
                        error: 'Session expired. Please login again.',
                    });
                    throw error;
                }
            },

            updateProfile: async (data: UpdateProfileRequest) => {
                try {
                    set({ isLoading: true, error: null });
                    const updatedUser = await authService.updateProfile(data);
                    set({
                        user: updatedUser,
                        isLoading: false,
                        error: null,
                    });
                } catch (error) {
                    const apiError = error as ApiError;
                    set({
                        isLoading: false,
                        error: apiError.detail,
                    });
                    throw error;
                }
            },

            changePassword: async (data: ChangePasswordRequest) => {
                try {
                    set({ isLoading: true, error: null });
                    await authService.changePassword(data);
                    set({ isLoading: false, error: null });
                } catch (error) {
                    const apiError = error as ApiError;
                    set({
                        isLoading: false,
                        error: apiError.detail,
                    });
                    throw error;
                }
            },

            forgotPassword: async (data: ForgotPasswordRequest) => {
                try {
                    set({ isLoading: true, error: null });
                    await authService.forgotPassword(data);
                    set({ isLoading: false, error: null });
                } catch (error) {
                    const apiError = error as ApiError;
                    set({
                        isLoading: false,
                        error: apiError.detail,
                    });
                    throw error;
                }
            },

            resetPassword: async (data: ResetPasswordRequest) => {
                try {
                    set({ isLoading: true, error: null });
                    await authService.resetPassword(data);
                    set({ isLoading: false, error: null });
                } catch (error) {
                    const apiError = error as ApiError;
                    set({
                        isLoading: false,
                        error: apiError.detail,
                    });
                    throw error;
                }
            },

            resendVerification: async (data: ResendVerificationRequest) => {
                try {
                    set({ isLoading: true, error: null });
                    await authService.resendVerification(data);
                    set({ isLoading: false, error: null });
                } catch (error) {
                    const apiError = error as ApiError;
                    set({
                        isLoading: false,
                        error: apiError.detail,
                    });
                    throw error;
                }
            },

            verifyEmail: async (token: string) => {
                try {
                    set({ isLoading: true, error: null });
                    await authService.verifyEmail(token);
                    set({ isLoading: false, error: null });
                    // Refresh user data after verification
                    await get().getCurrentUser();
                } catch (error) {
                    const apiError = error as ApiError;
                    set({
                        isLoading: false,
                        error: apiError.detail,
                    });
                    throw error;
                }
            },

            getCurrentUser: async () => {
                try {
                    set({ isLoading: true, error: null });
                    const user = await authService.getCurrentUser();
                    set({
                        user,
                        isAuthenticated: true,
                        isLoading: false,
                        error: null,
                    });
                } catch (error) {
                    const apiError = error as ApiError;
                    set({
                        user: null,
                        isAuthenticated: false,
                        isLoading: false,
                        error: apiError.detail,
                    });
                    throw error;
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
            if (authService.isAuthenticated() && !store.user) {
                try {
                    await store.getCurrentUser();
                } catch (error) {
                    // Token might be expired, clear auth state
                    store.setUser(null);
                }
            }
        };

        initAuth();
    }, [store]);

    return store;
};

export default useAuth;